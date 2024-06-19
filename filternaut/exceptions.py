class FilternautException(Exception):
    pass


class InvalidData(FilternautException):
    errors = None

    def __init__(self, errors):
        super().__init__()
        self.errors = errors
