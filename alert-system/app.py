#!venv/bin/python3

from fetcher import Fetcher
from parser import Parser
from pusher import Pusher

from datetime import datetime
from elasticsearch import Elasticsearch
from threading import Thread
import queue

es = None

page_index = ''
alerts_index = ''

start = None
fetch_delay = 0
max_alert_delta = 0


def init_globals():
    global es
    global page_index
    global alerts_index
    global start
    global fetch_delay
    global max_alert_delta

    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    page_index = 'filebeat-6.5.4-2019.02.09'
    alerts_index = 'alerts'

    start = datetime(2019, 2, 9, 0, 0, 0)

    fetch_delay = 10
    max_alert_delta = 600

    # For Testing Purposes
    es.indices.delete(index=alerts_index, ignore=[400, 404])
    es.indices.create(index=alerts_index)


def run_processes(steve_jobs):
    for job in steve_jobs:
        job.setDaemon(True)
        job.start()

    for job in steve_jobs:
        job.join()


# ./app.py
# -E localhost:9200
# -I filebeat-6.5.4-2019.02.08
# -i alerts
# -s 2019-2-9-10-0-0
# -d 10
# -m 600
if __name__ == '__main__':
    init_globals()

    fetch_queue = queue.Queue()
    push_queue = queue.Queue()

    running = True

    # then = datetime.now() - timedelta(seconds=fetch_delay)
    then = datetime(2019, 2, 9, 18, 0, 0)

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
