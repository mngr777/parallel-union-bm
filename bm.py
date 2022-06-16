#!/usr/bin/python3

import argparse
import datetime
import json
import psycopg2
from psycopg2 import sql as Sql
from statistics import mean, median

ColumnDefault = 'geom'
TimesDefault = 1

gVerbose = False

def vprint(*args, **kwargs):
    if (gVerbose): print(*args, **kwargs)

def load_connection(path):
    with open(path, 'r') as fd:
        data = json.load(fd)
        return data

def output_json(path, data):
    s = json.dumps(data, indent=4)
    if path == '-':
        print(s)
    else:
        file_output(path, s)

def file_output(path, data):
    # TODO: overwrite confirmation
    with open(path, 'w') as fd:
        fd.write(data)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--connection', '--conn', required=True, help='Connection config JSON file')
    parser.add_argument('--table', required=True, help='Table name')
    parser.add_argument('--column', default=ColumnDefault, help='Geometry column')
    parser.add_argument('--before', help='SQL to execute before running tests')
    parser.add_argument('--use-gridsize', action='store_true', help='Use grid size?')
    parser.add_argument('--add-buffer', action='store_true', help='add ST_Buffer')
    parser.add_argument('--times', type=int, default=TimesDefault, help='# of times to run tests')
    parser.add_argument('--out', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help='Print log messages')
    return parser.parse_args()

def time_ms_round(value):
    return round(value, 4)

def get_exec_time_ms(cursor):
    data = cursor.fetchone()[0][0]
    return data['Execution Time']

def bytes_to_str(value):
    return value.decode('utf-8')

def print_query(cursor):
    print('--------------------')
    print(bytes_to_str(cursor.query))
    print('--------------------')

def ident(text):
    return Sql.Identifier(text)

def execute(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor

def execute_file(conn, path):
    with open(path, 'r') as fd:
        sql = fd.read()
        vprint(sql)
        vprint()
        return execute(conn, sql)

def connect(params):
    conn = psycopg2.connect(**params)
    # connection.autocommit = True
    # connection.set_client_encoding('UTF8')
    return conn;

def test_parallel_union_explain(conn, args):
    ti = ident(args.table)
    ci = ident(args.column)
    gridsize_str = ', -1.0' if args.use_gridsize else ''
    if args.add_buffer:
        query = 'EXPLAIN SELECT ST_Union(ST_Buffer({}, 0.001)' + gridsize_str + ') AS geom FROM {}'
    else:
        query = 'EXPLAIN SELECT ST_Union({}' + gridsize_str + ') AS geom FROM {}'
    cursor = execute(conn, Sql.SQL(query).format(ci, ti))
    return map(lambda row: row[0], cursor.fetchall())

def test_parallel_union_request(conn, args):
    ti = ident(args.table)
    ci = ident(args.column)
    gridsize_str = ', -1.0' if args.use_gridsize else ''
    query = 'EXPLAIN (ANALYZE, FORMAT JSON) '
    if args.add_buffer:
        query += 'SELECT ST_Union(ST_Buffer({}, 0.001)' + gridsize_str + ') AS geom FROM {}'
    else:
        query += 'SELECT ST_Union({}' + gridsize_str + ') AS geom FROM {}'
    return execute(conn, Sql.SQL(query).format(ci, ti))

def test_parallel_union(conn, args, result):
    # Pring query plan
    plan = test_parallel_union_explain(conn, args)
    for line in plan:
        print(line)
    print()

    exec_times_ms = []
    for i in range(1, args.times + 1):
        # execute
        cursor = test_parallel_union_request(conn, args)
        time_ms = get_exec_time_ms(cursor)
        # print query first time
        if (i == 1):
            print_query(cursor)
        # print result
        vprint('  #{} {} ms'.format(i, time_ms_round(time_ms)))
        # store result
        exec_times_ms.append(time_ms)

    item = {
        'mean': time_ms_round(mean(exec_times_ms)),
        'median': time_ms_round(median(exec_times_ms))
    }
    print('mean: {} ms, median: {} ms'.format(item['mean'], item['median']))
    print()
    result['parallel_union'] = item

def run(conn, args):
    # Prepare
    if args.before:
        execute_file(conn, args.before)

    # Run tests
    result = {}

    test_parallel_union(conn, args, result)

    # Output
    if args.out:
        output_json(args.out, result)

def main():
    global gVerbose

    args = parse_args()
    gVerbose = args.verbose

    try:
        conn_params = load_connection(args.connection)
        conn = connect(conn_params)
        run(conn, args)

    except BaseException as e:
        print(e)

if __name__ == '__main__':
    main()
