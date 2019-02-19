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

        if gte_d == lte_d:
            self.__fetch_single_day(gte, gte_d, lte)
        else:
            self.__fetch_first_day(gte, gte_d)

            cursor_d = gte_d + timedelta(days=1)

            while cursor_d != lte_d:
                self.__fetch_all_day(cursor_d)

                cursor_d = cursor_d + timedelta(days=1)

            self.__fetch_last_day(lte, lte_d)

        if self.tracker.tracking:
            self.tracker.fetcher_done = True
            print('[x] Fetcher is done')
            return

    def __fetch_single_day(self, gte, gte_d, lte):
        index = '%s-%d.%02d.%02d' % (self.pages, gte_d.year, gte_d.month,
                                     gte_d.day)

        if self.es.indices.exists(index=index):
            self.__fetch_logs(index, gte, lte)

    def __fetch_first_day(self, gte, gte_d):
        index = '%s-%d.%02d.%02d' % (self.pages, gte_d.year, gte_d.month,
                                     gte_d.day)

        if self.es.indices.exists(index=index):
            temp_lte = datetime(gte_d.year, gte_d.month, gte_d.day, 23, 59, 59)
            self.__fetch_logs(index, gte, temp_lte)

    def __fetch_all_day(self, cursor_d):
        index = '%s-%d.%02d.%02d' % (self.pages, cursor_d.year, cursor_d.month,
                                     cursor_d.day)

        if self.es.indices.exists(index=index):
            temp_gte = datetime(cursor_d.year, cursor_d.month,
                                cursor_d.day, 0, 0, 0)
            temp_lte = datetime(cursor_d.year, cursor_d.month,
                                cursor_d.day, 23, 59, 59)

            self.__fetch_logs(index, temp_gte, temp_lte)

    def __fetch_last_day(self, lte, lte_d):
        index = '%s-%d.%02d.%02d' % (self.pages, lte_d.year, lte_d.month,
                                     lte_d.day)

        if self.es.indices.exists(index=index):
            temp_gte = datetime(lte_d.year, lte_d.month, lte_d.day, 0, 0, 0)
            self.__fetch_logs(index, temp_gte, lte)

    def __fetch_logs(self, page_index, gte, lte):
        print('[*] Log data from %s to %s from %s' % (gte, lte, page_index))

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

        # jason = {
        #     'sort': [{'@timestamp': {'order': 'asc'}}],
        #     'query': {
        #         'bool': {
        #             'must': {
        #                 'term': {
        #                     'tag.keyword': 'kube-apiserver-audit'
        #                 }
        #             },
        #             'filter': {
        #                 'range': {
        #                     '@timestamp': {
        #                         'gte': gte,
        #                         'lte': lte
        #                     }
        #                 }
        #             }
        #         }
        #     }
        # }

        jason = {
            "query": {
                "match": {
                    "tag.keyword": {
                        "query": "kube-apiserver-audit",
                        "type": "phrase"
                    }
                }
            }
        }

        res = escan(self.es, index=page_index, doc_type='fluentd',
                    preserve_order=True, query=jason)
        self.__add_to_fetch_queue(res)

    def __add_to_fetch_queue(self, res):
        count = 0

        for hit in res:
            self.fetch_queue.put(hit)

            count += 1

        print('[+] Amount of data fetched: %d' % count)
