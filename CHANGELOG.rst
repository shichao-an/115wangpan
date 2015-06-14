Changelog
=========

0.7.0 (2015-06-14)
------------------

- Added public methods: move, edit, mkdir (#13, #19)
- Added Pro API support for getting download URL (#21)
- Added ``receiver_directory``
- Added logging utility and debugging hooks (#22)
- Combined 115down and 115up into a single 115 commands
- Supported Python 3.4 by removing ``__del__``

0.6.0 (2015-05-17)
------------------

- Deprecated ``auto_logout`` argument
- Added cookies support to CLI commands

0.5.1 (2015-04-20)
------------------

- 115down: fixed sub-entry range parser to ordered list

0.5.0 (2015-04-12)
------------------

- 115down: supported both keeping directory structure and flattening
- Fixed ``Task`` to not inherit ``Directory``

0.4.2 (2015-04-03)
------------------

- Fixed broken upload due to source page change (``_parse_src_js_var``)

0.4.1 (2015-04-03)
------------------

- 115down: added range support for argument ``sub_num`` (#14)
- 115down: added size display for file and task entries

0.4.0 (2015-03-23)
------------------

- Added persistent session (cookies) feature
- Added search API
- Added CLI commands: 115down and 115up
- Fixed #10

0.3.1 (2015-02-03)
------------------

- Fixed broken release 0.3.0 due to a missing dependency

0.3.0 (2015-02-03)
------------------

- Used external package "homura" to replace downloader utility
- Merge #8: added add_task_url API

0.2.4 (2014-10-09)
------------------

- Fixed #5: add isatty() so progress refreshes less frequently on non-tty
- Fixed parse_src_js_var

0.2.3 (2014-09-23)
------------------

- Fixed #2: ``show_progress`` argument
- Added resume download feature

0.2.2 (2014-09-20)
------------------

- Added system dependencies to documentation

0.2.1 (2014-09-20)
------------------

- Fixed ``Task.status_human`` error

0.2.0 (2014-09-20)
------------------

- Added download feature to the API and ``download`` method to ``u115.File``
- Added elaborate exceptions
- Added ``auto_logout`` optional argument to ``u115.API.__init__``
- Updated Task status info


0.1.1 (2014-09-11)
------------------

- Fixed broken sdist release of v0.1.0.


0.1.0 (2014-09-11)
------------------

- Initial release.
