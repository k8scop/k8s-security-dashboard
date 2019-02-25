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
        user = source['user']['username']
        uri = source['requestURI']

        alert = None

        if regsearch(get_pods, uri):
            description = 'Pod enumeration on all namespaces'

            kubectl = 'get pods --all-namepspaces'

            alert = EnumAlert(timestamp, description, index, user,
                              'N/A', 'N/A', kubectl)
        elif regsearch(get_pods_in_namespace, uri):
            namespace = self.__find_namespace(uri)

            if source['verb'] == 'create':
                description = 'Pod creation on %s' % namespace

                alert = IntegrityAlert(timestamp, description, index, user,
                                       namespace)
            else:
                description = 'Pod enumeration on %s' % namespace

                kubectl = 'get pods --namespace %s' % namespace

                alert = EnumAlert(timestamp, description, index, user,
                                  namespace, 'N/A', kubectl)
        elif regsearch(describe_pods, uri):
            description = 'Describe request on all pods'

            kubectl = 'describe pods --all-namespaces'

            alert = EnumAlert(timestamp, description, index, user, 
                              'N/A', 'N/A', kubectl)
        elif regsearch(describe_pod, uri):
            namespace = self.__find_namespace(uri)
            pod = self.__find_pod(uri)

            description = 'Describe request on pod %s in %s' % (pod, namespace)

            kubectl = 'describe %s --namespace %s' % (pod, namespace)

            alert = EnumAlert(timestamp, description, index, user,
                              namespace, pod, kubectl)
        elif regsearch(secrets, uri):
            description = 'Attempt to retrieve secrets'

            namespace = self.__find_namespace(uri)
            pod = self.__find_secrets_pod(uri)

            if 'responseStatus' in source:
                response = source['responseStatus']['code']

                alert = SecretsAlert(timestamp, description, index, user,
                                     namespace, pod, response)
        elif regsearch(command_exec, uri):
            namespace = self.__find_namespace(uri)
            pod = self.__find_pod(uri)
            container = self.__find_container(uri)

            command = self.__parse_command(uri)

            if 'mnt' in command:
                description = 'Attempt to mount filesystem'
            else:
                description = 'Command execution detected'

            alert = RCEAlert(timestamp, description, index, user,
                             namespace, pod, container, command)

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
