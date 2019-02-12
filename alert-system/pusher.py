from datetime import datetime, timedelta
from time import sleep

from alert import Alert


class Pusher:
    def __init__(self, es, alerts_index, max_delta, push_queue, running):
        self.es = es
        self.alerts_index = alerts_index
        self.max_delta = max_delta
        self.push_queue = push_queue
        self.running = running

    def push(self):
        element, title = self.push_queue.get()

        index = element['_id']
        timestamp = element['_source']['@timestamp']

        latest_time = self.__get_latest_time(timestamp)

        old_alert = self.__search_alert(title, latest_time, timestamp)

        if old_alert is None:
            self.__push_new_alert(title, index, timestamp)
        else:
            self.__update_alert(old_alert, index, timestamp)

        sleep(1)

    def push_alerts_static(self):
        count = 0

        while self.push_queue.qsize() > 0:
            self.push()
            count += 1

        print('[+] Pushed %d alerts' % count)

    def push_alerts_update(self):
        while self.running:
            if self.push_queue.qsize() > 0:
                self.push()

    def __get_latest_time(self, timestamp):
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

        old_alert = None
        for hit in res['hits']['hits']:
            old_alert = hit

        return old_alert

    def __push_new_alert(self, title, index, timestamp):
        alert = Alert(timestamp, title, index, 1, timestamp)

        res = self.es.index(index=self.alerts_index, doc_type='doc',
                            body=alert.to_dict())

        print('[++] Added alert [%s] with _id %s' % (title, res['_id']))

    def __update_alert(self, old_alert, index, timestamp):
        _id = old_alert['_id']

        alert = Alert.from_dict(old_alert['_source'])

        alert.update(index, timestamp)

        self.es.update(index=self.alerts_index, doc_type='doc', id=_id,
                       body={'doc': alert.to_dict()})

        print('[+=] Updated alert with _id %s' % _id)
