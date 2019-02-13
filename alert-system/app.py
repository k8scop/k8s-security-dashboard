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

page_index = ''
alerts_index = ''

start = None
end = None

max_alert_delta = 0
fetch_delay = 0


def parse_arguments():
    parser = ArgumentParser(description='K8sCop Alert System')

    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')

    required.add_argument('--elastic', '-E', dest='es', type=str,
                          help='ElasticSearch instance ip:port', required=True)

    required.add_argument('--page-index', '-I', dest='page_index', type=str,
                          help='Index of the logs page', required=True)

    required.add_argument('--alerts-index', '-i', dest='alerts_index',
                          type=str, help='Index of the alerts page',
                          default='alerts', required=True)

    required.add_argument('--start', '-s', dest='start', type=str,
                          help='Start date and time yyyy-m-d-h-m-s',
                          required=True)

    required.add_argument('--max-alert-delta', '-D', dest='max_alert_delta',
                          type=int,
                          help='Max delta for alert aggregation in seconds',
                          required=True)

    required.add_argument('--analysis', '-A', dest='analysis', type=str,
                          choices=['static', 'streaming'],
                          help='K8sCop static or streaming analysis',
                          required=True)

    optional.add_argument('--end', '-e', dest='end', type=str,
                          default='now',
                          help='End date and time yyyy-m-d-h-s or now')

    optional.add_argument('--fetch-delay', '-d', dest='fetch_delay', type=int,
                          choices=[5, 10, 12], default=10,
                          help='Delay between log fetches in seconds')

    return parser.parse_args()


def init_globals(args):
    global analysis
    global es
    global page_index
    global alerts_index
    global start
    global end
    global fetch_delay
    global max_alert_delta

    analysis = args.analysis

    es_string = args.es.split(':')
    es = Elasticsearch([{'host': es_string[0], 'port': int(es_string[1])}])

    page_index = args.page_index
    alerts_index = args.alerts_index

    s = list(map(int, args.start.split('-')))
    start = datetime(s[0], s[1], s[2], s[3], s[4], s[5])

    if analysis == 'static':
        e_string = args.end
        if e_string == 'now':
            end = datetime.utcnow()
        else:
            e = list(map(int, e_string.split('-')))
            end = datetime(e[0], e[1], e[2], e[3], e[4], e[5])
    else:
        end = datetime.utcnow() - timedelta(seconds=fetch_delay)
        fetch_delay = args.fetch_delay

    max_alert_delta = args.max_alert_delta

    # For Testing Purposes
    es.indices.delete(index=alerts_index, ignore=[400, 404])
    es.indices.create(index=alerts_index, ignore=[400, 404])


def run_processes(steve_jobs):
    for job in steve_jobs:
        job.setDaemon(True)
        job.start()

    for job in steve_jobs:
        job.join()


if __name__ == '__main__':
    args = parse_arguments()

    is_static = args.analysis == 'static'
    tracker = Tracker(is_static, False, False, False)

    try:
        print('[*] Starting K8sCop in %s mode' % args.analysis)
        init_globals(args)
        print('[+] Connected to ElasticSearch')

        fetch_queue = Queue()
        push_queue = Queue()

        print('[*] Initialising fetcher, parser, pusher components')
        fetcher = Fetcher(es, page_index, fetch_delay,
                          fetch_queue, tracker)

        parser = Parser(fetch_queue, push_queue, tracker)

        pusher = Pusher(es, alerts_index, max_alert_delta,
                        push_queue, tracker)
        print('[+] Components initialised')
    except Exception as e:
        print('[!] Something went terribly wrong')
        print('[-] %s' % e)
        exit(0)

    parser_t = Thread(target=parser.parse)

    pusher_t = Thread(target=pusher.push)

    if is_static:
        fetcher_t = Thread(target=fetcher.fetch, args=(start, end))
    else:
        fetcher_t = Thread(target=fetcher.fetch_streaming, args=(start, end))

    try:
        print('[*] Launching threads')
        run_processes([fetcher_t, parser_t, pusher_t])
        print('[+] K8sCop is done')
    except KeyboardInterrupt:
        print('[!] K8sCop force quit')
