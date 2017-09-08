# Copyright 2016 The Flexbox Authors. All rights reserved.  
# Licensed under the open source MIT License, which is in the LICENSE file.  
from flask import Flask, jsonify, send_file, make_response, request
from flexbox import psql
from datetime import datetime,timedelta
import subprocess
import os
import socket
import tarfile
import gzip
import csv
import logging
from pytz import timezone
from logging.handlers import RotatingFileHandler
import yaml
app = Flask(__name__)

num = 5
error_seconds_since_last_record = 180
fmt = "%Y-%m-%d %H:%M:%S"
localtz = timezone('America/Managua')
now = datetime.now()
BACKUPCFGFILE = '/etc/flexbox/backup_cfg.yaml'



def get_zwave(num=num):
    #app.logger.error('An error occurred')
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)
    table_name = 'zwave_table'
    columns=['id','datetime','house_Voltage','house_Current','house_Power','house_Energy']
    output,rows = get_rows(table_dict[table_name],columns,num)
    return [output,columns,rows]

def get_mfi(num=num):
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)
    table_name = 'mfi_table'
    columns=['id','datetime','v_rms1','v_rms2','v_rms3','i_rms1','i_rms2','i_rms3',\
    'pf1','pf2','pf3','energy_sum1','energy_sum2','energy_sum3','active_pwr1',\
    'active_pwr2','active_pwr3','relay1','relay2','relay3']
    output,rows = get_rows(table_dict[table_name],columns,num)
    return [output,columns,rows]

def get_inside(num=num):
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)
    table_name = 'inside_table'
    columns=['id','datetime','inside_temp1','inside_temp2']
    output,rows = get_rows(table_dict[table_name], columns, num)
    return [output,columns,rows]

def get_switch(num=num):
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)
    table_name = 'switch_table'
    columns=['id','datetime','switch']
    output,rows = get_rows(table_dict[table_name],columns,num)
    return [output,columns,rows]

def get_ambient(num=num):
    metadata = psql.get_metadata()
    table_dict = psql.setup_tables(metadata)
    table_name = 'ambient_table'
    columns=['id','datetime','ambient_temp','humidity']
    output,rows = get_rows(table_dict[table_name],columns,num)
    return [output,columns,rows]

