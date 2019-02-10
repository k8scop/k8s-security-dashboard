class Parser:
    def __init__(self, fetch_queue, push_queue, running):
        self.fetch_queue = fetch_queue
        self.push_queue = push_queue
        self.running = running

    def parse(self):
        while self.running:
            if self.fetch_queue.qsize() > 0:
                element = self.fetch_queue.get()

                # print(json.dumps(element['_source']['system'], indent=4,
                #       sort_keys=False))

                if 'auth' in element['_source']['system']:
                    self.auth_alerts(element)

    def auth_alerts(self, element):
        if 'message' in element['_source']['system']['auth']:
            message = element['_source']['system']['auth']['message']

            if 'root' in message:
                title = 'Root activity detected'
                self.push_queue.put((element, title))

        if 'sudo' in element['_source']['system']['auth']:
            title = 'Someone sudoed!'
            self.push_queue.put((element, title))
