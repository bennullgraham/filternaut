from filternaut.exceptions import InvalidData

try:
    from rest_framework.exceptions import ParseError
    from rest_framework.filters import BaseFilterBackend
except ImportError:
    raise ImportError(
        "You must install Django REST Framework (pypi: "
        "'djangorestframework') to use Filternaut's DRF filter backend."
    )


class FilternautBackend(BaseFilterBackend):
    """
    FilternautBackend is a "custom generic filtering backend" for Django REST
    framework:
    http://www.django-rest-framework.org/api-guide/filtering/#custom-generic-filtering

    It allows straightforward filtering of a view's queryset using request
    parameters.
    """

    #: The host view must define filters at this attribute.
    filter_attr = "filternaut_filters"

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
                f"View {view} requires attribute '{self.filter_attr}' to use FilternautBackend"
            )

        if callable(filters):
            filters = filters(request)

        try:
            query = filters.parse(request.query_params)
            return self.is_valid(request, queryset, query)
        except InvalidData as ex:
            return self.is_invalid(request, queryset, ex.errors)

    def is_valid(self, request, queryset, query):
        """
        Apply Q-object ``query`` to ``queryset``. Provided for convenience when
        subclassing.
        """
        return queryset.filter(query)

    def is_invalid(self, request, queryset, errors):
        """
        Raise a ParseError containing the filter errors. This results in a 400
        Bad Request whose body details those errors. Provided for convenience
        when subclassing.
        """
        raise ParseError(errors)
