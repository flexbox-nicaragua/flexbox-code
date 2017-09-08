#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
get_flexbox_rows
from flask import Flask, jsonify, send_file, make_response, request, Response
from functools import wraps
from flexbox import psql_server as psql_server
from flexbox import analysis_tools
from datetime import datetime,timedelta
from sqlalchemy import cast,Date,text,func
import yaml
import time
import subprocess
import os
import socket
import tarfile
import gzip
import csv
import logging
from pytz import timezone
import json
from logging.handlers import RotatingFileHandler
import pandas as pd
application = Flask(__name__)

num = 1
error_seconds_since_last_record_network = 60*5
error_seconds_since_last_record_heartbeat = 60*30
error_seconds_since_last_record_twilio = 60*60*24*7
fmt = "%Y-%m-%d %H:%M:%S"
localtz = timezone('America/Managua')
now = datetime.now()
metadata_flexbox_db_server = psql_server.get_metadata()
flexbox_db_server_table_dict = psql_server.setup_tables(metadata_flexbox_db_server)

def get_network(flxbxNum,num=1):
    table_name = 'network_tests'
    output = get_flexbox_rows(flexbox_db_server_table_dict[table_name],num,flxbxNum,
        error_seconds_since_last_record_network)
    return output

def get_twilio_sent(flxbxNum,num=1):
    table_name = 'twilio_sent'
    output = get_flexbox_rows(flexbox_db_server_table_dict[table_name],num,flxbxNum,
        error_seconds_since_last_record_twilio)
    return output

