from datetime import datetime, timedelta
from time import sleep

from alert import Alert


class Pusher:
    def __init__(self, es, alerts_index, max_delta, push_queue, tracker):
        self.es = es
        self.alerts_index = alerts_index
        self.max_delta = max_delta
        self.push_queue = push_queue
        self.tracker = tracker

    def push(self):
        while True:
            if self.push_queue.qsize() > 0:
                self.__push_alert()
            else:
                if self.tracker.tracking:
                    if self.tracker.parser_done:
                        self.tracker.pusher_done = True
                        print('[+] Pusher is done')
                        return

    def __push_alert(self):
        alert = self.push_queue.get()

        latest_time = self.__get_at_least_time(alert.timestamp)

        old_alert = self.__search_alert(alert.title, latest_time,
                                        alert.timestamp)

        if old_alert is None:
            self.__push_new_alert(alert)
        else:
            self.__update_alert(old_alert, alert)

        sleep(1)

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

        old_alert = None
        for hit in res['hits']['hits']:
            old_alert = hit

        return old_alert

    def __push_new_alert(self, alert):
        res = self.es.index(index=self.alerts_index, doc_type='doc',
                            body=alert.to_dict())

        print('[++] [%s] %s' % (alert.title, res['_id']))

    def __update_alert(self, old_alert, new_alert):
        _id = old_alert['_id']

        alert = Alert.from_dict(old_alert['_source'])
        alert.merge(new_alert)

        self.es.update(index=self.alerts_index, doc_type='doc', id=_id,
                       body={'doc': alert.to_dict()})

        print('[+=] Updated alert %s' % _id)

    def __get_at_least_time(self, timestamp):
        timestamp = timestamp.split('.')[0]
        datetime_t = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
        return datetime_t - timedelta(seconds=self.max_delta)
