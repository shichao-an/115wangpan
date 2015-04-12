CLI Commands
============

.. highlight:: shell-session

There are two commands ``115down`` and ``115up`` that come with this package.

115down
-------
``115down`` is for listing tasks and downloading files and directories in the default downloads directory (:class:`u115.API.downloads_directory`).

Print help
~~~~~~~~~~

You can a comprehensive help message using the ``-h`` option:

::

    $ 115down -h

Authentication
~~~~~~~~~~~~~~
``115down`` needs to be authenticated every time it is invoked. You pass username to ``-u`` option, and you will be prompted for password without echoing.

::

    $ 115down -u yourname
    Password: 

If you don't want to be prompted for password every time, :ref:`set the credential file and section <login-and-credential-file>`. If the section is other than `default`, you specify the section name with ``-d``:

::

    $ 115down -d section_name

Listing tasks
~~~~~~~~~~~~~

Use ``-t`` to list task. The result output will contain a list of numbered tasks, each with status, size and name. The tasks are reversely ordered by creation time.

::
    $ 115down -t
    1 [TRANSFERRED] [3.2 GiB] <Task: [Airota&DHR&Mony][Jinrui wa Suitai Shimashita][1280x720]>
    2 [TRANSFERRED] [3.7 GiB] <Task: [CASO][Kill_Me_Baby][01-13][GB_BIG5][1280x720][x264_AAC]>
    3 [TRANSFERRED] [38.1 GiB] <Task: Shinryaku Ika Musume>
    ...

Downloading files
~~~~~~~~~~~~~~~~~

The default behavior of ``115down`` is to list entries (defaults to 30 entries) in the default downloads directory.

::

    $ 115down
    1 <Directory: [AirotaDHRMony][Jinrui wa Suitai Shimashita][1280x720]>
    2 <Directory: [CASO][Kill_Me_Baby][01-13][GB_BIG5][1280x720][x264_AAC]>
    3 <Directory: Shinryaku Ika Musume>
    4 <Directory: [Kamigami] Psycho-Pass 01-22 [1280x720 x264 AAC Sub(Chi,Jap)]>
    ...

To list more entries than default, pass a number to the ``-n`` option:

::

    $ 115down -n 60
    1 ...
    2 ...
    ...
    60 ...


To further list contents in a numbered entry:

::

    $ 115down 1
    <Directory: [AirotaDHRMony][Jinrui wa Suitai Shimashita][1280x720]> (13 out of 13)
         1 [291.2 MiB] <File: [Airota&amp;DHR&amp;Mony][Jinrui wa Suitai Shimashita][01][1280x720][x264_AAC].mp4>
         2 [277.5 MiB] <File: [Airota&amp;DHR&amp;Mony][Jinrui wa Suitai Shimashita][02][1280x720][x264_AAC].mp4>
         ...

To download all items of the specified entry, pass star (``*``) as the second arguments after the entry number.

::

    $ 115down 1 \*
    $ 115down 1 '*'


To download only one, or a range of items of the specified entry, use a number or range of numbers, like in the following examples.

Download the first item:

::

    $ 115down 1 1

Download item 2 and 4:

::

    $ 115down 1 2,4

Download item 1-8:

::

    $ 115down 1 1-8

Download a combination of items:

::

    $ 115down 1 1,3-4,6,9-12


The default downloading behavior is keeping the directory structure. If you want to flatten the directory so all files without creating any directories, pass the ``-f`` switch. This will download everything of this entry into the current working directory:

::

    $ 115down -f 1 `*`

If you want to print the files to be downloaded instead of really downloading them, use ``-s`` option to make a dry run.

::

    $ 115down -s 1 \*

115up
-----

You can create either BitTorrent or URL tasks using ``115up``. The authentication is same to that of ``115down``.

To create a BitTorrent task, pass the torrent path to ``-t``. If the task is succesfully created, its name and status will be printed.

::

    $ 115up -t ~/torrents/Mangaka-san.torrent
    Task is successfully created.
    [WOLF][Mangaka-san][01-12+OVA01-06][GB][720P][END] BEING TRANSFERRED

To create a URL pass, pass the link to ``-l``:

::

    $ 115up -l 'magnet:?xt=urn:btih...announce'
    Task is successfully created.
    [WOLF][Mangaka-san][01-12+OVA01-06][GB][720P][END] BEING TRANSFERRED
