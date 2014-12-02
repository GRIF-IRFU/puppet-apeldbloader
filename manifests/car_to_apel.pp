/**
 * This is a helper program, that will transform and fix the ARC accounting records so that the apeldbloader is happy with them.
 * 
 * It adds a Namespace which is apparently not found or correctly parsed by the apeldbloader
 * It copies xml GroupAttribute nodes and changes the "vo-role" and "vo-group" attributes to "role"/"group", so that apel is happy (the ARC CE seems to follow the CAR format)
 * 
 * If you're not sure things are working correctly, launch something like this with apeldbloader loglevel set to debug :
 * 
 * #maybe add a rm -rf archives/failed/
 * ( cd /var/run/arc/urs ;  /usr/local/bin/car_to_apel.py ; apeldbloader ; sleep 2 ; pkill -f apeldbloader ; less /var/log/apel/loader.log ) 2>&1 |less
 * 
 */
class apeldbloader::car_to_apel(
  $run_interval = 30, #time interval in minutes
){
  $prog='car_to_apel.py'
  
  package{'python-dirq':}
  ->
  file { $prog:
    path=> "/usr/local/sbin/${prog}",
    mode => 755,
    owner => root,
    source => 'puppet:///modules/apeldbloader/car_to_apel.py',
  }

  cron { 'car_to_apel':
    ensure  => present,
    command => "/usr/local/sbin/${prog} >> /var/log/car_to_apel.log 2>&1",
    user    => 'root',
    minute  => "*/${run_interval}",
    require => File[$prog],
  }
}
