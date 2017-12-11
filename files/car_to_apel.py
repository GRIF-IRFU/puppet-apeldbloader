#!/usr/bin/python
#
# This sends the ARC CAR accounting reports into a python dirqueue (this needs python-dirq),
# which then allows the apel dbloader to process this dirqueue directly and send the records
# into an apel accounting database, into the JobRecords table
#
# CAR accounting records are then TAR-archived into a subfolder, and failed records moved
# as is into another "failed" subfolder, so that nothing's lost in the process.
#
# A-REX job log files are deleted once processed from the jobcontroldir/logs directory, so that no record is duplicated on subsequent jura runs and archiving. 
#
# Copyright : F.SCHAER

from dirq.queue import Queue
import os
import xml.dom.minidom
import re
import datetime
import tarfile
import shutil
import ConfigParser
import logging
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',level=logging.INFO)

def dequote(s):
    """
    If a string has single or double quotes around it, remove them.
    Make sure the pair of quotes match.
    If a matching pair of quotes is not found, return the string unchanged.
    """
    if (s[0] == s[-1]) and s.startswith(("'", '"')):
        return s[1:-1]
    return s

def cleanuplog(filename,logsdir):
    """
    removes an A-REX job logfile from the controldir/logs
    Makes sure the given filename does not contain neither usagerecordCAR. nor usagerecord. in its name
    archive xml name (filename) is like this : usagerecordCAR.zZPLDmVo8knnAaRUDnyGx30mABFKDmABFKDmvhnNDmABFKDmYWpeXn.CSMCCY
    """
    newname=filename.replace('usagerecord','').replace('CAR.','')
    try:
        os.remove(logsdir+'/'+newname)
    except OSError:
        logging.error('Could not remove the A-REX job log file ' +logsdir+'/'+newname+ ': this may lead to infinite file republication !')
    return 0


#def fixNS(x):
#  for i in x.childNodes:
#        fixNS(i)
#  if x.nodeType == x.ELEMENT_NODE:
#      x.setAttribute("xmlns", "http://eu-emi.eu/namespaces/2012/11/computerecord")
QSCHEMA = {"body": "string", "signer":"string", "empaid":"string?", "error": "string?"}
previousDir = os.getcwd()

# FIRST : get the ARC archives directory
ARC_config='/etc/arc.conf'
arcdir=None
controldir=None
ARC_archives_section='grid-manager'
ARC_archives_option='jobreport_options'
ARC_archives_suoption='archiving'
# And the controldir location (used to cleanup <controldir>/logs/<job log file> once processed
ARC_controldir_section='grid-manager'
ARC_controldir_option='controldir'

config = ConfigParser.ConfigParser()
config.read(ARC_config)

if config.has_section(ARC_archives_section) and config.has_option(ARC_archives_section, ARC_archives_option):
    jobreport_opts=config.get(ARC_archives_section, ARC_archives_option).split(',')
    for opt,val in [ i.split(':') for i in jobreport_opts ]:
        if opt==ARC_archives_suoption:
            arcdir=val

if config.has_section(ARC_controldir_section) and config.has_option(ARC_controldir_section, ARC_controldir_option):
    controldir=dequote(config.get(ARC_controldir_section, ARC_controldir_option))

if not arcdir:
    logging.error("ARC " + ARC_archives_option + " option in " + ARC_archives_section + " section of "+ARC_config+" does not seem to contain an archiving dir suboption : cannot parse that dir for apel. exiting.")
    exit(2)

if not controldir:
    logging.error("ARC " + ARC_controldir_option + " option in " + ARC_controldir_section + " section of "+ARC_config+" does not seem to contain an archiving dir suboption : cannot parse that dir for apel. exiting.")
    exit(2)

joblogsdir=controldir + "/logs"
logging.info("Processing ARC archives in " + arcdir + "...")
logging.info("Will remove ARC job log files in " + joblogsdir + "...")

