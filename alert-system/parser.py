from re import search as regsearch
from urllib.parse import unquote

from alert import EnumAlert, TamperAlert, SecretsAlert, ExecAlert

pods_limit = r'^/api/v\d+/pods(\?limit=\d+)?$'
namespaces_n_pods = r'^/api/v\d+/namespaces/[\w\d_-]+/pods(\?limit=\d+)?$'
pods_include = r'^/api/v\d+/pods\?includeUninitialized=true$'
namespace_n_pods_include = r'^/api/v\d+/namespaces/[\w\d_-]+/pods\?includeUninitialized=true$'
namespaces_n_pods_p = r'^/api/v\d+/namespaces/[\w\d_-]+/pods/[\w\d_-]+$'
secrets_limit = r'^/api/v\d+/secrets(\?limit=\d)?$'
namespaces_n_secrets_limit = r'^/api/v\d+/namespaces/[\w\d_-]+/secrets(\?limit=\d+)?$'
namespaces_n_secrets_p = r'/^api/v\d+/namespaces/[\w\d_-]+/secrets/[\w\d_-]+$'
namespaces_n_pods_p_exec = r'^/api/v\d+/namespaces/[\w\d_-]+/pods/[\w\d_-]+/exec?'


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
        uri = source['requestURI']
        method = source['verb']

        user = ''
        if 'username' in source['user']:
            user = source['user']['username']

        response = 0
        if 'responseStatus' in source:
            response = source['responseStatus']['code']

        pod = 'N/A'
        if 'objectRef' in source:
            if 'name' in source['objectRef']:
                pod = source['objectRef']['name']

        alert = None

        if regsearch(pods_limit, uri):
            alert = self.__find_pods_limit(timestamp, index, user)
        elif regsearch(namespaces_n_pods, uri):
            alert = self.__find_namespace_n_pods(timestamp, index, user,
                                                 uri, method, response, pod)
        elif regsearch(pods_include, uri):
            alert = self.__find_pods_include(timestamp, index, user)
        elif regsearch(namespace_n_pods_include, uri):
            alert = self.__find_namespace_n_pods_include(timestamp, index,
                                                         user, uri)
        elif regsearch(namespaces_n_pods_p, uri):
            alert = self.__find_namespaces_n_pods_p(timestamp, index, user,
                                                    uri, method, response)
        elif regsearch(secrets_limit, uri):
            alert = self.__find_secrets_limit(timestamp, index, user, response)
        elif regsearch(namespaces_n_secrets_limit, uri):
            alert = self.__find_namespaces_n_secrets_limit(timestamp, index,
                                                           user, uri, response)
        elif regsearch(namespaces_n_secrets_p, uri):
            alert = self.__find_namespaces_n_secrets_p(timestamp, index, user,
                                                       uri, response)
        elif regsearch(namespaces_n_pods_p_exec, uri):
            alert = self.__find_namespaces_n_pods_p_exec(timestamp, index,
                                                         user, uri)

        if alert:
            self.push_queue_dict[alert.a_type].put(alert)

    def __find_pods_limit(self, timestamp, index, user):
        description = 'Pod enumeration in all namespaces'

        kubectl = 'get pods --all-namespaces'

        return EnumAlert(timestamp, description, index, user,
                         'N/A', 'N/A', kubectl)

    def __find_namespace_n_pods(self, timestamp, index, user,
                                uri, method, response, pod):
        namespace = self.__find_namespace(uri)

        if method == 'list':
            if response == 200:
                description = f'Pod enumeration in namespace {namespace}'

                kubectl = f'get pods --namespace {namespace}'

                return EnumAlert(timestamp, description, index, user,
                                 namespace, 'N/A', kubectl)
        elif method == 'create':
            if response == 201:
                description = f'{user} created pod in {namespace}'

                return TamperAlert(timestamp, description, index, user,
                                   namespace, pod)

    def __find_pods_include(self, timestamp, index, user):
        description = 'Pod information request in all namespaces'
        kubectl = 'describe pods --all-namespaces'

        return EnumAlert(timestamp, description, index, user,
                         'N/A', 'N/A', kubectl)

    def __find_namespace_n_pods_include(self, timestamp, index, user, uri):
        namespace = self.__find_namespace(uri)
        description = f'Pod information request in namespace {namespace}'

        kubectl = f'describe pods --namespace {namespace}'

        return EnumAlert(timestamp, description, index, user,
                         namespace, 'N/A', kubectl)

    def __find_namespaces_n_pods_p(self, timestamp, index, user,
                                   uri, method, response):
        namespace = self.__find_namespace(uri)
        pod = self.__find_pod(uri)

        if method == 'delete':
            if response == 200:
                namespace = self.__find_namespace(uri)
                pod = self.__find_pod(uri)

                description = f'{user} deleted {pod} in {namespace}'

                return TamperAlert(timestamp, description, index, user,
                                   namespace, pod)
        else:
            description = f'Information request on {pod} in {namespace}'

            kubectl = f'describe {pod} --namespace {namespace}'

            return EnumAlert(timestamp, description, index, user,
                             namespace, pod, kubectl)

    def __find_secrets_limit(self, timestamp, index, user,
                             response):
        if response == 200:
            description = 'Attempt to get all secrets'
            return SecretsAlert(timestamp, description, index, user,
                                'N/A', 'N/A', response)

    def __find_namespaces_n_secrets_limit(self, timestamp, index, user,
                                          uri, response):
        if response == 200:
            namespace = self.__find_namespace(uri)

            description = f'Attempt to get all secrets from {namespace}'

            return SecretsAlert(timestamp, description, index, user,
                                namespace, 'N/A', response)

    def __find_namespaces_n_secrets_p(self, timestamp, index, user,
                                      uri, response):
        if response == 200:
            namespace = self.__find_namespace(uri)
            pod = self.__find_secrets_pod(uri)

            description = f'Attempt to get secrets from {pod} in {namespace}'

            return SecretsAlert(timestamp, description, index, user,
                                namespace, pod, response)

    def __find_namespaces_n_pods_p_exec(self, timestamp, index, user,
                                        uri):
        description = 'Command execution detected'

        namespace = self.__find_namespace(uri)
        pod = self.__find_pod(uri)
        container = self.__find_container(uri)

        command = self.__parse_command(uri)

        return ExecAlert(timestamp, description, index, user,
                         namespace, pod, container, command)

    def __find_namespace(self, uri):
        hit = regsearch(r'namespaces/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return 'N/A'

    def __find_pod(self, uri):
        hit = regsearch(r'pods/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return 'N/A'

    def __find_secrets_pod(self, uri):
        hit = regsearch(r'secrets/[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('/')
            return tokens[1]
        else:
            return 'N/A'

    def __find_container(self, uri):
        hit = regsearch(r'container=[\w\d_-]+', uri)

        if hit:
            substring = hit.group(0)
            tokens = substring.split('=')
            return tokens[1]
        else:
            return 'N/A'

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
