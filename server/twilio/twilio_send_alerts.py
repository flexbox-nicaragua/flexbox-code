# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import pandas as pd
from twilio.rest import TwilioRestClient
import os
from pandas.tools.plotting import scatter_matrix
from datetime import date, datetime, timedelta
import copy
import numpy as np
import os.path
import requests
import re
import yaml
from flexbox import psql
from flexbox import psql_server
from flexbox import analysis_tools
from sqlalchemy import cast,Date,text
from flexbox import psql_server

TESTING=True
from_twilio_number = '+12223334444'
outlet_2 = []
receive_texts = []
#Datetime in UTC to match those in flexbox table
this_datetime = datetime.utcnow()


print datetime.now()
#Preparation for Texting
#This gets the phone numbers, a list of available flexboxes in the program,
#available hours, and hardcoded which outlets they are supposed to be on.
metadata = psql_server.get_metadata()
table_dict = psql_server.setup_tables(metadata)

avaiable_hours = {}
phone_dictionary = {}
phone_dictionary_reversed = {}
with open('twilio_auth.yaml') as f:
    cf = yaml.safe_load(f)
client = TwilioRestClient(cf['ACCOUNT_SID'],cf['AUTH_TOKEN'])
with open('../web/available_hours.yaml') as f:
    available_hours = yaml.safe_load(f)
with open('max_fridge_power.yaml') as f:
    max_fridge_power = yaml.safe_load(f)
with open('phonebook.yaml') as f:
    phone_dictionary = yaml.safe_load(f)
    phone_dictionary_reversed = dict((value,key)
                for key,value in phone_dictionary.items())
available_flexboxes = []
for val in available_hours.keys():
    if 'flxbx' in val:
        available_flexboxes.append(val)
correct_outlet = {}
for flxbx in available_flexboxes:
    correct_outlet[flxbx] = 3
    if flxbx in outlet_2:
        correct_outlet[flxbx] = 2
    else:
        correct_outlet[flxbx] = 3
def send_alert_message(message):
    print message
    if not TESTING:
        client.messages.create(
            to=phone_dictionary_reversed['Admin'],
            from_=from_twilio_number,
            body=message,
        )

def get_dataframe_from_sql(table_ref,this_datetime,look_back_hours,in_utc=True):
    look_back_datetime = this_datetime-timedelta(hours=look_back_hours)
    column_names = table_ref.columns.keys()
    df = pd.DataFrame(table_ref.select().\
                                  where(table_ref.c.datetime>=look_back_datetime).\
                                  where(table_ref.c.datetime<=this_datetime).\
    order_by(table_ref.c.datetime.asc()).execute().fetchall(),columns=column_names)
    if in_utc:
        df.index = df['datetime'] - timedelta(hours=6)
    else:
        df.index = df['datetime']
    return df

def get_temp_sensor_failure_rate(this_datetime,look_back_hours):
    inside_temperature = get_dataframe_from_sql(table_dict['inside_table'],\
                                                this_datetime,look_back_hours)
    temp_fails1 = {}
    temp_fails2 = {}
    for flxbx in available_flexboxes:
        temp_check = inside_temperature[inside_temperature['hostname']==flxbx]
        if len(temp_check)>0:
            temp_fails1[flxbx] = float(len(temp_check[(temp_check['inside_temp1']>50000) |\
                                           (temp_check['inside_temp1']<-25000)])/\
                                            float(len(temp_check)))
            temp_fails2[flxbx]= float(len(temp_check[(temp_check['inside_temp2']>50000) |\
                                           (temp_check['inside_temp2']<-25000)])/\
                                            float(len(temp_check)))
    return temp_fails1,temp_fails2

def send_temp_message(temp_fails1,temp_fails2):
    for flxbx in temp_fails1:
        if flxbx in temp_fails1 and temp_fails1[flxbx]>0.05 and \
                flxbx in temp_fails2 and temp_fails2[flxbx]>0.05:
            temp_message = flxbx + ':  AMBOS sensores TEMPERATURA estan dando valores que no son correctos. '+\
            'temp1:  ' +\
            str(round(temp_fails1[flxbx]*100,2))+'% y temp2: ' +\
            str(round(temp_fails2[flxbx]*100,2))+'% del tiempo'+\
            '. Checar inmediatamente en esta casa -'+\
            'telefono: '+ phone_dictionary_reversed[flxbx]

            ' del tiempo'
            send_alert_message(temp_message)
        elif flxbx in temp_fails1 and temp_fails1[flxbx]>0.05:
            temp_message = flxbx + ': sensor TEMPERATURA esta dando valores que no son correctos. '+\
            'temp1:  ' +str(round(temp_fails1[flxbx]*100,2))+'% del tiempo'+\
            '. Checar inmediatamente en esta casa - telefono '+phone_dictionary_reversed[flxbx]

            send_alert_message(temp_message)
        elif flxbx in temp_fails2 and temp_fails2[flxbx]>0.05:
            temp_message = flxbx + ': sensor TEMPERATURA esta dando valores que no son correctos. '+\
            'temp2:  ' +str(round(temp_fails2[flxbx]*100,2))+'% del tiempo'+\
            '. Checar inmediatamente en esta casa - telefono '+phone_dictionary_reversed[flxbx]
            send_alert_message(temp_message)

