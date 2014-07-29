/**
 * This configures the apeldbloader part of the apel-server component. 
 */
class apeldbloader(
  
  #DB params
  $db_name='accounting',
  $db_user='accounting',
  $db_hostname='changeme',
  $db_pass='changeme',
  $db_backend='mysql',
  $db_port=3306,
  $records_per_query=1000,
  $db_template = 'apeldbloader/db.erb', #this is the template used to create the db config. Can be overridden.
  
  #loader params
  $msgpath = '/var/spool/apel',
  $arc_car_recordsdir = '/var/run/arc/urs',
  $interval = 60,
  $save_messages = true,
  $log_level = 'INFO',
  $loader_template = 'apeldbloader/loader.erb'

) {
  
  package {'apel-server':}
  
  #configure the DB part
  class { apeldbloader::db : 
    db_name=>$db_name,
    db_user => $db_user,
    db_hostname => $db_hostname,
    db_pass => $db_pass,
    db_backend => $db_backend,
    db_port => $db_port,
    records_per_query => $records_per_query,
    db_template => $db_template 
  }
  
  #dbloader hacking directories.
  #we use the loader, and provide it directly with its data structure :
  file {
    "$msgpath": ensure=>directory, owner=>root, group=>root;
    "$arc_car_recordsdir": ensure=>directory, owner=>root, group=>root;
    "$msgpath/incoming": ensure=>link, target => $arc_car_recordsdir, owner=>root, group=>root;
  }
  
  #dbloader config
  file {'/etc/apel/loader.cfg':
    mode => 644,
    owner =>root,
    content => template($loader_template),
    require => Package['apel-server'],
    notify => Service[apeldbloader]
  }
  
  
  #create an init script so that the apeldbloader can be managed as a service, since it spawns itself as a daemon
  file { '/etc/init.d/apeldbloader':
    owner => root,
    group => root,
    mode => 755,
    source => 'puppet:///modules/apeldbloader/loader.init.sh'
  }
  
  service{'apeldbloader':
    ensure=>running,
    hasstatus=>true,
    require => File['/etc/init.d/apeldbloader','/etc/apel/loader.cfg','/etc/apel/db.cfg'],
  }

  #service
}
