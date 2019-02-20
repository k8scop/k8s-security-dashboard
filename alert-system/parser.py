from re import search as regsearch
from urllib.parse import unquote

from alert import RCEAlert, EnumAlert


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
        index = element['_id']

        timestamp = source['@timestamp']
        user = source['user']
        uri = source['uri']

        if 'pods' in uri:
            self.__enum_alerts(index, timestamp, user, uri)

        if 'exec?' in uri:
            self.__rce_alerts(index, timestamp, user, uri)

    def __find_namespace(self, uri):
        hit = regsearch('namespaces/[A-Za-z0-9_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return -1

    def __find_pod(self, uri):
        hit = regsearch('pods/[A-Za-z0-9_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return -1

    def __find_container(self, uri):
        hit = regsearch('container=[A-Za-z0-9_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('=')
            return tokens[1]
        else:
            return -1

    def __enum_alerts(self, index, timestamp, user, uri):
        description = {}
        description['title'] = 'Pod enumeration detected'
        description['user'] = user

        regex = '/api/v[0-9]+/pods'

        if regsearch('%s%s' % (regex, '?'), uri):
            kubectl_command = 'describe pods --all-namespaces'

            alert = EnumAlert(timestamp, description, index, 1, timestamp,
                              kubectl_command)

        elif regsearch(regex, uri):
            kubectl_command = 'get all-namespaces'

            alert = EnumAlert(timestamp, description, index, 1, timestamp,
                              kubectl_command)

        else:
            namespace = self.__find_namespace(uri)
            pods = self.__find_pod(uri)

            if pods is -1:
                kubectl_command = 'get pods --namespace %s' % namespace
            else:
                kubectl_command = 'describe [pods] %s --namespace %s' % (pods, namespace)

        alert = EnumAlert(timestamp, description, index, 1, timestamp,
                          kubectl_command)

        self.push_queue.put(alert)

    def __rce_alerts(self, index, timestamp, user, uri):
        description = {}

        description['title'] = 'Command execution detected'
        description['user'] = user
        description['namespace'] = self.__find_namespace(uri)
        description['pod'] = self.__find_pod(uri)
        description['container'] = self.__find_container(uri)

        command = self.__parse_command(uri)

        alert = RCEAlert(timestamp, description, index, 1, timestamp, command)

        self.push_queue.put(alert)

    def __parse_command(self, uri):
        command = ''

        from_index = uri.find('exec?')
        to_index = uri.find('&container')

        if from_index > -1 and to_index > -1:
            substring = uri[from_index:to_index]
            tokens = substring.split('command=')

            for i in range(1, len(tokens)):
                token = tokens[i]
                command = '%s %s' % (command, token)

        return unquote(command).replace('&', '').replace('+', ' ')
