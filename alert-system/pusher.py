from time import sleep

from alert import Alert


class Pusher:
    def __init__(self, name, es, alerts, max_delta, push_queue, tracker):
        self.name = name
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
                        print('[x] %s Pusher is done' % self.name)
                        return

    def __push_alert(self):
        alert = self.push_queue.get()

        timestamp = alert.get_timestamp_in_dt()
        least_time = alert.get_max_delta(self.max_delta)

        old_alert_dict = self.__search_alert(alert.a_type, alert.description,
                                             least_time, alert.timestamp)

        self.__push_or_update(timestamp, old_alert_dict, alert)

    def __search_alert(self, a_type, description, gte, lte):
        index = '%s-%d.%02d.%02d' % (self.alerts, gte.year, gte.month, gte.day)

        jason = {
            'query': {
                'bool': {
                    'must': {
                        'match': {
                            'a_type': a_type
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

        old_alert_dict = None

        if self.es.indices.exists(index=index):
            res = self.es.search(index=index, body=jason)

            for hit in res['hits']['hits']:
                if hit['_source']['description'] == description:
                    old_alert_dict = hit
                    break

        return old_alert_dict

    def __push_or_update(self, timestamp, old_alert_dict, alert):
        if old_alert_dict is None:
            index = '%s-%d.%02d.%02d' % (self.alerts, timestamp.year,
                                         timestamp.month, timestamp.day)

            self.__push_new_alert(index, alert)
        else:
            old_alert = Alert.from_dict(old_alert_dict['_source'])

            old_timestamp = old_alert.get_timestamp_in_dt()

            if old_timestamp.date() != timestamp.date():
                index = '%s-%d.%02d.%02d' % (self.alerts,
                                             old_timestamp.year,
                                             old_timestamp.month,
                                             old_timestamp.day)
            else:
                index = '%s-%d.%02d.%02d' % (self.alerts, timestamp.year,
                                             timestamp.month, timestamp.day)

            self.__update_alert(index, old_alert_dict['_id'], old_alert, alert)

    def __push_new_alert(self, index, alert):
        if not self.es.indices.exists(index=index):
            self.es.indices.create(index=index, ignore=[400, 404])

        res = self.es.index(index=index, doc_type='doc',
                            body=alert.to_dict())

        print('[++] [%s] %s' % (alert.description, res['_id']))

        sleep(3)

    def __update_alert(self, index, _id, old_alert, new_alert):
        old_alert.merge(new_alert)

        self.es.update(index=index, doc_type='doc', id=_id,
                       body={'doc': old_alert.to_dict()})

        print('[+=] Updated alert %s' % _id)

        sleep(1)
