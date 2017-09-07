from sqlalchemy import create_engine
from sqlalchemy import MetaData, Column, Table
from sqlalchemy import Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
import datetime


def setup_tables(metadata):
    '''
    This is where the tables for the PSQL database are defined.
    If columns/tables need to be changed, this is where it must happen.
    '''
    table_dict = {}
    inside_table = Table('inside_temps', metadata,
                    Column('datetime', DateTime),
                    Column('hostname', String,primary_key=True),
                    Column('id', String,primary_key=True),
                    Column('inside_temp1',Integer),
                    Column('inside_temp2',Integer),
                    Column('inside_temp3',Integer),
                    Column('inside_temp4',Integer),
                    Column('inside_temp5',Integer),
                    )
    switch_table = Table('switch', metadata,
                    Column('hostname', String,primary_key=True),
                    Column('id', String,primary_key=True),
                    Column('datetime', DateTime),
                    Column('switch',Boolean)
                    )

    ambient_table = Table('ambient', metadata,
                        Column('hostname', String,primary_key=True),
                        Column('id', String,primary_key=True),
                        Column('datetime', DateTime),
                        Column('ambient_temp',Float),
                        Column('humidity',Float),
                        )

    mfi_table = Table('fridge_power', metadata,
                        Column('hostname', String,primary_key=True),
                        Column('id', String,primary_key=True),
                        Column('datetime', DateTime),
                        Column('v_rms1',Float),
                        Column('v_rms2',Float),
                        Column('v_rms3',Float),
                        Column('i_rms1',Float),
                        Column('i_rms2',Float),
                        Column('i_rms3',Float),
                        Column('pf1',Float),
                        Column('pf2',Float),
                        Column('pf3',Float),
                        Column('energy_sum1',Float),
                        Column('energy_sum2',Float),
                        Column('energy_sum3',Float),
                        Column('active_pwr1',Float),
                        Column('active_pwr2',Float),
                        Column('active_pwr3',Float),
                        Column('relay1',Boolean),
                        Column('relay2',Boolean),
                        Column('relay3',Boolean),
                        )
    zwave_table = Table('house_power', metadata,
                        Column('hostname', String,primary_key=True),
                        Column('id', String,primary_key=True),
                        Column('datetime', DateTime),
                        Column('houseAll_Voltage',Float),
                        Column('houseAll_Current',Float),
                        Column('houseAll_Power',Float), #Watts
                        Column('houseAll_Energy',Float), #kWh
                        Column('house1_Voltage',Float),
                        Column('house1_Current',Float),
                        Column('house1_Power',Float), #Watts
                        Column('house1_Energy',Float), #kWh
                        Column('house2_Voltage',Float),
                        Column('house2_Current',Float),
                        Column('house2_Power',Float), #Watts
                        Column('house2_Energy',Float), #kWh
                        )
    network_tests = Table('network_tests', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
                        Column('parm', String),
                        Column('hostname', String),
                        Column('seqn', Integer),
                        Column('ts', Float),
                        Column('fail_pcnt', Integer),
                        Column('max', Float),
                        Column('avg', Float),
                        Column('modem_MB_used', Float),
                        Column('uptime_minutes', Float),
                        )

    twilio_received = Table('twilio_received', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('hostname', String),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
                        Column('date_last',DateTime),
                        Column('phone_number', String),
                        Column('message', String),
                        Column('limit_kwh', Integer),
                        )

    twilio_sent= Table('twilio_sent', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('hostname', String),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
                        Column('date_last',DateTime),
                        Column('phone_number', String),
                        Column('message', String),
                        Column('limit_crossed', Integer),
                        Column('limit_type', String),
                        )

    user_prices = Table('user_prices', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
                        Column('start_range', Integer),
                        Column('end_range', Integer),
                        Column('price', Float),
                        Column('tariff_code', String),
                        )

    demand_response = Table('demand_response', metadata,
                Column('id', String, primary_key=True,autoincrement=True),
                Column('hostname', String, primary_key=True),
                Column('datetime', DateTime,default=datetime.datetime.utcnow),
                Column('local_date', DateTime),
                Column('mfi_state', Integer),
                Column('control_source', String),
                Column('control_type', String),
                Column('limit_counter', Integer),
                Column('uptime_minutes', Float),
                )


    table_dict['inside_table'] = inside_table
    table_dict['switch_table'] = switch_table
    table_dict['ambient_table'] = ambient_table
    table_dict['mfi_table'] = mfi_table
    table_dict['zwave_table'] = zwave_table
    table_dict['network_tests'] = network_tests
    table_dict['twilio_received'] = twilio_received
    table_dict['twilio_sent'] = twilio_sent
    table_dict['user_prices'] = user_prices
    table_dict['demand_response'] = demand_response

    return table_dict

def setup_schema(drop=True):
    '''
    This method clears the database by dropping and readding the tables to the db.
    '''
    metadata = get_metadata()
    table_dict = setup_tables(metadata)
    # create or drops tables in database
    if drop:
        metadata.drop_all()
    metadata.create_all()
    return table_dict

def add_values_to_table(table_ref,value_dict):
    value = table_ref.insert()
    try:
        value.execute(value_dict)
    except IntegrityError as e:
        reason = e.message
        print 'Did not insert.'
        print reason

def get_metadata():
    engine = create_engine('postgresql://flexbox:flexbox@localhost/flexbox_db_server')
    metadata = MetaData(bind=engine)
    return metadata

def get_remote_metadata():
    engine = create_engine('postgresql://flexbox:flexbox@yourserverdomain.com/flexbox_db_server')
    metadata = MetaData(bind=engine)
    return metadata
