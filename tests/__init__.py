# -*- coding: utf8 -*-

from __future__ import unicode_literals, print_function, absolute_import
from django.conf import settings


# set up just enough of Django for testing
settings.configure(
    MIDDLEWARE_CLASSES=(),
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes', ),
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'}})


# sory pep8, this must come after settings config
import django  # noqa
try:
    django.setup()
except AttributeError:
    pass

# and this one too.
from django.db import connection  # noqa
connection.creation.create_test_db()


def flatten_qobj(qobj):
    """
    Flatten a Q object into a series of field, value pairs.
    """
    from django.db.models import Q
    for child in qobj.children:
        if isinstance(child, Q):
            for grandchild in flatten_qobj(child):
                yield grandchild
        else:
            yield child
