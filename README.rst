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

- Python 3
- Django 4.2 and 5.0
- Django REST Framework 3.15 (optional)

Documentation
=============

See https://filternaut.readthedocs.org for full documentation.
