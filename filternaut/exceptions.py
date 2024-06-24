from collections import defaultdict
from pprint import pformat


class FilternautException(Exception):
    pass


class InvalidData(FilternautException):
    errors = None

    def __init__(self, errors):
        if isinstance(errors, defaultdict):
            errors = dict(errors)
        super().__init__(pformat(errors))
        self.errors = errors
