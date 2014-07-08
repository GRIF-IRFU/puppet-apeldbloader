#!/bin/sh
# Startup script for apeldbloader
#
# chkconfig: - 95 05
# description: Run the apeldbloader as a daemon
# pidfile: /var/run/apel/loader.pid
#
# Source function library.
. /etc/rc.d/init.d/functions

user="root"
prog="apeldbloader"
PIDFILE=/var/run/apel/loader.pid

start() {
    echo -n $"Starting $prog: "
    su $user -c $prog
    RETVAL=$?
    if [ $RETVAL -ne 0 ]; then
        failure;
    else
        success;
    fi;
    echo
    return $RETVAL
}

stop() {
    echo -n $"Stopping $prog: "
    if [ -f $PIDFILE ]; then
        kill `cat $PIDFILE`
        RETVAL=$?
        if [ $RETVAL -ne 0 ]; then
            failure;
        else
            success;
        fi;
    else
        RETVAL=1
        failure;
    fi
    echo
    return $RETVAL
}


case "$1" in
        start)
            start
            ;;

        stop)
            stop
            ;;

        status)
            status -p $PIDFILE $prog
            ;;

        restart)
            stop
            start
            ;;

        reload)
            stop
            start
            ;;

        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1

esac

exit $RETVAL