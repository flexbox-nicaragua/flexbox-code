#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import pandas as pd
import os
from pandas.tools.plotting import scatter_matrix
from datetime import date, datetime, timedelta
import copy
import numpy as np
import os.path
import re
import random
from sqlalchemy import cast,Date,text
import json
from flexbox import psql_server


json_dict = {}
peak_shifting_dict = {}
## Importing Data

metadata = psql_server.get_metadata()
table_dict = psql_server.setup_tables(metadata)

this_datetime = datetime.now()


signal_table_peak_shifting = table_dict['peak_shifting_dr_table'].select().\
        where(cast(table_dict['peak_shifting_dr_table'].c.datetime,Date) == \
        this_datetime.date()).\
        where(table_dict['peak_shifting_dr_table'].c.signal == 1).\
        order_by(table_dict['peak_shifting_dr_table'].c.datetime.asc())\
        .execute().fetchone()

if signal_table_peak_shifting and len(signal_table_peak_shifting)>0:
    peak_start = signal_table_peak_shifting[0]
    peak_end = peak_start+timedelta(minutes=signal_table_peak_shifting[4])
    print peak_start
    print peak_end
    if this_datetime>=peak_start and this_datetime<=peak_end:
        peak_shifting_dict['start_time'] = \
            signal_table_peak_shifting[0].strftime('%Y-%m-%d %H:%M:%S')
        peak_shifting_dict['duration_minutes'] = signal_table_peak_shifting[4]

json_dict['peak_shifting_event'] = peak_shifting_dict
print json_dict
with open("../web/signals_time.json","wb") as outfile:
    json.dump(json_dict,outfile,indent=4)



