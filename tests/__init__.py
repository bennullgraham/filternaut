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
