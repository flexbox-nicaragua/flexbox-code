from sqlalchemy import create_engine
from sqlalchemy import MetaData, Column, Table
from sqlalchemy import Integer, String, DateTime, Boolean, Float, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime



def setup_tables(metadata):
    '''
    This is where the tables for the PSQL database are defined.
    If columns/tables need to be changed, this is where it must happen.
    '''
    table_dict = {}
    inside_table = Table('inside_temps', metadata,
                    Column('id', Integer, primary_key=True,autoincrement=True),
                    Column('datetime', DateTime,default=datetime.datetime.utcnow),
                    Column('inside_temp1',Integer),
                    Column('inside_temp2',Integer),
                    Column('inside_temp3',Integer),
                    Column('inside_temp4',Integer),
                    Column('inside_temp5',Integer),
                    )
    switch_table = Table('switch', metadata,
                    Column('id', Integer, primary_key=True,autoincrement=True),
                    Column('datetime', DateTime,default=datetime.datetime.utcnow),
                    Column('switch',Boolean)
                    )

    ambient_table = Table('ambient', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
                        Column('ambient_temp',Float),
                        Column('humidity',Float),
                        )

    mfi_table = Table('fridge_power', metadata,
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
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
                        Column('id', Integer, primary_key=True,autoincrement=True),
                        Column('datetime', DateTime,default=datetime.datetime.utcnow),
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
                    )

    demand_response = Table('demand_response', metadata,
                    Column('id', Integer, primary_key=True,autoincrement=True),
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
    value.execute(value_dict)

def get_metadata(batchEngine=True):
    if batchEngine:
        engine = create_engine('postgresql://flexbox:flexbox@localhost/flexbox_db')
    else:
        engine = create_engine('postgresql://flexbox:flexbox@localhost/flexbox_db')

    metadata = MetaData(bind=engine)
    return metadata

def get_pi_metadata(batchEngine=True):
    if batchEngine:
        engine = create_engine('postgresql://flexbox:flexbox@10.10.10.1/flexbox_db')
    else:
        engine = create_engine('postgresql://flexbox:flexbox@10.10.10.1/flexbox_db')

    metadata = MetaData(bind=engine)
    return metadata

def get_session():
    engine = create_engine('postgresql://flexbox:flexbox@localhost/flexbox_db')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def get_last_row(table_ref):
    engine = create_engine('postgresql://flexbox:flexbox@localhost/flexbox_db')
    metadata = MetaData(bind=engine)
    table_dict = setup_tables(metadata)
    result =  table_ref.select().\
        order_by(table_ref.c.datetime.desc()).execute()
    output_dict = {}
    result_tuple = result.fetchone()
    for i,column_name in enumerate(result.keys()):
        output_dict[column_name] = result_tuple[i]
    return output_dict
