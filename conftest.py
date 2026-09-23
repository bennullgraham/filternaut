import django
import pytest
from django.conf import settings


def pytest_configure():
    # set up just enough of Django for the tests and the doctests in docs/
    settings.configure(
        MIDDLEWARE=(),
        INSTALLED_APPS=(
            "django.contrib.auth",
            "django.contrib.contenttypes",
        ),
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        USE_TZ=True,  # only necessary for django<5
    )
    django.setup()

    from django.db import connection

    connection.creation.create_test_db(verbosity=0)


@pytest.fixture(autouse=True)
def doctest_globals(doctest_namespace):
    """
    Names available to every example in docs/. Mirrors doctest_global_setup in
    docs/conf.py, which is used when running doctests through Sphinx instead.
    """
    import pprint

    from django.contrib.auth.models import User

    import filternaut

    doctest_namespace.update(User=User, pprint=pprint, filternaut=filternaut)
