# timestamp: the timestamp of the alert
# title: the title of the alert
# indices: the list of entry indices related to the alert
# count: the number of times the alert was triggered
# last_seen: the timestamp of the last time the alert was triggered
# query: the search query, None if first time alert is triggered


class Alert:

    def __init__(self, timestamp, title, index, count, last_seen, specs):
        self.timestamp = timestamp
        self.title = title
        self.indices = [index]
        self.count = count
        self.last_seen = last_seen
        self.specs = [specs]

    def merge(self, new_alert):
        self.__update_indices(new_alert.indices)
        self.__update_count()
        self.__update_last_seen(new_alert.timestamp)
        self.__update_specs(new_alert.specs)

    def to_dict(self):
        data = {
            'timestamp': self.timestamp,
            'title': self.title,
            'indices': self.indices,
            'count': self.count,
            'last_seen': self.last_seen,
            'specs': self.specs
        }

        return data

    def __update_indices(self, new_index):
        self.indices.extend(new_index)

    def __update_count(self):
        self.count += 1

    def __update_last_seen(self, new_last_seen):
        self.last_seen = new_last_seen

    def __update_specs(self, new_spec):
        self.specs.extend(new_spec)

    @staticmethod
    def from_dict(jason):
        return Alert(jason['timestamp'], jason['title'], jason['indices'],
                     jason['count'], jason['last_seen'], jason['specs'])
