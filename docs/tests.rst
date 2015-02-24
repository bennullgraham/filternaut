Tests
=====

First, install the extra dependencies:

.. code-block:: console

  $ pip install requirements/maintainer.txt

You can run the test suite in a specific environment via tox. In this example,
against Python 2.7 and Django 1.4.  (Hint: try ``tox -l`` for a full list).

.. code-block:: console

  $ tox -e py27-dj14

The full set of environments can be run by providing no arguments to tox. If
it's the first time, consider opening a beer.

.. code-block:: console

  $ tox

Finally, you can run the test suite without tox if you prefer. You will need to
manually install additional dependencies if you choose to do this.

.. code-block:: console

  $ nosetests tests
