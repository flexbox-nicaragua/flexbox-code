#!/bin/bash
LOGPATH=/var/log/flexbox

while true
do
    echo 'Starting Flask'
    python -u /home/pi/flexbox/web/endpoints.py >> $LOGPATH/flask.out
done

