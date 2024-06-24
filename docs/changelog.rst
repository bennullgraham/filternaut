Changelog
=========

1.0.0
------

Very breaking change: immutable filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filters no longer mutate themselves when parsing, and several attributes of a
filter are now gone. There is no longer ``.errors``, ``.valid``, ``.dict`` or
``.Q``. These are all replaced by ``parse(data)`` and ``parse_to_dict(data)``
which respectively return a Django Q-object or its equivalent in dict form, or
raise an exception. ``parse_to_dict`` is only available on individual filters,
not once they've been ORed or ANDed together.

This change has been made because mutable filters almost guarantee subtle bugs.
If you use :py:class:`filternaut.drf.FilternautBackend` you do have some of
these bugs — the filter attribute is shared across all instances of your view
class, meaning state from a previous request can influence the current one, or
state from another thread can clobber your own. In general any sharing of
filter definitions across call-sites will have subtle issues too. The 1.0.0
release removes this problem. Follow this refactor guide to upgrade:

* If you only use :py:class:`filternaut.drf.FilternautBackend`, you don't need to
  do anything.

* If you call ``.parse()`` anywhere, you need to make the following
  refactor:

  .. code-block:: python

     # old
     filters = Filter("a") & Filter("b")
     filters.parse(input_data)
     if filters.valid:
         do_success_thing(filters.Q)
     else:
         do_failure_thing(filters.errors)

  .. code-block:: python

     # new
     filters = Filter("a") & Filter("b")
     try:
         query = filters.parse(input_data)
         do_success_thing(query)
     except filternaut.InvalidData as ex:
         do_failure_thing(ex.errors)

* If you've subclassed ``Filter`` or ``FilterTree``, check for any overrides of
  ``.errors``, ``.valid``, ``.dict`` or ``.Q``. If you were post-processing the
  parsed results in ``.Q``, override ``parse_to_dict(data)`` or ``parse(data)``
  and do the same post-processing there instead.

Other changes
~~~~~~~~~~~~~

- Previously, Python 2 support was unofficially still available. Now, it
  definitely doesn't work.

- Django 4.2 and 5.0 support. Django REST Framework 3.15 support.

0.0.14
------

- Filter defaults can be callable.

0.0.13
------

- Improve usability of ``multivalue_lookups`` by not requiring that all lookups
  argued have the ``__`` prefix on them.

0.0.12
------

- Lookups which require multiple values can be configured. ``__in`` works by
  default, but if you are using something custom or something I didn't bother
  setting up, like JSONField's ``__has_keys``, argue ``multivalue_lookups`` to
  your filter.

0.0.11
------

- Support "in" filters where a candidate value is null. Set
  ``none_to_isnull=True`` when creating a Filter to take advantage of this.

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

