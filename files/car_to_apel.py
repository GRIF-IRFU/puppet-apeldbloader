#!/usr/bin/python
#
# This sends the ARC CAR accounting reports into a python dirqueue (this needs python-dirq),
# which then allows the apel dbloader to process this dirqueue directly and send the records
# into an apel accounting database, into the JobRecords table
#
# CAR accounting records are then TAR-archived into a subfolder, and failed records moved
# as is into another "failed" subfolder, so that nothing's lost in the process.
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
ARC_archives_section='grid-manager'
ARC_archives_option='jobreport_options'
ARC_archives_suoption='archiving'

config = ConfigParser.ConfigParser()
config.read(ARC_config)

if config.has_section(ARC_archives_section) and config.has_option(ARC_archives_section, ARC_archives_option):
    jobreport_opts=config.get(ARC_archives_section, ARC_archives_option).split(',')
    for opt,val in [ i.split(':') for i in jobreport_opts ]:
        if opt==ARC_archives_suoption:
            arcdir=val

if not arcdir:
    logging.error("ARC " + ARC_archives_option + " option in " + ARC_archives_section + " section of "+ARC_config+" does not seem to contain an archiving dir suboption : cannot parse that dir for apel. exiting.")
    exit(2)

logging.info("Processing ARC archives in " + arcdir + "...")

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
            os.remove(filename)   #remove CAR file that was just archived, so that it's not added again in the dirq next time we run
          else:
            logging.warnging("file " + filename + " already in archive " + tarfileN + " : something might be going wrong. Moving it in archives/failed")
            shutil.move(filename,failures)
          #mark record as processed
          processed+=1
finally:
    numrecords=len(tarball.getnames());
    tarball.close()
    os.chdir(previousDir)
    logging.debug("number of tarball members : " + str(numrecords))
    if numrecords==0 and processed==0:
        logging.info('did not process any record, and tarball is empty : removing it to avoid a python bug.')
        os.remove(tarfileN)

exit(0)
