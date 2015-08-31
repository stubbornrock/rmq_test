#!/bin/bash
#
# https://github.com/jasonmcintosh/rabbitmq-zabbix
#
cd "$(dirname "$0")"

file_name=".rab.auth"
if [ -f $file_name ]; then 
    source ./$file_name
else
    echo "$file_name is Not Exist !"
    exit 1
fi
 
#FILTER=$1
# For example, 
# FILTER='{"durable": true}'
# FILTER='{"durable": true, "vhost": "mine"}'
# FILTER='[{"name": "mytestqueuename"}, {"name": "queue2"}]'

if [[ -z "$1" ]]; then
    ./api2.py --username=$USERNAME --password=$PASSWORD --hostname=$HOSTNAME --check=list_queues --conf=$CONF
else
    FILTER=$1
    ./api2.py --username=$USERNAME --password=$PASSWORD --hostname=$HOSTNAME --check=list_queues --filter="$FILTER" --conf=$CONF
fi



