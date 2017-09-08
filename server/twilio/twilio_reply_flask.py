#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flask import Flask, request, redirect
from flask import copy_current_request_context
import twilio.twiml
from flexbox import psql_server as psql
from flexbox import analysis_tools
from datetime import datetime
import re
import pandas as pd
import numpy as np
import copy
import yaml
import time
import os
from multiprocessing import Process
from difflib import SequenceMatcher
TIMEOUT=18000
app = Flask(__name__)




metadata = psql.get_metadata()
table_dict = psql.setup_tables(metadata)


@app.route("/", methods=['GET', 'POST'])
def run_flask_twilio():
    """Respond to incoming calls with a simple text message."""
    #Grabbing data and pulling it
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)

    # Opening Twilio
    resp = twilio.twiml.Response()
    # Getting data from the message
    if request.values.get('Body',None):
        input_flask_message = request.values.get('Body',None).encode('ascii','ignore')
        phone_number =request.values.get('From',None).encode('ascii','ignore')

        #1. Extracting values from message
        message_words = input_flask_message.split(' ')
        message_words = [word for word in message_words if word!='']
    else:
        message_words = None #Used so that this code can be tested in a web browser without error
    with open('phonebook.yaml') as f:
        phone_dictionary = yaml.safe_load(f)
    admin = False
    if phone_number in phone_dictionary.keys():
        flxbx = phone_dictionary[phone_number]

        if message_words and (len(re.findall('\d+',input_flask_message)) >0 or 'kwh' in input_flask_message.lower()):
            try:
                #This raises an exception if it can't parse the data from the second element of the message
                date = datetime.strptime(message_words[1],'%d/%m/%Y')
            except:
                #This prematurely returns so that the code doesn't attempt to do anythign with the bad date that was provided.
                resp.message("El formato de dia/mes/ano que usted escribio esta mal escrito. Por favor verfique el formato."+
                    " Por ejemplo si el dia es el 6 de Marzo. El mensaje deberia decir 'limite 6/3/2016 150 kWh'")
                return str(resp)

            #Pulling the third word from the message and getting the first element of the list
            limit = re.findall("(\d+)", message_words[2])[0]

            #2. Output Dictionary to be inserted into SQL table
            output_dict = {}
            output_dict['hostname']= phone_dictionary[phone_number]
            output_dict['date_last'] = date
            output_dict['phone_number'] = phone_number #Specified by Twilio message
            output_dict['message'] = input_flask_message
            output_dict['limit_kwh'] = int(limit)
            psql.add_values_to_table(table_dict['twilio_received'],output_dict)
            output_message = "Muchas gracias!"

        elif message_words and SequenceMatcher(None, "energia", message_words[0].lower()).ratio()>0.5:
            # The next two lines are SQL Alchemy code, ordering each house energy data by date and then executing
            last_row = table_dict['twilio_received'].select("hostname='"+flxbx+"'").\
                order_by(table_dict['twilio_received'].c.datetime.desc()).execute().fetchone()

            if last_row:
                last_date = last_row[3]

                energia = analysis_tools.get_energy_since_date(flxbx,last_date)
                '''
                df = create_monotonically_increasing_energy_vals(table_dict,flxbx)
                if len(df[last_date:])>0:
                    energia=df[last_date:]['houseAll_Energy'][-1:].iloc[0] - \
                    df[last_date:]['houseAll_Energy'][:1].iloc[0]
                else:
                    energia=0
                '''
                output_message = 'Usted ha utilizado ' + str(round(energia))+ ' kWh desde ' + last_date.strftime('%d/%m/%Y')
            else:
               output_message = "Primero necesitamos que nos mande su limite!"
        else:
            output_message = "Gracias! Si hay algun problema por favor comunicarse con Odaly. De otra manera, tenga un buen dia!"
    else:
        output_message = "Hola! Por favor contacte a Odaly para registra su telefono. Gracias!"
    if admin:
        output_message = 'Admin Mode-' + flxbx + ' used for testing-'+output_message
    resp.message(output_message)
    return str(resp)

class myThread(Process):
    def __init__(self):
        Process.__init__(self)

    def run(self):
        print 'Running Twilio Flask at ' + str(datetime.now())
        different = True
        app.run(host='0.0.0.0',debug=True)

while True:
    p = myThread()
    p.start()
    print "Main thread PID:",os.getpid()
    print "Launched process PID:",p.pid
    p.join(TIMEOUT)
    if p.is_alive:
        p.terminate()
        time.sleep(10)
