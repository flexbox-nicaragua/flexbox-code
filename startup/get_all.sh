#!/bin/bash
echo 'Starting Data Logging'
FLEXPATH=/home/pi/flexbox/scripts/get_scripts
LOGPATH=/var/log/flexbox
sudo mkdir -p /var/log/flexbox
nohup python -u $FLEXPATH/get_inside_temp.py &>> $LOGPATH/temp.out&
nohup python -u $FLEXPATH/get_switch.py &>> $LOGPATH/switch.out&
nohup sudo python -u $FLEXPATH/get_ambient.py &>> $LOGPATH/ambient.out&
nohup python -u $FLEXPATH/get_zwave.py &>> $LOGPATH/zwave.out&
nohup python -u $FLEXPATH/get_mfi.py &>> $LOGPATH/mfi.out&
nohup sudo python -u /home/pi/flexbox/scripts/send_scripts/network_test.py &>> $LOGPATH/network_test.out&
echo "Everything is loaded. Look in ${LOGPATH} for any issues."

