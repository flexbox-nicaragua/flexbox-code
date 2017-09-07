#!/bin/bash
IPADDRSTRING="$(hostname -I)"
if [[ "$IPADDRSTRING" != *10.10.10.1* ]]; then
	sudo service hostapd restart
	sudo ifconfig wlan0 10.10.10.1
	sudo service isc-dhcp-server restart
fi

#sudo /home/pi/flexbox/packages/umtskeeper/umtskeeper --sakisoperators "USBINTERFACE='0' OTHER='USBMODEM' USBMODEM='12d1:1003' SIM_PIN='1234' APN='CUSTOM_APN' CUSTOM_APN='provider.com' APN_USER='0' APN_PASS='0'" --sakisswitches "--sudo --console" --devicename 'Huawei' --log --silent --monthstart 8 --nat 'no' --httpserver &>> /home/pi/flexbox/log/umts.log &
#sudo /home/pi/flexbox/packages/umtskeeper/umtskeeper --sakisoperators "USBINTERFACE='0' OTHER='USBMODEM' USBMODEM='12d1:1003' SIM_PIN='1234' APN='CUSTOM_APN' CUSTOM_APN='provider.com' APN_USER='0' APN_PASS='0'" --sakisswitches "--sudo --console" --devicename 'Huawei' --log --silent --nat 'no' & 