def get_flexbox_status(flxbxNum):

    with open('flexbox_upper_deadband.yaml') as f:
        max_temp_dict = yaml.safe_load(f)

    output = {}
    result_dict = {}
    demand_response_values = flexbox_db_server_table_dict['demand_response'].select().\
        where(flexbox_db_server_table_dict['demand_response'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['demand_response'].c.datetime.desc()).limit(num)
    result = demand_response_values.execute()
    rows = result.fetchone()
    most_recent_entry_dr = None
    if rows:
        columns = result.keys()
        last_row,most_recent_entry_dr = sql_results_to_dict(columns,[rows])
        output_demand_response = last_row[0]
        result_dict.update(output_demand_response)

    house_power_values = flexbox_db_server_table_dict['zwave_table'].select().\
        where(flexbox_db_server_table_dict['zwave_table'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['zwave_table'].c.datetime.desc()).limit(num)
    result = house_power_values.execute()
    rows = result.fetchone()
    if rows:
        columns = result.keys()
        last_row,most_recent_entry = sql_results_to_dict(columns,[rows])
        if last_row:
            result_dict.update(last_row[0])

    inside_temp_values = flexbox_db_server_table_dict['inside_table'].select().\
        where(flexbox_db_server_table_dict['inside_table'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['inside_table'].c.datetime.desc()).limit(num)
    result = inside_temp_values.execute()
    rows = result.fetchone()
    if rows:
        columns = result.keys()
        last_row,most_recent_entry = sql_results_to_dict(columns,[rows])
        if last_row:
            if 'inside_temp1' in last_row[0] and 'inside_temp2' in last_row[0] and\
            last_row[0]['inside_temp1'] and last_row[0]['inside_temp2'] and\
             last_row[0]['inside_temp1']!=85000 and last_row[0]['inside_temp2']!=85000:
                last_row[0]['inside_temp'] = (last_row[0]['inside_temp1']+last_row[0]['inside_temp2'])/2000.0
            elif 'inside_temp1' in last_row[0] and last_row[0]['inside_temp1'] and last_row[0]['inside_temp1']!=85000:
                last_row[0]['inside_temp'] = last_row[0]['inside_temp1']/1000.0
            elif 'inside_temp2' in last_row[0] and last_row[0]['inside_temp2'] and last_row[0]['inside_temp2']!=85000:
                last_row[0]['inside_temp'] = last_row[0]['inside_temp2']/1000.0
            result_dict.update(last_row[0])

    fridge_power_values = flexbox_db_server_table_dict['mfi_table'].select().\
        where(flexbox_db_server_table_dict['mfi_table'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['mfi_table'].c.datetime.desc()).limit(num)
    result = fridge_power_values.execute()
    rows = result.fetchone()
    if rows:
        columns = result.keys()
        last_row,most_recent_entry = sql_results_to_dict(columns,[rows])
        result_dict.update(last_row[0])


    if result_dict:
        result_dict = {key:result_dict[key] for key in ['houseAll_Power','houseAll_Energy',
                                                    'active_pwr3','energy_sum3',
                                                    'control_source','control_type',
                                                    'mfi_state','uptime_minutes',
                                                    'inside_temp',
                                                    'hostname'] if key in result_dict.keys()}
        if flxbxNum in max_temp_dict.keys():
            result_dict['max_temp_limit'] = max_temp_dict[flxbxNum]
        if most_recent_entry:
            result_dict['datetime'] = most_recent_entry.strftime(fmt)
        else:
            result_dict['datetime'] = None
        output['result'] = [result_dict]
        output['last_record'] =  most_recent_entry.strftime(fmt)
        output['since_last_record'] = (datetime.utcnow() - rows['datetime']).total_seconds()
        if len(rows) > 0 and float(output['since_last_record']) > error_seconds_since_last_record_heartbeat:
             output['status'] = 'ERROR'
        elif len(rows) > 0:
            output['status'] = 'GOOD'

    return output

def get_flexbox_status2(flxbxNum):

    with open('flexbox_upper_deadband.yaml') as f:
        max_temp_dict = yaml.safe_load(f)

    with open('available_hours.yaml') as f:
        available_hours_dict = yaml.safe_load(f)


    output = {}
    result_dict = {}
    demand_response_values = flexbox_db_server_table_dict['demand_response'].select().\
        where(flexbox_db_server_table_dict['demand_response'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['demand_response'].c.datetime.desc()).limit(num)
    result = demand_response_values.execute()
    rows = result.fetchone()
    most_recent_entry_dr = None
    if rows:
        columns = result.keys()
        last_row,most_recent_entry_dr = sql_results_to_dict(columns,[rows])
        output_demand_response = last_row[0]
        result_dict.update(output_demand_response)

    demand_response_peak_shifting_values = flexbox_db_server_table_dict['peak_shifting_dr_table'].select().\
        where(cast(flexbox_db_server_table_dict['peak_shifting_dr_table'].c.date,Date) == datetime.now().date()).\
        order_by(flexbox_db_server_table_dict['peak_shifting_dr_table'].c.datetime.desc())

    result = demand_response_peak_shifting_values.execute()
    rows = result.fetchone()
    most_recent_entry_dr_peak_shifting = None
    if rows:
        columns = result.keys()
        last_row,most_recent_entry_dr_peak_shifting = \
            sql_results_to_dict(columns,[rows],fix_utc=False)
        output_peak_shifting = last_row[0]
        end_peak_time = output_peak_shifting['datetime']+\
            timedelta(minutes=output_peak_shifting['duration_minutes'])
        if most_recent_entry_dr!=None:
            if most_recent_entry_dr>=output_peak_shifting['datetime'] and \
                    most_recent_entry_dr<=end_peak_time:
                output_peak_shifting['signal_peak_shifting'] = 1
            else:
                output_peak_shifting['signal_peak_shifting'] = 0
        else:
            if datetime.now()>=output_peak_shifting['datetime'] and \
                datetime.now()<=end_peak_time:
                output_peak_shifting['signal_peak_shifting'] = 1
            else:
                output_peak_shifting['signal_peak_shifting'] = 0
        result_dict.update(output_peak_shifting)

    inside_temp_values = flexbox_db_server_table_dict['inside_table'].select().\
        where(flexbox_db_server_table_dict['inside_table'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['inside_table'].c.datetime.desc()).limit(num)
    result = inside_temp_values.execute()
    rows = result.fetchone()
    if rows:
        columns = result.keys()
        last_row,most_recent_entry_temp = sql_results_to_dict(columns,[rows])
        if last_row:
            if 'inside_temp1' in last_row[0] and 'inside_temp2' in last_row[0] and\
            last_row[0]['inside_temp1'] and last_row[0]['inside_temp2'] and\
             last_row[0]['inside_temp1']!=85000 and last_row[0]['inside_temp2']!=85000:
                last_row[0]['inside_temp'] = (last_row[0]['inside_temp1']+last_row[0]['inside_temp2'])/2000.0
            elif 'inside_temp1' in last_row[0] and last_row[0]['inside_temp1'] and last_row[0]['inside_temp1']!=85000:
                last_row[0]['inside_temp'] = last_row[0]['inside_temp1']/1000.0
            elif 'inside_temp2' in last_row[0] and last_row[0]['inside_temp2'] and last_row[0]['inside_temp2']!=85000:
                last_row[0]['inside_temp'] = last_row[0]['inside_temp2']/1000.0
            result_dict.update(last_row[0])

    fridge_power_values = flexbox_db_server_table_dict['mfi_table'].select().\
        where(flexbox_db_server_table_dict['mfi_table'].c.hostname == flxbxNum).\
        order_by(flexbox_db_server_table_dict['mfi_table'].c.datetime.desc()).limit(num)
    result = fridge_power_values.execute()
    rows = result.fetchone()
    if rows:
        columns = result.keys()
        last_row,most_recent_entry_mfi = sql_results_to_dict(columns,[rows])
        result_dict.update(last_row[0])

    if result_dict:
        result_dict = {key:result_dict[key] for key in ['active_pwr2','active_pwr3','energy_sum3',
                                                    'control_source','control_type',
                                                    'mfi_state',
                                                    'relay3',
                                                    'hostname','signal_peak_shifting'] if key in result_dict.keys()}
        if 'signal_peak_shifting' not in result_dict:
            result_dict['signal_peak_shifting'] = -1
        if 'relay3' in result_dict:
            if result_dict['relay3']==True:
                result_dict['relay3']="ON"
            elif result_dict['relay3']==False:
                result_dict['relay3']="OFF"
        if flxbxNum in max_temp_dict.keys():
            result_dict['max_temp_limit'] = max_temp_dict[flxbxNum]
        if flxbxNum in available_hours_dict.keys():
            if most_recent_entry_dr and most_recent_entry_dr.hour in available_hours_dict[flxbxNum]:
                result_dict['required_off_now'] = False
            else:
                result_dict['required_off_now'] = True
            result_dict['available_hours'] =available_hours_dict[flxbxNum]

        if most_recent_entry_dr!=None:
            result_dict['datetime'] = most_recent_entry_dr.strftime(fmt)
        else:
            result_dict['datetime'] = None
        output['result'] = [result_dict]
        output['hostname'] = int(flxbxNum.replace('flxbxD',''))
        if most_recent_entry_dr!=None:
            output['last_record'] =  most_recent_entry_dr.strftime(fmt)
            output['since_last_record'] = (datetime.now() - most_recent_entry_dr).total_seconds()
        if 'relay3' not in result_dict or (result_dict['relay3']=="OFF" and (result_dict['signal_peak_shifting']==0 and\
                                             result_dict['required_off_now']==False)):
            output['status'] = 'ERROR'

        elif result_dict['relay3']=="ON" and ((result_dict['signal_peak_shifting']==1 and\
                                            ('control_source' in result_dict and\
                                            result_dict['control_source']!='max_temp_limit_reached')) or\
                                            result_dict['required_off_now']==True):
            output['status'] = 'ERROR'
        elif result_dict['control_source'] == 'lost_connection_to_mfi':
            output['status'] = 'ERROR'
        elif output['since_last_record']>1200:
            output['status'] = 'ERRORTIME'
        else:
            output['status'] = 'GOOD'

    return output

def get_twilio_status(flxbx):

    result_dict = {}
    output = {}

    with open('../twilio/tariff_codes.yaml') as f:
        tariff_codes = yaml.safe_load(f)
    last_row = flexbox_db_server_table_dict['twilio_received'].select("hostname='"+flxbx+"'").\
            order_by(flexbox_db_server_table_dict['twilio_received'].\
            c.datetime.desc()).execute().fetchone()

    if last_row:
        last_date = last_row[3]
        limit = last_row[6]

        energia = analysis_tools.get_energy_since_date(flxbx,last_date)

        tariff_code=tariff_codes[flxbx]
        last_row_sent_kwh = flexbox_db_server_table_dict['twilio_sent'].select().\
            where(text("hostname='"+flxbx+"'")).\
            where(text("limit_type='kwh'")).\
            where(cast(flexbox_db_server_table_dict['twilio_sent'].c.date_last,Date)==last_date).\
            order_by(flexbox_db_server_table_dict['twilio_sent'].\
            c.datetime.desc()).execute().fetchone()

        if last_row_sent_kwh:
            previously_crossed_start_range = last_row_sent_kwh[6]
            last_date_sent_kwh = last_row_sent_kwh[3]
            last_text_sent_kwh = last_row_sent_kwh[2]

            if last_date_sent_kwh != last_date:
                previously_crossed_start_range=-1
        else:
            previously_crossed_start_range = -1
            last_text_sent_kwh = None

        last_row_user_prices = flexbox_db_server_table_dict['user_prices'].select().\
            where(flexbox_db_server_table_dict['user_prices'].c.start_range<=energia).\
            where(flexbox_db_server_table_dict['user_prices'].c.end_range>energia).\
            where(flexbox_db_server_table_dict['user_prices'].c.tariff_code==tariff_code).\
            order_by(flexbox_db_server_table_dict['user_prices'].\
            c.datetime.desc()).execute().fetchone()

        start_range = last_row_user_prices[2]
        end_range = last_row_user_prices[3]
        price = last_row_user_prices[4]
        recent_price_date = last_row_user_prices[1]

        ##Twilio Percent Texts
        last_row_sent = flexbox_db_server_table_dict['twilio_sent'].select().\
            where(text("hostname='"+flxbx+"'")).\
            where(text("limit_type='percent'")).\
            where(cast(flexbox_db_server_table_dict['twilio_sent'].c.date_last,Date)==last_date).\
            order_by(flexbox_db_server_table_dict['twilio_sent'].\
            c.datetime.desc()).execute().fetchone()




        if last_row_sent:
            previously_crossed = last_row_sent[6]
            last_date_sent = last_row_sent[3]
            last_text_sent = last_row_sent[2]

            if last_date_sent != last_date:
                previously_crossed=0

             ### Creating a Warning for Increased Average Consumption Since last Text Message
            energia_pct_limit = analysis_tools.get_energy_since_date(flxbx,last_text_sent)
            if (datetime.now() - last_text_sent).days > 0:
                daily_pct_warning = energia_pct_limit/float((datetime.now()-last_text_sent).days)
            else:
                daily_pct_warning = 0
        else:
            previously_crossed = 0
            last_date_sent = last_date
            last_text_sent = None
            last_text_sent_percent = None



        ### Creating a Value that Calculates the Tarifa Social
        if (datetime.now()-last_date_sent).days>0:
            daily_pct_social = energia/float((datetime.now()-last_date_sent).days)
        else:
            daily_pct_social = energia

        ###

        ### Determining Tariff Code for SQL queries
        if daily_pct_social < 5 and tariff_code == 'T-0' and energia <= 150:
            tariff_code_for_sql = 'T-Social'
        elif tariff_code == 'T-J':
            tariff_code_for_sql = 'T-0'
        else:
            tariff_code_for_sql = tariff_code

        ine_user_prices = flexbox_db_server_table_dict['user_prices'].select().\
                        where(flexbox_db_server_table_dict['user_prices'].c.start_range<=energia).\
                        where(flexbox_db_server_table_dict['user_prices'].c.tariff_code==tariff_code_for_sql).\
                        where(cast(flexbox_db_server_table_dict['user_prices'].c.datetime,Date)==recent_price_date).\
                        order_by(flexbox_db_server_table_dict['user_prices'].\
                        c.datetime.desc()).execute().fetchall()

        cost_energia = 0

        for val in ine_user_prices:

            this_start_range = val[2]
            this_end_range = val[3]

            #Creating a scalar so that we appropriately assing subsidies to jubilados
            if tariff_code == 'T-J' and this_end_range <= 150:
                subsidy_scalar = 0.44
            else:
                subsidy_scalar = 1


            if energia <= this_end_range:
                cost_energia += (energia - this_start_range) * val[4] * subsidy_scalar
            else:
                 cost_energia += (this_end_range - this_start_range) * val[4] * subsidy_scalar
        result_dict['hostname'] = flxbx
        result_dict['limit'] = limit
        result_dict['last_%'] = previously_crossed
        result_dict['cost'] = int(cost_energia)
        result_dict['current_%'] = float(energia)/float(limit)*100
        result_dict['start_range'] = start_range
        if end_range == 1000000:
            end_range = ''
        result_dict['end_range'] = end_range
        result_dict['price'] = price
        result_dict['energy'] = str(int(energia))+'/'+str(limit)
        result_dict['last_sent_percent'] = last_text_sent
        result_dict['last_received'] = last_date_sent
        result_dict['last_sent_kwh'] = last_text_sent_kwh
        if last_text_sent_kwh!=None and last_text_sent and last_text_sent_kwh > last_text_sent:
            result_dict['datetime'] = last_text_sent_kwh
        elif last_text_sent_kwh!=None and last_text_sent and last_text_sent_kwh < last_text_sent:
            result_dict['datetime'] = last_text_sent
        elif last_text_sent_kwh!=None:
            result_dict['datetime'] = last_text_sent_kwh
        elif last_text_sent_percent!=None:
            result_dict['datetime'] = last_text_sent
        else:
            result_dict['datetime'] = last_date_sent

        text_count = len(flexbox_db_server_table_dict['twilio_sent'].select().\
            where(text("hostname='"+flxbx+"'")).\
            where(cast(flexbox_db_server_table_dict['twilio_sent'].c.date_last,Date)==last_date).\
            order_by(flexbox_db_server_table_dict['twilio_sent'].\
            c.datetime.desc()).execute().fetchall())

        result_dict['text_count'] = text_count
        output['last_record'] =  result_dict['datetime'].strftime(fmt)
        output['since_last_record'] = (datetime.utcnow() - result_dict['datetime']).total_seconds()

        if float(output['since_last_record']) > error_seconds_since_last_record_twilio:
             output['status'] = 'ERROR'
        else:
            output['status'] = 'GOOD'
        output['result'] = [result_dict]

    return output

def sql_results_to_dict(columns,rows,table_name_for_d3_conversion=None,convert_for_d3=False,fix_utc=True):
    all_rows = []
    most_recent_entry = None
    if rows and len(rows)>0:
        most_recent_entry = rows[0]['datetime']-timedelta(hours=6)
        for row in rows:
            row_object = {}
            contains_data = False
            for i,column in enumerate(columns):
                if column == 'datetime':
                    if convert_for_d3 or not fix_utc:
                        row_object[column] = row[i]#conversion happens in adjust_for_d3 depending on table
                    else:
                        row_object[column] = row[i]-timedelta(hours=6)#.replace(tzinfo=localtz)

                elif row[i]!=None:
                    row_object[column] = row[i]
                if row[i]!=None and column not in ['id','hostname','datetime']:
                    contains_data = True
            if contains_data==True:
                if convert_for_d3:
                    row_object = adjust_values_for_d3(table_name_for_d3_conversion,row_object)
                if row_object:
                    all_rows.append(row_object)
    return all_rows,most_recent_entry

def adjust_values_for_d3(table_name,row_object):
    if table_name == "inside_temps":
        row_object['datetime'] = (row_object['datetime']-timedelta(hours=6)).strftime("%Y%m%d%H%M%S")
        if 'inside_temp1' in row_object.keys() and 'inside_temp2' in row_object.keys():
            row_object['value_to_plot'] = (row_object['inside_temp1']+row_object['inside_temp2'])/2.0/1000.0
        elif 'inside_temp1' in row_object.keys():
            row_object['value_to_plot'] = (row_object['inside_temp1'])/1000.0
        elif 'inside_temp2' in row_object.keys():
            row_object['value_to_plot'] = (row_object['inside_temp2'])/1000.0
        return {key:row_object[key] for key in ['value_to_plot','datetime']}
    if table_name == "fridge_power":
        row_object['datetime'] = (row_object['datetime']-timedelta(hours=6)).strftime("%Y%m%d%H%M%S")
        if 'relay3' in row_object.keys():
            row_object['value_to_plot'] = row_object['relay3']
            return row_object
    if table_name == "house_power":
        row_object['datetime'] = (row_object['datetime']-timedelta(hours=6)).strftime("%Y%m%d%H%M%S")
        if 'houseAll_Power' in row_object.keys():
            row_object['value_to_plot'] = row_object['houseAll_Power']
            return {key:row_object[key] for key in ['value_to_plot','datetime']}
    if table_name == "peak_shifting_dr":
        row_object['datetime_start'] = row_object['datetime'].strftime("%Y%m%d%H%M%S")
        row_object['datetime_end'] = (row_object['datetime']+timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
        row_object['datetime'] = (row_object['datetime']).strftime("%Y%m%d%H%M%S")

        if 'signal' in row_object and row_object['signal']==1:
            row_object['value_to_plot'] = 1
        else:
            row_object['value_to_plot'] = 0
        return {key:row_object[key] for key in ['value_to_plot','datetime','datetime_start','datetime_end']}

def get_flexbox_rows(table,num,flxbxNum,error_seconds_since_last_record=60,convert_for_d3=False,
        columns=None,since=None):
    if since!=None:
        values = table.select().where(table.c.hostname == flxbxNum)\
        .where(table.c.datetime>since)\
        .order_by(table.c.datetime.desc()).limit(num)
    else:
        values = table.select().where(table.c.hostname == flxbxNum).order_by(table.c.datetime.desc()).limit(num)
    result = values.execute()
    if num==1:
        rows = result.fetchone()
        if rows!=None:
            rows = [rows]
    else:
        rows = result.fetchall()
    if not columns:
        columns = result.keys()
    output = {}
    all_rows,most_recent_entry = sql_results_to_dict(columns,rows,table.name,convert_for_d3)
    if most_recent_entry:
        output['result'] = all_rows
        output['last_record'] =  most_recent_entry.strftime(fmt)
        output['since_last_record'] = (datetime.utcnow() - rows[0]['datetime']).total_seconds()

        if len(rows) > 0 and float(output['since_last_record']) > error_seconds_since_last_record:
             output['status'] = 'ERROR'
        elif len(rows) > 0:
            output['status'] = 'GOOD'
    return output


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    with open('login.yaml') as f:
        cf = yaml.safe_load(f)
    return username in cf.keys() and password == cf[username]

def check_auth_cosmos(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    with open('login_cosmos.yaml') as f:
        cf = yaml.safe_load(f)
    return username in cf.keys() and password == cf[username]

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@application.route("/twilioSent")
def print_twilio_sent():
    flexboxes = []
    for val in range(1,30):
        flexbox_last_value = get_twilio_sent("flxbxD"+str(val))
        if flexbox_last_value:
            flexboxes.append(flexbox_last_value)
    return jsonify({'flexboxes':flexboxes})

@application.route("/plotTemps")
def print_plot_temps():
    return jsonify(get_plot_temps())

@application.route("/networkTests")
def print_network_tests():
    flexboxes = []
    for val in range(1,30):
        flexbox_last_value = get_network("flxbxD"+str(val))
        if flexbox_last_value:
            flexboxes.append(flexbox_last_value)
    return jsonify({'flexboxes':flexboxes})

@application.route("/flexboxStatuses")
def print_network_flexbox_statuses():
    flexboxes = []
    for val in range(1,30):
        flexbox_last_value = get_flexbox_status("flxbxD"+str(val))
        if flexbox_last_value and 'hostname' in flexbox_last_value['result'][0]:
            flexboxes.append(flexbox_last_value)
    return jsonify({'flexboxes':flexboxes})


@application.route("/flexboxStatuses2")
def print_network_flexbox_statuses2():
    flexboxes = []
    for val in range(1,30):
        flexbox_last_value = get_flexbox_status2("flxbxD"+str(val))
        if flexbox_last_value and 'result' in flexbox_last_value and 'hostname' in flexbox_last_value['result'][0]:
            flexboxes.append(flexbox_last_value)
    return jsonify({'flexboxes':flexboxes})


@application.route("/twilioStatuses")
def print_network_twilio_statuses():
    flexboxes = []
    for val in range(0,30):
        flexbox_last_value = get_twilio_status("flxbxD"+str(val))
        if flexbox_last_value:
            flexboxes.append(flexbox_last_value)
    return jsonify({'flexboxes':flexboxes})

@application.route("/anyData")
def print_data():
    hostname = request.args.get('hostname')
    number_rows = request.args.get('limit')
    table_name = request.args.get('table')
    last_week = request.args.get('last_week')
    d3 = request.args.get('d3')
    if d3 and d3.lower() == "true":
        convert_for_d3 = True;
    else:
        convert_for_d3 = False;
    if last_week and last_week.lower() == "true":
        if table_name in flexbox_db_server_table_dict.keys():
            output = get_flexbox_rows(flexbox_db_server_table_dict[table_name],
                number_rows,hostname,convert_for_d3=convert_for_d3,since=datetime.now()-timedelta(days=7))
    else:
        if table_name in flexbox_db_server_table_dict.keys():
            output = get_flexbox_rows(flexbox_db_server_table_dict[table_name],
                number_rows,hostname,convert_for_d3=convert_for_d3)
    return jsonify(output)


@application.route("/flexboxStatus")
def print_flexbox_status():
    hostname = request.args.get('hostname')
    output = get_flexbox_status(hostname)
    return jsonify(output)

@application.route("/twilioStatus")
def print_twilio_status():
    hostname = request.args.get('hostname')
    output = get_twilio_status(hostname)
    return jsonify(output)

@application.route("/signal")
def print_control_signal():
    with open('signals.json') as data_file:
        return jsonify(json.load(data_file))

@application.route("/signal_time")
def print_control_new_signal():
    with open('signals_time.json') as data_file:
        return jsonify(json.load(data_file))
@application.route("/signal_time_never")
def print_control_never_signal():
    with open('signals_time_never.json') as data_file:
        return jsonify(json.load(data_file))
#Pages
@application.route('/')
@requires_auth
def root():
    return application.send_static_file('flexboxStatuses2.html')

@application.route('/flexboxTwilioPage')
@requires_auth
def flexbox_twilio_page():
    return application.send_static_file('flexboxTwilio.html')

@application.route('/flexboxTwilioStatusesPage')
@requires_auth
def flexbox_twilio_statuses_page():
    return application.send_static_file('flexboxTwilioStatuses.html')

@application.route('/networkTestsPage')
@requires_auth
def network_tests_page():
    return application.send_static_file('networkTests.html')

@application.route('/flexboxStatusesPage')
@requires_auth
def flexbox_statuses_page():
    return application.send_static_file('flexboxStatuses.html')

@application.route('/flexboxStatuses2Page')
@requires_auth
def flexbox_statuses2_page():
    return application.send_static_file('flexboxStatuses2.html')

@application.route('/pythonPlotsPage')
@requires_auth
def plot_from_python_page():
    return application.send_static_file('flexboxPythonPlots.html')

@application.route('/plotTempsPage')
@requires_auth
def plot_temps_page():
    return application.send_static_file('plotTemps.html')

@application.route('/plotSingleFlexboxPage')
@requires_auth
def plot_single_flexbox_page():
    return application.send_static_file('plotSingleFlexbox.html')

@application.route('/<path:path>')
@requires_auth
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  #if '.json' in path:
    return application.send_static_file(path)


if __name__ == "__main__":
    application.run(host='0.0.0.0',port=5010,debug=True)
