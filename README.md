puppet-apeldbloader
===================

A puppet module to configure the apeldbloader part of the EMI/UMD apel-server

Usage :

    class { apeldbloader :
      #DB params
      db_name=>hiera('apelparser::config::mysql_database'),
      db_user=>hiera('apelparser::config::mysql_user'),
      db_hostname=>hiera('apelparser::config::mysql_hostname'),
      db_pass=>hiera('apelparser::config::mysql_password'),
  
      #loader params
      save_messages => true,
    }
    ->
    class {apeldbloader::car_to_apel: }
