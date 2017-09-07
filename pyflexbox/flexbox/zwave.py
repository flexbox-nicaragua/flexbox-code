import openzwave
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption
import time
import os
from louie import dispatcher


def louie_network_started(network):
    print("Hello from network : I'm started : homeid %0.8x - %d nodes were found." % \
        (network.home_id, network.nodes_count))

def louie_network_stopped(network):
    print("Hello from network : it stopped :(.")

def louie_network_failed(network):
    print("Hello from network : it failed :(.")

def louie_node_update(network, node):
    print('Hello from node : %s.' % node)

def louie_value_update(network, node, value):
    print('Hello from value : %s.' % value)

def init_zwave(device,config_path):
    #device ="/dev/ttyUSB0"
    log="None"

    #Define some manager options
    options = ZWaveOption(device, \
      config_path=config_path, user_path=config_path, cmd_line="")
    #config_path=str(os.getcwd())+"/../../packages/python-openzwave/openzwave/config", \
    options.set_log_file("OZW_Log.log")
    options.set_append_log_file(False)
    options.set_console_output(True)
    options.set_save_log_level('Info')
    options.set_logging(False)
    options.lock()

    #Create a network object
    network = ZWaveNetwork(options, autostart=True)

    dispatcher.connect(louie_network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)

    return network

def read_zwave(network):

    output_dict = {}
    for node in network.nodes:
        for val in network.nodes[node].get_sensors():
            label = network.nodes[node].values[val].label
            network.nodes[node].refresh_info()
            instance = network.nodes[node].values[val].instance
            if instance == 1:
                instance_text = "All"
            elif instance == 2:
                instance_text = "1"
            elif instance == 3:
                instance_text = "2"
            if  not network.nodes[node].isNodeFailed:
                if  label == 'Current' or \
                label == 'Voltage' or \
                label == 'Power' or \
                label == 'Energy':
                    output_dict['house'+instance_text+'_'+label] = network.nodes[node].get_sensor_value(val)
    return output_dict

def run_zwave(device,config_path):
    print 'Initializing Zwave Network'
    network = init_zwave(device,config_path)
    print 'Waiting...'
    time.sleep(5.0)
    return read_zwave(network)


def print_all_zwave(network):
    value_dict_by_id = {}
    correct_id = '';
    for node in network.nodes:
        value_dict = network.nodes[node].get_values_by_command_classes()
        for val in value_dict:
            objects = value_dict[val]
            for entry in objects:
                data = objects[entry].to_dict()
		print data
