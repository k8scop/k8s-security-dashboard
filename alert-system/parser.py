from re import search as regsearch
from urllib.parse import unquote

from alert import RCEAlert, EnumAlert, IntegrityAlert, SecretsAlert

get_pods = r'^/api/v\d+/pods$'
get_pods_in_namespace = r'^/api/v1/namespaces/[\w\d_-]+/pods$'
describe_pods = r'^/api/v\d+/pods?includeUninitialized=true$'
describe_pod = r'^/api/v\d+/namespaces/[\w\d_-]+/pods/[\w\d_-]+$'
secrets = r'/api/v\d+/namespaces/[\w\d_-]+/secrets/[\w\d_-]+$'
command_exec = r'^/api/v\d+/namespaces/[\w\d_-]+/pods/[\w\d_-]+/exec?'


class Parser:
    def __init__(self, fetch_queue, push_queue_dict, tracker):
        self.fetch_queue = fetch_queue
        self.push_queue_dict = push_queue_dict
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

        alert = self.__create_alert(element)

        if alert:
            self.push_queue_dict[alert.a_type].put(alert)

    def __create_alert(self, element):
        source = element['_source']
        index = element['_id']

        timestamp = source['@timestamp']
        user = source['user']
        uri = source['uri']

        description = {}
        description['user'] = user

        alert = None

        if regsearch(get_pods, uri):
            description['title'] = 'Pod enumeration detected'

            enums = 'get pods --all-namepspaces'

            alert = EnumAlert(timestamp, description,
                              index, 1, timestamp, [enums])
        elif regsearch(get_pods_in_namespace, uri):
            namespace = self.__find_namespace(uri)

            if source['method'] == 'create':
                description['title'] = 'Pod creation detected'
                description['namespace'] = namespace

                alert = IntegrityAlert(timestamp, description,
                                       index, 1, timestamp)
            else:
                description['title'] = 'Pod enumeration detected'

                enums = 'get pods --namespace %s' % self.__find_namespace(uri)

                alert = EnumAlert(timestamp, description,
                                  index, 1, timestamp, [enums])
        elif regsearch(describe_pods, uri):
            description['title'] = 'Pod enumeration detected'

            enums = 'describe pods --all-namespaces'

            alert = EnumAlert(timestamp, description,
                              index, 1, timestamp, [enums])
        elif regsearch(describe_pod, uri):
            description['title'] = 'Pod enumeration detected'

            enums = 'describe %s --namespace %s' % (
                self.__find_pod(uri), self.__find_namespace(uri))

            alert = EnumAlert(timestamp, description,
                              index, 1, timestamp, [enums])
        elif regsearch(secrets, uri):
            description['title'] = 'Attempt to retrieve secrets'
            description['namespace'] = self.__find_namespace(uri)
            description['pod'] = self.__find_secrets_pod(uri)

            response = source['response']

            alert = SecretsAlert(timestamp, description, index, 1, timestamp,
                                 [response])
        elif regsearch(command_exec, uri):
            description['user'] = user
            description['namespace'] = self.__find_namespace(uri)
            description['pod'] = self.__find_pod(uri)
            description['container'] = self.__find_container(uri)

            command = self.__parse_command(uri)

            if 'mnt' in command:
                description['title'] = 'Attempt to mount filesystem'
            else:
                description['title'] = 'Command execution detected'

            alert = RCEAlert(timestamp, description,
                             index, 1, timestamp, [command])

        return alert

    def __find_namespace(self, uri):
        hit = regsearch(r'namespaces/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return -1

    def __find_pod(self, uri):
        hit = regsearch(r'pods/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return -1

    def __find_secrets_pod(self, uri):
        hit = regsearch(r'secrets/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return -1

    def __find_container(self, uri):
        hit = regsearch(r'container=[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('=')
            return tokens[1]
        else:
            return -1

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
