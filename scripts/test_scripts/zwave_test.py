# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flexbox import zwave
device = '/dev/zwave'
config_path = '/etc/flexbox'
print zwave.run_zwave(device,config_path)
