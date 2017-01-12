# -*- coding: utf8 -*-

from __future__ import absolute_import, unicode_literals

from collections import Iterable

import six

from django.forms import (BooleanField, CharField, ChoiceField, ComboField,
                          DateField, DateTimeField, DecimalField, EmailField,
                          FilePathField, FloatField, ImageField, IntegerField,
                          MultipleChoiceField, MultiValueField,
                          NullBooleanField, RegexField, SlugField,
                          SplitDateTimeField, TimeField, TypedChoiceField,
                          URLField)
from filternaut import Filter

# note IPAddressField, GenericIPAddressField and TypedMultipleChoiceField are
# conditionally imported later in this file; they are not available in all
# versions of Django.


__all__ = [
    'BooleanFilter', 'CharFilter', 'ChoiceFilter', 'ComboFilter', 'DateFilter',
    'DateTimeFilter', 'DecimalFilter', 'EmailFilter', 'FilePathFilter',
    'FloatFilter', 'IPAddressFilter', 'ImageFilter', 'FieldFilter',
    'IntegerFilter', 'MultiValueFilter', 'MultipleChoiceFilter',
    'NullBooleanFilter', 'RegexFilter', 'SlugFilter', 'SplitDateTimeFilter',
    'TimeFilter', 'TypedChoiceFilter', 'URLFilter']


def is_listlike(val):
    """
    True if `val` is an iterable (list, tuple, ...) but not a string
    """
    return isinstance(val, Iterable) and not isinstance(val, six.string_types)


class FieldFilter(Filter):
    """
    FieldFilters use a django.forms.Field to clean their input value when
    generating a Q object.

    This class is designed to be extended by subclasses which provide their own
    form-field instances. However, you could use it in combination with a
    custom field like so:

        filter = FieldFilter(SpecialField(), dest='...')
    """

    def __init__(self, dest, field, **kwargs):
        self.field = field
        super(FieldFilter, self).__init__(dest, **kwargs)

    def clean(self, value):
        if is_listlike(value):
            return type(value)(self.field.clean(v) for v in value)
        else:
            return self.field.clean(value)


# -- mixtures of fieldfilter and django fields requiring additional arguments


class ChoiceFilter(FieldFilter):
    def __init__(self, dest, choices, *args, **kwargs):
        field = ChoiceField(choices=choices)
        super(ChoiceFilter, self).__init__(dest, field=field, *args, **kwargs)


class RegexFilter(FieldFilter):
    def __init__(self, dest, regex, *args, **kwargs):
        field = RegexField(regex=regex)
        super(RegexFilter, self).__init__(dest, field=field, *args, **kwargs)


class FilePathFilter(FieldFilter):
    def __init__(self, dest, path, *args, **kwargs):
        field = FilePathField(path=path)
        super(FilePathFilter, self).__init__(dest, field=field,
                                             *args, **kwargs)


class BooleanFilter(FieldFilter):
    """
    BooleanField required=True does not have sanely.
    """
    def __init__(self, dest, **kwargs):
        field = BooleanField(required=False)
        super(BooleanFilter, self).__init__(dest, field=field, **kwargs)


# -- simple mixtures of fieldfilter and django fields.

class FieldMixin(object):
    def __init__(self, dest, **kwargs):
        field = self.field_class()
        super(FieldMixin, self).__init__(dest, field=field, **kwargs)


class CharFilter(FieldMixin, FieldFilter):
    field_class = CharField


class ComboFilter(FieldMixin, FieldFilter):
    field_class = ComboField


class DateFilter(FieldMixin, FieldFilter):
    field_class = DateField


class DateTimeFilter(FieldMixin, FieldFilter):
    field_class = DateTimeField


class DecimalFilter(FieldMixin, FieldFilter):
    field_class = DecimalField


class EmailFilter(FieldMixin, FieldFilter):
    field_class = EmailField


class FloatFilter(FieldMixin, FieldFilter):
    field_class = FloatField


class ImageFilter(FieldMixin, FieldFilter):
    field_class = ImageField


class IntegerFilter(FieldMixin, FieldFilter):
    field_class = IntegerField


class MultiValueFilter(FieldMixin, FieldFilter):
    field_class = MultiValueField


class MultipleChoiceFilter(FieldMixin, FieldFilter):
    field_class = MultipleChoiceField


class NullBooleanFilter(FieldMixin, FieldFilter):
    field_class = NullBooleanField


class SlugFilter(FieldMixin, FieldFilter):
    field_class = SlugField


class SplitDateTimeFilter(FieldMixin, FieldFilter):
    field_class = SplitDateTimeField


class TimeFilter(FieldMixin, FieldFilter):
    field_class = TimeField


class TypedChoiceFilter(FieldMixin, FieldFilter):
    field_class = TypedChoiceField


class URLFilter(FieldMixin, FieldFilter):
    field_class = URLField


# -- mixtures of fieldfilter and django fields which were not present in older
# -- django versions

try:
    # django 1.3 and older did not have GenericIPAddressField or
    # TypedMultipleChoiceField, so we must conditionally define our matching
    # Filters.
    from django.forms import GenericIPAddressField, TypedMultipleChoiceField
except ImportError:
    pass
else:
    class GenericIPAddressFilter(FieldMixin, FieldFilter):
        field_class = GenericIPAddressField

    class TypedMultipleChoiceFilter(FieldMixin, FieldFilter):
        field_class = TypedMultipleChoiceField

    __all__.extend((
        'GenericIPAddressFilter',
        'TypedMultipleChoiceFilter'))

try:
    # django 1.9 and later drop support for IPAddressField
    from django.forms import IPAddressField
except ImportError:
    pass
else:
    class IPAddressFilter(FieldMixin, FieldFilter):
        field_class = IPAddressField

    __all__.extend(('IPAddressField', ))
