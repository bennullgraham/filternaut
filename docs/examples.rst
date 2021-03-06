Examples
========

Using a Simple Filter
---------------------

Here Filternaut pulls a username from ``user_data`` and filters a User queryset
with it. Filternaut is overkill for such a simple job, but hey, it's the first
example.

.. testcode::

   from filternaut import Filter

   user_data = {'username': 'nostromo'}
   filters = Filter('username')
   filters.parse(user_data)
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."username" = nostromo

Using Lookups
-------------

It's common to require comparisons such as greater than, less than, etc.
against one field. You can provide a ``lookups`` argument to specify these.

.. testcode::

   from filternaut.filters import Filter

   filters = Filter('username', lookups=['icontains', 'contains'])
   filters.parse({'username__icontains': 'nostromo'})
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."username" LIKE %nostromo%...

The default comparison is 'exact', which is the equivalent of using no
comparison affix when filtering with Django's ORM. To keep the 'exact'
comparison when explicitly listing lookups, you must add ``'exact'`` to the
list:

.. code-block:: python

   filters = Filter('last_login', lookups=['year', 'exact'])

If you provide only one lookup, the source data can optionally omit the lookup
from the name of the key:

.. testcode::

   from filternaut.filters import Filter

   filters = Filter('email', lookups=['iexact'])

   # the lookup can be omitted...
   filters.parse({'email': 'Sentence@Case.COM'})

   # ...or included
   filters.parse({'email__iexact': 'Sentence@Case.COM'})

Combining Several Filters
-------------------------

Now Filternaut is used to filter Users with either an email, a username, or a
(first name, last name) pair.

.. testcode::

   from filternaut import Filter

   user_data = {'email': 'user3@example.org', 'username': 'user3'}
   filters = (
       Filter('email') |
       Filter('username') |
       (Filter('first_name') & Filter('last_name')))
   filters.parse(user_data)
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE ("auth_user"."email" = user3@example.org OR
          "auth_user"."username" = user3)


The same filters generate result in different SQL when given different input
data:

.. testcode::

   user_data = {'first_name': 'Art', 'last_name': 'Vandelay'}
   filters.parse(user_data)
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE ("auth_user"."first_name" = Art AND
          "auth_user"."last_name" = Vandelay)

Filtering with Multiple Values
------------------------------

Using the lookup ``__in`` triggers the collection of multiple values from the
source. If this is the case, the source must provide a ``getlist`` method.
Django's QueryDict provides such a method.

.. testcode::

   from filternaut.filters import Filter
   from django.utils.datastructures import MultiValueDict

   filters = Filter(source='groups', dest='groups__name', lookups=['in'])
   user_data = MultiValueDict({'groups': ['foo', 'bar']})
   filters.parse(user_data)
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_group"."name" IN (foo, bar)

If the source does not provide a ``getlist`` method Filternaut will fall back
to a single value, but still deliver it as a list.

If you'd like one of your multiple values to be None and match against some row
in your database with a null value, you need to take two special actions.
Firstly you must tell filternaut to treat the None specially, and secondly you
must construct the backing form-field yourself so it can be given the
`required` parameter which is otherwise always True.

.. testcode::

   from filternaut.filters import FieldFilter
   from django.forms import IntegerField
   from django.utils.datastructures import MultiValueDict

   filters = FieldFilter(
      'id', none_to_isnull=True, lookups='in',
      field=IntegerField(required=False)
   )
   user_data = MultiValueDict({'id': [1, None]})
   filters.parse(user_data)
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE ("auth_user"."id" IN (1) OR "auth_user"."id" IS NULL)

The reason this is a special case arises from the way SQL treats null.

Mapping a Different Public API onto your Schema.
------------------------------------------------

In this example, the source data's ``last_transaction`` value filters on the
value of a field across a distant relationship. This allows you to simplify or
hide the details of your schema, and to later change them without changing the
names you expose.

.. testcode::

   from filternaut import Filter
   filters = Filter(
       source='last_payment',
       dest='order__transaction__created_date',
       lookups=['lt', 'lte', 'gt', 'gte'])

Default Values for Filters
--------------------------

Filters can be given default values.

.. testcode::

   from filternaut import Filter
   filters = Filter('is_active', default=True)
   filters.parse({})  # no 'is_active'
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."is_active" = True

When a default value is used, lookups are ignored. Most combinations of lookups
are mutually exclusive when comparing the same value. For example, filtering by
``score__lt=3`` and ``score__gt=3`` does not make any sense. Instead, a lookup
of ``exact`` is used. ``default_lookup`` may be used to override this.

