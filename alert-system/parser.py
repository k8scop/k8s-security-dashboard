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
                        print('[x] Parser is done')
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

        # For Testing Purposes
        if 'system' in source:
            if 'syslog' in source['system']:
                if 'message' in source['system']['syslog']:
                    if 'DHCPREQUEST' in source['system']['syslog']['message']:
                        title = 'DHCP stoof'
                        specs = source['system']['syslog']['message']
                        alert = Alert(timestamp, title, index, 1, timestamp, 
                                      specs)
                        self.push_queue.put(alert)
            if 'auth' in source['system']:
                if 'program' in source['system']['auth'] and 'message' in source['system']['auth']:
                    if source['system']['auth']['program'] == 'sudo':
                        if 'opened' in source['system']['auth']['message']:
                            title = 'Someone sudoed!'
                            specs = source['system']['auth']['message']
                            alert = Alert(timestamp, title, index, 1,
                                          timestamp, specs)
                            self.push_queue.put(alert)

    def __parse_command(self, uri):
        tokens = uri.split('command=')

        if len(tokens) > 1:
            more_tokens = tokens[1].split('&')
            command = more_tokens[0]

            return unquote(command).replace('+', ' ')
        else:
            return ''
