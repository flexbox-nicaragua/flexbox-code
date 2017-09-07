#!/bin/bash
nohup sudo python -u /home/pi/flexbox/scripts/send_scripts/send_single_heartbeat.py &>> /var/log/flexbox/heartbeat.out&
