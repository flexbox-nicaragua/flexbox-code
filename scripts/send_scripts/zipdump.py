#!/usr/bin/env python2
# -*- coding: ascii -*-

from flexbox import psql
from datetime import datetime, timedelta
import time
from itertools import islice
from sqlalchemy import and_
import sqlalchemy
import yaml
import os
import logging
import tarfile
import gzip
import csv
import StringIO
import socket
import sys

#mounting the usb reliably
#flask endpoints
#make manual launch button
#add tar logs
#split up UI to make it faster
#Is it the rendering or the bw?
#make one call that gets x values for each table at the same time
#just one endpoint with all single values
#add refresh per table and finally have dump link
#take all data from last dump
#TODO local filename save <a download='FileName' href='your_url'>
#realtime rfresh
#TODO how is postgres doing comparisons on dates? Does it assume gmtime? Also, how is python rendering them?
#TODO there's a scenario where not all data is collected. If at a single point in time a date earlier than the present is recorded only the data after the bad earlier date will be retained.
#update setup.py to copy files into etc

APPNAM = 'zipdump'
APPVER = '2'
REPORTSTR = ":{}: version :{}:. Table backup from :{}:. Pulling data from :{}:, with first data point found on day :{}: with datetime :{}:, and having id :{}:. The most recent data point is :{}:. The data covers :{}:/:{}: points"
YAMLCFGDIR =  '/etc/flexbox/'
YAMLCFGFILE = 'backup_cfg.yaml'
DAYFORMAT = "%Y-%m-%d_"


#http://stackoverflow.com/questions/5680264/python-create-a-compressed-tar-file-for-streamed-writing
def add_tar_info(tar, data, db_name):
    data.seek(0)
    info = tar.tarinfo()
    info.name = '{}.csv'.format(db_name)
    info.uname = 'flexbox'
    info.gname = 'flexbox'
    cur_time = time.time()
    info.ctime = cur_time
    info.mtime = cur_time
    info.atime = cur_time
    info.size = data.len
    tar.addfile(info, data)


def tar_dump(path, dct, start_date_time,
             end_date_time, metadata, dirs, note="", out_file=None):
    import StringIO
    import tarfile
    import time
    if out_file == None:
        out_file = 'zipdump_{}_{}_{}_{}.tar.gz'.format(
            note, int(time.time()), start_date_time.strftime('%Y-%m-%d-%H-%M-%S'),
            end_date_time.strftime('%Y-%m-%d-%H-%M-%S')
        )
    tar = tarfile.open(os.path.join(path, out_file), 'w:gz')

    for db in dct:
        add_tar_info(tar, dct[db], db)
    add_tar_info(tar, metadata, 'metadata')
    for d in dirs:
        tar.add(d)
    tar.close()

#def tar_logs(log_dir, out_path, name):
#    now = datetime.now()
#    name = now.strftime(DAYFORMAT + socket.gethostname()
#    file_name = os.path.join(out_path, name + ".tar.gz")
#    tar = tarfile.open(file_name, "w:gz")
#    tar.add(log_dir)
#    tar.close()
#    return file_name
#

class metadata(object):
    def __init__(self, version, domain, context):
        self.version = version
        self.domain = domain
        self.context = context

    """Parition can be column, row, or cell if it's a single cell.
    aspect_index must be a key which identifies the cell or cells when combines with the aspect."""
    def add_key(self, aspect, key, typ, value, parition="Column", aspect_index=None):
        pass

    def get_keys(self):
        pass


