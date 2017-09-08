# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import Adafruit_DHT as DHT
import Adafruit_CharLCD as LCD
import subprocess
import time

inside_dest = '/sys/bus/w1/devices/'

def get_cat_from_file(directory):
    p = subprocess.Popen('cat '+directory,
                 shell=True,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)
    return p.communicate()

def get_ls_from_folder(directory):
    p = subprocess.Popen('ls '+ directory,
                 shell=True,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)
    return p.communicate()

def get_inside_fridge_ids():
    sens_ids = []
    stdout, stderr = get_ls_from_folder(inside_dest)
    if stderr:
        print 'Error getting sensor ids.'+ str(stderr)
    else:
        for line in stdout.split('\n'):
            if len(line) > 0 and 'master' not in line:
                sens_ids.append(line)
    sens_ids.sort()
    return sens_ids

def get_inside_fridge_temp(sens_id):
    sens_dest = inside_dest + sens_id + '/w1_slave' 
    stdout, stderr = get_cat_from_file(sens_dest)
    string = sens_id+': '
    val = None
    if len(stderr)>0:
        print stderr
    else:
        if 'YES' in stdout.split('\n')[0]:
            val = int(str(stdout.split('t=')[1]).replace('\n',''))
            string += 'Success ' + str(val)
        else:
            print 'Failed Checksum'
    
    return val

def get_inside_fridge_temps():
    vals = {}
    sens_ids = get_inside_fridge_ids()
    for sens_id in sens_ids:
        vals[sens_id] = get_inside_fridge_temp(sens_id)
    return vals

def get_magnetic_switch():
    num = '23'
    stdout,stderr = get_cat_from_file('/sys/class/gpio/gpio'+num+'/value')
    if '0' in stdout:
        return False
    elif '1' in stdout:
        return True
    else:
        subprocess.Popen('sudo echo '+num+' > /sys/class/gpio/export',shell=True)
        stdout,stderr = get_cat_from_file('/sys/class/gpio/gpio'+num+'/value')
        if '0' in stdout:
            return False
        elif '1' in stdout:
            return True
        else:
            return None


def get_button(num):
    stdout,stderr = get_cat_from_file('/sys/class/gpio/gpio'+num+'/value')
    if '0' in stdout:
        return True
    return False

def get_ambient_temp_humidity():
    humidity, temperature = DHT.read_retry(DHT.DHT22,18)
    if humidity is not None and temperature is not None:
        return [temperature,humidity]
    else:
        return [None,None]

def write_to_LCD(lcd,message):
    lcd.clear()
    lcd.show_cursor(True)
    lcd.message(message)
    lcd.move_right()
    lcd.move_left()

def get_time_rtc():
    p = subprocess.Popen('sudo hwclock -r',
                 shell=True,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE)
    stdout,stderr = p.communicate()
    return stdout.replace('\n','')



