Filternaut
==========

Filternaut generates arbitrarily complex Q-objects from simple data. It fits
nicely into situations where users provide data which you want to filter your
queryset with.

Filternaut is indirectly a collection of fields, but it differs from Django
forms in that you specify the logical relationships between fields, as well
their names and types.

Filternaut is similar to Django Filters, but does not provide any machinery for
rendering a user interface and does not inspect your models to autogenerate
filters. However, Django Filters chains many calls to ``.filter()`` which can
lead to unexpected join behaviour. Filternaut does not suffer this problem, and
can better model the relationships between filters.

Quickstart
----------

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
------------

.. code-block:: console

    $ pip install django-filternaut

Filternaut is compatible with:

- Python 2.7 and 3.4
- Django 1.2 through to 1.8 alpha 1
- Django REST Framework 2.4 and 3.0 (optional)

Examples
--------

1. Using a simple filter

   Here Filternaut pulls a username from ``user_data`` and filters a User
   queryset with it. Filternaut is overkill for such a simple job, but hey,
   it's the first example.

  .. doctest::

    >>> from filternaut import Filter
    >>>
    >>> user_data = {'username': 'nostromo'}
    >>> filters = Filter('username')
    >>> filters.parse(user_data)
    >>> User.objects.filter(filters.Q).query.__str__()
    u'SELECT "auth_user"."id", ... WHERE "auth_user"."username" = nostromo'

2. Combining several filters

   Now Filternaut is used to filter Users with either an email, a username, or
   a (first name, last name) pair.

  .. doctest::

    >>> from filternaut import Filter
    >>>
    >>> user_data = {'email': 'user3@example.org', 'username': 'user3'}
    >>> filters = (
    ...     Filter('email') |
    ...     Filter('username') |
    ...     (Filter('first_name') & Filter('last_name')))
    >>> filters.parse(user_data)
    >>> User.objects.filter(filters.Q).query.__str__()
    u'SELECT "auth_user"."id", ... WHERE ("auth_user"."email" = user3@example.org OR "auth_user"."username" = user3)'

    >>> # the same filters behave differently with different input data.
    >>> user_data = {'first_name': 'Art', 'last_name': 'Vandelay'}
    >>> filters.parse(user_data)
    >>> User.objects.filter(filters.Q).query.__str__()
    u'SELECT "auth_user"."id", ... WHERE ("auth_user"."first_name" = Art AND "auth_user"."last_name" = Vandelay)'

3. Mapping a different public API onto your schema.

  In this example, the source data's ``last_transaction`` value filters on the
  value of a field across a distant relationship. This allows you to simplify
  or hide the details of your schema, and to later change them without changing
  the names you expose.

  .. doctest::

    >>> from filternaut import Filter
    >>> filters = Filter(
    ...     source='last_payment',
    ...     dest='order__transaction__created_date',
    ...     lookups=['lt', 'lte', 'gt', 'gte'])

4. Requiring certain filters

  If it's mandatory to provide certain filtering values, you can use the
  ``required`` argument. By default, filters are not required.

   .. doctest::

    >>> from filternaut import Filter
    >>> filters = Filter('username', required=True)
    >>> filters.parse({})  # no 'username'
    >>> filters.errors
    {'username': u'This field is required'}

  Filternaut does not currently support conditional requirements. That is,
  there is no way to say "If filter A has a value, filter B must also have a
  value". For more complex cases where this is necessary, it is recommended to
  construct several separate sets of filters, wrap them in the necessary logic,
  and combine their Q objects if the right conditions are met.

5. Using Lookups

   It's common to k

