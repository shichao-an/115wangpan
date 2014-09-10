Quickstart
==========

Login and credential file
-------------------------

To login with your account, simply call :class:`u115.API.login` with ``username`` and ``password`` as argument.

.. code-block:: python

    >>> from u115 import API
    >>> api = API()
    >>> api.login()
    >>> api.login('username@example.com', 'password')
    True

You can also put username and password in the file ``~/.115`` as credentials with the following format:

.. code-block:: ini

    [default]
    username = username@example.com
    password = defaultpassword

    [another]
    username = another@example.com
    password = anotherpassword

Then, you can login without providing username and password, only specifying the section name (defaults to `default`).

.. code-block:: python

    >>> api.login(section='another')
    True

Getting and managing tasks
--------------------------

You can retrieve tasks using :func:`u115.API.get_tasks`. This function takes an optional argument, `count`, which defaults to 30. You can specify a smaller or larger integer value:

.. code-block:: python

    >>> api.get_tasks(60)

.. toctree::
   :maxdepth: 2
