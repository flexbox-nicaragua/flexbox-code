# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from bs4 import BeautifulSoup
import urllib2
import re
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import cast,Date,text
from sqlalchemy.exc import IntegrityError
from flexbox import psql_server

url = 'http://www.cndc.org.ni/Principal/PREDESPACHO_archivos/sheet002.htm'
try:
    response = urllib2.urlopen(url)
except:
    response = urllib2.urlopen(url.replace('_archivos','_files'))
data = response.read()
soup = BeautifulSoup(data,"html5lib")
column_list = [header.text.encode('ascii','ignore') for header in soup.find('table').findAll('tr')[10].findAll('td')]
column_list.insert(0,'HORA')
column_list = column_list[:column_list.index('IND')+2]
column_list.insert(column_list.index('IND'),'Demanda')
column_list.insert(column_list.index('IND'),'Bombeo')

prices = []
for val in range(11,35):
    output_dict = {}
    row = [header.text.encode('ascii','ignore') for header in soup.find('table').findAll('tr')[val].findAll('td')][:len(column_list)]
    for i,column in enumerate(column_list):
        if column == 'IND':
            prices.append(float(row[i]))
dt_indexes = []
for i in range(0,24):
    dt_indexes.append(datetime(datetime.now().year,
        datetime.now().month,datetime.now().day)+timedelta(hours=i))
pred_actual_prices = pd.DataFrame(prices,index=dt_indexes)
pred_actual_prices.columns = ['IND']

pred_actual_prices['date'] = pred_actual_prices.index.date
pred_actual_prices['hour'] = pred_actual_prices.index.hour
pred_actual_prices['prog_ind'] = pred_actual_prices['IND']


###
### Beggining to Chose the DR Event for the Next Day


sub_date = pred_actual_prices

sub_date['rolling_rank3'] = [None] * len(sub_date['prog_ind'])
sub_date['rolling_rank2'] = [None] * len(sub_date['prog_ind'])

for i,val in enumerate(sub_date['prog_ind']):
    if i <= 21:
        sub_date['rolling_rank3'][i] = (sub_date['prog_ind'][i] + sub_date['prog_ind'][i+1]  + sub_date['prog_ind'][i+2])/3
        sub_date['rolling_rank2'][i] = (sub_date['prog_ind'][i] + sub_date['prog_ind'][i+1])/2

    if i == 22:
        sub_date['rolling_rank3'][i] = (sub_date['prog_ind'][i] + sub_date['prog_ind'][i+1])/2
        sub_date['rolling_rank2'][i] = (sub_date['prog_ind'][i] + sub_date['prog_ind'][i+1])/2

    if i == 23:
        sub_date['rolling_rank3'][i] = sub_date['prog_ind'][i]
        sub_date['rolling_rank2'][i] = sub_date['prog_ind'][i]
    else:
        pass

# Creating the rolling rank
sub_date_sorted = sub_date.sort_values(by='rolling_rank3',ascending=False)



##
## Chosing the Event


highest_hour_price = sub_date[sub_date['prog_ind'] == max(sub_date['prog_ind'])][['prog_ind','hour']].rename(columns={'prog_ind':'price'})
highest_hour_price['event'] = 'hour'
three_hour_dr = sub_date[sub_date['rolling_rank3'] == max(sub_date['rolling_rank3'])][['rolling_rank3','hour']].rename(columns={'rolling_rank3':'price'})
three_hour_dr['event'] = 'three_hour'
two_hour_dr = sub_date[sub_date['rolling_rank2'] == max(sub_date['rolling_rank2'])][['rolling_rank2','hour']].rename(columns={'rolling_rank2':'price'})
two_hour_dr['event'] = 'two_hour'

highest_hour_price = highest_hour_price.append(three_hour_dr)
highest_hour_price = highest_hour_price.append(two_hour_dr)

max_price_event =  highest_hour_price[highest_hour_price['event'] == 'hour']

two_three_dr_hours = range(highest_hour_price[highest_hour_price['event'] == 'three_hour']['hour'][0],highest_hour_price[highest_hour_price['event'] == 'three_hour']['hour'][0]+3)\
+ range(highest_hour_price[highest_hour_price['event'] == 'two_hour']['hour'][0],highest_hour_price[highest_hour_price['event'] == 'two_hour']['hour'][0]+2)


if max_price_event['hour'][0] not in two_three_dr_hours:
    event = highest_hour_price[highest_hour_price['event'] == 'hour']
elif highest_hour_price[highest_hour_price['event'] == 'three_hour']['price'][0] >= highest_hour_price[highest_hour_price['event'] == 'two_hour']['price'][0] :
    event = highest_hour_price[highest_hour_price['event'] == 'three_hour']
elif highest_hour_price[highest_hour_price['event'] == 'three_hour']['price'][0] < highest_hour_price[highest_hour_price['event'] == 'two_hour']['price'][0] :
    event = highest_hour_price[highest_hour_price['event'] == 'two_hour']
if event.shape[0] > 1:
    event = event.head(1)
else:
    pass

if event['event'][0] == 'hour':
    event['additional_hours'] = 0
elif event['event'][0] == 'two_hour':
    event['additional_hours'] = 1
elif event['event'][0] == 'three_hour':
    event['additional_hours'] = 2
else:
    pass

hours_list =  list(range(event['hour'][0],event['hour'][0] + event['additional_hours'][0]+1))
hour_start = int(event['hour'][0])
duration = (event['additional_hours'][0]+1)*60
output_dict = {}

metadata = psql_server.get_metadata()
table_dict = psql_server.setup_tables(metadata_control)
output_dict = {}
output_dict['date'] = event.index.date[0]
output_dict['hour_start'] = hour_start
output_dict['datetime'] = datetime.combine(event.index.date[0],\
                        datetime.min.time())+timedelta(hours=hour_start)
output_dict['signal'] = 1
output_dict['duration_minutes']=duration
print output_dict
psql_server.add_values_to_table(table_dict['peak_shifting_dr_table'],output_dict)