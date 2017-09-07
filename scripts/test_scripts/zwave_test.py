from flexbox import zwave
device = '/dev/zwave'
config_path = '/etc/flexbox'
print zwave.run_zwave(device,config_path)