def make_csv(query_list,table_name,columns,name):

    if not os.path.exists(name):
        os.makedirs(name)

    with open(name+'/'+table_name+'.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(columns)
        writer.writerows(query_list)

def make_tar(outputs,name):
    for key in outputs:
        make_csv(outputs[key][2],key,outputs[key][1],name)
    tar = tarfile.open(name+".tar.gz", "w:gz")
    tar.add(name)
    tar.close()
    for key in outputs:
        os.remove(name+"/"+key+".csv")
    os.rmdir(name)
    return name+".tar.gz"

@app.route("/backup_dir")
def get_sd_files():
    with open(BACKUPCFGFILE, 'r') as f:
        cfg = yaml.safe_load(f)
        backup_dir = os.path.join(cfg['dev'], cfg['dir'], socket.gethostname())
    if not os.path.exists(backup_dir):
        return jsonify({})
    backup_files = os.listdir(backup_dir)
    backup_files.sort()
    file_listing = {k:{'fname':k} for k in backup_files}
    if request.args.get('fname', ''):
        fname = request.args.get('fname')
        if fname in backup_files:
            return send_file(os.path.join(backup_dir, fname),
                             mimetype='application/x-gzip')
                             #attachment_filename=fname, as_attachment=True)
        else:
            return make_response("File not found.", 404)
    if request.args.get('update', ''):
        subprocess.Popen(
            ["nohup", "python",
            "/home/pi/flexbox/scripts/send_scripts/zipdump.py"
        ])
        waitHTML = "\n".join([
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">',
            '<html>',
            '<head>',
            '<title>Updating Backup</title>',
            '<meta http-equiv="refresh" content="5; url=backups.html">',
            '</head>',
            '<body>',
            '<p>Backup in progress please wait 5 minutes for a refresh.</p>',
            '<p><a href="backups.html">',
            '<h1>Click here to proceed to the backups listing.</h1>',
            '</a>Note that the backup might not be available yet.</p>',
            '</body>',
            '</html>'])
        return make_response(waitHTML,200)

    for k in backup_files:
        if k.startswith('zipdump'):
            metadata = k.split('_')
            if len(metadata) == 5:
                appname, note, timestamp, start_date, end_date = metadata
                file_listing[k]['appname'] = appname
                file_listing[k]['note'] = note
                file_listing[k]['timestamp'] = timestamp
                file_listing[k]['start_date'] = start_date
                file_listing[k]['end_date'] = end_date[0:-7]
                file_listing[k]['file_location'] = os.path.join(backup_dir, k)
                file_listing[k]['short_name'] = "_".join([appname, note, timestamp])
        else:
            file_listing[k]['appname'] = 'na'
    return jsonify(file_listing)

#TODO Sanitize columns
@app.route("/get_rows")
def get_rows_wrapper():
    try:
        metadata = psql.get_metadata()
        table_dict = psql.setup_tables(metadata)
        table = request.args.get('table')
        columns = request.args.get('columns').split(',')
        if 'id' in columns:
            columns.remove('id')
        if 'datetime' in columns:
            columns.remove('datetime')
        columns.insert(0,'id')
        columns.insert(1,'datetime')
        num = int(request.args.get('num'))
        output = get_rows(table_dict[table], columns, int(num))
    except Exception , e :
        out = 'Query Failed.\n'
        out += str(request.args)
        out += str(e)

        return make_response(out, 404)
    return jsonify(output[0])

def get_rows(table,columns,num):

    values = table.select().order_by(table.c.id.desc()).limit(num)
    result = values.execute()
    columns = result.keys()
    rows = result.fetchall()
    most_recent_entry = rows[0]['datetime'] - timedelta(hours=6)
    output = {}
    all_rows = []
    for row in rows:
        row_object = {}
        for i,column in enumerate(columns):
            if column == 'datetime':
                row_object[column] = (row[i]-timedelta(hours=6)).strftime(fmt)
            else:
                row_object[column] = row[i]
        all_rows.append(row_object)
    output['result'] = all_rows
    output['last_record'] =  most_recent_entry.strftime(fmt)
    output['since_last_record'] = (datetime.now() - most_recent_entry).seconds
    if len(rows) > 0 and float(output['since_last_record']) > error_seconds_since_last_record:
         output['status'] = 'ERROR'
    else:
        output['status'] = 'GOOD'
    return output,rows

@app.route("/1all")
def print_1all():
    ambient, _, _ = get_ambient(1)
    switch, _, _ = get_switch(1)
    zwave, _, _ = get_zwave(1)
    mfi, _, _ = get_mfi(1)
    inside, _, _ = get_inside (1)
    output = {'ambient':ambient, 'switch': switch, 'zwave': zwave, 'mfi': mfi, 'inside': inside}
    return jsonify(output)

@app.route("/ambient")
def print_ambient():
    output = get_ambient(num)
    return jsonify(output[0])

@app.route("/switch")
def print_switch():
    output = get_switch(num)
    return jsonify(output[0])

@app.route("/inside")
def print_inside():
    output = get_inside(num)
    return jsonify(output[0])

@app.route("/mfi")
def print_mfi():
    output = get_mfi(num)
    return jsonify(output[0])

@app.route("/zwave")
def print_zwave():
    output = get_zwave(num)
    return jsonify(output[0])

@app.route("/dump2months")
def get_csv_2months():
    all_outputs = {}
    all_outputs['zwave'] = get_zwave(345600)
    all_outputs['ambient'] = get_ambient(345600)
    all_outputs['inside'] = get_inside(105795)
    all_outputs['switch'] = get_switch(100000)
    all_outputs['mfi'] = get_mfi(100000)
    name = "flbx2mnths"+str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(socket.gethostname())
    filename = make_tar(all_outputs,dir_prefix+name)
    return send_file(filename, mimetype='application/x-gzip')

@app.route("/dumpAll")
def get_csv_all():
    all_outputs = {}
    all_outputs['zwave'] = get_zwave(None)
    all_outputs['ambient'] = get_ambient(None)
    all_outputs['inside'] = get_inside(None)
    all_outputs['switch'] = get_switch(None)
    all_outputs['mfi'] = get_mfi(None)
    name = "flbx2mnths"+str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(socket.gethostname())
    filename = make_tar(all_outputs,dir_prefix+name)
    return send_file(filename, mimetype='application/x-gzip')

@app.route("/getLogs")
def get_logs():

    tar = tarfile.open(name+".tar.gz", "w:gz")
    tar.add(name)
    tar.close()
    name = "flbx2mnths"+str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(socket.gethostname())
    filename = make_tar(all_outputs,dir_prefix+name)
    return send_file(filename, mimetype='application/x-gzip')

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  return app.send_static_file(path)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=80)
