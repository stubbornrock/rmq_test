#!/bin/bash
#
# https://github.com/jasonmcintosh/rabbitmq-zabbix
#
#UserParameter=rabbitmq[*],<%= zabbix_script_dir %>/rabbitmq-status.sh
cd "$(dirname "$0")"

file_name=".rab.auth"
if [ -f $file_name ]; then
    source ./$file_name
else
    echo "$file_name is Not Exist !"
    exit 1
fi

if [[ ! -z "$1" ]]; then
    TYPE_OF_CHECK=$1
    if [[ "$TYPE_OF_CHECK" == "check_queue" ]];then
        if [[ ! -z "$2" ]];then
            FILTER=$2
            ./api2.py --hostname=$HOSTNAME --username=$USERNAME --password=$PASSWORD --check=$TYPE_OF_CHECK --filters="$FILTER" --conf=$CONF
            exit 0
        fi
    fi
fi
./api2.py --hostname=$HOSTNAME --username=$USERNAME --password=$PASSWORD --check=$TYPE_OF_CHECK --conf=$CONF
