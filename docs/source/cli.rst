CLI Commands
============

.. highlight:: shell-session

``115`` is the CLI command that comes with this package. There are two sub-commands:

* ``115 down``: for downloading files
* ``115 up``: for creating tasks from torrents and links

115
---

``115`` mainly handles authentication and getting account information. The default action is to attempt to authenticate the API through one of ways discussed later.

Authentication
~~~~~~~~~~~~~~

``115`` needs to be authenticated every time it is invoked. You can pass username to ``-u`` option, and you will be prompted for password without echoing.

::

    $ 115 -u yourname
    Password: 

If you don't want to be prompted for password every time, :ref:`set the credential file and section <login-and-credential-file>`. If the section is other than `default`, you specify the section name with ``-d``:

::

    $ 115 -d section_name

Using cookies
~~~~~~~~~~~~~

You can use cookies to enable persistent session. The cookies file is ``~/.115cookies``. If this file exists, ``115 down`` and ``115 up`` will automatically use cookies. Otherwise, you have to save the cookies first using the ``-c`` option:

::

    $ 115 -d section_name -c
    Cookies is saved.
    $ 115 down -t
    API has logged in from cookies.
    ...

If using the default section (``default``), ``-d`` can be omitted:

::

    $ 115 -c
    Cookies is saved.

If you do not want to use cookies any more, simply remove the ``~/.115cookies`` file.

Account information
~~~~~~~~~~~~~~~~~~~

``-i`` option can be used to print account information:

::

    $ 115 -i
    Username: yourname@example.com
    User ID: 1234567
    Used storage: 1.0 GiB
    Total storage: 30 TiB
    Task count: 10
    Task quota: 1000

Debug mode
~~~~~~~~~~

``-D`` can enable debug by setting the effective log level to DEBUG:

::
    $ 115 -D -i
    DEBUG:API:_debug: 
       TYPE: Response
       FUNC: has_logged_in
      STATE: False
    CONTENT: {'state': False, 'message': ''}

    API has logged in from cookies.
    DEBUG:API:_debug: 
      TYPE: Request
      FUNC: _req_get_storage_info
       URL: http://115.com
    METHOD: GET
    PARAMS: {'ac': 'get_storage_info', '_': '12345678', 'ct': 'ajax'}
    ...

Print help
~~~~~~~~~~

You can print a comprehensive help message using the ``-h`` option:

::

    $ 115 -h


115 down
--------

``115 down`` is for listing tasks and downloading files and directories in the default downloads directory (:class:`u115.API.downloads_directory`/.

Listing tasks
~~~~~~~~~~~~~

Use ``-t`` to list task. The result output will contain a list of numbered tasks, each with status, size and name. The tasks are reversely ordered by creation time.

::

    $ 115 down -t
    1 [TRANSFERRED] [3.2 GiB] <Task: [Airota&DHR&Mony][Jinrui wa Suitai Shimashita][1280x720]>
    2 [TRANSFERRED] [3.7 GiB] <Task: [CASO][Kill_Me_Baby][01-13][GB_BIG5][1280x720][x264_AAC]>
    3 [TRANSFERRED] [38.1 GiB] <Task: Shinryaku Ika Musume>
    ...

Downloading files
~~~~~~~~~~~~~~~~~

The default behavior of ``115 down`` is to list entries (defaults to 30 entries) in the default downloads directory.

::

    $ 115 down
    1 <Directory: [AirotaDHRMony][Jinrui wa Suitai Shimashita][1280x720]>
    2 <Directory: [CASO][Kill_Me_Baby][01-13][GB_BIG5][1280x720][x264_AAC]>
    3 <Directory: Shinryaku Ika Musume>
    4 <Directory: [Kamigami] Psycho-Pass 01-22 [1280x720 x264 AAC Sub(Chi,Jap)]>
    ...

To list more entries than default, pass a number to the ``-n`` option:

::

    $ 115 down -n 60


To further list contents in a numbered entry:

::

    $ 115 down 1
    <Directory: [AirotaDHRMony][Jinrui wa Suitai Shimashita][1280x720]> (13 out of 13)
         1 [291.2 MiB] <File: [Airota&amp;DHR&amp;Mony][Jinrui wa Suitai Shimashita][01][1280x720][x264_AAC].mp4>
         2 [277.5 MiB] <File: [Airota&amp;DHR&amp;Mony][Jinrui wa Suitai Shimashita][02][1280x720][x264_AAC].mp4>
         ...

To download all items of the specified entry, pass star (``*``) as the second arguments after the entry number.

::

    $ 115 down 1 \*
    $ 115 down 1 '*'


To download only one, or a range of items of the specified entry, use a number or range of numbers, like in the following examples.

Download the first item:

::

    $ 115 down 1 1

Download item 2 and 4:

::

    $ 115 down 1 2,4

Download items 1 to 8:

::

    $ 115 down 1 1-8

Download a combination of items:

::

    $ 115 down 1 1,3-4,6,9-12


The default downloading behavior is keeping the directory structure. If you want to flatten the directory, pass the ``-f`` switch. This will download everything of this entry into the current working directory without creating any directories:

::

    $ 115 down -f 1 `*`

If you want to print the files to be downloaded instead of really downloading them, use ``-s`` option to make a dry run.

::

    $ 115 down -s 1 \*

115 up
------

You can create either BitTorrent or URL tasks using ``115 up``. 

To create a BitTorrent task, pass the torrent path to ``-t``. If the task is succesfully created, its name and status will be printed.

::

    $ 115 up -t ~/torrents/Mangaka-san.torrent
    Task is successfully created.
    [WOLF][Mangaka-san][01-12+OVA01-06][GB][720P][END] BEING TRANSFERRED

To create a URL pass, pass the link to ``-l``:

::

    $ 115 up -l 'magnet:?xt=urn:btih...announce'
    Task is successfully created.
    [WOLF][Mangaka-san][01-12+OVA01-06][GB][720P][END] BEING TRANSFERRED
