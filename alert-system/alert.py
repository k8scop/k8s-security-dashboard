# timestamp: the timestamp of the alert
# title: the title of the alert
# indices: the list of entry indices related to the alert
# count: the number of times the alert was triggered
# last_seen: the timestamp of the last time the alert was triggered
# query: the search query, None if first time alert is triggered


class Alert:

    def __init__(self, timestamp, title, index, count, last_seen, query=''):
        self.timestamp = timestamp
        self.title = title
        self.indices = [index]
        self.count = count
        self.last_seen = last_seen

        if query == '':
            self.query = '_id:%s' % index
        else:
            self.query = query

    def update(self, new_index, new_last_seen):
        self.__update_indices(new_index)
        self.__update_count()
        self.__update_last_seen(new_last_seen)
        self.__update_query(new_index)

    def to_dict(self):
        data = {
            'timestamp': self.timestamp,
            'title': self.title,
            'indices': self.indices,
            'count': self.count,
            'last_seen': self.last_seen,
            'query': self.query
        }

        return data

    def __update_indices(self, new_index):
        self.indices.append(new_index)

    def __update_count(self):
        self.count += 1

    def __update_last_seen(self, new_last_seen):
        self.last_seen = new_last_seen

    def __update_query(self, new_index):
        self.query += ' OR _id:%s' % new_index

    @staticmethod
    def from_dict(jason):
        return Alert(jason['timestamp'], jason['title'], jason['indices'],
                     jason['count'], jason['last_seen'], jason['query'])
