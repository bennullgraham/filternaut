Filternaut
**********

Filternaut is a simple library which generates arbitrarily complex Django
Q-objects from simple data. It fits nicely into situations where users provide
data which you want to filter a queryset with.

Filternaut is indirectly a collection of fields, but it differs from Django
forms in that you specify the logical relationships between fields, as well
their names and types.

Filternaut is similar to Django Filters, but does not provide any machinery for
rendering a user interface and does not inspect your models to autogenerate
filters. However, Django Filters chains many calls to ``.filter()`` which means
OR-like behaviour with more than one join. Filternaut supports either
behaviour.

Quickstart
==========

.. code-block:: python

    # filters are combined using logical operators
    filters = (
        DateTimeFilter('created_date', lookups=['lt', 'gt']) &
        CharFilter('username', lookups=['icontains']))

    # they can read their values from anything dict-like
    filters.parse(request.GET)

    # and have a form-like 'validity pattern'.
    if filters.valid:
        queryset = queryset.filter(filters.Q)
    else:
        raise HttpResponseBadRequest(filters.errors)


Installation
============

.. code-block:: console

    $ pip install django-filternaut

Filternaut is compatible with:

- Python 3
- Django 2.2 and 3.0
- Django REST Framework 3.11 (optional)

Python 2.7 support is still in the codebase but no longer tested. You are
welcome to try your luck.

Documentation
=============

.. toctree::
   :hidden:

   self

.. toctree::
   :maxdepth: 2

   examples
   api
   tests


Changelog
=========

0.0.11
------

- Support "in" filters where a candidate value is null. Set
  `none_to_isnull=True` when creating a Filter to take advantage of this.
- Move test suite up to Django 2.2 and 3.0; DRF 3.11; Python 3.5+. Filternaut
  will still run on Python 2.7 but it is no longer official or tested.

0.0.10
------

- Fix incorrect project URL in setup.py (thanks Jonathan Barratt!)

0.0.9
-----

- Filters accepting multiple values now correctly clean each value individually

0.0.8
-----

- Official support for DRF 3.4, Python 3.5 and Django 1.10
- Fix issue where exactly six 1.9 was a dependency

0.0.7
-----

- Fix BooleanFilter rejecting falsish values
- Add support for Django 1.9
- Remove support for Django REST Framework 2.x and 3.1; add support for 3.3
