Usage
=====

Using a simple filter
---------------------

Here Filternaut pulls a username from ``user_data`` and filters a User queryset
with it. ``user_data`` could be filter config provided from anywhere it makes
sense, but one place it definitely makes sense is from the query parameters of
a request. So if you prefer, read ``user_data`` as ``request.GET``, or
``request.query_params`` if you're using Django REST Framework.

Filternaut is overkill for this simple job, but hey, it's the first example.

.. testcode::

   from filternaut import Filter

   user_data = {'username': 'nostromo'}
   filters = Filter('username')
   query = filters.parse(user_data)
   qs = User.objects.filter(query)
   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."username" = nostromo

I agree, it's pretty unlikely you want to regularly print out the SQL of your
queryset like I do in these examples. I'm doing this because, well it *is* nice
to see how the filters are applied in the database, but so I can doctest the
output.

Combining several filters
-------------------------

You probably have more than one filter parameter. Here's an example where
filtering is performed on email, username, or a (first, last) name pair. Note
how ``&`` and ``|`` are used to combine the filters; these operators control
whether the conditions in the query will be AND or OR.

.. testcode::

   from filternaut import Filter

   user_data = {'email': 'user3@example.org', 'username': 'user3'}
   filters = (
       Filter('email') |
       Filter('username') |
       (Filter('first_name') & Filter('last_name'))
   )
   query = filters.parse(user_data)
   qs = User.objects.filter(query)
   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE ("auth_user"."email" = user3@example.org OR
          "auth_user"."username" = user3)


The same filters result in different SQL when given different input data:

.. testcode::

   user_data = {'first_name': 'Art', 'last_name': 'Vandelay'}
   query = filters.parse(user_data)
   qs = User.objects.filter(query)
   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE ("auth_user"."first_name" = Art AND
          "auth_user"."last_name" = Vandelay)


Specifying types for filters
----------------------------

So far we've been using a plain ``Filter`` to do the work. This filter can
generate queries, but doesn't do any kind of validation or type conversion. If
you're accepting string values over a request and querying against strings in
the database, hell, you don't need validation or type conversion.

But if you do need those things, you can pick specific filter subclasses to do
the job. In this example, a :py:class:`filternaut.filters.DateTimeFilter`
validates input and converts a basic date input into a full datetime. Under the
hood, DateTimeFilter uses ``django.forms.DateTimeField`` to do this extra work.
In fact, there's a Filternaut filter for every Django form field. You don't
*have* to do it this way; subclass Filter and implement
:py:meth:`~filternaut.Filter.clean` if you like. But anyway, the example:


.. testcode::

   from filternaut.filters import DateTimeFilter

   user_data = {'date_joined': '2020-01-01T00:00Z'}
   filters = DateTimeFilter('date_joined')
   query = filters.parse(user_data)
   qs = User.objects.filter(query)
   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."date_joined" = 2020-01-01 ...

Validating input
----------------

