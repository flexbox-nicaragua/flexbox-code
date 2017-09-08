#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from twilio.rest import TwilioRestClient
from flexbox import psql_server as psql
from flexbox import analysis_tools
from sqlalchemy import cast,Date,text
from datetime import datetime
import re
import pandas as pd
import yaml
import time
import numpy as np
import copy


from_twilio_number = '+12223334444'



def create_ewarning():
    with open('twilio_auth.yaml') as f:
        cf = yaml.safe_load(f)
    client = TwilioRestClient(cf['ACCOUNT_SID'], cf['AUTH_TOKEN'])
    with open('phonebook.yaml') as f:
        phone_dictionary = yaml.safe_load(f)
        phone_dictionary_reversed = dict((value,key)
                for key,value in phone_dictionary.items())
    with open('tariff_codes.yaml') as f:
        tariff_codes = yaml.safe_load(f)

    #Grabbing data and pulling it
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)

    dfs = {}
    for flxbx in phone_dictionary.values():
        # The next two lines are SQL Alchemy code, ordering each house energy data by date and then executing
        last_row = table_dict['twilio_received'].select("hostname='"+flxbx+"'").\
            order_by(table_dict['twilio_received'].\
            c.datetime.desc()).execute().fetchone()

        if last_row:
            last_date = last_row[3]
            limit = last_row[6]
            phone_number = phone_dictionary_reversed[flxbx]
            last_text_sent = None

            # The next two lines are SQL Alchemy code, ordering each house energy data by date and then executing
            energia = analysis_tools.get_energy_since_date(flxbx,last_date)
            '''
            dfs[flxbx] = create_monotonically_increasing_energy_vals(table_dict,flxbx)
            if len(dfs[flxbx])>0 and len(dfs[flxbx][last_date:])>0:
                energia = dfs[flxbx][last_date:]['houseAll_Energy'][-1:].iloc[0] -\
                    dfs[flxbx][last_date:]['houseAll_Energy'][:1].iloc[0]
            else:
                energia = 0
            '''
            ######################
            #Querying the twilio sent table for kWh thresholds (in order find out their price of electricity)
            tariff_code=tariff_codes[flxbx]

            last_row_sent_kwh = table_dict['twilio_sent'].select().\
                where(text("hostname='"+flxbx+"'")).\
                where(text("limit_type='kwh'")).\
                where(cast(table_dict['twilio_sent'].c.date_last,Date)==last_date).\
                order_by(table_dict['twilio_sent'].\
                c.datetime.desc()).execute().fetchone()

            if last_row_sent_kwh:
                previously_crossed_start_range = last_row_sent_kwh[6]
                last_date_sent_kwh = last_row_sent_kwh[3]

                if last_date_sent_kwh != last_date:
                    previously_crossed_start_range=-1
            else:
                previously_crossed_start_range = -1

            last_row_user_prices = table_dict['user_prices'].select().\
                where(table_dict['user_prices'].c.start_range<=energia).\
                where(table_dict['user_prices'].c.end_range>energia).\
                where(table_dict['user_prices'].c.tariff_code==tariff_code).\
                order_by(table_dict['user_prices'].\
                c.datetime.desc()).execute().fetchone()
            start_range = last_row_user_prices[2]
            end_range = last_row_user_prices[3]
            price = last_row_user_prices[4]
            recent_price_date = last_row_user_prices[1]

            output_dict = {}
            if start_range!=previously_crossed_start_range:
                if end_range < 1000000:
                    message = 'Su consumo ha rebasado el costo de energia anterior. De ' + str(start_range)+ ' kWh a ' \
                    +str(end_range) + ' kWh usted estara pagando $C '+str(price)+'/kWh'
                else:
                    message = 'Su consumo ha rebasado el costo de energia anterior. De ahora en adelante usted estara pagando C$'+str(price)+\
                        '/kWh.'
                limit_crossed = start_range
                client.messages.create(
                    to= phone_number,
                    from_=from_twilio_number,
                    body=flxbx.replace("flxbx","")+":"+message,
                )
                output_dict['hostname']= flxbx
                output_dict['date_last'] = last_date
                output_dict['datetime'] = datetime.now()
                output_dict['phone_number'] = phone_number #Specified by Twilio message
                output_dict['message'] = message
                output_dict['limit_crossed'] = limit_crossed
                output_dict['limit_type'] = 'kwh'
                print tariff_code + ":" + str(energia) + "kWh:" + message
                enter_data = psql.add_values_to_table(table_dict['twilio_sent'],output_dict)

            #########################################################

            #Querying the Twilio sent table for percents
            last_row_sent = table_dict['twilio_sent'].select().\
                where(text("hostname='"+flxbx+"'")).\
                where(text("limit_type='percent'")).\
                where(cast(table_dict['twilio_sent'].c.date_last,Date)==last_date).\
                order_by(table_dict['twilio_sent'].\
                c.datetime.desc()).execute().fetchone()
            if last_row_sent:
                previously_crossed = last_row_sent[6]
                last_date_sent = last_row_sent[3]
                last_text_sent = last_row_sent[2]

                if last_date_sent != last_date:
                    previously_crossed=0

            else:
                last_text_sent = last_date
                last_date_sent = last_date
                previously_crossed = 0

            ### Creating a Warning for Increased Average Consumption Since last Text Message
            energia_pct_limit = analysis_tools.get_energy_since_date(flxbx,last_text_sent)
            if (datetime.now() - last_text_sent).days > 0:
                daily_pct_warning = energia_pct_limit/float((datetime.now()-last_text_sent).days)
            else:
                daily_pct_warning = 0


            ### Creating a Value that Calculates the Tarifa Social
            daily_pct_social = energia/float((datetime.now()-last_date_sent).days)

            ###

            ### Determining Tariff Code for SQL queries
            if daily_pct_social < 5 and tariff_code == 'T-0' and energia <= 150:
                tariff_code_for_sql = 'T-Social'
            elif tariff_code == 'T-J':
                tariff_code_for_sql = 'T-0'
            else:
                tariff_code_for_sql = tariff_code

            ine_user_prices = table_dict['user_prices'].select().\
                            where(table_dict['user_prices'].c.start_range<=energia).\
                            where(table_dict['user_prices'].c.tariff_code==tariff_code_for_sql).\
                            where(cast(table_dict['user_prices'].c.datetime,Date)==recent_price_date).\
                            order_by(table_dict['user_prices'].\
                            c.datetime.desc()).execute().fetchall()

            cost_energia = 0

            for val in ine_user_prices:

                this_start_range = val[2]
                this_end_range = val[3]

                #Creating a scalar so that we appropriately assing subsidies to jubilados
                if tariff_code == 'T-J' and this_end_range <= 150:
                    subsidy_scalar = 0.44
                else:
                    subsidy_scalar = 1


                if energia <= this_end_range:
                    cost_energia += (energia - this_start_range) * val[4] * subsidy_scalar
                else:
                     cost_energia += (this_end_range - this_start_range) * val[4] * subsidy_scalar


           # print str(flxbx) + ':'+ str(energia)+" out of " + str(limit)+" last crossed:"+str(previously_crossed) + ' and cost is ' + str(cost_energia)

            cost_energia_var = 'El  gasto actual en Cordobas de los kWh consumidos (sin incluir IVA, alumbrado, y otros gastos) es de $C' + str(round(cost_energia,2)) + '. '

            mensaje_warning = ''
            if (daily_pct_warning > 5) and (daily_pct_social <= 5):
                mensaje_warning = 'Desde el ultimo mensaje usted ha estado consumiendo mas de 5 kWh/dia. Si usted sigue consumiendo energia de esta manera lo mismo podria perder la tarifa social.'
            elif  (daily_pct_warning > daily_pct_social) and (daily_pct_social > 5):
                mensaje_warning = 'Desde el ultimo mensaje que usted recibio, usted ha estado consumiendo ' + str(round((daily_pct_warning - daily_pct_social),3)) + ' mas kWh por dia en promedio. Si quiere llegar a su limite de energia cuide su consumo.'

            if energia and limit and energia >= 0.1*limit:
                message = ''
                if energia >= 1*limit and previously_crossed != 100:
                    message = 'Usted ha pasado su limite :( Sugerimos solo utilizar la luz para cosas indispensables de aqui al siguiente recibo! ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var
                    limit_crossed = 100
                elif energia >= 0.90*limit and previously_crossed < 90:
                    message = 'Cuidado, usted esta apunto de cruzar su limite (90%)! Sugerimos solo utilizar la luz para cosas indispensables de aqui al siguiente recibo. ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var
                    limit_crossed = 90
                elif energia >= 0.80*limit and previously_crossed < 80:
                    message = 'Usted ha pasado el 80% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                    limit_crossed = 80
                elif energia >= 0.7*limit and previously_crossed < 70:
                    limit_crossed = 70
                    message = 'Usted ha pasado el 70% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.6*limit and previously_crossed < 60:
                    limit_crossed = 60
                    message = 'Usted ha pasado el 60% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.5*limit and previously_crossed < 50:
                    limit_crossed = 50
                    message = 'Usted ha pasado el 50% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.4*limit and previously_crossed < 40:
                    limit_crossed = 40
                    message = 'Usted ha pasado el 40% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.3*limit and previously_crossed < 30:
                    limit_crossed = 30
                    message = 'Usted ha pasado el 30% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.2*limit and previously_crossed < 20:
                    limit_crossed = 20
                    message = 'Usted ha pasado el 20% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                elif energia >= 0.10*limit and previously_crossed < 10:
                    limit_crossed = 10
                    message = 'Usted ha pasado el 10% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. ' + cost_energia_var + mensaje_warning
                '''
                else:
                    limit_crossed=0
                    message = 'Usted ha pasado el X% de su limite establecido ' + '(' + str(limit)+'kWh) ' + 'el ' + last_date.strftime('%d/%m/%Y') + '. Ha gastado ' + str(int(round(energia))) + ' kWh hasta el dia de hoy. '  + 'Su tarifa social es ' + str(daily_pct_social) + ' su tarifa warning es ' + str(daily_pct_warning) + ' Su energia es' +  str(energia)
                '''
                print message

                if len(message) >0:
                    client.messages.create(
                        to= phone_number,
                        from_=from_twilio_number,
                        body=flxbx.replace("flxbx","")+":"+message,
                    )

                    #2. Output Dictionary
                    output_dict = {}
                    output_dict['hostname']= flxbx
                    output_dict['date_last'] = last_date
                    output_dict['phone_number'] = phone_number #Specified by Twilio message
                    output_dict['message'] = message
                    output_dict['limit_crossed'] = limit_crossed
                    output_dict['limit_type'] = 'percent'

                    enter_data = psql.add_values_to_table(table_dict['twilio_sent'],output_dict)
create_ewarning()

