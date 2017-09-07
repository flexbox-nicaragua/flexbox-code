#!/usr/bin/env python2
import time
from flexbox import sensors
from flexbox import psql
from datetime import datetime

LOOP_WAIT = 0.25
HEARTBEAT = 60

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)
print 'Starting Switch at ' + str(datetime.now())
recorded_output_dict = None
time1 = datetime.now()

while True:
    time.sleep(LOOP_WAIT)
    isOpen = sensors.get_magnetic_switch()
    time_diff = (datetime.now()-time1).seconds
    if isOpen is not None:
        if recorded_output_dict is None or isOpen != recorded_output_dict['switch'] or time_diff > HEARTBEAT:
            output_dict = {'switch':isOpen}
            psql.add_values_to_table(table_dict['switch_table'],output_dict)
            recorded_output_dict = output_dict
            time1 = datetime.now()
