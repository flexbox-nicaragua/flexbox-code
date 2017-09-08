#Socket Server
This is the folder of python scripts for running the socket on the server side.

Screen is a way for scripts to run on the server even when you close the terminal window. They run in a 'terminal' that you can detach or re-attach to. 

To run something in screen, type the word 'screen' in the terminal. Then hit enter. 
You are now inside of a screen terminal Run a script as if you would in a normal terminal. Then when you are done, hold down Ctrl and Shift while typing AD. This will allow you to detach from the screen. To see that screen, type 'screen -ls' in the terminal, which will list all of the screen terminals that are currently running.
It is important to run the following scripts in screen sessions:
flexbox/server/twilio/twilio_reply_flask.py
flexbox/server/web/receive_heartbeat.py
flexbox/server/web/network_test_server.py

and the following scripts when the server boots:
sudo start endpoint_server


The following should go in the crontab

@reboot /home/flexbox/server/twilio/twilio_reply_flask.py
@reboot sudo /home/flexbox/server/web/endpoint_server.py
@reboot /home/flexbox/flexbox/server/receive_heartbeat_with_processes.py
@reboot /home/flexbox/flexbox/server/network_test_server.py
0 9,10,11,12,13,14,15,16,17,18,19,20,21 * * * cd /home/flexbox/flexbox/server/twilio; ./twilio_percent_send.py
0 23 * * * cd ~/flexbox/server; ./scrape_predespacho.py
0 19 * * * cd ~/flexbox/server/demand_response; python ./write_peak_shaving_dr_to_db.py
0 * * * * cd ~/flexbox/server/demand_response; python ./update_dr_signal.py
0 * * * * cd ~/flexbox/server/web/screen_logs; ./clear_logs.sh

Make sure to move login.yaml.example to login.yaml in server/web and update the username/password

screen sessions logs are in server/web/screen_logs. 


```
+-- demand_response
|   +-- update_dr_signal_time.py

```

## update_dr_signal_time.py
This script looks up whether a signal should be sent for that hour (peak shaving) or for the next 20 minutes (wind event) based on the information coming from the dispatch center.

## Web Service Requirements (optional)

To use the web interface, you must download the following javascript dependencies and put them in their respective js and css folders inside server/web/static and web/static

- [d3](https://d3js.org/)
- [c3](http://c3js.org/)
- [pickadate](http://amsul.ca/pickadate.js/) (need picker.js and picker.date.js)
- [bootstrap](http://getbootstrap.com/) (bootstrap.min.js and bootstrap.min.css)
- [jquery](https://jquery.com/) (jquery.min.js)