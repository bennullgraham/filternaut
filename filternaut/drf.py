# -*- coding: utf8 -*-

from __future__ import unicode_literals

try:
    from rest_framework.filters import BaseFilterBackend
    from rest_framework.exceptions import ParseError
except ImportError:
    raise ImportError(
        "You must install Django REST Framework (pypi: "
        "'djangorestframework') to use Filternaut's DRF filter backend.")


class FilternautBackend(BaseFilterBackend):
    """
    FilternautBackend is a "custom generic filtering backend" for Django REST
    framework:
    http://www.django-rest-framework.org/api-guide/filtering/#custom-generic-filtering

    It allows straightforward filtering of a view's queryset using request
    parameters.
    """

    #: The host view must define filters at this attribute.
    filter_attr = 'filternaut_filters'

    def filter_queryset(self, request, queryset, view):
        """
        Decide whether to apply the filters defined by
        ``view.filternaut_filters`` on the argued queryset. If the filters
        parse correctly, ``is_valid`` is called. If not, ``is_invalid`` is
        called
        """
        try:
            filters = getattr(view, self.filter_attr)
        except AttributeError:
            raise AttributeError(
                "View {} requires attribute '{}' "
                "to use FilternautBackend".format(view, self.filter_attr))

        if callable(filters):
            filters = filters(request)

        filters.parse(request.query_params)

        if filters.valid:
            return self.is_valid(request, queryset, filters)
        else:
            return self.is_invalid(request, queryset, filters)

    def is_valid(self, request, queryset, filters):
        """
        Apply ``filters`` to ``queryset``. Provided for convenience when
        subclassing.
        """
        return queryset.filter(filters.Q)

    def is_invalid(self, request, queryset, filters):
        """
        Raise a ParseError containing the filter errors. This results in a 400
        Bad Request whose body details those errors. Provided for convenience
        when subclassing.
        """
        raise ParseError(filters.errors)
