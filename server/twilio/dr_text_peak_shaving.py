# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from twilio.rest import TwilioRestClient
from flexbox import psql_server as psql
#from flexbox import analysis_tools
from sqlalchemy import cast,Date,text
from datetime import date, datetime, timedelta
import re
import pandas as pd
import yaml
import time
import numpy as np
import copy

#Brining Libraries for FlexBox Data
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Column, Table
from sqlalchemy import Integer, String, DateTime, Boolean, Float, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from_twilio_number = '+12223334444'  


# Opening the yaml files with the twilio account info
with open('twilio_auth.yaml') as f:
    cf = yaml.safe_load(f)
    client = TwilioRestClient(cf['ACCOUNT_SID'], cf['AUTH_TOKEN'])
with open('phonebook.yaml') as f:
    phone_dictionary = yaml.safe_load(f)
    phone_dictionary_reversed = dict((value,key)
            for key,value in phone_dictionary.items())
with open('../web/available_hours.yaml') as f:
    required_hours_off = yaml.safe_load(f)


####  Defining the function
def send_dr_text(dr_data_frame,dr_type,phones,required_hours):

    #dr_data_frame['signal'] = 1

    for houses in required_hours:
        #print houses, required_hours_off[str(houses)]
        #print dr_data_frame['hour'][0], required_hours[str(houses)],dr_data_frame['signal'][0]
        if len(dr_data_frame)>0 and (dr_data_frame.index[0].hour\
                                     in required_hours[str(houses)]) and dr_data_frame['signal'][0] ==1:

            if dr_type == "price":
                duration_minutes =  dr_data_frame['duration_minutes'][0]
                if duration_minutes== None:
                    print 'NO DURATION FOUND!'
                    duration_minutes = 60
                message_text = "Actualmente (las " + \
                str(dr_data_frame.index[0].hour) + \
                    " horas), estamos en un evento de " + \
                    "'Precio' con duracion de "+ \
                    str(duration_minutes/60)+ \
                    " hora(s). Su refrigerador esta oscilando"+ \
                    " en una temperatura un poco mas alta de lo normal, pero" + \
                    " esta prendido. Gracias por su cooperacion."
            else:
                message_text = "Actualmente (las " + str(dr_data_frame[0].index.hour) + " horas), estamos en un evento de " + \
                "'Viento' con duracion de 20 minutos. Su refrigerador esta oscilando en una temperatura un poco mas alta de lo normal, pero" + \
                " esta prendido. Gracias por su cooperacion."

           # print houses, required_hours[str(houses)], message_text

            # Text everyone
            if houses!='flxbxD0':
                print message_text
                message = client.messages.create(
                    to= phones[str(houses)],
                    from_=from_twilio_number,
                    body=message_text,
                )
                print message_text


##### 1.  Bringing the DR Events

# Server Connection

metadata = psql_server.get_metadata()
table_dict = psql_server.setup_tables(metadata)


#####  2.  Peak Shifting DR Table
column_names = table_dict['peak_shifting_dr_table'].columns.keys()
peak_shifting_dr_row = table_dict['peak_shifting_dr_table'].select().\
                        where(table_dict['peak_shifting_dr_table'].c.hour_start==datetime.now().hour).\
                        where(cast(table_dict['peak_shifting_dr_table'].c.datetime,Date)==datetime.now().date()).\
                        order_by(table_dict['peak_shifting_dr_table'].c.datetime.desc()).execute().fetchone()
if peak_shifting_dr_row!=None:
    peak_shifting_dr = pd.DataFrame([peak_shifting_dr_row],columns=column_names)
    peak_shifting_dr.index = peak_shifting_dr['datetime']
    ##### 3. Running function defined above
    send_dr_text(dr_data_frame = peak_shifting_dr,
        dr_type = "price",phones=phone_dictionary_reversed, required_hours = required_hours_off)