if not os.path.isdir(joblogsdir):
    logging.error("ARC joblogs dir '" + joblogsdir + "' does not seem to exist ?! Will not continue as cleanup is essential to not duplicate the CAR archives (and fill the disks)")
    exit(2)

# init directories and filenames
archives=os.path.join(arcdir,"archives")
failures=os.path.join(archives,'failed')
tarfileN=os.path.join(archives,str(datetime.datetime.now().strftime("%Y-%m-%d.tar")))

# Then : cleanup previous runs already emptied by the apeldbloader
for root, dirs, files in os.walk(arcdir,topdown=False):
     for name in dirs:
         fname = os.path.join(root,name)
         if re.compile('[0-9]{8,8}').match(name) and not os.listdir(fname): #to check wither the dir is empty and of the form 01234567 (the dirq tmp dirs)
             logging.info("removing emtpty dir " + fname)
             os.removedirs(fname)

#then, make sure we don't remove CAR records, just archive them
if not os.path.isdir(archives):
    os.mkdir(archives)
if not os.path.isdir(failures):
    os.mkdir(failures)

#init structures and archive file, chdir
dirq = Queue(arcdir, schema=QSCHEMA)
tarball = tarfile.open(tarfileN,mode='a:')
tarmembers = tarball.getnames()
processed=0

try:
  os.chdir(arcdir)
  #create the incoming dir pointing lo cwd, so that apeldbloader is happy
  if not os.path.isdir('incoming'):
    os.symlink('.','incoming')
  #process CAR xml records
  for filename in os.listdir('.'):
      if filename.startswith("usagerecordCAR"):
          doc=xml.dom.minidom.parse(filename)
          #fixNS(doc)
          for node in doc.childNodes:
            node.setAttribute("xmlns", "http://eu-emi.eu/namespaces/2012/11/computerecord")
          #fix vo-group/role apel stuff

          #create tag without the vo- prefix, for apel, and for this, clone the node
          for node in doc.getElementsByTagName('GroupAttribute'):
            if node.hasAttribute('urf:type') and (node.getAttribute('urf:type')=='vo-group' or node.getAttribute('urf:type')=='vo-role'):
              n=node.cloneNode(deep=True)
              n.setAttribute('urf:type',node.getAttribute('urf:type')[3:])
              node.parentNode.appendChild(n)

          #doc.firstChild.setAttribute("xmlns", "http://eu-emi.eu/namespaces/2012/11/computerecord")
          dirq.add({"body"  : doc.toxml(),
                 "signer": "ARCtoAPEL",
                 "empaid": "unknown"
                 })
          if filename not in tarmembers:
            logging.debug('adding ' + filename + ' to ' + tarfileN)
            tarball.add(filename) #add file to archive
            cleanuplog(filename,joblogsdir) #remove the A-REX file that was used to create the CAR archive
            os.remove(filename)   #remove CAR file that was just archived, so that it's not added again in the dirq next time we run
          else:
            logging.warning("file " + filename + " already in archive " + tarfileN + " : something might be going wrong. Moving it in archives/failed")
            try:
                shutil.move(filename,failures)
                cleanuplog(filename,joblogsdir) #remove the A-REX file that was used to create the CAR archive
            except shutil.Error as why:
                logging.error("error while moving " + arcdir + '/' + filename + " : " + str(why))
                logging.error("removing " + arcdir + '/' + filename )
                try:
                    os.remove(filename)
                except OSError:
                    pass
          #mark record as processed
          processed+=1

      #not interested in non-CAR records pilling up
      if filename.startswith("usagerecord."):
          try:
              os.remove(filename)
          except OSError:
              pass

finally:
    numrecords=len(tarball.getnames());
    tarball.close()
    os.chdir(previousDir)
    print "processed %d records." % processed
    logging.debug("number of tarball members : " + str(numrecords))
    if numrecords==0 and processed==0:
        logging.info('did not process any record, and tarball is empty : removing it to avoid a python bug.')
        os.remove(tarfileN)

exit(0)
