#!/usr/bin/env python2
from multiprocessing import Process
import os,time
from datetime import datetime

from flexbox import mfi
from flexbox import psql

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)
TIMEOUT = 3600
print('Starting MFI at {}'.format(str(datetime.now())))
class myThread(Process):
    def __init__(self):
        Process.__init__(self)

    def run(self):
        loop_wait = 0.2
        min_diff = 0.01
        heartbeat = 60
        # mfi_IPs = ['10.10.10.101','10.10.10.100']
        mfi_IPs = ['10.10.10.101']
        good_ip = mfi_IPs[0]
        time1 = datetime.now()
        recorded_output_dict = {}
        different = True
        while True:
            time.sleep(loop_wait)
            output_dict = mfi.get_mfi_data(good_ip,time1,180000000)
            if output_dict is None:
                rot = mfi_IPs.pop(0)
                mfi_IPs.append(rot)
                good_ip = mfi_IPs[0]
            time_diff = (datetime.now() - time1).seconds
            if output_dict and recorded_output_dict:
                diff_1 = abs(recorded_output_dict['i_rms1']-output_dict['i_rms1'])
                diff_2 = abs(recorded_output_dict['i_rms2']-output_dict['i_rms2'])
                diff_3 = abs(recorded_output_dict['i_rms3']-output_dict['i_rms3'])
                different = (diff_1>min_diff) or (diff_2>min_diff) or (diff_3>min_diff)
            if output_dict and (different or time_diff>heartbeat):
                print output_dict
                psql.add_values_to_table(table_dict['mfi_table'],output_dict)
                recorded_output_dict = output_dict
                time1 = datetime.now()

while True:
    p = myThread()
    p.start()
    print("Main thread PID: {}".format(os.getpid()))
    print("Launched process PID: {}".format(p.pid))
    p.join(TIMEOUT)
    if p.is_alive:
        p.terminate()