def send_mfi_message(this_datetime,look_back_hours,minutes_since_last_heartbeat):
    mfi_df = get_dataframe_from_sql(table_dict['mfi_table'],this_datetime,
                                    look_back_hours,in_utc=False)
    for flxbx in available_flexboxes:
        if flxbx!='flxbxD6':
            if len(mfi_df[mfi_df['hostname']==flxbx])>0:
                if mfi_df[mfi_df['hostname']==flxbx].iloc[-1].relay3 == True:
                    fridge_state = 'ON'
                elif mfi_df[mfi_df['hostname']==flxbx].iloc[-1].relay3 == False:
                    fridge_state = 'OFF'
                else:
                    fridge_state = 'text_error'
                if mfi_df[mfi_df['hostname']==flxbx].iloc[-1].\
                    datetime<this_datetime-timedelta(minutes=minutes_since_last_heartbeat):
                    minutes_since = int(float((this_datetime-mfi_df[mfi_df['hostname']==\
                                                        flxbx].iloc[-1].datetime).seconds)/60.0)
                    message = flxbx+': El MFI no esta funcionado para ' + str(minutes_since)+\
                    ' minutos. Es todavia '+ fridge_state +'.  '+\
                    'Checar inmediatamente en esta casa - telefono: '+phone_dictionary_reversed[flxbx]
                    send_alert_message(message)
            else:
                message = flxbx +': El MFI no esta funcionado para mas que '+str(look_back_hours)+\
                    ' horas. '+\
                    'Checar inmediatamente en esta casa - telefono: '+phone_dictionary_reversed[flxbx]
                send_alert_message(message)

