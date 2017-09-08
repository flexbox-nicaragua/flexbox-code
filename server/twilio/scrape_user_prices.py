# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from datetime import datetime
from flexbox import psql_server as psql

if __name__ == '__main__':

    #Update the following each month according to that months prices for each tariff (T-0,T-1,T-Social)
    month_num = 12
    year_num = 2015
    tariff_date = datetime(year_num,month_num,1)
    t0_values = [8,10,12,14,15,18,20]
    t1_values = [8,16]
    tSocial_values = [8,10,12,14,15,18,20]

    ### The following loads it into the appropriate database

    start_range_options = [0,25,50,100,150,500,1000]
    end_range_options = [25,50,100,150,500,1000,1000000]
    output_dict = {}
    for i,value in enumerate(t0_values):
        output_dict['datetime'] = tariff_date
        output_dict['start_range'] = start_range_options[i]
        output_dict['end_range'] = end_range_options[i]
        output_dict['price'] = value
        output_dict['tariff_code'] = 'T-0'
        psql.add_values_to_table(table_dict['user_prices'],output_dict)

    start_range_options = [0,150]
    end_range_options = [150,1000000]
    output_dict = {}
    for i,value in enumerate(t1_values):
        output_dict['datetime'] = tariff_date
        output_dict['start_range'] = start_range_options[i]
        output_dict['end_range'] = end_range_options[i]
        output_dict['price'] = value
        output_dict['tariff_code'] = 'T-1'
        psql.add_values_to_table(table_dict['user_prices'],output_dict)

    start_range_options = [0,25,50,100,150,500,1000]
    end_range_options = [25,50,100,150,500,1000,2000]
    output_dict = {}
    for i,value in enumerate(tSocial_values):
        output_dict['datetime'] = tariff_date
        output_dict['start_range'] = start_range_options[i]
        output_dict['end_range'] = end_range_options[i]
        output_dict['price'] = value
        output_dict['tariff_code'] = 'T-Social'
        psql.add_values_to_table(table_dict['user_prices'],output_dict)
