class apeldbloader::db(
  $db_name,
  $db_user,
  $db_hostname,
  $db_pass,
  $db_backend,
  $db_port,
  $records_per_query,
  $db_template = 'apeldbloader/db.cfg', #this is the template used to create the db config. Can be overridden.
) {
  
  #configure the DB part
  Package ['apel-server']
  ->
  file {'/etc/apel/db.cfg':
    owner=>root,
    group=>root,
    mode => 640,
    content=>template($db_template)
  }

}
