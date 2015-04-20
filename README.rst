115 Wangpan
===========

|Build| |PyPI version|

115 Wangpan (115网盘 or 115云) is an unofficial Python API and SDK for 115.com. Supported Python verisons are 2.6, 2.7 and 3.3.

* Documentation: http://115wangpan.readthedocs.org
* GitHub: https://github.com/shichao-an/115wangpan
* PyPI: https://pypi.python.org/pypi/115wangpan/

Features
--------

* Authentication
* Persistent session
* Tasks management: BitTorrent and links
* Files management: uploading, downloading and searching

Installation
------------

`libcurl <http://curl.haxx.se/libcurl/>`_ is required. Install dependencies before installing the python package:

Ubuntu:

.. code-block:: bash

    $ sudo apt-get install libcurl4-openssl-dev python-dev

Fedora:

.. code-block:: bash

    $ sudo yum groupinstall "Development Tools"
    $ sudo yum install libcurl libcurl-devel python-devel


Then, you can install with pip:

.. code-block:: bash

    $ pip install 115wangpan

Or, if you want to install the latest from GitHub:

.. code-block:: bash

    $ pip install git+https://github.com/shichao-an/115wangpan

Usage
-----

.. code-block:: python

    >>> import u115
    >>> api = u115.API()
    >>> api.login('username@example.com', 'password')
    True
    >>> tasks = api.get_tasks()
    >>> task = tasks[0]
    >>> print task.name
    咲-Saki- 阿知賀編 episode of side-A
    >>> print task.status_human
    TRANSFERRED
    >>> print task.size_human
    1.6 GiB
    >>> files = task.list()
    >>> files
    [<File: 第8局 修行.mkv>]
    >>> f = files[0]
    >>> f.url
    u'http://cdnuni.115.com/some-very-long-url.mkv'
    >>> f.directory
    <Directory: 咲-Saki- 阿知賀編 episode of side-A>
    >>> f.directory.parent
    <Directory: 离线下载>


CLI commands 
------------

* 115down: for downloading files
* 115up: for creating tasks from torrents and links

.. |Build| image:: https://api.travis-ci.org/shichao-an/115wangpan.png?branch=master
   :target: http://travis-ci.org/shichao-an/115wangpan
.. |PyPI version| image:: https://pypip.in/v/115wangpan/badge.png
   :target: https://pypi.python.org/pypi/115wangpan/
