#!/usr/bin/env python2
import os
import yaml
import json
import requests
from flexbox import psql,mfi,sensors
from sqlalchemy import cast,Date,text
from datetime import datetime, timedelta

def update_mfi_state_sql(table_ref,new_mfi_state,control_source,control_type,limit_counter):
    output_dict = {}
    output_dict['mfi_state'] = new_mfi_state
    output_dict['control_source'] = control_source
    output_dict['control_type'] = control_type
    output_dict['local_date'] = datetime.now().date()
    output_dict['limit_counter'] = limit_counter
    output_dict['uptime_minutes'] = get_system_uptime()
    psql.add_values_to_table(table_ref,output_dict)


def get_system_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds/60.0
    except:
        return -1.0
    return -1.0

def get_signal_from_dict(json_signal):
    current_command = None
    new_mfi_state = 1
    control_type = 'none'
    if 'start_time' in json_signal['peak_shifting_event']:
        last_start_peak = json_signal['peak_shifting_event']['start_time']
        last_duration_peak = json_signal['peak_shifting_event']['duration_minutes']
        last_start_peak_datetime = datetime.\
                strptime(last_start_peak,'%Y-%m-%d %H:%M:%S')
        print 'Last Peak Event Start:'+str(last_start_peak_datetime)
        print 'Last Peak Event End:'+str(last_start_peak_datetime+timedelta(minutes=int(last_duration_peak)))
        if datetime.now()<last_start_peak_datetime+timedelta(minutes=int(last_duration_peak)):
            control_type = 'peak_shaving'
            current_command = 1
            new_mfi_state = 1 - current_command
    elif 'start_time' in json_signal['net_load_event']:
        last_start_net_load = json_signal['net_load_event']['start_time']
        last_duration_net_load = json_signal['net_load_event']['duration_minutes']
        last_start_net_load_datetime = datetime.\
                strptime(last_start_net_load,'%Y-%m-%d %H:%M:%S')
        print 'Last Net Load Event Start:'+str(last_start_net_load_datetime)
        print 'Last Net Load Event End:'+str(last_start_net_load_datetime+timedelta(minutes=int(last_duration_net_load)))
        if datetime.now()<last_start_net_load_datetime+timedelta(minutes=int(last_duration_net_load)):
            control_type = 'net_load'
            current_command = 1
            new_mfi_state = 1 - current_command
    else:
        current_command = 0
        control_type = 'none'
        new_mfi_state = 1 - current_command
    return current_command,new_mfi_state,control_type

def get_signal_from_server():
    current_command = None
    control_type = 'none'
    new_mfi_state = 1
    json_signal = None
    lost_connection_to_server = False
    try:
        r = requests.get('http://yourserverdomain.com/signal_time')
        json_signal = r.json()
        with open("signals_local.json","wb") as outfile:
            json.dump(json_signal,outfile,indent=4)
        current_command,new_mfi_state,control_type = get_signal_from_dict(json_signal)
    except Exception,e:
        print str(e)
        lost_connection_to_server = True
        current_command = None
        new_mfi_state = 1
        control_type = 'none'

    '''
    Testing
    control_type = 'none'#'net_load'
    new_mfi_state = 1#1
    #current_command = 1-new_mfi_state
    current_command = None#None#1
    lost_connection_to_server = True #True
    '''
    return lost_connection_to_server,current_command,new_mfi_state,control_type

