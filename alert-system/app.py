#!venv/bin/python3

from argparse import ArgumentParser
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from threading import Thread
from queue import Queue

from fetcher import Fetcher
from parser import Parser
from pusher import Pusher

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
                          help='End date and time yyyy-m-d-h-s')

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

    e = args.es.split(':')
    es = Elasticsearch([{'host': e[0], 'port': int(e[1])}])

    page_index = args.page_index
    alerts_index = args.alerts_index

    s = list(map(int, args.start.split('-')))
    start = datetime(s[0], s[1], s[2], s[3], s[4], s[5])

    if analysis == 'static':
        e = list(map(int, args.end.split('-')))
        end = datetime(e[0], e[1], e[2], e[3], e[4], e[5])
    else:
        end = datetime.utcnow() - timedelta(seconds=fetch_delay)
        fetch_delay = args.fetch_delay

    max_alert_delta = args.max_alert_delta

    # For Testing Purposes
    es.indices.delete(index=alerts_index, ignore=[400, 404])
    es.indices.create(index=alerts_index)


def run_processes(steve_jobs):
    for job in steve_jobs:
        job.setDaemon(True)
        job.start()

    print('[+] Threads launched')

    for job in steve_jobs:
        job.join()


if __name__ == '__main__':
    args = parse_arguments()

    try:
        print('[*] Starting %s K8sCop' % args.analysis)
        init_globals(args)
        print('[+] Connected to ElasticSearch')

        fetch_queue = Queue()
        push_queue = Queue()

        running = True

        print('[*] Initialising fetcher, parser, pusher components')
        fetcher = Fetcher(es, page_index, fetch_delay, fetch_queue, running)
        parser = Parser(fetch_queue, push_queue, running)
        pusher = Pusher(es, alerts_index, max_alert_delta, push_queue, running)
        print('[+] Components initialised')

        print('[*] Fetching initial log bulk')
        res = fetcher.fetch(start, end)
        fetcher.add_to_fetch_queue(res)
        print('[+] Log bulk fetched')

        print('[*] Parsing log bulk and searching for incidents')
        parser.parse_static()
        print('[+] Initial log bulk parsed')

        print('[*] Pushing alerts')
        pusher.push_alerts_static()
    except Exception as e:
        print('[!] Something went terribly wrong')
        print('[-] %s' % e)
        exit(0)

    if analysis == 'streaming':
        try:
            print('[*] Making threads')
            fetcher_t = Thread(target=fetcher.fetch_update, args=(end,))
            parser_t = Thread(target=parser.parse_update)
            pusher_t = Thread(target=pusher.push_alerts_update)
            run_processes([fetcher_t, parser_t, pusher_t])
        except KeyboardInterrupt:
            running = False
            exit(0)
    else:
        print('[+] K8sCop static analysis done')
