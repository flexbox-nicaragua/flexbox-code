# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
import paramiko
import sys
import subprocess
import time
import logging
from datetime import datetime

def get_mfi_data(hostname,last_success=datetime.now(),timeout=300):
    port=22
    username='ubnt'
    password='ubnt'
    ssh_lines = []
    mfi_dict = {}
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    try:
        client.connect(hostname,port=port, username=username, password=password,timeout=5)
        stdin, stdout, stderr = client.exec_command("echo 0 > /proc/gpio/led_status")
        stdin, stdout, stderr = client.exec_command("echo 0 > /proc/led/status")
        stdin, stdout, stderr = client.exec_command("echo 1 > /proc/power/enabled1; echo 1 > /proc/power/enabled2; echo 1 > /proc/power/enabled3")
        stdin, stdout, stderr = client.exec_command("cd /proc/power; grep '' pf* v_rms* active_pwr* i_rms* energy_sum* relay*")
        for line in stdout:
            ssh_lines.append(line.strip('\n'))
        client.close()

        for ssh_line in ssh_lines:
            ssh_split = ssh_line.split(':')
            key = str(ssh_split[0])
            val = ssh_split[1]
            if "energy_sum" in key or "active_pwr" in key or "v_rms" in key or "pf" in key or "i_rms" in key:
                mfi_dict[key] = float(val)
            elif "relay" in key:
                mfi_dict[key] = bool(float(val))
        return mfi_dict
    except Exception,e:
        print 'ERROR: Unable to connect to ' + hostname + '. Trying to reset the services.'
        print 'ERROR occurred at ' + str(datetime.now())
        print 'ERROR its been ' + str((datetime.now()-last_success).seconds) + ' seconds since last success.'
        service_reset = 'sudo service hostapd restart;'
        service_reset += 'sudo ifconfig wlan0 10.10.10.1;'
        service_reset += 'sudo service isc-dhcp-server restart'
        if (datetime.now() - last_success).seconds > timeout:
            p = subprocess.call(service_reset,shell=True)
        time.sleep(30)
        return None

def control_mfi(hostname,state,outlet=3):
    '''
    This takes a state (1 or 0) and sends it to the mfi to turn it on or off.
    state: 1 is on, 0 is off
    outlet: which outlet to alter the state for
    hostname: the ip address of the mfi (should always be 10.10.10.1)

    username is ubnt always, and the ssh key for the flexbox is loaded onto the mfi at setup,
    using ssh-copy-id, so no need for a password.
    '''
    username = 'ubnt'
    password = 'ubnt'
    command = "echo '"+str(state)+"' | sshpass -p"+password+" ssh -o 'StrictHostKeyChecking no' "+username+"@"+hostname+" 'cat > /proc/power/relay"+str(outlet)+"'"
    print command
    subprocess.Popen(command,shell=True)
    ssh = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = ssh.communicate()
    errcode = ssh.returncode
    print err
    return errcode==0

