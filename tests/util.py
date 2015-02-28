from django.core.exceptions import ValidationError
from django.db.models import Q

from filternaut import Filter


def flatten_qobj(qobj):
    """
    Flatten a Q object into a series of field, value pairs.
    """
    for child in qobj.children:
        if isinstance(child, Q):
            for grandchild in flatten_qobj(child):
                yield grandchild
        else:
            yield child


class NopeFilter(Filter):
    """
    A filter which always raises a validation error.
    """
    def clean(self, value):
        raise ValidationError(["Nope"])
