from alert import Alert

from datetime import datetime, timedelta
import time


class Pusher:
    def __init__(self, es, alerts_index, max_delta, push_queue, running):
        self.es = es
        self.alerts_index = alerts_index
        self.max_delta = max_delta
        self.push_queue = push_queue
        self.running = running

    def push_alerts(self):
        while self.running:
            if self.push_queue.qsize() > 0:
                element, title = self.push_queue.get()

                index = element['_id']
                timestamp = element['_source']['@timestamp']

                gte = self.__get_gte(timestamp)

                a = self.__search_alert(title, gte, timestamp)

                if a is None:
                    self.__push_new_alert(title, index, timestamp)
                else:
                    self.__update_alert(a, index, timestamp)

                time.sleep(1)

    def __get_gte(self, timestamp):
        datetime_t = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        return datetime_t - timedelta(seconds=self.max_delta)

    def __search_alert(self, title, gte, lte):
        jason = {
            'query': {
                'bool': {
                    'must': {
                        'match': {
                            'title': title
                        }
                    },
                    'filter': {
                        'range': {
                            'last_seen': {
                                'gte': gte,
                                'lte': lte
                            }
                        }
                    }
                }
            }
        }

        res = self.es.search(index=self.alerts_index, body=jason)

        a = None
        for hit in res['hits']['hits']:
            a = hit

        return a

    def __push_new_alert(self, title, index, timestamp):
        alert = Alert(timestamp, title, [index], 1, timestamp)

        self.es.index(index=self.alerts_index, doc_type='doc',
                      body=alert.to_dict())

        print('added %s' % title)

    def __update_alert(self, a, index, timestamp):
        _id = a['_id']

        a = Alert.from_dict(a['_source'])

        a.update(index, timestamp)

        self.es.update(index=self.alerts_index, doc_type='doc', id=_id, 
                       body={'doc': a.to_dict()})

        print('updated %s' % a.title)
