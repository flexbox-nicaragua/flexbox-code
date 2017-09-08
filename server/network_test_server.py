#!/usr/bin/env python2
# Copyright 2016 The Flexbox Authors. All rights reserved.
# Licensed under the open source MIT License, which is in the LICENSE file.
from flexbox import psql_server
import socket
import traceback

# TODO
# Have the server run on both IPv4 and IPv6
RESULTS_PORT = 51337
network_tests = psql_server.setup_tables(
                                         psql_server.get_metadata()
                                         )['network_tests']


def setup_reciever(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', RESULTS_PORT))
    s.listen(60)
    return s


def get_result(reciever):
    while True:
        c, addr = reciever.accept()
        c.settimeout(10)
        stuff = ""
        try:
            while not ('|' in stuff):
                stuff += c.recv(4096)
        except Exception as e:
            stuff = None
            print('Exception')
            print(e)
            print(traceback.print_exc())
        finally:
            if c is not None:
                c.close()
        yield stuff


def clean_results(results):
    while True:
        for res in results:
            if res is not None and res.endswith('|'):
                yield res


def main():
    print(socket.getaddrinfo(None, RESULTS_PORT, socket.AF_UNSPEC,
                             socket.SOCK_STREAM, 0, socket.AI_PASSIVE))
    result_src = clean_results(get_result(setup_reciever(RESULTS_PORT)))
    for netstat_val in result_src:
        netstat_val = netstat_val[0:-1].split(',')

        output_dict = dict(list(zip(['parm', 'hostname', 'seqn', 'ts',
                                     'fail_pcnt', 'max', 'avg', 'modem_MB_used',
                                    'uptime_minutes'],
                                    netstat_val)))
        if output_dict['hostname'] == 'flxbxD0':
            print(output_dict)
            print netstat_val
            print result_src
        try:
            psql_server.add_values_to_table(network_tests, output_dict)
        except Exception:
            print(traceback.print_exc())


if __name__ == "__main__":
    main()
