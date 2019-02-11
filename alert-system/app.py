#!venv/bin/python3

from fetcher import Fetcher
from parser import Parser
from pusher import Pusher

from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from threading import Thread
import argparse
import queue

es = None

page_index = ''
alerts_index = ''

start = None
fetch_delay = 0
max_alert_delta = 0


def parse_arguments():
    parser = argparse.ArgumentParser(description='K8sCop Alert System')

    required = parser.add_argument_group('required arguments')

    required.add_argument('--elastic', '-E', dest='es', type=str,
                          help='ElasticSearch instance ip:port', required=True)

    required.add_argument('--page-index', '-I', dest='page_index', type=str,
                          help='Index of the log page', required=True)

    required.add_argument('--alerts-index', '-i', dest='alerts_index',
                          type=str, help='Index of the alerts page',
                          default='alerts', required=True)

    required.add_argument('--start', '-s', dest='start', type=str,
                          help='Start date and time yyyy-m-d-h-m-s',
                          required=True)

    required.add_argument('--fetch-delay', '-d', dest='fetch_delay', type=int,
                          help='Delay between log fetches in seconds',
                          required=True)

    required.add_argument('--max-alert-delta', '-D', dest='max_alert_delta',
                          type=int,
                          help='Max delta for alert aggregation in seconds',
                          required=True)

    return parser.parse_args()


def init_globals(args):
    global es
    global page_index
    global alerts_index
    global start
    global fetch_delay
    global max_alert_delta

    e = args.es.split(':')
    es = Elasticsearch([{'host': e[0], 'port': int(e[1])}])

    page_index = args.page_index
    alerts_index = args.alerts_index

    s = list(map(int, args.start.split('-')))
    start = datetime(s[0], s[1], s[2], s[3], s[4], s[5])

    fetch_delay = args.fetch_delay
    max_alert_delta = args.max_alert_delta

    # For Testing Purposes
    es.indices.delete(index=alerts_index, ignore=[400, 404])
    es.indices.create(index=alerts_index)


def run_processes(steve_jobs):
    for job in steve_jobs:
        job.setDaemon(True)
        job.start()

    for job in steve_jobs:
        job.join()


if __name__ == '__main__':
    args = parse_arguments()
    init_globals(args)

    fetch_queue = queue.Queue()
    push_queue = queue.Queue()

    running = True

    then = datetime.now() - timedelta(seconds=fetch_delay)

    fetcher = Fetcher(es, page_index, fetch_delay, fetch_queue, running)
    parser = Parser(fetch_queue, push_queue, running)
    pusher = Pusher(es, alerts_index, max_alert_delta, push_queue, running)

    res = fetcher.fetch(start, then)
    fetcher.add_to_fetch_queue(res)

    try:
        fetcher_t = Thread(target=fetcher.fetch_update, args=(then,))
        parser_t = Thread(target=parser.parse)
        pusher_t = Thread(target=pusher.push_alerts)
        run_processes([fetcher_t, parser_t, pusher_t])
    except KeyboardInterrupt:
        running = False
