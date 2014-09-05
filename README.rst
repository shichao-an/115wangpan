115 Lixian
==========

Unofficial Python API for 115, mainly pertinent to its "Lixian" (offline) features.

Under development.

Features
--------

* Account login and logout
* BT tasks management
* File management

Usage
-----
::

    >>> import u115
    >>> api = u115.API()
    >>> api.login('yourname@example.com', 'yourpassword')
    >>> tasks = api.get_tasks()
    >>> task = tasks[0]
    >>> print task.name
    咲-Saki- 阿知賀編 episode of side-A
    >>> print task.size_human
    1.6 GiB
    >>> files = task.list()
    >>> files
    [<File: 第8局 修行.mkv>]
    >>> f = files[0]
    >>> f.get_download_url()
    u'http://cdnuni.115.com/some-very-long-url.mkv'
    >>> f.directory
    <Directory: 咲-Saki- 阿知賀編 episode of side-A>
    >>> f.directory.parent
    <Directory: 离线下载>