import logging
LOGYAMLCFGFILE = "/etc/flexbox/log_cfg.yaml"
LEVELNAMES = {'NOTSET':logging.NOTSET, 'DEBUG':logging.DEBUG,  'WARN':logging.WARN, 'WARNING':logging.WARNING, 'INFO':logging.INFO, 'ERROR':logging.ERROR, 'CRITICAL':logging.CRITICAL, 'FATAL':logging.FATAL}
with open(LOGYAMLCFGFILE,'r') as f:
    cfg = yaml.safe_load(f)
    log_name = '-'.join([APPNAM, APPVER,  __name__])
    log_dir = cfg['log_dir']
    log_file = os.path.join(log_dir, log_name)
    log_debug_level = logging.NOTSET
    if cfg['log_level'] in  LEVELNAMES:
        log_debug_level = LEVELNAMES[cfg['log_level']]
    try:
        logging.basicConfig(filename=log_file, format='%(asctime)s:%(levelname)s:%(message)s', level=log_debug_level)
    except IOError:
        print('Defaulting to logfile in current directoy.')
        logging.basicConfig(filename=os.path.join('.', log_name), level=log_debug_level)


def main():
    with open(os.path.join(YAMLCFGDIR, YAMLCFGFILE), 'r') as f:
        cfg = yaml.safe_load(f)
        past_days = int(cfg['past_days'])
        tables = cfg['tables']
        backup_path = os.path.join(cfg['dev'], cfg['dir'], socket.gethostname())
        table_settings = cfg['table_settings']
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)


    current_date = datetime(*(time.gmtime()[0:3]))
    start_date =  current_date - timedelta(days=past_days)
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)

    data = {}
    metadata = []
    earliest_datapoint_date = datetime(3000,1,1)
    latest_datapoint_date = datetime(1970,1,1)
    for table_name in tables:
        test_date = start_date
        table = table_dict[table_name]
        values = []

        #Look for first id after the requested date
        test_values = []
        while test_date <= current_date:
            test_values = table.select().where(
                    and_(test_date <= table.c.datetime,
                        table.c.datetime < (test_date + timedelta(days=1)))).execute()
            test_values_cols = test_values.keys()
            test_values = test_values.fetchall()
            if len(test_values):
                break
            test_date += timedelta(days=1)

        #test_values, table min,max limits,
        #write out csv as another fcn table_name, colnames, values
        if len(test_values):
            #pull data starting from the entry with that date
            start_date_id = min(zip(*test_values)[test_values_cols.index('id')])
            count = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
                        table).execute().fetchone()[0]
            min_pull = max(int(table_settings[table_name]['min'])*past_days, count - start_date_id + 1)
            limit = min(min_pull, int(table_settings[table_name]['max'])*past_days)
            values = table.select().order_by(table.c.id).limit(limit).execute()#.where(table.c.id >= start_date_id).
            colnames = values.keys()
            values = values.fetchall()
            first_datapoint_date = min(zip(*values)[colnames.index('datetime')])
            last_datapoint_date = max(zip(*values)[colnames.index('datetime')])

            csvIO = StringIO.StringIO()
            outCSV = csv.writer(csvIO)
            outCSV.writerow(colnames)
            outCSV.writerows(values)
            data[table_name] = csvIO

            #metadata and logging
            earliest_datapoint_date = min(earliest_datapoint_date, first_datapoint_date)
            latest_datapoint_date = max(latest_datapoint_date, last_datapoint_date)
            report = REPORTSTR.format(
                APPNAM, APPVER, table_name, start_date, test_date,
                first_datapoint_date, start_date_id, last_datapoint_date,
                len(values), count
            )
            metadata.append(report)
            print(report)
            logging.info(report)
        print(table_name)

    with open(LOGYAMLCFGFILE,'r') as f:
        cfg = yaml.safe_load(f)
        log_name = '-'.join([APPNAM, APPVER,  __name__])
        log_dir = cfg['log_dir']

    out_file = None
    if len(sys.argv) > 1:
        out_file = sys.argv[1]
        out_file = str(time.time()) + '_' + out_file
    tar_dump(backup_path, data, earliest_datapoint_date,
             latest_datapoint_date, StringIO.StringIO("\n".join(metadata)),
             [YAMLCFGDIR, log_dir], 'V' + APPVER, out_file)


if __name__ == "__main__":
    main()

