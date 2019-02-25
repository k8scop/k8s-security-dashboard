from datetime import datetime, timedelta
from elasticsearch.helpers import scan as escan
from time import sleep


class Fetcher:
    def __init__(self, es, pages, delay, fetch_queue, tracker):
        self.es = es
        self.pages = pages
        self.delay = delay
        self.fetch_queue = fetch_queue
        self.tracker = tracker

    def fetch(self, start, end):
        while not self.tracker.fetcher_done:
            sleep(self.delay)

            self.__fetch(start, end)

            start = end
            end = end + timedelta(seconds=self.delay)

    def __fetch(self, gte, lte):
        gte_d = gte.date()
        lte_d = lte.date()

        if gte.date() == lte.date():
            self.__fetch_single_day(gte, lte)
        else:
            self.__fetch_first_day(gte)

            cursor_d = gte_d + timedelta(days=1)

            while cursor_d != lte_d:
                self.__fetch_all_day(cursor_d)

                cursor_d = cursor_d + timedelta(days=1)

            self.__fetch_last_day(lte)

        if self.tracker.tracking:
            self.tracker.fetcher_done = True
            print('[x] Fetcher is done')
            return

    def __fetch_single_day(self, gte, lte):
        index = '%s-%d.%02d.%02d' % (self.pages, gte.year, gte.month, gte.day)

        if self.es.indices.exists(index=index):
            self.__fetch_logs(index, gte, lte)

    def __fetch_first_day(self, gte):
        index = '%s-%d.%02d.%02d' % (self.pages, gte.year, gte.month, gte.day)

        if self.es.indices.exists(index=index):
            temp_lte = datetime(gte.year, gte.month, gte.day, 23, 59, 59)
            self.__fetch_logs(index, gte, temp_lte)

    def __fetch_all_day(self, cursor_d):
        index = '%s-%d.%02d.%02d' % (self.pages, cursor_d.year,
                                     cursor_d.month, cursor_d.day)

        if self.es.indices.exists(index=index):
            temp_gte = datetime(cursor_d.year, cursor_d.month,
                                cursor_d.day, 0, 0, 0)
            temp_lte = datetime(cursor_d.year, cursor_d.month,
                                cursor_d.day, 23, 59, 59)

            self.__fetch_logs(index, temp_gte, temp_lte)

    def __fetch_last_day(self, lte):
        index = '%s-%d.%02d.%02d' % (self.pages, lte.year, lte.month, lte.day)

        if self.es.indices.exists(index=index):
            temp_gte = datetime(lte.year, lte.month, lte.day, 0, 0, 0)
            self.__fetch_logs(index, temp_gte, lte)

    def __fetch_logs(self, page_index, gte, lte):
        print('[*] Log data from %s to %s from %s' % (gte, lte, page_index))

        jason = {
            'sort': [{'@timestamp': {'order': 'asc'}}],
            'query': {
                'bool': {
                    'must': {
                        'match': {
                            'origin': 'audit'
                        }
                    },
                    'filter': {
                        'range': {
                            '@timestamp': {
                                'gte': gte,
                                'lte': lte
                            }
                        }
                    }
                }
            }
        }

        res = escan(self.es, index=page_index, doc_type='fluentd',
                    preserve_order=True, query=jason)
        count = self.__add_to_fetch_queue(res)

        print('[+] Amount of data fetched: %d' % count)

    def __add_to_fetch_queue(self, res):
        count = 0

        for hit in res:
            self.fetch_queue.put(hit)

            count += 1

        return count
