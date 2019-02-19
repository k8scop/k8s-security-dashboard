from time import sleep

from alert import Alert


class Pusher:
    def __init__(self, es, alerts, max_delta, push_queue, tracker):
        self.es = es
        self.alerts = alerts
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
                        print('[x] Pusher is done')
                        return

    def __push_alert(self):
        alert = self.push_queue.get()

        least_time = alert.get_max_delta(self.max_delta)

        timestamp_d = alert.get_timestamp_in_dt().date()

        index = '%s-%d.%02d.%02d' % (self.alerts, timestamp_d.year,
                                     timestamp_d.month, timestamp_d.day)

        if not self.es.indices.exists(index=index):
            self.es.indices.create(index=index, ignore=[400, 404])

        old_alert_dict = self.__search_alert(index, alert.title,
                                             least_time, alert.timestamp)

        self.__push_or_update(index, timestamp_d, old_alert_dict, alert)

        sleep(0.33)

    def __search_alert(self, alerts, title, gte, lte):
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

        res = self.es.search(index=alerts, body=jason)

        old_alert = None
        for hit in res['hits']['hits']:
            old_alert = hit

        return old_alert

    def __push_or_update(self, index, timestamp_d, old_alert_dict, alert):
        if old_alert_dict is None:
            self.__push_new_alert(index, alert)
        else:
            old_alert = Alert.from_dict(old_alert_dict['_source'])

            old_timestamp_d = old_alert.get_timestamp_in_dt().date()

            if old_timestamp_d != timestamp_d:
                index = '%s-%d.%02d.%02d' % (self.alerts,
                                             old_timestamp_d.year,
                                             old_timestamp_d.month,
                                             old_timestamp_d.day)

            self.__update_alert(index, old_alert_dict['_id'], old_alert, alert)

    def __push_new_alert(self, alerts, alert):
        res = self.es.index(index=alerts, doc_type='doc',
                            body=alert.to_dict())

        print('[++] [%s] %s' % (alert.title, res['_id']))

    def __update_alert(self, alerts, _id, old_alert, new_alert):
        old_alert.merge(new_alert)

        self.es.update(index=alerts, doc_type='doc', id=_id,
                       body={'doc': old_alert.to_dict()})

        print('[+=] Updated alert %s' % _id)
