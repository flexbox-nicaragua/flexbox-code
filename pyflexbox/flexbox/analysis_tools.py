# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import numpy as np
import traceback
import pandas as pd
from flexbox import psql_server
import copy

import pandas as pd
import os
from pandas.tools.plotting import scatter_matrix
from datetime import date, datetime, timedelta, time
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib as mpl
import seaborn as sns
sns.set_style("white")
import statsmodels.api as sm
from sklearn import linear_model
from scipy.stats import norm,ttest_ind
from scipy import stats
import copy
import numpy as np
import os.path
from ggplot import *
from matplotlib.cm import cool
import re
import yaml
from flexbox import psql
from flexbox import psql_server

#Brining Libraries for FlexBox Data
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Column, Table
from sqlalchemy import Integer, String, DateTime, Boolean, Float, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import cast,Date,text
from flexbox import psql_server

def create_monotonically_increasing_energy_vals(table_dict,flxbx):
    column_names = table_dict['zwave_table'].columns.keys()
    # The next two lines are SQL Alchemy code, ordering each house energy data by date and then executing
    df = pd.DataFrame(table_dict['zwave_table'].select("hostname='"+flxbx+"'").\
         order_by(table_dict['zwave_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(df)>0 :
        df['month'] = [x.month for x in df['datetime']] #list comprehension can also be written into a for loop as exemplified below
        #I added the line below so that the dataframe can be indexed by datetime, making slices easier
        df.index = df.index = pd.to_datetime(df['datetime']) #<--- I added this line
        #Below adds a new column to take into account when the Z-wave gets reset to 0
        threshold = np.nanpercentile(df[df['houseAll_Energy'].diff()>0]['houseAll_Energy'].diff(),98)*2
        if threshold != threshold:#this checks if threshold is NaN, in which case we don't have to worry about outliers.
            temporary_df_copy = copy.deepcopy(df[df['houseAll_Energy']>0])
        else:
            temporary_df = copy.deepcopy(df[(abs(df['houseAll_Energy'].diff())<threshold) & (df['houseAll_Energy']>0)])
            temporary_df_copy = copy.deepcopy(temporary_df[abs(temporary_df['houseAll_Energy'].diff())<threshold])
        temporary_df_fixed = copy.deepcopy(temporary_df_copy)
        for val in temporary_df_copy['houseAll_Energy'].loc[temporary_df_copy['houseAll_Energy'].diff()<-1].index:
            temporary_df_fixed['houseAll_Energy'][val:]=\
            temporary_df_fixed['houseAll_Energy'][val:]-temporary_df_copy['houseAll_Energy'].diff()[val]
        return temporary_df_fixed

    else:
        return pd.DataFrame()

def get_energy_since_date(flxbx,last_date,remote=False):
    if remote:
        metadata = psql_server.get_remote_metadata()
    else:
        metadata = psql_server.get_metadata()
    table_dict = psql_server.setup_tables(metadata)
    df = create_monotonically_increasing_energy_vals(table_dict,flxbx)
    if len(df)>0 and len(df[last_date:])>0:
        energia = df[last_date:]['houseAll_Energy'][-1:].iloc[0] -\
            df[last_date:]['houseAll_Energy'][:1].iloc[0]
    else:
        energia = 0
    return energia
