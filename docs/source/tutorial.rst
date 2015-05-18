Tutorial
========

.. _login-and-credential-file:

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

To check whether API has logged:


.. code-block:: python

    >>> api.has_logged_in
    True

Cookies
-------

You can enable cookies to make a persistent session by providing ``persistent`` (True) and ``cookies_filename`` arguments.

.. code-block:: python

    >>> from u115 import API
    >>> api = API(persistent=True, cookies_filename='cookies.txt')
    >>> api.has_logged_in
    False
    >>> api.login(section='default')
    >>> api.has_logged_in
    True
    >>> api.save_cookies()
    >>> exit()
    # Invoke Python interpreter again
    >>> from u115 import API
    >>> api = API(persistent=True, cookies_filename='cookies.txt')
    >>> api.has_logged_in  # Already logged in using cookies
    True

You can also save cookies or load cookies explicitly.

.. code-block:: python

    >>> from u115 import API
    >>> api = API()
    >>> api.login()
    True
    # Do something ...
    >>> api.save_cookies()
    >>> exit()
    # Now invoke Python interpreter again
    >>> from u115 import API
    >>> api = API()
    >>> api.load_cookies()
    >>> api.has_logged_in
    True


Getting tasks
-------------

You can retrieve tasks using :func:`u115.API.get_tasks`. This function takes an optional argument, ``count``, which defaults to 30. You can specify a smaller or larger integer value:

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

Normally, if it is a BitTorrent task and has been transferred, it has an associated directory which contains "lixian" (offline) files:

.. code-block:: python

    >>> task.is_directory
    True
    >>> task.is_transferred
    True
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

Creating URL tasks
------------------

You can create URL (link) tasks. HTTP, HTTPS, FTP, Magnet, and eD2k links are supported.

.. code-block:: python

    >>> api.add_task_url('http://example.com/file.txt')
    >>> api.add_task_url('magnet:?xt.1=urn:sha1:YNCKHT.2=urn:sha1:TXGCZQT')


System directories 
------------------

The account has its offline space that stores files transferred from tasks or uploaded by users. The root directory has access to all available files.

.. code-block:: python

    >>> api.root_directory
    <Directory: 文件>
    >>> api.root_directory.list()
    [<Directory: 我的接收>]


After your tasks are transferred, the files go to the downloads directory (:attr:`u115.API.downloads_directory`).

.. code-block:: python

    >>> api.downloads_directory
    <Directory: 离线下载>

If you have created BitTorrent tasks by uploading torrents, you will have a torrents directory (:attr:`u115.API.torrents_directory`), which holds uploaded torrent files.

.. code-block:: python

    >>> api.torrents_directory
    <Directory: 种子文件>

Directory and files
-------------------

You can list contents of a directory using ``list()`` method of a :class:`Directory <u115.Directory>`. 

.. code-block:: python

    >>> entries = api.downloads_directory.list()
    >>> d = entries[0]
    >>> d_entries = d.list()
    >>> d_entries
    [<Directory: BK>, <Directory: MP3>, <File: Cover.jpg>
    >>> dd_entries = d_entries[0].list()
    >>> dd_entries.list()
    [<File: IMG_0003.jpg>, <File: IMG_0004.jpg>, <File: IMG_0005.jpg>, <File: IMG_0006.jpg>]


To get number of entries in a directory:

.. code-block:: python

    >>> d.count
    45

The default behavior is to list 30 entries. You can list specified number of entries, either with or without ``count``. The following two are equivalent:

.. code-block:: python

    >>> d.list(100)
    >>> d.list(count=100)

List all files by passing ``count`` of itself:

.. code-block:: python

    >>> d.list(d.count)

There are other arguments that can be passed to ``list()``, e.g. ``order`` (order of entries, which can be `user_ptime` (default), `file_size` and `file_name`), ``asc`` (whether in ascending order), ``show_dir`` (whether to show directories). For full list of arguments, see :meth:`u115.Directory.list`.

.. code-block:: python

    # List 100 smallest files
    >>> d.list(count=100, order='file_size', asc=True)
    # Do not include directories
    >>> d.list(show_dir=False)

A directory has a parent directory, which can be accessed via ``parent`` attribute:

.. code-block:: python

    >>> d.parent
    <Directory: 离线下载>
    >>> d.parent.parent
    <Directory: 我的接收>
    # root directory has no parent
    >>> d.root_directory.parent
    # None

Delete the file or directory:

.. code-block:: python

    >>> f = d.list()[0]
    >>> f.delete()
    True
    >>> f.is_deleted
    True


Search directories and files
----------------------------

You can search directories and files by passing the ``keyword`` to :meth:`u115.API.search`:

.. code-block:: python

    >>> api.search('manga')
    [<Directory: [WOLF][Mangaka-san][01-12+OVA01-06][GB][720P][END]>, <File: [WOLF][Mangaka-san][01][GB][720P].mp4>, ...]

By default, the search result limits to 30 items. To get more result, pass ``count`` to the methods:

.. code-block:: python
    
    >>> api.search('.mp4', count=100)


Download files
--------------

For offline files, you can retrieve download links:

.. code-block:: python

    >>> f = dd_entries.list()[0]
    >>> f
    <File: video.mov>
    >>> f.url
    u'http://cdnuni.115.com/very-long-name.mov'
    >>> f.download()
             1%   14.3 MiB     437.3 KiB/s         0:53:45 ETA


There are also extra options for :meth:`download() <u115.File.download>`. The default behavior is downloading the file to the current working directory, resuming download progress if the file already exists (with the same path), and automatically retrying upon closed transfer until the file's download is finished.

.. code-block:: python

    # Download to path ~/Downloads
    >>> f.download(path='~/Downloads')
    # Do not show progres
    >>> f.download(show_progress=False)
    # Override existing file without resuming downloads
    >>> f.download(resume=False)


Upload files
------------

You can upload files to any offline directory (defaults to ``downloads_directory``):

.. code-block:: python
    
    >>> p = api.downloads_directory.parent
    >>> p
    <Directory: 我的接收>
    >>> u = api.upload('/path/to/photo.jpg', directory=p)
    >>> u
    <File: photo.jpg>

The file you upload can be a torrent file, which you can open later and create a task from it:

.. code-block:: python

    >>> u = api.upload('/path/to/movie.torrent')
    >>> u.is_torrent
    True
    >>> t = u.open_torrent()
    >>> t.submit()
    

Account and storage info
------------------------

You can get user info:

.. code-block:: python

    >>> api.user_id
    u'123456789'
    >>> api.username
    u'yourname@exmaple.com'
    >>> api.get_user_info()
    {u'state': True, u'data': ...}

You can have an overview of your storage information:

.. code-block:: python

    >>> api.get_storage_info(human=True)
    {u'total': '152.3 GiB', u'used': '3.6 GiB'}

.. toctree::
   :maxdepth: 2
