from datetime import datetime


class Alert:
    def __init__(self, a_type, timestamp, description, index, user):
        self.a_type = a_type
        self.timestamp = timestamp
        self.description = description
        self.index = index
        self.user = user

    def get_timestamp_in_dt(self):
        timestamp = self.timestamp.split('.')[0]
        return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')

    def to_dict(self):
        data = {
            'a_type': self.a_type,
            'timestamp': self.timestamp,
            'description': self.description,
            'index': self.index,
            'user': self.user
        }

        return data


class EnumAlert(Alert):
    def __init__(self, timestamp, description, index, user,
                 namespace, pod, kubectl):
        super().__init__('Enum', timestamp, description, index, user)

        self.namespace = namespace
        self.pod = pod
        self.kubectl = kubectl

    def to_dict(self):
        data = super().to_dict()

        data['namespace'] = self.namespace
        data['pod'] = self.pod
        data['kubectl'] = self.kubectl

        return data


class IntegrityAlert(Alert):
    def __init__(self, timestamp, description, index, user,
                 namespace):
        super().__init__('Integrity', timestamp, description, index, user)

        self.namespace = namespace

    def to_dict(self):
        data = super().to_dict()

        data['namespace'] = self.namespace

        return data


class SecretsAlert(Alert):
    def __init__(self, timestamp, description, index, user,
                 namespace, pod, response):
        super().__init__('Secrets', timestamp, description, index, user)

        self.namespace = namespace
        self.pod = pod
        self.response = response

    def to_dict(self):
        data = super().to_dict()

        data['namespace'] = self.namespace
        data['pod'] = self.pod
        data['response'] = self.response

        return data


class RCEAlert(Alert):
    def __init__(self, timestamp, description, index, user,
                 namespace, pod, container, command):
        super().__init__('RCE', timestamp, description, index, user)

        self.namespace = namespace
        self.pod = pod
        self.container = container
        self.command = command

    def to_dict(self):
        data = super().to_dict()

        data['namespace'] = self.namespace
        data['pod'] = self.pod
        data['container'] = self.container
        data['command'] = self.command

        return data
