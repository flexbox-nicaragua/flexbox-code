#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flexbox import flexbox_pb2
from flexbox import psql
from datetime import datetime
import socket
import time
import sys

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)


def create_message(ambient_val,inside_val,switch_val,mfi_val,zwave_val,dr_val):
    message = flexbox_pb2.heartbeat_message()
    message.hostname = socket.gethostname()
    message.id = int(datetime.utcnow().strftime("%s"))
    if ambient_val!=None:
        if ambient_val[0]!=None:
            message.ambient.id = ambient_val[0]
        if ambient_val[1]!=None:
            message.ambient.datetime = int(ambient_val[1].strftime("%s"))
        if ambient_val[2]!=None:
            message.ambient.temperature = ambient_val[2]
        if ambient_val[3]!=None:
            message.ambient.humidity = ambient_val[3]
    if inside_val!=None:
        if inside_val[0]!=None:
            message.inside_temps.id = inside_val[0]
        if inside_val[1]!=None:
            message.inside_temps.datetime = int(inside_val[1].strftime("%s"))
        temp1 = inside_val[2]
        temp2 = inside_val[3]
        if inside_val[2] == None:
            temp1 = 85000
        if inside_val[3] == None:
            temp2 = 85000

        message.inside_temps.temp1 = temp1
        message.inside_temps.temp2 = temp2
    if switch_val!=None:
        if switch_val[2]!=None:
            message.switch.id = switch_val[0]
            message.switch.datetime = int(switch_val[1].strftime("%s"))
            message.switch.open = switch_val[2]
    if mfi_val!=None:
        if mfi_val[0]!=None:
            message.fridge_power.id = mfi_val[0]
        if mfi_val[1]!=None:
            message.fridge_power.datetime = int(mfi_val[1].strftime("%s"))
        if mfi_val[2]!=None:
            message.fridge_power.v_rms1 = mfi_val[2]
        if mfi_val[3]!=None:
            message.fridge_power.v_rms2 = mfi_val[3]
        if mfi_val[4]!=None:
            message.fridge_power.v_rms3 = mfi_val[4]
        if mfi_val[5]!=None:
            message.fridge_power.i_rms1 = mfi_val[5]
        if mfi_val[6]!=None:
            message.fridge_power.i_rms2 = mfi_val[6]
        if mfi_val[7]!=None:
            message.fridge_power.i_rms3 = mfi_val[7]
        if mfi_val[8]!=None:
            message.fridge_power.pf1 = mfi_val[8]
        if mfi_val[9]!=None:
            message.fridge_power.pf2 = mfi_val[9]
        if mfi_val[10]!=None:
            message.fridge_power.pf3 = mfi_val[10]
        if mfi_val[11]!=None:
            message.fridge_power.energy_sum1 = mfi_val[11]
        if mfi_val[12]!=None:
            message.fridge_power.energy_sum2 = mfi_val[12]
        if mfi_val[13]!=None:
            message.fridge_power.energy_sum3 = mfi_val[13]
        if mfi_val[14]!=None:
            message.fridge_power.active_pwr1 = mfi_val[14]
        if mfi_val[15]!=None:
            message.fridge_power.active_pwr2 = mfi_val[15]
        if mfi_val[16]!=None:
            message.fridge_power.active_pwr3 = mfi_val[16]
        if mfi_val[17]!=None:
            message.fridge_power.relay1 = mfi_val[17]
        if mfi_val[18]!=None:
            message.fridge_power.relay2 = mfi_val[18]
        if mfi_val[19]!=None:
            message.fridge_power.relay3 = mfi_val[19]

    if zwave_val!=None:
        if zwave_val[0]!=None:
            message.house_power.id = zwave_val[0]
        if zwave_val[1]!=None:
            message.house_power.datetime = int(zwave_val[1].strftime("%s"))
        if zwave_val[2]!=None:
            message.house_power.houseAll_Voltage = zwave_val[2]
        if zwave_val[3]!=None:
            message.house_power.houseAll_Current = zwave_val[3]
        if zwave_val[4]!=None:
            message.house_power.houseAll_Power = zwave_val[4]
        if zwave_val[5]!=None:
            message.house_power.houseAll_Energy = zwave_val[5]

        if zwave_val[6]!=None:
            message.house_power.house1_Voltage = zwave_val[6]
        if zwave_val[7]!=None:
            message.house_power.house1_Current = zwave_val[7]
        if zwave_val[8]!=None:
            message.house_power.house1_Energy = zwave_val[8]
        if zwave_val[9]!=None:
            message.house_power.house1_Power = zwave_val[9]
        if zwave_val[10]!=None:
            message.house_power.house2_Voltage = zwave_val[10]
        if zwave_val[11]!=None:
            message.house_power.house2_Current = zwave_val[11]
        if zwave_val[12]!=None:
            message.house_power.house2_Energy = zwave_val[12]
        if zwave_val[13]!=None:
            message.house_power.house2_Power = zwave_val[13]

    if dr_val!=None:
        if dr_val[0]!=None:
            message.demand_response.id = dr_val[0]
        if dr_val[1]!=None:
            message.demand_response.datetime = int(dr_val[1].strftime("%s"))
        if dr_val[2]!=None:
            message.demand_response.local_date = int(dr_val[2].strftime("%s"))
        if dr_val[3]!=None:
            message.demand_response.mfi_state = dr_val[3]
        if dr_val[4]!=None:
            message.demand_response.control_source = dr_val[4]
        if dr_val[5]!=None:
            message.demand_response.control_type = dr_val[5]
        if dr_val[6]!=None:
            message.demand_response.limit_counter = dr_val[6]
        if dr_val[7]!=None:
            message.demand_response.uptime_minutes = dr_val[7]

    return message

def send_packet(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = ('yourserverdomain.com', 10000)
    #print('connecting to {0} port {0}'.format((server_address,)))

    try:
        sock.connect(server_address)
        try:
            # Send data
            sys.stdout.write('o')
            sys.stdout.flush()
            sock.sendall(message)

            # Look for the response
            amount_received = 0
            amount_expected = 3
            '''
            while amount_received < amount_expected:
                data = sock.recv(3)
                amount_received += len(data)
                #print >>sys.stderr, 'received "%s"' % data
            print
            '''
            print 'Packet sent at ' + str(datetime.now())
        finally:
            sys.stdout.write('.')
            sys.stdout.flush()
            sock.close()
    except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
        print(e)

def main():
    start = time.time()
    ambient_val = table_dict['ambient_table'].select().order_by(table_dict['ambient_table'].c.id.desc()).limit(1).execute().fetchone()
    inside_val = table_dict['inside_table'].select().order_by(table_dict['inside_table'].c.id.desc()).limit(1).execute().fetchone()
    mfi_val = table_dict['mfi_table'].select().order_by(table_dict['mfi_table'].c.id.desc()).limit(1).execute().fetchone()
    switch_val = table_dict['switch_table'].select().order_by(table_dict['switch_table'].c.id.desc()).limit(1).execute().fetchone()
    zwave_val = table_dict['zwave_table'].select().order_by(table_dict['zwave_table'].c.id.desc()).limit(1).execute().fetchone()
    dr_val = table_dict['demand_response'].select().order_by(table_dict['demand_response'].c.id.desc()).limit(1).execute().fetchone()
    print dr_val
    message = create_message(ambient_val,inside_val,switch_val,mfi_val,zwave_val,dr_val).SerializeToString()
    print 'MFI: ' + str(mfi_val)
    print zwave_val
    overhead = time.time() - start
    #print(overhead)
    send_packet(message)

if __name__ == '__main__':
    main()
