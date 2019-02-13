from datetime import timedelta
from elasticsearch.helpers import scan as escan
from time import sleep


class Fetcher:
    def __init__(self, es, page_index, delay, fetch_queue, tracker):
        self.es = es
        self.page_index = page_index
        self.delay = delay
        self.fetch_queue = fetch_queue
        self.tracker = tracker

    def fetch(self, gte, lte):
        print('[*] Log data between %s and %s' % (gte, lte))

        jason = {
            'sort': [{'@timestamp': {'order': 'asc'}}],
            'query': {
                'range': {
                    '@timestamp': {
                        'gte': gte,
                        'lte': lte
                    }
                }
            }
        }

        res = escan(self.es, index=self.page_index, doc_type='fluentd',
                    preserve_order=True, query=jason)
        self.__add_to_fetch_queue(res)

    def fetch_streaming(self, start, end):
        while True:
            sleep(self.delay)

            self.fetch(start, end)

            start = end
            end = end + timedelta(seconds=self.delay)

    def __add_to_fetch_queue(self, res):
        count = 0

        for hit in res:
            self.fetch_queue.put(hit)

            count += 1

        if self.tracker.tracking:
            self.tracker.fetcher_done = True
            print('[+] Fetcher is done')
            return

        print('[+] Amount of data fetched: %d' % count)