.. testcode::

   from datetime import datetime
   from filternaut import Filter
   filters = Filter('last_login', lookups=['lte', 'lt', 'gt', 'gte'],
                    default=datetime.now(), default_lookup='lte')
   filters.parse({})  # no 'last_login'
   print(User.objects.filter(filters.Q).query)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   SELECT "auth_user"."id", ...
   WHERE "auth_user"."last_login" <= ...

Requiring Certain Filters
-------------------------

If it's mandatory to provide certain filtering values, you can use the
``required`` argument. By default, filters are not required.

.. testcode::

   from filternaut import Filter

   filters = Filter('username', required=True)
   filters.parse({})  # no 'username'

   print(filters.valid)
   print(filters.errors)

.. testoutput::

   False
   {'username': ['This field is required']}

Conditional Requirements
------------------------

Sometimes a field is required only when another is present. For example, you
may say that a value for ``last_name`` must be accompanied by a value for
``first_name``, whilst also allowing neither. Additionally, you may say that a
value for ``middle_name`` requires values for ``first_name`` and ``last_name``,
but not vice versa. That example is illustrated here:

.. testcode::

   from filternaut import Filter, Optional

   filters = (
      Optional(
         Filter('first_name', required=True),
         Filter('middle_name'),
         Filter('last_name', required=True)) &
      Filter('badgers_defeated'))

   filters.parse({'first_name': 'Nostromo'})
   print(filters.errors['__all__'])
   print(filters.errors['last_name'])

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   ['If any of first_name, last_name, middle_name are provided,
     all must be provided']
   ['This field is required']

Though the middle name filter isn't required itself, when present it triggers
the requirement of the filters that are.

.. testcode::

   filters.parse({'middle_name': 'Boone'})
   print(filters.errors['__all__'])
   print(filters.errors['first_name'])
   print(filters.errors['last_name'])

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   ['If any of first_name, last_name, middle_name are provided,
     all must be provided']
   ['This field is required']
   ['This field is required']

When all required filters in an Optional group are present, the filters as a
whole are valid.

.. testcode::

   filters.parse({
      'first_name': 'Nostromo',
      'last_name': 'Cheradenine'})
   assert filters.valid

Similarly, when none of the filters in an Optional group are present, the
filters as a whole are valid.

.. testcode::

   filters.parse({})
   assert filters.valid

Validating and Transforming Source Data
---------------------------------------

Filters can be combined with ``django.forms.fields.Field`` instances to
validate and transform source data.

.. testcode::

   from django.forms import DateTimeField
   from filternaut.filters import FieldFilter

   filters = FieldFilter('signup_date', field=DateTimeField())
   filters.parse({'signup_date': 'potato'})

   print(filters.valid)
   print(filters.errors)

.. testoutput::

   False
   {'signup_date': ['Enter a valid date/time.']}

Instead of making you provide your own ``field`` argument, Filternaut pairs
most of Django's Field subclasses with Filters. They can be used like so:

.. testcode::

   from filternaut.filters import ChoiceFilter

   difficulties = [(4, 'Torment I'), (5, 'Torment II')]
   filters = ChoiceFilter('difficulty', choices=difficulties)
   filters.parse({'difficulty': 'foo'})

   print(filters.valid)
   print(filters.errors)

.. testoutput::

   False
   {'difficulty': ['Select a valid choice. foo is not ...']}

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
- GenericIPAddressFilter
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
- TypedMultipleChoiceFilter
- URLFilter


Django REST Framework
---------------------

Using Filternaut with Django REST Framework is no more complicated than normal;
simply connect, for example, a request's query parameters to a view's queryset:

.. testcode::

   from filternaut.filters import CharFilter, EmailFilter
   from rest_framework import generics

   class UserListView(generics.ListAPIView):
       model = User

       def filter_queryset(self, queryset):
           filters = CharFilter('username') | EmailFilter('email')
           filters.parse(self.request.query_params)
           queryset = super(UserListView, self).filter_queryset(queryset)
           return queryset.filter(filters.Q)


Filternaut also provides a Django REST Framework-compatible filter backend:

.. testcode::

   from filternaut.drf import FilternautBackend
   from filternaut.filters import CharFilter, EmailFilter
   from rest_framework import views

   class MyView(views.APIView):
       filter_backends = (FilternautBackend, )
       filternaut_filters = CharFilter('username') | EmailFilter('email')

The attribute ``filternaut_filters`` should contain one or more Filter
instances. Instead of an attribute, it can also be a callable which returns a
list of filters, allowing the filters to vary on the current request:

.. testcode::

   from rest_framework import views

   class MyView(views.APIView):
       filter_backends = (FilternautBackend, )

       def filternaut_filters(self, request):
           choices = ['guest', 'developer']
           if request.user.is_staff:
               choices.append('manager')
           return ChoiceFilter('account_type', choices=enumerate(choices))
