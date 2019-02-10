from datetime import timedelta
from elasticsearch.helpers import scan as escan
import time


class Fetcher:
    def __init__(self, es, page_index, delay, fetch_queue, running):
        self.es = es
        self.page_index = page_index
        self.delay = delay
        self.fetch_queue = fetch_queue
        self.running = running

    def fetch(self, gte, lte):
        print('fetching data between %s and %s...' % (gte, lte))

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

        res = escan(self.es, index=self.page_index, doc_type='doc',
                    preserve_order=True, query=jason)

        return res

    def fetch_update(self, then):
        while self.running:
            time.sleep(self.delay)

            new_then = then + timedelta(seconds=self.delay)

            res = self.fetch(then, new_then)
            self.add_to_fetch_queue(res)

            then = new_then

    def add_to_fetch_queue(self, res):
        count = 0

        for hit in res:
            self.fetch_queue.put(hit)

            count += 1

        print('amount of data fetched: %d' % count)