def get_timedelta_info(td):
    days = td.days
    hours = td.seconds//3600
    minutes = (td.seconds//60)%60
    seconds = (td.seconds)%3600%60
    return td.days, td.seconds//3600, (td.seconds//60)%60, seconds

def send_network_message(this_datetime,look_back_hours,minutes_since_last_network):
    network_tests = get_dataframe_from_sql(table_dict['network_tests'],this_datetime,look_back_hours)
    for flxbx in available_flexboxes:
        if len(network_tests[network_tests['hostname']==flxbx])>0:
            network_gaps = (network_tests[network_tests['hostname']==flxbx]['datetime']-\
            network_tests[network_tests['hostname']==flxbx]['datetime'].shift())
            average_gap = network_gaps.mean()
            largest_gap = network_gaps.max()
            last_gap = this_datetime-timedelta(hours=6)-\
                network_tests[network_tests['hostname']==flxbx].index[-1]

            days,hours,minutes,seconds = get_timedelta_info(largest_gap)
            last_days,last_hours,last_minutes,last_seconds = get_timedelta_info(last_gap)
            gap_string = network_gaps.shift(-1).idxmax().strftime('%m-%d %H:%M')+" to "+\
            network_gaps.idxmax().strftime('%m-%d %H:%M')
            '''
            if largest_gap.seconds>5400 || last_gap>:
                network_message = flxbx + ': lost connection for ' + str(days)+' days, '+\
                    str(hours)+' hours, '+str(minutes)+' minutes '+ ' from ' + gap_string+\
                    ', have not had a connection for ' +\
                    str(last_hours)+' hours, '+str(last_minutes)+' minutes '\
                    +str(last_seconds)+' seconds '
                send_alert_message(network_message)
            '''
            if last_gap.seconds>60*minutes_since_last_network:
                network_message = flxbx + ': El MODEM no esta funcionando para '+\
                str(last_hours)+' hours y ' + str(last_minutes)+' minutos. '+\
                'Checar inmediatamente en esta casa - telefono: '+phone_dictionary_reversed[flxbx]
                send_alert_message(network_message)

def send_system_network_message(this_datetime,look_back_hours):
    network_tests = get_dataframe_from_sql(table_dict['network_tests'],this_datetime,look_back_hours)
    network_tests==network_tests[network_tests.index<this_datetime]
    if len(network_tests)==0:
        send_alert_message("The network test script is down!")

def send_system_heartbeat_message(this_datetime,look_back_hours):
    dr_table = get_dataframe_from_sql(table_dict['demand_response'],this_datetime,look_back_hours)
    dr_table==dr_table[dr_table.index<this_datetime]
    if len(dr_table)==0:
        send_alert_message("THE HEARTBEAT SCRIPT IS DOWN!!!!")

def send_zwave_message():
    metadata = psql_server.get_metadata()
    table_dict = psql_server.setup_tables(metadata)

    dfs = {}
    for flxbx in available_flexboxes:
        # The next two lines are SQL Alchemy code, ordering each house energy data by date and then
        last_row = table_dict['twilio_received'].select("hostname='"+flxbx+"'").\
             order_by(table_dict['twilio_received'].\
             c.datetime.desc()).execute().fetchone()

        if last_row:
             last_date = last_row[3]
             limit = last_row[6]
             last_text_sent = None

             # The next two lines are SQL Alchemy code, ordering each house energy data by date and t
             energia = analysis_tools.get_energy_since_date(flxbx,last_date)
             print flxbx+': '+str(last_date)+' : '+str(energia)
             if (datetime.now()-last_date).days>31:
                 if flxbx in receive_texts:
                    zwave_message = flxbx+': Hay uno mes desde un limite en el database.'\
                        +' El ultimo ves es '+str(last_date)
                    send_alert_message(zwave_message)
                 else:
                    print flxbx +' hasn\'t set a limit but does not receive messages.'
             elif (datetime.now()-last_date).days<0:
                zwave_message = flxbx+': El limite es incorrecta. El limite en el server es '\
                    +str(last_date)+' pero este en el futuro!'
                send_alert_message(zwave_message)
             elif energia == 0 and (datetime.now()-last_date).days>2:
                 zwave_message = flxbx+': Es possible el zwave no es funcianado. Checar'\
                 + ' immediatamente en esta casa por favor.'
                 send_alert_message(zwave_message)


def send_outlet_message(this_datetime,look_back_hours):
    metadata = psql_server.get_metadata()
    table_dict = psql_server.setup_tables(metadata)

    peak_shifting_df = get_dataframe_from_sql(table_dict\
                        ['peak_shifting_dr_table'],
                        this_datetime-timedelta(hours=6),look_back_hours+3,in_utc=False)
    peak_event = False
    if len(peak_shifting_df)>0:
        start_peak_event = peak_shifting_df.iloc[-1]['datetime']
        end_peak_event = start_peak_event +\
            timedelta(minutes=peak_shifting_df.iloc[-1]['duration_minutes'])
        print 'Ommitting Outlet checks for when peak events have recently occurred'
        print start_peak_event
        print end_peak_event
        for hours_back in range(look_back_hours):
            time_check = this_datetime -timedelta(hours=6+hours_back)
            peak_event = (time_check>=start_peak_event) and \
                        (time_check<=end_peak_event)
            print time_check
    print peak_event
    mfi_df = get_dataframe_from_sql(table_dict['mfi_table'],this_datetime,look_back_hours)
    hour = (this_datetime-timedelta(hours=(look_back_hours+6))).hour
    for flxbx in available_flexboxes:
        if flxbx not in ['flxbxD21']:
            is_available = True
            for val in range(hour,hour+look_back_hours):
                if val not in available_hours[flxbx]:
                    is_available = False
            if not peak_event and is_available and\
                    len(mfi_df[mfi_df['hostname']==flxbx])>0:
                energy_sum3 = sum(mfi_df[mfi_df['hostname']==flxbx]['active_pwr3'])
                energy_sum2 = sum(mfi_df[(mfi_df['hostname']==flxbx)&\
                                        (mfi_df['active_pwr2']<\
                                        max_fridge_power[flxbx])]['active_pwr2'])
                if not peak_event and energy_sum3<energy_sum2 and \
                        correct_outlet[flxbx]==3:
                    outlet_message = flxbx + ': El freezer esta conectado en'+\
                        'el outlet equivocado (outlet 2 (roja)).'+\
                        ' Checar inmediatamente en esta casa - telefono: '+\
                        phone_dictionary_reversed[flxbx]
                    send_alert_message(outlet_message)
                elif energy_sum3>energy_sum2 and correct_outlet[flxbx]==2:
                    outlet_message = flxbx + ': El freezer esta conectado en'+\
                        'el outlet equivocado (outlet 3 (negro)).'+\
                        ' Checar inmediatamente en esta casa - telefono: '+\
                        phone_dictionary_reversed[flxbx]
                    send_alert_message(outlet_message)
                elif energy_sum3==0 and energy_sum2==0 and not peak_event:
                    outlet_message = flxbx + ': El freezer esta conectado en'+\
                        ' NO outlet.'+\
                        ' Checar inmediatamente en esta casa - telefono: '+\
                        phone_dictionary_reversed[flxbx]
                    send_alert_message(outlet_message)
                    print hour
                    print available_hours[flxbx]

def send_ambient_message(this_datetime,look_back_hours):
    ambient_df = get_dataframe_from_sql(table_dict['ambient_table'],this_datetime,look_back_hours)
    for flxbx in available_flexboxes:
        if len(ambient_df[ambient_df['hostname']==flxbx])==0:
            send_alert_message(flxbx+": Problema con sensora ambiente")
        else:
            print flxbx+':'+str(ambient_df[ambient_df['hostname']==flxbx].iloc[-1].name)

def send_relay_message(this_datetime,look_back_hours):
    mfi_df = get_dataframe_from_sql(table_dict['mfi_table'],this_datetime,look_back_hours)
    dr_df = get_dataframe_from_sql(table_dict['demand_response'],this_datetime,look_back_hours)
    for flxbx in available_flexboxes:
        if len(dr_df[dr_df['hostname']==flxbx])>0 and len(mfi_df[mfi_df['hostname']==flxbx])>0:
            df_combine = pd.DataFrame([dr_df[dr_df['hostname']==flxbx]['mfi_state'].\
                                    resample('60S').mean().dropna(),\
                        mfi_df[mfi_df['hostname']==flxbx]['relay3'].resample('60S').\
                        mean().dropna()]).T.dropna()
            df_combine['matching_relay'] = df_combine['mfi_state']-df_combine['relay3']
            if len(df_combine[df_combine['matching_relay']!=0])>5:
                relay_message = flxbx+\
                ': This is a test: The relay on this flexbox is not matching the dr signal.'
                print relay_message
                #send_alert_message(relay_message)

try:
    look_back_minutes = 30
    send_system_heartbeat_message(this_datetime,look_back_minutes/60.0)
except:
    send_alert_message("Exception Accessing PSQL. "+\
                       "Server requires immediate attention.")

if requests.get('http://yourdomainhere.com/signal_time').status_code!=200:
    send_alert_message("The nginx server is down, no events will be sent!")
#Runs every 10 minutes
#Checks that heartbeat is running
look_back_minutes = 30
send_system_heartbeat_message(this_datetime,look_back_minutes/61.0)

if TESTING:
    send_ambient_message(this_datetime,24)

#Runs every hour
#Checkst that network testing script is running
if TESTING or (datetime.now().minute==10):
    look_back_minutes = 10
    send_system_network_message(this_datetime,look_back_minutes/60.0)

#Runs every 10 minutes
#Checks that relay is correct
look_back_minutes = 10
send_relay_message(this_datetime,look_back_minutes/60.0)

#Run each hour at :10
#Checks that each flexbox is connected over the modem
if TESTING or (datetime.now().minute==10 and datetime.now().hour>=7):
    look_back_hours = 12
    minutes_since_last_network=90
    send_network_message(this_datetime,look_back_hours,minutes_since_last_network)

#Run each hour at :10,
#Checks that each flexbox's MFI values are being sent through the heartbeat
if TESTING or (datetime.now().minute==10 and datetime.now().hour>=7):
    look_back_hours = 5
    minutes_since_last_heartbeat = 180
    send_mfi_message(this_datetime,look_back_hours,minutes_since_last_heartbeat)
    #flxbxD6 is exceptioned currently!!!!!

#Runs once a day at 9AM
#Checks that each flexbox's temperature sensors are functioning
look_back_hours = 24
if TESTING or (datetime.now().hour == 9 and datetime.now().minute==10):
    temp_fails1,temp_fails2 = get_temp_sensor_failure_rate(this_datetime,look_back_hours)
    send_temp_message(temp_fails1,temp_fails2)

#Run each hour at :00,
#Checks that each flexbox's MFI is on the right outlet
if TESTING or (datetime.now().minute==0 and datetime.now().hour>=7):
    look_back_hours = 3
    send_outlet_message(this_datetime,look_back_hours)
    send_outlet_message_flxbxD21(this_datetime,7)

if TESTING or datetime.now().minute==0 and datetime.now().hour == 10:
    send_zwave_message()

