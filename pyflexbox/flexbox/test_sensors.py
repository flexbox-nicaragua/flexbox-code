import Adafruit_CharLCD as LCD
from flexbox import mfi
import subprocess
import time

from flexbox import sensors

def test_LCD():
    lcd_rs = 25
    lcd_en = 24
    lcd_d4 = 5
    lcd_d5 = 13
    lcd_d6 = 19
    lcd_d7 = 26
    lcd_columns = 16
    lcd_rows = 2
    lcd_backlight = 6
    lcd = LCD.Adafruit_CharLCD(lcd_rs,lcd_en,lcd_d4,lcd_d5,lcd_d6,
        lcd_d7,lcd_columns,lcd_rows,lcd_backlight)

    sensors.write_to_LCD(lcd,'Test Message 1')
    print 'It should say "Test Message 1" on the screen'
    time.sleep(3.0)
    sensors.write_to_LCD(lcd,'Blues\nBrothers')
    print 'It should say "Blues Brothers" across two lines of the screen'
    time.sleep(3.0)
    lcd.clear()

def test_LEDs():
    print 'LED Testing'
    num = '22'
    test_LED('22')
    test_LED('17')
    test_LED('27')

def test_buttons():
    print 'Button Testing'
    test_button('21')
    test_button('20')
    test_button('16')
    test_button('12')

def test_button(num):
    print 'Testing buttons. You will have to hold down each button for 5 seconds.'
    pushed_count = 0
    total_count = 0
    button_pushed = False
    while not button_pushed and total_count<100:
        time.sleep(0.2)
        total_count +=1
        if sensors.get_button(num):
            pushed_count += 1
        else:
            pushed_count = 0
        if pushed_count>4:
            button_pushed = True
        print 'Button ' + num +' Pressed?: ' + str(button_pushed)+ ', count='+str(pushed_count)
    if button_pushed:
        print 'Button successfully pressed'
    else:
        print 'ERROR: Button never pressed'


def i2c_test():
    p = subprocess.Popen('sudo i2cdetect -y 1',
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if '68' in stdout:
        print 'I2C connected but not configured (68)'
    elif 'UU' in stdout:
        print 'I2C connected and configured.'
        print 'Real Time is ' + str(sensors.get_time_rtc())
    else:
        print 'ERROR: I2C not detected.'

def test_magnetic_switch():
    switch_closed = False
    closed_count = 0
    total_count = 0
    while not switch_closed and total_count<100:
        time.sleep(0.2)
        total_count +=1
        if not sensors.get_magnetic_switch():
            closed_count +=1
        else:
            closed_count = 0
        if closed_count>4:
            switch_closed = True
        print 'Switched Closed?: ' + str(switch_closed)+ ', count='+str(closed_count)
    if switch_closed:
        print 'Switch successfully closed'
    else:
        print 'ERROR: Switch never closed'

def test_LED(num):
    subprocess.Popen('sudo sh -c \'echo "out" > /sys/class/gpio/gpio'+num+'/direction\'',shell=True)
    subprocess.Popen('sudo echo 1 > /sys/class/gpio/gpio'+num+'/value',shell=True)
    print 'LED should be on...'
    time.sleep(1)
    subprocess.Popen('sudo echo 0 > /sys/class/gpio/gpio'+num+'/value',shell=True)
    print 'LED should now be off.'

def test_inside_fridge_temps():
    print 'Testing Inside Fridge Temp Sensors'
    print 'Temps:'+str(sensors.get_inside_fridge_temps())

def test_ambient_temp_humidity():
    print 'Testing Ambient Temp/Humidity'
    [temperature,humidity] = sensors.get_ambient_temp_humidity()
    if temperature and humidity:
    	print'Temp={0:0.1f}*C Humidity={1:0.1f}%'.format(temperature,humidity)
    else:
	print 'ERROR: Can not retrieve humidity or temperature value.'
def test_mfi(hostname):
    print mfi.get_mfi_data(hostname)
