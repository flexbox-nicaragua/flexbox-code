#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import socket
import sys
from flexbox import psql_server
from flexbox import flexbox_pb2
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import traceback
from multiprocessing import Process
import os,time

def load_columns(hostname, pbuff, col_names):
    output_dict = {'hostname':hostname}
    for out_key, key in col_names:
        if pbuff.HasField(key):
            output_dict[out_key] = getattr(pbuff,key)
        else:
            print 'missing ' + str(key)
    #print hostname
    output_dict['id'] = output_dict['datetime']
    return output_dict

def save_message(protobuff_message):
    metadata = psql_server.get_metadata()
    table_dict = psql_server.setup_tables(metadata)

    incoming_message = flexbox_pb2.heartbeat_message()
    incoming_message.ParseFromString(protobuff_message)
    hostname = incoming_message.hostname
    message_id = incoming_message.id
    print(str(hostname) + ' ' + str(message_id))

    ambient_keymap = (('id','id'), ('datetime', 'datetime'), ('ambient_temp', 'temperature'),
                      ('humidity', 'humidity'))
    output_dict = load_columns(hostname, incoming_message.ambient, ambient_keymap)
    try:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        psql_server.add_values_to_table(table_dict['ambient_table'],output_dict)
    except IntegrityError:
        print('Integrity Error (probably duplicate id) for ambient_table')
    except Exception:
        print(traceback.print_exc())

    inside_keymap = (('id','id'), ('datetime', 'datetime'), ('inside_temp1', 'temp1'),
                      ('inside_temp2', 'temp2'))
    output_dict = load_columns(hostname, incoming_message.inside_temps, inside_keymap)
    try:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        psql_server.add_values_to_table(table_dict['inside_table'],output_dict)
    except IntegrityError as ie:
        print('Integrity Error (probably duplicate id) for inside_table')
    except:
        print(traceback.print_exc())

    switch_keymap = (('id','id'), ('datetime', 'datetime'), ('switch', 'open'))
    output_dict = load_columns(hostname, incoming_message.switch, switch_keymap)
    try:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        psql_server.add_values_to_table(table_dict['switch_table'],output_dict)
    except IntegrityError:
        print('Integrity Error (probably duplicate id) for switch_table')
    except Exception:
        print(traceback.print_exc())


    fridge_power_keymap = (('id','id'), ('datetime', 'datetime'),
                           ('v_rms1', 'v_rms1'), ('v_rms2', 'v_rms2'), ('v_rms3', 'v_rms3'),
                           ('i_rms1', 'i_rms1'), ('i_rms2', 'i_rms2'), ('i_rms3', 'i_rms3'),
                           ('pf1', 'pf1'), ('pf2', 'pf2'), ('pf3', 'pf3'),
                           ('energy_sum1', 'energy_sum1'), ('energy_sum2', 'energy_sum2'),
                           ('energy_sum3', 'energy_sum3'), ('active_pwr1', 'active_pwr1'),
                           ('active_pwr2', 'active_pwr2'), ('active_pwr3', 'active_pwr3'),
                           ('relay1', 'relay1'), ('relay2', 'relay2'), ('relay3', 'relay3')
                          )
    output_dict = load_columns(hostname, incoming_message.fridge_power, fridge_power_keymap)
    try:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        psql_server.add_values_to_table(table_dict['mfi_table'],output_dict)
    except IntegrityError:
        print('Integrity Error (probably duplicate id) for mfi_table')
    except Exception:
        print traceback.print_exc()

    house_power_keymap = (('id','id'), ('datetime', 'datetime'),
                          ('houseAll_Voltage', 'houseAll_Voltage'),
                          ('houseAll_Current', 'houseAll_Current'),
                          ('houseAll_Power', 'houseAll_Power'),
                          ('houseAll_Energy', 'houseAll_Energy'),
                          ('house1_Voltage', 'house1_Voltage'),
                          ('house1_Current', 'house1_Current'),
                          ('house1_Power', 'house1_Power'),
                          ('house1_Energy', 'house1_Energy'),
                          ('house2_Voltage', 'house2_Voltage'),
                          ('house2_Current', 'house2_Current'),
                          ('house2_Power', 'house2_Power'),
                          ('house2_Energy', 'house2_Energy')
                         )
    output_dict = load_columns(hostname, incoming_message.house_power, house_power_keymap)
    try:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        psql_server.add_values_to_table(table_dict['zwave_table'],output_dict)
        if hostname=='flxbxD16':
            print output_dict
    except IntegrityError:
        print('Integrity Error (probably duplicate id) for zwave_table')
    except Exception:
        print traceback.print_exc()

    demand_response_keymap = (('id','id'), ('datetime', 'datetime'),
                           ('local_date', 'local_date'), ('mfi_state', 'mfi_state'),
                           ('control_source', 'control_source'),
                           ('control_type', 'control_type'), ('limit_counter', 'limit_counter'),
                           ('uptime_minutes','uptime_minutes')
                          )
    output_dict = load_columns(hostname, incoming_message.demand_response, demand_response_keymap)
    if 'datetime' in output_dict:
        output_dict['datetime'] = datetime.fromtimestamp(output_dict['datetime'])
        output_dict['local_date'] = datetime.fromtimestamp(output_dict['local_date'])
        if output_dict['datetime']>datetime(2000,1,1):
            try:
                psql_server.add_values_to_table(table_dict['demand_response'],output_dict)
            except IntegrityError:
                print('Integrity Error (probably duplicate id) for demand_response')
            except Exception:
                print traceback.print_exc()
        else:
            print 'Error receiving demand response protobuff, incorrect datetime received.'

TIMEOUT = 600
class myThread(Process):
    def __init__(self):
        Process.__init__(self)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(10)
        server_address = ('0.0.0.0', 10000)
        print('Starting up on %s port %s' % server_address)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(server_address)

        sock.listen(1)

        while True:
            print('waiting for a connection')
            connection, client_address = sock.accept()

            try:
                print('connection from: {0}'.format((client_address,)))
                data = connection.recv(1000)
                print('data length: {0}'.format(len(data),))
                if data:
                    save_message(data)
                    print('Sending ACK back to the client')
                    connection.sendall('ACK')
            except:
                print(traceback.print_exc())
            finally:
                connection.close()

while True:
    p = myThread()
    p.start()
    print("Main thread PID: {}".format(os.getpid()))
    print("Launched process PID: {}".format(p.pid))
    p.join(TIMEOUT)
    if p.is_alive:
        p.terminate()
