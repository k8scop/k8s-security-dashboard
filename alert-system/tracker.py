class Tracker:
    def __init__(self, tracking, fetcher_done, parser_done, pusher_done):
        self.tracking = tracking
        self.fetcher_done = fetcher_done
        self.parser_done = parser_done
        self.pusher_done = pusher_done