def dr_local_control(mfi_hostname,mfi_outlet):
    '''
    current_command: The command that has been pulled from the server.

    new_mfi_state: The state to be sent to the mfi. It is typically the opposite of the current_command variable.
    For example, if the command is 1 because a peak shaving event is occuring, the new_mfi_state = 0.
    This relationship breaks down during other constraints, such as:
    -if the fridge has already been off past its required number of hours
    -if the fridge crosses past its upper deadband + X degrees.
    -if the connection is lost to the server.

    last_command: The previous command that the script registered from the server.
    1 indicates a peak shaving event, 0 indicates no peak shaving event.

    (DEPRECATED) last_command_datetime: The time (in utc) of the most recent registered command from the server.
    This is used in addition to the limit_counter to determine whether max_off_hours has been reached.

    (DEPRECATED) last_limit_counter: The time (in seconds) that have so far been counted against the max_off_hours variable.
    This is used to store the time spent during previous events when there are multiple events within one day.

    last_control_source: The source of the most recent control signal for the mfi.
    The two current options are:
    'server' (as in it read the value direct from the server) or
    'required_to_be_off' (as in it stopped participating in the event because it is during a time that it has been
    hardcoded to remain off)
    '''

    current_temp_list = sensors.get_inside_fridge_temps().values()
    current_temp_list = [temp for temp in current_temp_list if temp<50000 and temp>-25000]
    current_temp = float(sum(value for value in current_temp_list)/len(current_temp_list))/1000.0
    control_source = 'server'
    #Signal
    lost_connection_to_server,current_command,new_mfi_state,control_type = get_signal_from_server()


    #Limits based on type of DR signal
    with open('/etc/flexbox/demand_response.yaml') as f:
        dr_properties = yaml.safe_load(f)
    available_hours_list = dr_properties['available_hours_list']
    upper_temp_band = dr_properties['upper_temp_band']

    if control_type == 'peak_shaving':
        upper_temp_plus = dr_properties['upper_temp_band_plus_peak_shaving']
    elif control_type == 'net_load':
        upper_temp_plus = dr_properties['upper_temp_band_plus_net_load']
    else:
        upper_temp_plus = 0
    #Previous command information
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)

    status = ''
    last_row_dict_mfi = {}
    column_names_mfi = table_dict['mfi_table'].columns.keys()
    last_row_mfi = table_dict['mfi_table'].select().\
        where(table_dict['mfi_table'].c.datetime>datetime.utcnow()-timedelta(minutes=10)).\
        order_by(table_dict['mfi_table'].c.datetime.desc()).execute().fetchone()
    if last_row_mfi:
        for i,column in enumerate(column_names_mfi):
            last_row_dict_mfi[column] = last_row_mfi[i]
        actual_mfi_state = last_row_dict_mfi['relay3']
    else:
        actual_mfi_state = None
        status+= 'No MFI state read, will send signal. '
    status+= 'Actual MFI state currently is '+str(actual_mfi_state) + '. '



    column_names = table_dict['demand_response'].columns.keys()
    last_row = table_dict['demand_response'].select().\
        where(cast(table_dict['demand_response'].c.local_date,Date)==datetime.now().date()).\
        order_by(table_dict['demand_response'].c.datetime.desc()).execute().fetchone()

    last_row_peak_shaving = table_dict['demand_response'].select().\
        where(table_dict['demand_response'].c.mfi_state==0).\
        where(table_dict['demand_response'].c.control_type=='peak_shaving').\
        where(table_dict['demand_response'].c.control_source=='server').\
        order_by(table_dict['demand_response'].c.datetime.desc()).execute().fetchone()

    last_row_net_load = table_dict['demand_response'].select().\
        where(table_dict['demand_response'].c.mfi_state==0).\
        where(table_dict['demand_response'].c.control_type=='net_load').\
        where(table_dict['demand_response'].c.control_source=='server').\
        order_by(table_dict['demand_response'].c.datetime.desc()).execute().fetchone()

    last_row_net_load_dict = {}
    last_row_peak_shaving_dict = {}
    if last_row_net_load:
        for i,column in enumerate(column_names):
            last_row_net_load_dict[column] = last_row_net_load[i]

    if last_row_peak_shaving:
        for i,column in enumerate(column_names):
            last_row_peak_shaving_dict[column] = last_row_peak_shaving[i]

    last_row_dict = {}
    last_mfi_state = None
    last_control_source = None
    required_fridge_is_off = datetime.now().hour not in available_hours_list
    if last_row:
        for i,column in enumerate(column_names):
            last_row_dict[column] = last_row[i]
        last_command = 1 - last_row_dict['mfi_state']
        last_mfi_state = last_row_dict['mfi_state']
        last_command_datetime = last_row_dict['datetime']
        last_limit_counter = last_row_dict['limit_counter']
        last_control_type = last_row_dict['control_type']
        last_control_source = last_row_dict['control_source']
        limit_counter = (datetime.utcnow() - last_command_datetime).seconds+last_limit_counter
        updated_limit_counter = limit_counter

    if required_fridge_is_off:
        new_mfi_state = 0
        control_source = 'required_to_be_off'
        control_type = 'none'
        status+='This is not available for DR at this hour. '
        if last_row and last_mfi_state == 1:
            updated_limit_counter = last_limit_counter
        if last_row and last_control_source == 'required_to_be_off':
            updated_limit_counter = last_limit_counter
        elif not last_row:
            updated_limit_counter = 0
        else:
            updated_limit_counter = limit_counter
    elif last_row:

        #Constraints
        upper_temp_band_plus_reached = current_temp > (upper_temp_band+upper_temp_plus)
        return_to_upper_temp_band_reached = current_temp < upper_temp_band

        print 'is fridge supposed to be hardcoded off right now?' + str(required_fridge_is_off)
        if not lost_connection_to_server:

            print 'Last Signal:'+str(last_command)
            print 'Last limit counter:'+str(last_limit_counter)
            print 'Current limit counter:'+str(limit_counter)
            print 'hours that fridge is available for DR:'+str(available_hours_list)
            print 'Current temp is '+str(current_temp) + " with band+limit as " + str(upper_temp_band) + " + " + str(upper_temp_plus)

        if lost_connection_to_server:
            print 'Lost connection at: '+str(datetime.now())
            print 'Last limit counter:'+str(last_limit_counter)
            control_source = 'lost_connection_to_server'
            try:
                with open("signals_local.json","rb") as infile:
                    json_signal = json.load(infile)
                current_command,new_mfi_state,control_type = get_signal_from_dict(json_signal)
            except:
                print "Can't read from json file and lost connection to server"
                pass
        elif current_command == 1:
            print 'Current Signal:'+str(current_command)
            if last_command == 1 and upper_temp_band_plus_reached:
                new_mfi_state = 1
                status+='However, this has exceeded the upper temperature limit, '+\
                    'so we are overriding until we cool down to the upper band.'
                control_source = 'max_temp_limit_reached'
            elif last_command == 1 and last_control_source == 'required_to_be_off':
                status+='This is now available and engaged in a DR event. '
            elif last_command == 1 and last_control_source == 'lost_connection_to_mfi':
                status+='This DR event is starting because mfi connection returned. '
            elif last_command == 1:
                status+='This DR event is continuing. '
            elif last_command == 0 and last_control_source in [ 'max_temp_limit_reached',\
                                                                'lost_connection_to_server',\
                                                                'lost_connection_to_mfi']:
                updated_limit_counter = last_limit_counter
                if last_control_source in ['lost_connection_to_server','lost_connection_to_mfi']:
                    status+='The last entry in the database was a lost connection value,'+\
                        ' so we are writing to indicate connection was restored. '
                elif return_to_upper_temp_band_reached:
                    status+='We are no longer above the upper band, so we are joining the DR event again. '
                else:
                    new_mfi_state = 1
                    control_source = last_control_source
                    status+='This DR event is being overriden by '+last_control_source+'. '
            elif last_command == 0:
                updated_limit_counter = last_limit_counter
                status+='We were given the signal to begin a new DR event. '
        elif current_command == 0:
            if last_command == 1 and last_control_source == 'required_to_be_off':
                status+='We are now available for DR events again.'
                updated_limit_counter = last_limit_counter
            elif last_command == 1:
                status+='We were given the signal to stop this DR event. '
            elif last_command == 0 and last_control_source == 'lost_connection_to_server':
                updated_limit_counter = last_limit_counter
                status+='We are not in a DR event but we have re-established the server connection. '
            elif last_command == 0 and last_control_source == 'lost_connection_to_mfi':
                status+='We are not in a DR event but we have re-established the mfi connection. '
                updated_limit_counter = last_limit_counter
            elif last_command == 0 and last_control_source == 'max_temp_limit_reached':
                status+='We are not in a DR event so we no longer need to worry about temperature limits. '
                updated_limit_counter = last_limit_counter
            elif last_command == 0:
                status+='We are not in a DR event. '
    elif not lost_connection_to_server:
        updated_limit_counter = 0
        status+='No previous command yet today. '
        '''
        if required_fridge_is_off:
            new_mfi_state = 0
            control_source = 'required_to_be_off'
            control_type = 'none'
            status+='This is not available for DR at this hour. '
        '''
        if current_command == 1:
            status+='Beginning first DR event. '
            updated_limit_counter = 0
        elif current_command == 0:
            pass
    else:
        updated_limit_counter = 0
        control_source = 'lost_connection_to_server'
        status+='Has not yet found a connection to server: '+str(datetime.now())+'. '

    if actual_mfi_state == None or actual_mfi_state != new_mfi_state:
        status+= 'Send Command to MFI.'
        mfi_success = mfi.control_mfi(mfi_hostname,new_mfi_state,mfi_outlet)
        print mfi_success
        print 'Last actual mfi state was ' + str(actual_mfi_state)
        print 'Last recorded mfi state was ' + str(last_mfi_state)
        print 'Currently sending mfi state as ' + str(new_mfi_state)
        if not mfi_success:
            status += 'Lost connection to mfi. '
            control_source = 'lost_connection_to_mfi'

    status+='Adding a row to the database. '
    update_mfi_state_sql(table_dict['demand_response'],new_mfi_state,control_source,control_type,updated_limit_counter)

    print status

if __name__ == "__main__":
    mfi_hostname = '10.10.10.101'
    mfi_outlet = 3
    dr_local_control(mfi_hostname,mfi_outlet)

