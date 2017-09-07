#!/usr/bin/env python2

import ping
import requests
from xml.etree import ElementTree
import math
import time
from arrow import utcnow
from multiprocessing import Process, Queue
from flexbox import psql
import socket
import struct
import sys
import random

PCOUNT = 6
PINTERVAL = 30          # Seconds less than a minute
BINTERVAL = 120         # Minutes
BWSIZE = 375000         # Three Megabits (Mb) in Bytes (B)
BWSEND = ''.join(
                 [str(random.randint(0, 9)) for x in range(BWSIZE)]
                )

SERVERNAME = 'yourserverdomain.com'
PORT = 51337

# Database Setup
network_tests = psql.setup_tables(psql.get_metadata())['network_tests']

# TODO
# Use arrow arithmetic and arrow objects instead of seconds and magic numbers
# Add a SIGTERM handler
# xmit: optimize by pooling data together


def write_db(data):
    psql.add_values_to_table(network_tests, data)

def get_modem_usage():
    try:
        r = requests.get('http://192.168.8.1/api/monitoring/traffic-statistics')
        tree = ElementTree.fromstring(r.content)
        data_used_bytes = (int(tree.find('TotalDownload').text)+int(tree.find('TotalUpload').text))
        data_used_mb = data_used_bytes/1048576.0
        return data_used_mb
    except:
        return None


def send_report(data, connection):
    out = []
    for key in ('parm', 'hostname', 'seqn', 'ts', 'fail_pcnt', 'max', 'avg','modem_MB_used'):
        if (key == 'max' or key == 'avg' or key == 'modem_MB_used') and (data[key] is None):
            out.append(float('nan'))
        else:
            out.append(data[key])
    # struct_format = '=cppififfc'
    # connection.sendall(struct.pack(struct_format, *out))
    connection.sendall(",".join([str(x) for x in out]) + '|')


def test_bw(server, size_bytes, timeout):
    s = None
    fail = 100
    end_t = 0
    now_t = 0
    dur_t = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(1)
        s.settimeout(40)
        s.connect((SERVERNAME, PORT+1))
        now_t = utcnow().float_timestamp
        s.sendall(BWSEND)
        end_t = utcnow().float_timestamp
        fail = 0
        dur_t = (end_t - now_t)*1000
    except socket.timeout as to:
        print(to)
    except socket.error as se:
        print(se)
    except Exception as e:
        print(e)
    finally:
        if s is not None:
            s.close()
    res = (fail, dur_t, dur_t)  # % lost, max avg
    return res


def xmit(q):
    while True:
        data = q.get()
        write_db(data)

        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setblocking(1)
            s.settimeout(40)
            s.connect((SERVERNAME, PORT))
            send_report(data, s)
            # data = s.recv(1024)
        except socket.timeout as to:
            print(to)
        except socket.error as se:
            print(se)
        except Exception as e:
            print(e)
        finally:
            if s is not None:
                s.close()

        # print 'Received', repr(data)


def enqueue(q, result, timeout=1):
    try:
        q.put(result, block=True, timeout=timeout)
    except Queue.Full as qf:
        print(qf)


def main():

    hostname = socket.gethostname()
    p_timeout = max(int(math.floor(PINTERVAL / PCOUNT)), 1)

    # Communications handler

    out_q = Queue()
    proc = Process(target=xmit, args=(out_q,))
    proc.start()
    # proc.join()

    # Start reporting thread
    # This is the ping and bw thread

    # Start all the pings at a random offset to reduce collisions on reboot
    next_ping = utcnow().timestamp + PINTERVAL
    next_bw = utcnow().timestamp + BINTERVAL * 60

    p_seqn = 0
    b_seqn = 0
    while True:
        modem_usage = get_modem_usage()
        t_now = utcnow().timestamp

        next_ping = t_now + PINTERVAL
        res = ping.quiet_ping(SERVERNAME, count=PCOUNT, timeout=p_timeout)
        res = ('ping', hostname, p_seqn, t_now) + res+(modem_usage,)
        res = dict(list(zip(
            ('parm', 'hostname','seqn', 'ts', 'fail_pcnt', 'max', 'avg','modem_MB_used'),
            res)))
        print res
        enqueue(out_q, res, timeout=max(p_timeout, 1))
        p_seqn += 1
        t_stop = utcnow().timestamp

        # Also test BW
        if t_stop >= next_bw:
            next_bw = t_stop + BINTERVAL*60
            res = test_bw(SERVERNAME, size_bytes=BWSIZE, timeout=PINTERVAL)
            res = ('band', hostname, modem_usage, b_seqn, t_stop) + res + (modem_usage,)
            res = dict(list(zip(
                ('parm', 'hostname','seqn', 'ts', 'fail_pcnt', 'max', 'avg','modem_MB_used'),
                res)))
            enqueue(out_q, res)
            b_seqn += 1
            sys.stdout.write('*')

        # Wait until next ping test
        sys.stdout.write('.')
        if t_stop >= next_bw:
            sys.stdout.write('*')
        sys.stdout.flush()

        t_end = utcnow().timestamp
        if t_end < next_ping:
            time.sleep(next_ping - t_end)

if __name__ == "__main__":
    main()
