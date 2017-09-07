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

#Bringing in Libraries for Grid 20 second Data
from niuera_nica import psql_niuera_cndc_hourly as psql_hour
from sqlalchemy import cast,Date,text
from niuera_nica import psql_niuera_real_time
from flexbox import psql_server
from niuera_nica import psql_niuera_control


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


def read_dr_data(source,date_select,flexbox_repo_path='/Users/Diego/Desktop/Projects_Code/'):

    df_dic = {}
    day_start_utc = datetime.combine(date_select,datetime.min.time())+timedelta(hours=6)
    day_end_utc = datetime.combine(date_select,datetime.max.time())+timedelta(hours=6)
    ##### 1. Household Energy and Refrigeration Data

    # Server Connection
    if source == "server":
        engine = create_engine('postgresql://flexbox:flexbox@yourserverdomain.com/flexbox_db_server')
        metadata = MetaData(bind=engine)
    else:
         metadata = psql_server.get_metadata()

    # Inside Temperature
    table_dict = psql_server.setup_tables(metadata)
    column_names = table_dict['inside_table'].columns.keys()
    inside_temperature = pd.DataFrame(table_dict['inside_table'].select().\
        where(table_dict['inside_table'].c.datetime>=day_start_utc).\
        where(table_dict['inside_table'].c.datetime<=day_end_utc).\
        order_by(table_dict['inside_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(inside_temperature)>0:
        inside_temperature.index = inside_temperature['datetime'] - timedelta(hours=6)
        inside_temperature['date'] = inside_temperature.index.date
        inside_temperature['hour'] = inside_temperature.index.hour

    # Refrigerator Energy and Power
    column_names = table_dict['mfi_table'].columns.keys()
    mfi = pd.DataFrame(table_dict['mfi_table'].select().\
        where(table_dict['mfi_table'].c.datetime>=day_start_utc).\
        where(table_dict['mfi_table'].c.datetime<=day_end_utc).\
        order_by(table_dict['mfi_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(mfi)>0:
        mfi.index = mfi['datetime'] - timedelta(hours=6)
        mfi['date'] = mfi.index.date
        mfi['hour'] = mfi.index.hour

    # Refrigerator Energy and Power
    column_names = table_dict['zwave_table'].columns.keys()
    zwave = pd.DataFrame(table_dict['zwave_table'].select().\
        where(table_dict['zwave_table'].c.datetime>=day_start_utc).\
        where(table_dict['zwave_table'].c.datetime<=day_end_utc).\
        order_by(table_dict['zwave_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(zwave)>0:
        zwave.index = zwave['datetime'] - timedelta(hours=6)
        zwave['date'] = zwave.index.date
        zwave['hour'] = zwave.index.hour

    # Demand Response
    column_names = table_dict['demand_response'].columns.keys()
    dr = pd.DataFrame(table_dict['demand_response'].select().\
        where(table_dict['demand_response'].c.datetime>=day_start_utc).\
        where(table_dict['demand_response'].c.datetime<=day_end_utc).\
        order_by(table_dict['demand_response'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(dr)>0:
        dr.index = dr['datetime']
        dr['date'] = dr.index.date
        dr['hour'] = dr.index.hour


    ##### 2. Hourly Prediction Data

    # Server Connection
    if source == "server":
        engine = create_engine('postgresql://niuera_analyzer:analysis@yourserverdomain.com/cndc_hourly_db')
        metadata = MetaData(bind=engine)
    else:
        metadata = psql_hour.get_metadata()

    table_dict = psql_hour.setup_tables(metadata)
    column_names = table_dict['predespacho_table'].columns.keys()

    pred_frame = pd.DataFrame(table_dict['predespacho_table'].select().\
                              where(cast(table_dict['predespacho_table'].c.datetime,Date)==date_select).\
                              order_by(table_dict['predespacho_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(pred_frame)>0:
        pred_frame.index = pred_frame['datetime']
        pred_frame['date'] = pred_frame.index.date
        pred_frame['hour'] = pred_frame.index.hour

    pred_frame['gen_wind'] = pred_frame['AMY1'] + pred_frame['AMY2']+ pred_frame['PBP'] + pred_frame['EOL'] + pred_frame['ABR']
    pred_frame['load_inter_total'] = pred_frame['LNI-L9040'] + pred_frame['SND-L9090']+ pred_frame['AMY-L9030'] + pred_frame['TCPI-L9150']
    pred_frame['net_demand'] = pred_frame['Demanda'] - pred_frame['gen_wind'] + pred_frame['load_inter_total']


    ##### 3. Real Time 20 Second and 5 Second Data

    # Server Connection

    if source == "server":
        engine = create_engine('postgresql://niuera_analyzer:analysis@yourserverdomain.com/niuera_real_time_db')
        metadata = MetaData(bind=engine)
    else:
        metadata = psql_niuera_real_time.get_metadata()


    table_dict = psql_niuera_real_time.setup_tables(metadata)

    # Extracting 20 Second Data Tables
    column_names = table_dict['cndc_20sec_table'].columns.keys()
    twenty_sec = pd.DataFrame(table_dict['cndc_20sec_table'].select().\
                              where(cast(table_dict['cndc_20sec_table'].c.datetime,Date)==date_select).\
                              order_by(table_dict['cndc_20sec_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    twenty_sec.index = twenty_sec['datetime']
    if len(twenty_sec)>0:
        twenty_sec['date'] = twenty_sec.index.date
        twenty_sec['hour'] = twenty_sec.index.hour

        wind_plants = ['gen_EOL','gen_ABR','gen_AMY','gen_PBP']
        wind_plant_limits = [45,40,63,40]

        #Dropping Wind Values that Might be Outliers
        twenty_sec.loc[twenty_sec['gen_EOL'] > 45*10, 'gen_EOL'] = None
        twenty_sec.loc[twenty_sec['gen_ABR'] > 40*10, 'gen_ABR'] = None
        twenty_sec.loc[twenty_sec['gen_AMY'] > 63*10, 'gen_AMY'] = None
        twenty_sec.loc[twenty_sec['gen_PBP'] > 40*10, 'gen_PBP'] = None

        twenty_sec['gen_wind'] = (twenty_sec['gen_EOL'] + twenty_sec['gen_ABR'] + twenty_sec['gen_AMY'] + twenty_sec['gen_PBP'])/10

        #Dropping Demand Values that Might be Outliers
        twenty_sec['load_total'] =  (twenty_sec['load_BZN'] +  twenty_sec['load_CHG'] + twenty_sec['load_acoyapa'] + twenty_sec['load_altamira'] + twenty_sec['load_amerrisque'] + twenty_sec['load_asososca']+ twenty_sec['load_asturias'] + twenty_sec['load_batahola'] + twenty_sec['load_bluefields']+twenty_sec['load_boaco'] +  twenty_sec['load_chinandega'] + twenty_sec['load_corinto'] + twenty_sec['load_corocito'] + twenty_sec['load_diriamba']+twenty_sec['load_el_mojon'] + twenty_sec['load_el_periodista'] + twenty_sec['load_el_tuma']+twenty_sec['load_el_viejo'] + twenty_sec['load_enacal'] + twenty_sec['load_esteli']+ twenty_sec['load_granada']+twenty_sec['load_la_esperanza'] + twenty_sec['load_la_gateada'] + twenty_sec['load_las_banderas']+ twenty_sec['load_leon_1']+twenty_sec['load_leon_2'] + twenty_sec['load_los_brasiles'] + twenty_sec['load_malpaisillo']+ twenty_sec['load_managua']+twenty_sec['load_masatepe'] + twenty_sec['load_matagalpa'] + twenty_sec['load_matiguas_mulukuku_siuna']+ twenty_sec['load_nadaime']+twenty_sec['load_oriental'] + twenty_sec['load_portezuelo'] + twenty_sec['load_punta_huete']+ twenty_sec['load_rivas']+twenty_sec['load_san_benito'] + twenty_sec['load_san_miguelito'] + twenty_sec['load_san_ramon']+ twenty_sec['load_sandino']+twenty_sec['load_santa_clara'] + twenty_sec['load_sebaco'] + twenty_sec['load_ticuantepe_2']+ twenty_sec['load_tipitapa'] +  twenty_sec['load_yalaguina'])/10
        twenty_sec.loc[twenty_sec['load_total'] > 850, 'load_total'] = None

        twenty_sec['load_inter_total'] = (twenty_sec['inter_LNI-L9040'] + twenty_sec['inter_SND-L9090'] + twenty_sec['inter_AMY-L9030']+ twenty_sec['inter_TCPI-L9150'])/10
        twenty_sec.loc[twenty_sec['load_inter_total'] < -100, 'load_inter_total'] = None
        twenty_sec.loc[twenty_sec['load_inter_total'] > 100, 'load_inter_total'] = None

        #Net Demand
        twenty_sec['net_demand'] = twenty_sec['load_total'] - twenty_sec['gen_wind'] #+ twenty_sec['load_inter_total']


    ##### 4.  Bringing the DR Events

    # Server Connection
    if source == "server":
        engine = create_engine('postgresql://niuera_analyzer:analysis@yourserverdomain.com/niuera_control_db')
        metadata = MetaData(bind=engine)
    else:
        metadata = psql_niuera_control.get_metadata()

    table_dict = psql_niuera_control.setup_tables(metadata)

    # Net Load DR
    column_names = table_dict['net_load_dr_table'].columns.keys()
    net_load_dr = pd.DataFrame(table_dict['net_load_dr_table'].select().\
                              where(cast(table_dict['net_load_dr_table'].c.datetime,Date)==date_select).\
                              order_by(table_dict['net_load_dr_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(net_load_dr)>0:
        net_load_dr.index = net_load_dr['datetime']
        net_load_dr['date'] = net_load_dr.index.date
        net_load_dr['hour'] = net_load_dr.index.hour

    # Peak Shifting DR Table
    column_names = table_dict['peak_shifting_dr_table'].columns.keys()
    peak_shifting_dr = pd.DataFrame(table_dict['peak_shifting_dr_table'].select().\
                              where(cast(table_dict['peak_shifting_dr_table'].c.datetime,Date)==date_select).\
                              order_by(table_dict['peak_shifting_dr_table'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(peak_shifting_dr)>0:
        peak_shifting_dr.index = peak_shifting_dr['datetime']
        peak_shifting_dr['date'] = peak_shifting_dr.index.date
        peak_shifting_dr['hour'] = peak_shifting_dr.index.hour


    ####### 5. Network Tests

    # Server Connection
    if source == "server":
        engine = create_engine('postgresql://flexbox:flexbox@yourserverdomain.com/flexbox_db_server')
        metadata = MetaData(bind=engine)
    else:
        metadata = psql_server.get_metadata()

    table_dict = psql_server.setup_tables(metadata)
    column_names = table_dict['network_tests'].columns.keys()
    network_tests = pd.DataFrame(table_dict['network_tests'].select().\
        where(table_dict['network_tests'].c.datetime>=day_start_utc).\
        where(table_dict['network_tests'].c.datetime<=day_end_utc).\
        order_by(table_dict['network_tests'].c.datetime.asc()).execute().fetchall(),columns=column_names)
    if len(network_tests)>0:
        network_tests.index = network_tests['datetime'] - timedelta(hours=6)
        network_tests['date'] = network_tests.index.date
        network_tests['hour'] = network_tests.index.hour


    #### 6. Information Hard Coded into Houses

    # Max temp dictionary


    with open(flexbox_repo_path+'/server/web/flexbox_upper_deadband.yaml') as f:
        max_temp_dict = yaml.safe_load(f)
    with open(flexbox_repo_path+'/server/web/available_hours.yaml') as f:
        required_hours_off = yaml.safe_load(f)

    df_dic['inside_temperature'] = inside_temperature
    df_dic['mfi'] = mfi
    df_dic['zwave'] = zwave
    df_dic['dr'] = dr
    df_dic['pred_frame'] = pred_frame
    df_dic['twenty_sec'] = twenty_sec
    df_dic['net_load_dr'] = net_load_dr
    df_dic['peak_shifting_dr'] = peak_shifting_dr
    df_dic['network_tests'] = network_tests
    df_dic['max_temp_dict'] = max_temp_dict
    df_dic['required_hours_off'] = required_hours_off

    return (df_dic);

def plot_dr_data(df_dic,date_select,house_id,save=False,image_dest=None,dpi=100):

    inside_temperature = df_dic['inside_temperature']
    mfi = df_dic['mfi']
    zwave = df_dic['zwave']
    dr = df_dic['dr']
    pred_frame = df_dic['pred_frame']
    twenty_sec = df_dic['twenty_sec']
    net_load_dr = df_dic['net_load_dr']
    peak_shifting_dr = df_dic['peak_shifting_dr']
    max_temp_dict = df_dic['max_temp_dict']
    required_hours_off = df_dic['required_hours_off']
    network_tests = df_dic['network_tests']

    if house_id in max_temp_dict and house_id in required_hours_off:
        # Day subsets for each dataframe
        if len(twenty_sec)>0:
            day_subset = twenty_sec[twenty_sec['date'] == date_select][['hour','load_total','gen_wind','net_demand','load_inter_total']]
            day_subset = day_subset.dropna()
            day_subset_resample = day_subset.resample('H',closed='left').mean()
        if len(net_load_dr)>0:
            day_net_load_dr = net_load_dr[net_load_dr['date'] ==  date_select][['signal','arma_signal']]
        if len(pred_frame)>0:
            day_subset_pred = pred_frame[pred_frame['date'] ==  date_select][['hour','Demanda','net_demand','gen_wind']]
        if len(peak_shifting_dr)>0:
            day_peak_shift = peak_shifting_dr[peak_shifting_dr['date'] ==  date_select][['signal','duration_minutes']]

        #plt.subplot(411)




        dr_fig = plt.figure()
        # Plot
        plt.title('Grid')
        if len(pred_frame)>0:
            plt.plot(day_subset_pred.index,day_subset_pred['Demanda'],'.')
            plt.plot(day_subset_pred.index,day_subset_pred['net_demand'],'.')
            plt.plot(day_subset_pred.index,day_subset_pred['gen_wind'],'.')

        if len(twenty_sec)>0:
            plt.plot(day_subset.index,day_subset['load_total'])
            plt.plot(day_subset.index,day_subset['gen_wind'])
            plt.plot(day_subset.index,day_subset['net_demand'])

        # Getting unique events and then plotting them in time
        if len(peak_shifting_dr)>0:
            peak_shift_event = day_peak_shift[day_peak_shift['signal']==1].iloc[0]
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        if len(twenty_sec)>0:
            net_load_dr_events = (day_net_load_dr[day_net_load_dr['signal'] == 1]).index.unique()
            net_load_dr_arma = (day_net_load_dr[day_net_load_dr['arma_signal'] == 1]).index.unique()
            for event in net_load_dr_events:
                plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')
            for event in net_load_dr_arma:
                plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='yellow')
        else:
            net_load_dr_events = []
        ##############


        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        #plt.tight_layout()
        if save==True:
            dr_fig.savefig(image_dest+'/grid.png',dpi=dpi)
        ##################
        #plt.subplot(412)

        # Day subsets for Inside temperautre
        temp_fig = plt.figure()
        if len(inside_temperature)>0:
            inside_day_subset = inside_temperature[(inside_temperature['date'] == date_select) &\
             (inside_temperature['hostname'] == house_id)][['hour','date','hour','hostname','inside_temp1','inside_temp2']]
            inside_day_subset = inside_day_subset.dropna()


            plt.title('Temps')
            plt.plot(inside_day_subset.index,inside_day_subset['inside_temp1']/1000,'.')
            plt.plot(inside_day_subset.index,inside_day_subset['inside_temp2']/1000,'.')

        # Plotting the temperature limits
        plt.axhline(y=max_temp_dict[str(house_id)],c="blue",linewidth=2,zorder=0)
        plt.axhline(y=max_temp_dict[str(house_id)]+3,c="blue",linewidth=2,zorder=0)

        # Plotting the hours that it is required to be on
        for hour_on in required_hours_off[str(house_id)]:
            if hour_on == 24 and 0 in required_hours_off[str(house_id)]:
                pass
            elif hour_on == 23:
                 plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select+timedelta(days=1),time(0)),
                        alpha=0.1, color='green')
            else:
                if hour_on == 24:
                    hour_on = 0
                plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select,time(hour_on+1)),
                        alpha=0.1, color='green')


        # DR Events

        if len(peak_shifting_dr)>0:
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        for event in net_load_dr_events:
            plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')


        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        if save == True:
            temp_fig.savefig(image_dest+'/temps.png',dpi=dpi)

        ###############
        mfi_fig = plt.figure()
        if len(mfi)>0:
            mfi_day_subset = mfi[(mfi['date'] == date_select) &\
             (mfi['hostname'] == house_id)][['hour','date','hour','hostname','active_pwr2','active_pwr3','energy_sum2','energy_sum3','relay2','relay3']]
            mfi_day_subset = mfi_day_subset.dropna()


            plt.title('Fridge Power')
            plt.plot(mfi_day_subset.index,mfi_day_subset['active_pwr2'],'r.')
            plt.plot(mfi_day_subset.index,mfi_day_subset['active_pwr3'],'k.')

        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        if len(peak_shifting_dr)>0:
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        for event in net_load_dr_events:
            plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')

        # Plotting the hours that it is required to be on
        for hour_on in required_hours_off[str(house_id)]:
            if hour_on == 24 and 0 in required_hours_off[str(house_id)]:
                pass
            elif hour_on == 23:
                 plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select+timedelta(days=1),time(0)),
                        alpha=0.1, color='green')
            else:
                if hour_on == 24:
                    hour_on = 0
                plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select,time(hour_on+1)),
                        alpha=0.1, color='green')

        #plt.tight_layout()
        if save==True:
            plt.savefig(image_dest+'/mfi.png',dpi=dpi)
        #################################################
        # DR Events

        relay_fig = plt.figure()
        plt.title('Fridge Relay State')

        if len(peak_shifting_dr)>0:
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        for event in net_load_dr_events:
            plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')

        # Plotting the hours that it is required to be on
        for hour_on in required_hours_off[str(house_id)]:
            if hour_on == 24 and 0 in required_hours_off[str(house_id)]:
                pass
            elif hour_on == 23:
                 plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select+timedelta(days=1),time(0)),
                        alpha=0.1, color='green')
            else:
                if hour_on == 24:
                    hour_on = 0
                plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select,time(hour_on+1)),
                        alpha=0.1, color='green')

        if len(mfi)>0:
            # Plot Relays
            val_list = []
            for val in mfi_day_subset['relay3']:
                if val == True:
                    val_list.append(1)
                elif val == False:
                    val_list.append(-1)
                elif val == None:
                    val_list.append(0)
                else:
                    pass

            mfi_day_subset['val_relay'] = val_list
            plt.plot(mfi_day_subset.index,mfi_day_subset['val_relay'],'.')
            plt.ylim(-1.5,1.5)
        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        #plt.tight_layout()
        if save==True:
            relay_fig.savefig(image_dest+'/relay.png',dpi=dpi)
        #########################################

        # Network Plots
        network_fig = plt.figure()
        plt.title('Network Status')

        if len(peak_shifting_dr)>0:
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        for event in net_load_dr_events:
            plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')

        # Plotting the hours that it is required to be on
        for hour_on in required_hours_off[str(house_id)]:
            if hour_on == 24 and 0 in required_hours_off[str(house_id)]:
                pass
            elif hour_on == 23:
                 plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select+timedelta(days=1),time(0)),
                        alpha=0.1, color='green')
            else:
                if hour_on == 24:
                    hour_on = 0
                plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select,time(hour_on+1)),
                        alpha=0.1, color='green')


        if len(network_tests)>0:
            day_network_tests = network_tests[(network_tests['date'] ==  date_select) &\
                 (network_tests['hostname'] ==  house_id)][['datetime','parm']]
            day_network_tests['test'] = 1

            plt.plot(day_network_tests.index,day_network_tests['test'],'.')
        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        #plt.tight_layout()
        if save==True:
            plt.savefig(image_dest+'/network.png',dpi=dpi)
    #########################################

        # Zwave Plots
        zwave_fig = plt.figure()
        plt.title('Z-wave Status')

        if len(peak_shifting_dr)>0:
            plt.axvspan(peak_shift_event.name,
                peak_shift_event.name+\
                timedelta(minutes=peak_shift_event['duration_minutes']), alpha=0.3, color='red')
        for event in net_load_dr_events:
            plt.axvspan(event,event + timedelta(minutes=20), alpha=0.3, color='blue')

        # Plotting the hours that it is required to be on
        for hour_on in required_hours_off[str(house_id)]:
            if hour_on == 24 and 0 in required_hours_off[str(house_id)]:
                pass
            elif hour_on == 23:
                 plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select+timedelta(days=1),time(0)),
                        alpha=0.1, color='green')
            else:
                if hour_on == 24:
                    hour_on = 0
                plt.axvspan(datetime.combine(date_select,time(hour_on)),\
                    datetime.combine(date_select,time(hour_on+1)),
                        alpha=0.1, color='green')

        if len(zwave)>0:
            day_zwave = zwave[(zwave['date'] ==  date_select) &\
                 (zwave['hostname'] ==  house_id)][['datetime','houseAll_Power']]

            plt.plot(day_zwave.index,day_zwave['houseAll_Power'],'.')
        plt.xlim(datetime.combine(date_select,datetime.min.time()),\
             datetime.combine(date_select,datetime.max.time()))
        #plt.tight_layout()
        if save==True:
            plt.savefig(image_dest+'/zwave.png',dpi=dpi)

        plt.close("all")
    else:
        print str(house_id) +' is not in the temperature or available hours dictionaries.'

def read_and_plot_dr_data_all(source,date_select,flexbox_repo_path,image_dest,save=False,dpi=100):
    print 'source: '+source
    print 'date_select: '+str(date_select)
    print 'path: '+flexbox_repo_path
    print 'image_dest: '+image_dest
    print 'save:'+str(save)
    print 'dpi:'+str(dpi)
    df_data_dic = read_dr_data(source = "local",
    date_select = date_select,
    flexbox_repo_path=flexbox_repo_path)
    for val in range(1,30):
        flxbx = 'flxbxD'+str(val)
        if not os.path.exists(image_dest+'/'+flxbx):
            os.makedirs(image_dest+'/'+flxbx)
        try:
            plot_dr_data(df_data_dic, date_select = date_select,house_id=flxbx,
            image_dest=image_dest+'/'+flxbx+'/',save=save,dpi=dpi)
        except:
            print 'Exception for flexbox '+flxbx
            traceback.print_exc()

if __name__ == "__main__":
    days=0
    today = (datetime.now()-timedelta(days=days)).date()
    directory = '../../server/web/static/images/'+today.strftime('%Y-%m-%d')+'/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    read_and_plot_dr_data_all('local',today,'../../',directory,save=True,dpi=50)
