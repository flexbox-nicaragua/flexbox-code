#!/usr/bin/env python2
import time
from flexbox import sensors
from flexbox import psql
from datetime import datetime

LOOP_WAIT = 0.1
MIN_DIFF = 0.15
HEARTBEAT = 60

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)
time1 = datetime.now()
print 'Starting Ambient at ' + str(time1)
recorded_output_dict = {}
while True:
    time.sleep(LOOP_WAIT)
    output_dict = {}
    time_diff = (datetime.now() - time1).seconds
    [temperature,humidity] = sensors.get_ambient_temp_humidity()
    if temperature is not None and humidity is not None:
        output_dict['ambient_temp'] = temperature
        output_dict['humidity'] = humidity
        if recorded_output_dict:
            diff_temp = abs(output_dict['ambient_temp'] - recorded_output_dict['ambient_temp'])
            diff_hum = abs(output_dict['humidity'] - recorded_output_dict['humidity'])
            difference = diff_temp > MIN_DIFF or diff_hum > MIN_DIFF
        else:
            difference = True
        if difference or time_diff > HEARTBEAT:
            psql.add_values_to_table(table_dict['ambient_table'],output_dict)
            recorded_output_dict = output_dict
            time1 = datetime.now()
