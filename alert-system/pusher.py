class Pusher:
    def __init__(self, name, es, alerts, push_queue, tracker):
        self.name = name
        self.es = es
        self.alerts = alerts
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

        index = '%s-%d.%02d.%02d' % (self.alerts, timestamp.year,
                                     timestamp.month, timestamp.day)

        if not self.es.indices.exists(index=index):
            self.es.indices.create(index=index, ignore=[400, 404])

        self.es.index(index=index, doc_type='doc', body=alert.to_dict())

        print('[++] [%s]' % (alert.description))
