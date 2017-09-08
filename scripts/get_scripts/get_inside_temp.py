#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flexbox import sensors
from flexbox import psql
from Queue import Queue
from threading import Thread
import time
from datetime import datetime
import yaml

with open('/etc/flexbox/temp_assign.yaml') as f:
        cf = yaml.safe_load(f)
print 'Starting inside temps at ' + str(datetime.now())
# Set up some global variables
queue = Queue()
NUM_FETCH_THREADS = 4
LOOP_WAIT = 0.25
MIN_DIFF = 250.0
HEARTBEAT = 60
vals = {}
sens_ids = []

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)

def downloadEnclosures(i, q):
    """This is the worker thread function.
    It processes items in the queue one after
    another.  These daemon threads go into an
    infinite loop, and only exit when
    the main thread ends.
    """
    while True:
        sens_id = q.get()
        if sens_id:
            vals[sens_id] = sensors.get_inside_fridge_temp(sens_id)
        q.task_done()


# Set up some threads to fetch the enclosures
for i in range(NUM_FETCH_THREADS):
    worker = Thread(target=downloadEnclosures, args=(i, queue,))
    worker.setDaemon(True)
    worker.start()

# Download the feed(s) and put the enclosure URLs into
# the queue.
recorded_output_dict = {}
time1 = datetime.now()
while True:
    time.sleep(LOOP_WAIT)
    if queue.empty():
        output_dict = {}
        diff_dict = {}
        different = False
        time_diff = (datetime.now() - time1).seconds
        if len(vals)>4:
            print vals
        for i,key in enumerate(vals):
            if vals[key] != None:
                print cf
                output_dict['inside_'+cf[key]] = vals[key]
        if output_dict and recorded_output_dict and \
                output_dict.keys() == recorded_output_dict.keys():
            diff_dict = {key : output_dict[key] - recorded_output_dict.get(key,0) for key in output_dict.keys()}
            different = True in [abs(x)>120 for x in diff_dict.values()]
        else:
            different = True
        if output_dict and (different or time_diff>HEARTBEAT):
            psql.add_values_to_table(table_dict['inside_table'],output_dict)
            recorded_output_dict = output_dict
            time1 = datetime.now()
	    print output_dict
        sens_ids = sensors.get_inside_fridge_ids()
        for sens_id in sens_ids:
            queue.put(sens_id)
# Now wait for the queue to be empty, indicating that we have
# processed all of the downloads.
queue.join()
print '*** Done'
