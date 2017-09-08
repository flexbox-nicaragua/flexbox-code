# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flexbox import analysis_tools as at
from datetime import datetime,timedelta
import os
import os.path

days=0
today = (datetime.now()-timedelta(days=days)).date()
directory = 'static/images/'+today.strftime('%Y-%m-%d')+'/'
if not os.path.exists(directory):
    os.makedirs(directory)
at.read_and_plot_dr_data_all('local',today,'../../',directory,save=True,dpi=50)