Once you've started :ref:`specifying types for filters <Specifying types for
filters>` you'll start seeing validation errors for invalid input. Specifically
these are an exception raised when calling :py:meth:``parse(data)``. I haven't
included these in the examples so far to keep it focused, and I'll continue
leaving out the exception handling unless it's relevant. 

The exception object has a dictionary of errors suitable for rendering in HTML
or dumping back in an API response. In the example below, the errors are just
printed out.

.. testcode::

   invalid_data = {'date_joined': 'Yesterday afternoon'}
   filters = DateTimeFilter('date_joined')
   filters.parse(invalid_data)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   Traceback (most recent call last): 
   ...
   InvalidData: {'date_joined': ['Enter a valid date/time.']}



Using lookups
-------------

You'll probably want to use comparisons like "greater than" in your filtering.
Filternaut directly exposes the Django lookup scheme, because it's a good
scheme. You just need to list which lookups are allowed for each filter, and
then they can begin appearing in the incoming user data:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - User data
     - Outcome

   * - ``{"date_joined": "..."}``
     - The filter config has only the field name; there's no lookup appended.
       The default lookup of the filter is used. This is ``exact`` although you
       can change it with ``default_lookup``. ``iexact`` often makes sense too.

   * - ``{"date_joined__gt": "..."}``
     - The filter config references a field (``date_joined``) with a lookup
       appended (``gt``, greater-than). If your filter has ``gt`` added to its
       lookup list, a query for join-dates greater than "..." will be produced.


.. testcode::

   from filternaut.filters import Filter

   # these two forms are equivalent
   filters = Filter('date_joined', lookups=['lt', 'lte', 'gt', 'gte'])
   filters = Filter('date_joined', lookups='lt,lte,gt,gte')

   query = filters.parse({'date_joined__gte': '2020-01-01T00:00Z'})
   qs = User.objects.filter(query)
   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."date_joined" >= 2020-01-01 ...

The default lookup is 'exact', which is the equivalent of using no affix when
filtering with Django's ORM. If you do specify other lookups but want to keep
'exact', you must add ``'exact'`` to the list too:

.. code-block:: python

   filters = Filter('last_login', lookups=['year', 'exact'])

If only one lookup is possible then it doesn't need to appear in the incoming
data:

.. testcode::

   from filternaut.filters import Filter

   filters = Filter('email', lookups=['iexact'])

   # these two are equivalent
   filters.parse({'email': 'Sentence@Case.COM'})
   filters.parse({'email__iexact': 'Sentence@Case.COM'})

Filtering with multiple values
------------------------------

If you want to filter with multiple values, for example "give me the users with
IDs 1, 2 or 3", you need to meet a few conditions. These are easy to meet,
because Filternaut works well with query parameters, and query parameters *are*
multi-valued.

* Unsurprisingly, multiple values must be provided! In the example above, those
  would be the IDs 1, 2 and 3.

* The lookup must be multi-valued too; ``__in`` is the obvious one. Notice in
  the code example below how ``__in`` is the only lookup permitted, making it
  the default.

* The incoming data must have a ``getlist`` method. Both Django request's
  ``request.GET`` and Django REST Framework's ``request.query_params`` have
  this. There's detail about overriding this requirement further
  `below <Overriding how multiple values are obtained>`_.


.. testcode::

   from filternaut.filters import Filter
   from django.utils.datastructures import MultiValueDict

   # you would usually use request.GET which is already a multi-value dict
   user_data = MultiValueDict({'groups': ['foo', 'bar']})

   filters = Filter(source='groups', dest='groups__name', lookups=['in'])
   query = filters.parse(user_data)
   qs = User.objects.filter(query)

   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_group"."name" IN (foo, bar)

If the source does not provide a ``getlist`` method, Filternaut will fall back
to using whatever single value is present.

Overriding how multiple values are obtained
-------------------------------------------

If your source does contain multiple values but doesn't have a ``getlist``, you
are still OK. Note that if you're using Django's ``request.GET`` or Django REST
Framework's ``request.query_params`` as your source, it already does have
``getlist`` and you don't need to take any special action.

If your source is a dictionary whose values are list-like already, and the
problem is only that it doesn't have a ``getlist`` method, you can wrap it in
MultiValueDict:

.. testcode::

   from filternaut.filters import Filter
   from django.utils.datastructures import MultiValueDict

   filters = Filter("id")

   # value is listlike, but plain dictionary has no getlist method
   custom_multivalue_data = {"id": [1, 2, 3]}

   # you can wrap in MultiValueDict for compatibility
   wrapped = MultiValueDict(custom_multivalue_data)

   # profit
   filters.parse(wrapped)

If you have a more complicated situation, you can change how the value is
extracted by overriding :py:meth:`filternaut.Filter.get_source_value`. For
example, you might have multiple values delivered at separate numbered keys,
like this:

.. code-block::

   username_0=foo
   username_1=bar
   username_2=quux

The code below will collect those values and produce a query like ``where
username in (foo, bar, quux)``.

.. testcode::

   import itertools
   from filternaut.filters import Filter

   class NumberedKeysFilter(Filter):
       def get_source_value(self, key, data, many=False):
           if not many:
               return super().get_source_value(key, data, many)

           values = []
           numbered_keys = (f"{key}_{n}" for n in itertools.count())
           for numbered_key in numbered_keys:
               if numbered_key in data:
                   values.append(data[numbered_key])
               else:
                   break
           return values

   source = {"username_0": "foo", "username_1": "bar", "username_2": "quux"}
   filter = NumberedKeysFilter("username", lookups="in")
   print(filter.parse_to_dict(source))

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   {'username__in': ['foo', 'bar', 'quux']}



Multiple values when one of the values is null
----------------------------------------------

If you're not a database person, you might be surprised by the following:

.. code-block:: sql

   -- does not find any nodes whose parent_id is null
   select node where parent_id in (1, 2, null)

   -- finds nodes with parent_id=1/2, or with null parent_id.
   select node where parent_id in (1, 2) or parent_id is null

Django honours this, so we can make the same comparison via the ORM:

.. code-block:: python

   # does not find any nodes whose parent_id is null
   Node.objects.filter(parent_id__in=[1, 2, None])

   # finds nodes with parent_id=1/2 or with null parent_id.
   Node.objects.filter(Q(parent_id__in=[1, 2]) | Q(parent_id__isnull=True))

By default, Filternaut behaves the same. Here's the same example as above
through Filternaut:

.. testcode::

   source = MultiValueDict({
       "parent_id__in": [1, 2],
       "parent_id__isnull": [True]  # [...] is required by MultiValueDict
   })
   filters = Filter("parent_id", lookups="in,isnull")
   pprint.pprint(filters.parse_to_dict(source))

.. testoutput::

   {'parent_id__in': [1, 2], 'parent_id__isnull': True}

There are sane reasons for this behaviour originating in correctness, but when
providing user filtering you may prefer clarity over correctness. If so, you
can create a filter with ``none_to_isnull=True``. This will pull the None out
and convert it into an is-null check.

This example achieves the same result as above, without requiring a complicated
construction in the source data:

.. testcode::

   source = MultiValueDict({"parent_id__in": [1, 2, None]})
   filters = filternaut.filters.IntegerFilter("parent_id", lookups="in", none_to_isnull=True)
   pprint.pprint(filters.parse(source))

.. testoutput::

   <Q: (OR: ('parent_id__in', [1, 2]), ('parent_id__isnull', True))>

Be aware that the output of ``parse_to_dict`` does not undergo none-to-isnull
conversion; it only applies to ``parse`` (and that's why this example is the
only one to use a Q-repr directly).

Mapping a different public API onto your schema
-----------------------------------------------

Up until now these examples have given a single first argument to ``Filter()``,
and under the hood it's been used as both the publicly exposed name and the ORM
name of the field. But you can also specify both the "source" (public) and
"dest" (ORM) names. This means you can hide irrelevant complexity in your
schema, or later change that schema without changing the names you expose. In
this example, the source data's ``last_transaction`` value filters on the value
of a field across a distant relationship.

.. testcode::

   from filternaut import Filter
   filters = Filter(
       source='last_payment',
       dest='order__transaction__created_date',
       lookups='lt,lte,gt,gte'
   )

Default values for filters
--------------------------

Filters can be given default values for situations when no value appears in the
source data:

.. testcode::

   from filternaut import Filter
   filters = Filter('is_active', default=True)
   query = filters.parse({})  # no 'is_active'
   qs = User.objects.filter(query)

   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."is_active"

When a default value is used, lookups are ignored. Most combinations of lookups
are mutually exclusive when comparing the same value. For example, filtering by
``score__lt=3`` and ``score__gt=3`` does not make any sense. Instead, a lookup
of ``exact`` is used. ``default_lookup`` may be used to override this.

.. testcode::

   from datetime import datetime, timezone
   from filternaut import Filter
   filters = Filter(
       'last_login',
       lookups='lte,lt,gt,gte',
       default=datetime(2020, 1, 1, tzinfo=timezone.utc),
       default_lookup='lte'
   )
   query = filters.parse({})  # no 'last_login'
   qs = User.objects.filter(query)

   print(qs.query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."last_login" <= 2020-01-01 ...

Required filters
----------------

If it's mandatory to provide certain filtering values, you can use the
``required`` argument. By default, filters are not required.

.. testcode::

   from filternaut import Filter

   filters = Filter('username', required=True)
   filters.parse({})  # no 'username'

.. testoutput::

   Traceback (most recent call last): 
   ...
   InvalidData: {'username': ['This field is required']}

Collectively requiring or ignoring filters
------------------------------------------

:py:class:`filternaut.Optional`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes a field is required only when another is present. For example, you
may require that a value for ``last_name`` is accompanied by a value for
``first_name``, whilst also allowing neither. 

.. testcode::

   from filternaut import Filter, Optional

   filters = Optional(
      Filter('first_name', required=True),
      Filter('middle_name'),
      Filter('last_name', required=True)
   )

   filters.parse({'first_name': 'Nostromo'})

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   Traceback (most recent call last): 
   ...
   InvalidData: {
      '__all__': ['If any of first_name, last_name, middle_name are provided, all must be provided'],
      'first_name': ['This field is required'],
      'last_name': ['This field is required'],
   }

Note that ``middle_name`` isn't required. Generally when using
:py:class:`filternaut.Optional`, all the child filters would have
``required=True``, however not always. In this example setup, providing a
``first_name`` triggers the requirement on ``last_name``, but not on
``middle_name``. However, if ``middle_name`` *is* provided, the other two names
become required too.

.. testcode::

   filters.parse({'middle_name': 'Boone'})

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   Traceback (most recent call last): 
   ...
   InvalidData: {
      '__all__': ['Only one of email, username can be provided'],
      'first_name': ['This field is required'],
      'last_name': ['This field is required'],
   }


:py:class:`filternaut.OneOf`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrapping filters in :py:class:`filternaut.OneOf` will enforce that only one of
their values can be supplied at once. For example, if you want to query a user
by email address, or by username, but not allow both at once:

.. testcode::

   from filternaut import OneOf

   filters = OneOf(Filter("username"), Filter("email"))
   filters.parse({"username": "foo", "email": "bar"})

.. testoutput::

   Traceback (most recent call last): 
   ...
   InvalidData: {'__all__': ['Only one of email, username can be provided']}


Specifying choices with ChoiceFilter
------------------------------------

.. testcode::

   from filternaut.filters import ChoiceFilter

   difficulties = [(4, 'Torment I'), (5, 'Torment II')]
   filters = ChoiceFilter('difficulty', choices=difficulties)
   filters.parse({'difficulty': 'foo'})

.. testoutput::

   Traceback (most recent call last): 
   ...
   InvalidData: {'difficulty': ['Select a valid choice. foo is not ...']}


Specifying arguments to field-specific filters
----------------------------------------------

Filters wrapping fields which require special arguments to instantiate (e.g.
``choices`` in the :ref:`example above <Specifying choices with ChoiceFilter>`)
also require those arguments. That is, because ChoiceField needs ``choices``,
so does ChoiceFilter.

The full list of field-specific filter classes is:

- BooleanFilter
- CharFilter
- ChoiceFilter
- ComboFilter
- DateFilter
- DateTimeFilter
- DecimalFilter
- EmailFilter
- FieldFilter
- FilePathFilter
- FloatFilter
- GenericIPAddressFilter
- IPAddressFilter
- ImageFilter
- IntegerFilter
- MultiValueFilter
- MultipleChoiceFilter
- NullBooleanFilter
- RegexFilter
- SlugFilter
- SplitDateTimeFilter
- TimeFilter
- TypedChoiceFilter
- TypedMultipleChoiceFilter
- URLFilter


Django REST Framework
---------------------

Using Filternaut with Django REST Framework is no more complicated than normal;
simply connect, for example, a request's query parameters to a view's queryset:

.. testcode::

   from filternaut.filters import CharFilter, EmailFilter
   from rest_framework import generics, exceptions

   class UserListView(generics.ListAPIView):
       model = User

       def filter_queryset(self, queryset):
           queryset = super().filter_queryset(queryset)
           filters = CharFilter('username') | EmailFilter('email')

           try:
              query = filters.parse(self.request.query_params)
           except filternaut.InvalidData as ex:
               raise exceptions.ParseError(ex.errors)

           return queryset.filter(query)


Filternaut also provides a Django REST Framework-compatible filter backend
:py:class:`filternaut.drf.FilternautBackend` to reduce the boilerplate. It does
the same as above, filtering the queryset or raising a ParseError. Here's how
to use it:

.. testcode::

   from filternaut.drf import FilternautBackend
   from filternaut.filters import CharFilter, EmailFilter
   from rest_framework import views

   class MyView(views.APIView):
       filter_backends = (FilternautBackend, )
       filternaut_filters = CharFilter('username') | EmailFilter('email')

The attribute ``filternaut_filters`` should combine one or more Filter
instances, or be a callable accepting the current request and returning the
same.


.. testcode::

   from rest_framework import views

   class MyView(views.APIView):
       filter_backends = (FilternautBackend, )

       def filternaut_filters(self, request):
           choices = ['guest', 'developer']
           if request.user.is_staff:
               choices.append('manager')
           return ChoiceFilter('account_type', choices=enumerate(choices))
