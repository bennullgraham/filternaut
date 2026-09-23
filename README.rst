Filternaut
**********

Filternaut is a simple library which generates arbitrarily complex Django
Q-objects from simple data. It fits nicely into situations where users provide
data which you want to filter a queryset with. For example, if you have an API
listing and want to let the requester filter that listing with query params,
Filternaut is the ticket.

Using Filternaut, you put together filters of different types — e.g. a date
filter and an email filter — and say what their logical relationships are.

Quickstart
==========

.. code-block:: python

    # first define how you will parse the incoming filters choices.
    filters = (
        DateTimeFilter('created_date', lookups=['lt', 'gt']) &
        CharFilter('username', lookups=['icontains'])
    )

    # then use this to parse anything dict-like. This returns a Django
    # Q-object for use with the ORM's .filter().
    try:
        query = filters.parse(request.GET)
        return queryset.filter(query)
    except filternaut.InvalidData as ex:
        raise HttpResponseBadRequest(ex.errors)


Installation
============

.. code-block:: console

    $ pip install django-filternaut

Filternaut is compatible with:

- Python 3.10+
- Django 4.2, 5.2 and 6.1
- Django REST Framework (optional), any release supporting your Django version

Development
===========

Filternaut uses `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: console

    $ uv sync
    $ uv run pytest
    $ uv run ruff check

The test suite includes doctests from docs/.

To test against another Python or Django version, as CI does:

.. code-block:: console

    $ uv run --isolated --python 3.10 pytest
    $ uv run --isolated --python 3.12 --with "django~=4.2.0" --with djangorestframework pytest

The isolated flag will leave your .venv untouched.

Documentation
=============

See https://filternaut.readthedocs.org for full documentation.
