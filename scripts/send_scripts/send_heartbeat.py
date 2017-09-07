#!/usr/bin/env python2
from flexbox import flexbox_pb2
from flexbox import psql
from datetime import datetime
import socket
import time
import sys

FREQUENCY = 1

metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)


def create_message(ambient_val,inside_val,switch_val,mfi_val,zwave_val):
    message = flexbox_pb2.heartbeat_message()
    message.hostname = socket.gethostname()
    message.id = int(datetime.utcnow().strftime("%s"))
    message.ambient.id = ambient_val[0]
    message.ambient.datetime = int(ambient_val[1].strftime("%s"))
    message.ambient.temperature = ambient_val[2]
    message.ambient.humidity = ambient_val[3]
    message.inside_temps.id = inside_val[0]
    message.inside_temps.datetime = int(inside_val[1].strftime("%s"))
    temp1 = inside_val[2]
    temp2 = inside_val[3]
    if inside_val[2] == None:
        temp1 = 85000
    if inside_val[3] == None:
        temp2 = 85000
    message.inside_temps.temp1 = temp1
    message.inside_temps.temp2 = temp2

    message.switch.id = switch_val[0]
    message.switch.datetime = int(switch_val[1].strftime("%s"))
    message.switch.open = switch_val[2]

    message.fridge_power.id = mfi_val[0]
    message.fridge_power.datetime = int(mfi_val[1].strftime("%s"))
    message.fridge_power.v_rms1 = mfi_val[2]
    message.fridge_power.v_rms2 = mfi_val[3]
    message.fridge_power.v_rms3 = mfi_val[4]
    message.fridge_power.i_rms1 = mfi_val[5]
    message.fridge_power.i_rms2 = mfi_val[6]
    message.fridge_power.i_rms3 = mfi_val[7]
    message.fridge_power.pf1 = mfi_val[8]
    message.fridge_power.pf2 = mfi_val[9]
    message.fridge_power.pf3 = mfi_val[10]
    message.fridge_power.energy_sum1 = mfi_val[11]
    message.fridge_power.energy_sum2 = mfi_val[12]
    message.fridge_power.energy_sum3 = mfi_val[13]
    message.fridge_power.active_pwr1 = mfi_val[14]
    message.fridge_power.active_pwr2 = mfi_val[15]
    message.fridge_power.active_pwr3 = mfi_val[16]
    message.fridge_power.relay1 = mfi_val[17]
    message.fridge_power.relay2 = mfi_val[18]
    message.fridge_power.relay3 = mfi_val[19]

    message.house_power.id = zwave_val[0]
    message.house_power.datetime = int(zwave_val[1].strftime("%s"))
    message.house_power.houseAll_Voltage = zwave_val[2]
    message.house_power.houseAll_Current = zwave_val[3]
    message.house_power.houseAll_Power = zwave_val[4]
    message.house_power.houseAll_Energy = zwave_val[5]

    message.house_power.house1_Voltage = zwave_val[6]
    message.house_power.house1_Current = zwave_val[7]
    message.house_power.house1_Energy = zwave_val[8]
    message.house_power.house1_Power = zwave_val[9]

    message.house_power.house2_Voltage = zwave_val[10]
    message.house_power.house2_Current = zwave_val[11]
    message.house_power.house2_Energy = zwave_val[12]
    message.house_power.house2_Power = zwave_val[13]
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
        finally:
            sys.stdout.write('.')
            sys.stdout.flush()
            sock.close()
    except (socket.error, socket.herror, socket.gaierror, socket.timeout) as e:
        print(e)

def main():
    print('Starting hearbeat.')
    target_modulus_ms = int(1/FREQUENCY*1000)
    old_mfi_val = None
    while True:
        start = time.time()
        ambient_val = table_dict['ambient_table'].select().order_by(table_dict['ambient_table'].c.id.desc()).limit(1).execute().fetchone()
        inside_val = table_dict['inside_table'].select().order_by(table_dict['inside_table'].c.id.desc()).limit(1).execute().fetchone()
        mfi_val = table_dict['mfi_table'].select().order_by(table_dict['mfi_table'].c.id.desc()).limit(1).execute().fetchone()
        switch_val = table_dict['switch_table'].select().order_by(table_dict['switch_table'].c.id.desc()).limit(1).execute().fetchone()
        zwave_val = table_dict['zwave_table'].select().order_by(table_dict['zwave_table'].c.id.desc()).limit(1).execute().fetchone()
        if zwave_val and switch_val and mfi_val and inside_val and ambient_val and (mfi_val!=old_mfi_val):
            message = create_message(ambient_val,inside_val,switch_val,mfi_val,zwave_val).SerializeToString()
            #print 'MFI: ' + str(mfi_val)
            overhead = time.time() - start
            #print(overhead)
            print message
            send_packet(message)

            cur_time = time.time() * 1000
            next_send = target_modulus_ms - (int(cur_time) % target_modulus_ms)
            #print(next_send)
            wait = float(next_send)/1000 - overhead
            if wait > 0:
                time.sleep(wait)
        old_mfi_val = mfi_val
if __name__ == '__main__':
    main()
