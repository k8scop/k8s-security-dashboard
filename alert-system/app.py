#!venv/bin/python3

from argparse import ArgumentParser
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from threading import Thread
from queue import Queue

from fetcher import Fetcher
from parser import Parser
from pusher import Pusher
from tracker import Tracker

analysis = ''

es = None

pages = ''
alerts = ''

start = None
end = None

fetch_delay = 0

tracker = Tracker(False, False, False, False)


def parse_arguments():
    parser = ArgumentParser(description='K8sCop Alert System')

    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('--elastic', '-E', dest='es', type=str,
                          help='ElasticSearch instance ip:port', required=True)

    required.add_argument('--pages', '-I', dest='pages', type=str,
                          help='Name of the logs pages', required=True)

    required.add_argument('--alerts', '-i', dest='alerts', type=str,
                          help='Name of the alerts pages', default='alerts',
                          required=True)

    required.add_argument('--start', '-s', dest='start', type=str,
                          help='Start date and time yyyy-m-d-h-m-s',
                          required=True)

    required.add_argument('--analysis', '-A', dest='analysis', type=str,
                          choices=['static', 'streaming'],
                          help='K8sCop static or streaming analysis',
                          required=True)

    optional.add_argument('--end', '-e', dest='end', type=str,
                          default='now',
                          help='End date and time yyyy-m-d-h-s or now')

    optional.add_argument('--fetch-delay', '-d', dest='fetch_delay', type=int,
                          choices=[3, 5, 8, 10, 12], default=10,
                          help='Delay between log fetches in seconds')

    return parser.parse_args()


def init_globals(args):
    global analysis
    global es
    global pages
    global alerts
    global start
    global end
    global fetch_delay
    global tracker

    analysis = args.analysis

    es_string = args.es.split(':')
    es = Elasticsearch([{'host': es_string[0], 'port': int(es_string[1])}])

    pages = args.pages
    alerts = args.alerts

    s = list(map(int, args.start.split('-')))
    start = datetime(s[0], s[1], s[2], s[3], s[4], s[5])

    if analysis == 'static':
        tracker.set_tracking()

        e_string = args.end
        if e_string == 'now':
            end = datetime.utcnow()
        else:
            e = list(map(int, e_string.split('-')))
            end = datetime(e[0], e[1], e[2], e[3], e[4], e[5])
    else:
        end = datetime.utcnow() - timedelta(seconds=fetch_delay)
        fetch_delay = args.fetch_delay


def run_processes(steve_jobs):
    for job in steve_jobs:
        job.setDaemon(True)
        job.start()

    for job in steve_jobs:
        job.join()


if __name__ == '__main__':
    args = parse_arguments()
    init_globals(args)

    print(f'[*] Starting K8sCop in {analysis} mode')
    print('[+] Connected to ElasticSearch')

    try:
        fetch_queue = Queue()

        push_queue_dict = {}
        push_queue_dict['Enum'] = Queue()
        push_queue_dict['Tamper'] = Queue()
        push_queue_dict['Secrets'] = Queue()
        push_queue_dict['Exec'] = Queue()

        print('[*] Initialising fetcher, parser, pusher components')
        fetcher = Fetcher(es, pages, fetch_delay, fetch_queue, tracker)
        parser = Parser(fetch_queue, push_queue_dict, tracker)

        pusher_enu = Pusher('Enum', es, alerts,
                            push_queue_dict['Enum'], tracker)
        pusher_tam = Pusher('Tamper', es, alerts,
                            push_queue_dict['Tamper'], tracker)
        pusher_sec = Pusher('Secrets', es, alerts,
                            push_queue_dict['Secrets'], tracker)
        pusher_rce = Pusher('Exec', es, alerts,
                            push_queue_dict['Exec'], tracker)
        print('[+] Components initialised')
    except Exception as e:
        print('[!] Something went terribly wrong')
        print(f'[-] {e}')
        exit(0)

    fetcher_t = Thread(target=fetcher.fetch, args=(start, end))

    parser_t = Thread(target=parser.parse)

    pusher_t1 = Thread(target=pusher_enu.push)
    pusher_t2 = Thread(target=pusher_tam.push)
    pusher_t3 = Thread(target=pusher_sec.push)
    pusher_t4 = Thread(target=pusher_rce.push)

    try:
        print('[*] Launching threads')
        run_processes([fetcher_t, parser_t,
                       pusher_t1, pusher_t2, pusher_t3, pusher_t4])
        print('[x] K8sCop is done')
    except KeyboardInterrupt:
        print('[!] K8sCop force quit')
