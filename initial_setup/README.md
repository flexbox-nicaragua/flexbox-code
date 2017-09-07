99-usb-serial.rules needs to go in /etc/udev/rules.d
basic.vim needs to be renamed .vimrc and go in /home/pi/
the contents of append_to_fstab need to go at the bottom of /etc/fstab
the contents of crontab need to go inside of crontab -e
copy rc.local to /etc/rc.local
copy contents of config to /etc/flexbox
edit /etc/dhcp/dhcpd.conf at the bottom of the file, replace the MAC address with the MFI's MAC address
edit /etc/flexbox/temp_assign.yaml with the temperature ids from /sys/bus/w1/devices
create /mount/backup
edit /etc/flexbox/demand_response.yaml with required hour fridge needs to be on and upper deadband information
