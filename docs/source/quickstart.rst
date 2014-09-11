Quickstart
==========

Login and credential file
-------------------------

To login with your account, simply call :class:`u115.API.login` with ``username`` and ``password`` as argument.

.. code-block:: python

    >>> from u115 import API
    >>> api = API()
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

Getting tasks
-------------

You can retrieve tasks using :func:`u115.API.get_tasks`. This function takes an optional argument, `count`, which defaults to 30. You can specify a smaller or larger integer value:

.. code-block:: python

    >>> tasks = api.get_tasks(60)
    >>> tasks
    [<Task: TVアニメ「ローゼンメイデン」オリジナルサウンドトラック (320K+BK)>, <Task: Sword Art Online II - 10.mkv>, <Task: 咲-Saki- 阿知賀編 episode of side-A>]

To get count of total number of existing tasks and quota for this month:

.. code-block:: python

    >>> api.task_count
    3
    >>> api.task_quota
    27

To get the information of a specific task:

.. code-block:: python

    >>> task = tasks[1]
    >>> task.add_time
    datetime.datetime(2014, 9, 6, 23, 48, 58)
    >>> task.status_human
    'TRANSFERRED'

If the tasks has been transferred, it has a associated directory which contains "lixian" (offline) files:

.. code-block:: python

    >>> task.directory
    <Directory: Sword Art Online II - 10.mkv>
    >>> task.list() # or task.directory.list()
    [<File: Sword Art Online II - 10.mkv>]

Creating BitTorrent tasks
-------------------------

You can upload a torrent and create a task on the fly:

.. code-block:: python

    >>> api.add_task_bt('~/downloads/Black_Bullet_OP.torrent')
    True
    >>> api.get_tasks()
    [<Task: Black Bullet OP>, <Task: TVアニメ「ローゼンメイデン」オリジナルサウンドトラック (320K+BK)>, ...]

Or you can edit the torrent and select files before submitting:

.. code-block:: python

    >>> u = api.add_task_bt('~/downloads/Black_Bullet_OP.torrent', select=True)
    >>> files = u.files
    [<TorrentFile: [*] black bullet.mp4>, <TorrentFile: [*] black bullet [commentary].mp4>, ...]
    >>> files[0].unselect()
    >>> files
    [<TorrentFile: [ ] black bullet.mp4>, <TorrentFile: [*] black bullet [commentary].mp4>, ...]
    >>> u.submit()

Directories and files
---------------------




.. toctree::
   :maxdepth: 2
