from urllib.parse import unquote
from alert import Alert


class Parser:
    def __init__(self, fetch_queue, push_queue, tracker):
        self.fetch_queue = fetch_queue
        self.push_queue = push_queue
        self.tracker = tracker

    def parse(self):
        while True:
            if self.fetch_queue.qsize() > 0:
                self.__parse_log()
            else:
                if self.tracker.tracking:
                    if self.tracker.fetcher_done:
                        self.tracker.parser_done = True
                        print('[+] Parser is done')
                        return

    def __parse_log(self):
        element = self.fetch_queue.get()

        self.__find_alerts(element)

    def __find_alerts(self, element):
        source = element['_source']

        timestamp = source['@timestamp']
        index = element['_id']

        if 'uri' in source:
            uri = source['uri']
            if 'exec' in uri:
                tag = source['tag'].replace('-audit', '')
                title = 'Command execution by %s on %s' % (source['user'], tag)

                specs = self.__parse_command(uri)

                alert = Alert(timestamp, title, index, 1, timestamp, specs)

                self.push_queue.put(alert)

    def __parse_command(self, uri):
        tokens = uri.split('command=')
        more_tokens = tokens[1].split('&')
        command = more_tokens[0]

        return unquote(command).replace('+', ' ')
