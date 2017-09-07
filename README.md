# Flexbox Code Repository

This code is meant to be run by git cloning in the home directory of a Raspbian image on a raspberry pi. Follow the instructions in each README within each folder to ensure that all setup has been configured properly.

Some of the included scripts send and receive data from a centralized server. The domain in these scripts is currently at 'yourserverdomain.com', and will need to be replaced with your actual server domain during implementation.

.
+-- initial_setup
|   +-- 99-usb-serial.rules
|   +-- append_to_fstab
|   +-- crontab
|   +-- demand_response.yaml
|   +-- rc.local
|   +-- reset_db.py
|   +-- setup_pi.sh
|   +-- temp_assign.yaml
|   +-- README.md
|   +-- config
+-- _packages
|   +-- README.md
+-- _pyflexbox
|   +-- setup.py
|   +-- flexbox
+-- _scripts
|   +-- control_scripts
|   +-- get_scripts
|   +-- get_scripts
|   +-- send_scripts
|   +-- test_scripts
+-- _startup
|   +-- startup.sh
|   +-- get_all.sh
|   +-- flask_launch.sh
+-- _web
|   +-- endpoints.py
|   +-- static