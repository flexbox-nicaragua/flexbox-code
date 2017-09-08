#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import time
from multiprocessing import Process
from datetime import datetime
import os
from flexbox import zwave
from flexbox import psql

DEVICE = '/dev/zwave'
TIMEOUT = 1800
CONFIG_PATH = '/etc/flexbox'

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)
print 'Starting ZWAVE at ' + str(datetime.now())

class myThread(Process):
    def __init__(self):
        Process.__init__(self)

    def run(self):
        loop_wait = 1
        min_diff = 0.01
        heartbeat = 60
        print 'Initializing Zwave Network'
        network = zwave.init_zwave(DEVICE, CONFIG_PATH)
        print 'Waiting...'
        time.sleep(5.0)
        recorded_output_dict = {}
        different = True
        time1 = datetime.now()
        while True:
            time.sleep(loop_wait)
            output_dict = zwave.read_zwave(network)
            time_diff = (datetime.now() - time1).seconds
            if recorded_output_dict and output_dict:
                if 'houseAll_Current' in output_dict:
                    diff_current = abs(output_dict['houseAll_Current']-recorded_output_dict['houseAll_Current'])
                    different = diff_current > min_diff
                else:
                    print str(datetime.now())+' ERROR: Zwave dictionary not correct. it seems to have only these keys:' + str(output_dict.keys())
            if time_diff < 0:
                time1 = datetime.now()
                print datetime.now()+' ERROR: Improper time at: ' + time1
            elif output_dict and (different or time_diff > heartbeat):
                psql.add_values_to_table(table_dict['zwave_table'],output_dict)
                recorded_output_dict = output_dict
                time1 = datetime.now()
            if output_dict and output_dict['house1_Energy'] == 0:
                print 'Zero Energy, Restarting: '+str(datetime.now())
                return

while True:
    p = myThread()
    p.start()
    print "Main thread PID:",os.getpid()
    print "Launched process PID:",p.pid
    p.join(TIMEOUT)
    if p.is_alive:
        p.terminate()
