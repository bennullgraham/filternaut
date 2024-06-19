from django.core.exceptions import ValidationError
import pytest
from contextlib import contextmanager
from django.db.models import Q

from filternaut import Filter
from filternaut.exceptions import InvalidData


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


def assert_parsed_ok(parse_result):
    """
    Check a Q-object is returned from parsing.

    Because the test for parsing OK is implicit -- no exception was raised --
    it makes the tests harder to understand. This function is here to avoid
    that problem, because it makes the expectation explicit. It doesn't
    actually need to *do* anything, but while we're here, we check if the
    return is a Q.

    If parsing is not OK, an InvalidData or other exception will bubble up.
    """
    assert isinstance(parse_result, Q)


@contextmanager
def assert_parse_invalid():
    with pytest.raises(InvalidData) as ex_info:
        yield ex_info.value


class NopeFilter(Filter):
    """
    A filter which always raises a validation error.
    """

    def clean(self, value):
        raise ValidationError(["Nope"])
