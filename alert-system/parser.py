class Parser:
    def __init__(self, fetch_queue, push_queue, running):
        self.fetch_queue = fetch_queue
        self.push_queue = push_queue
        self.running = running

    def parse(self):
        element = self.fetch_queue.get()

        if 'auth' in element['_source']['system']:
            self.auth_alerts(element)

    def parse_static(self):
        while self.fetch_queue.qsize() > 0:
            self.parse()

    def parse_update(self):
        while self.running:
            if self.fetch_queue.qsize() > 0:
                self.parse()

    def auth_alerts(self, element):
        if 'message' in element['_source']['system']['auth']:
            message = element['_source']['system']['auth']['message']

            if 'ssh' in message:
                title = 'Root activity detected'
                self.push_queue.put((element, title))

        if 'sudo' in element['_source']['system']['auth']:
            title = 'User %s sudoed' % element['_source']['system']['auth']['user']
            self.push_queue.put((element, title))
