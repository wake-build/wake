class NoConfigFoundException(Exception):
    def __init__(self, path):
        self.path = path
        super(NoConfigFoundException, self).__init__(
            "No config found at path: %s" % path
        )
