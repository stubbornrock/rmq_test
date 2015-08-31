#!/bin/bash
#
# Author:shuai
#
cd "$(dirname "$0")"

file_name=".rab.auth"
if [ -f $file_name ]; then 
    source ./$file_name
else
    echo "$file_name is Not Exist !"
    exit 1
fi 
./api2.py --username=$USERNAME --password=$PASSWORD --hostname=$HOSTNAME --check=list_whole_sys_items --conf=$CONF