6. Using Filters with Fields

   Filters can be combined with ``django.forms.fields.Field`` instances to
   validate and transform source data.

   .. doctest::

     >>> from django.forms import DateTimeField
     >>> from filternaut.filters import FieldFilter
     >>>
     >>> filters = FieldFilter('signup_date', field=DateTimeField())
     >>> filters.parse({'signup_date': 'potato'})
     >>> filters.errors
     {'signup_date': [u'Enter a valid date/time.']}

  Instead of making you provide your own ``field`` argument, Filternaut pairs
  most of Django's Field subclasses with Filters. They can be used like so:

  .. doctest::

    >>> from filternaut.filters import ChoiceFilter
    >>>
    >>> difficulties = [(4, 'Torment I'), (5, 'Torment II')]
    >>> filters = ChoiceFilter('difficulty', choices=difficulties)
    >>> filters.field
    <django.forms.fields.ChoiceField ...>

    >>> filters.parse({'difficulty': 'foo'})
    >>> filters.errors
    {'difficulty': [u'Select a valid choice. foo is not ...']}

  Filters wrapping fields which require special arguments to instantiate (e.g.
  ``choices`` in the example above) also require those arguments. That is,
  because ChoiceField needs ``choices``, so does ChoiceFilter.

  The full list of field-specific filter classes is:

  - BooleanFilter
  - CharFilter
  - ChoiceFilter
  - ComboFilter
  - DateFilter
  - DateTimeFilter
  - DecimalFilter
  - EmailFilter
  - FilePathFilter
  - FloatFilter
  - GenericIPAddressFilter (Django 1.4 and greater)
  - IPAddressFilter
  - ImageFilter
  - FieldFilter
  - IntegerFilter
  - MultiValueFilter
  - MultipleChoiceFilter
  - NullBooleanFilter
  - RegexFilter
  - SlugFilter
  - SplitDateTimeFilter
  - TimeFilter
  - TypedChoiceFilter
  - TypedMultipleChoiceFilter (Django 1.4 and greater)
  - URLFilter


Django REST Framework
---------------------

Using Filternaut with Django REST Framework is no more complicated than normal;
simply connect, for example, a request's query parameters to a view's queryset:

.. doctest::

    >>> from filternaut.filters import CharFilter, EmailFilter
    >>> from rest_framework import generics
    >>>
    >>> class UserListView(generics.ListAPIView):
    ...     model = User
    ...
    ...     def filter_queryset(self, queryset):
    ...         filters = CharFilter('username') | EmailFilter('email')
    ...         filters.parse(self.request.QUERY_PARAMS)
    ...         queryset = super(UserListView, self).filter_queryset(queryset)
    ...         return queryset.filter(filters.Q)

Filternaut also provides a Django REST Framework-compatible filter backend:

.. doctest::

    >>> from filternaut.drf import FilternautBackend
    >>> from filternaut.filters import CharFilter, EmailFilter
    >>> from rest_framework import views

    >>> class MyView(views.APIView):
    ...     filter_backends = (FilternautBackend, )
    ...     filternaut_filters = CharFilter('username') | EmailFilter('email')

The attribute ``filternaut_filters`` should contain one or more Filter
instances. Instead of an attribute, it can also be a callable which returns a
list of filters, allowing the filters to vary on the current request:

.. doctest::

    >>> from rest_framework import views
    >>>
    >>> class MyView(views.APIView):
    ...     filter_backends = (FilternautBackend, )
    ...
    ...     def filternaut_filters(self, request):
    ...         choices = ['guest', 'developer']
    ...         if request.user.is_staff:
    ...             choices.append('manager')
    ...         return ChoiceFilter('account_type', choices=enumerate(choices))

Tests
-----

First, install the extra dependencies:

.. code-block:: console

  $ pip install requirements/maintainer.txt

You can run the test suite in a specific environment via tox. In this example,
against Python 2.7 and Django 1.4.  (Hint: try ``tox -l`` for a full list).

.. code-block:: console

  $ tox -e py27-dj14

The full suite can be run by providing no arguments to tox. If it's the first
time, consider opening a beer.

.. code-block:: console

  $ tox

Finally, you can run the test suite without tox if you prefer:

.. code-block:: console

  $ nosetests
