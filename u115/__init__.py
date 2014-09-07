# -*- coding: utf-8 -*-
"""
.. autoclass:: RequestHandler
   :members:
   :undoc-members:

.. autoclass:: Request
   :members:
   :undoc-members:

   .. automethod:: __init__

.. autoclass:: Response
   :members:
   :undoc-members:

.. autoclass:: Passport
   :members:
   :undoc-members:

.. autoclass:: API
   :members:
   :undoc-members:

.. autoclass:: Task
   :members:
   :undoc-members:

.. autoclass:: Torrent
   :members:
   :undoc-members:

.. autoclass:: TorrentFile
   :members:
   :undoc-members:

.. autoclass:: File
   :members:
   :undoc-members:

.. autoclass:: Directory
   :members:
   :undoc-members:

.. autoclass::  APIError
   :members:
   :undoc-members:


"""

import humanize
import json
import os
import re
import requests
import time
from hashlib import sha1
from bs4 import BeautifulSoup
#import pdb
import utils
from u115 import conf

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'


class RequestHandler(object):
    """
    Request handler that maintains session

    :ivar session: underlying :class:`requests.Session` instance

    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT

    def get(self, url, params=None):
        """
        Initiate a GET request
        """
        r = self.session.get(url, params=params)
        return self._response_parser(r, expect_json=False)

    def post(self, url, data, params=None):
        """
        Initiate a POST request
        """
        r = self.session.post(url, data=data, params=params)
        return self._response_parser(r, expect_json=False)

    def send(self, request):
        """
        Send a formatted API request

        :param request: a formatted request object
        :type request: :class:`Request`
        """
        r = self.session.request(method=request.method,
                                 url=request.url,
                                 params=request.params,
                                 data=request.data,
                                 files=request.files)
        return self._response_parser(r)

    def _response_parser(self, r, expect_json=True):
        """
        :param :class:`requests.Response` r: a response object of the Requests
            library
        :param bool expect_json: if True, raise APIError if response is not in
            JSON format
        """
        if r.ok:
            try:
                j = r.json()
                return Response(j.get('state'), j)
            except ValueError:
                # No JSON-encoded data returned
                if expect_json:
                    print r.content
                    raise APIError('Invalid API access.')
                return Response(False, r.content)
        else:
            r.raise_for_status()


class Request(object):
    """Formatted API request class"""

    def __init__(self, url, method='GET', params=None, data=None,
                 files=None, headers=None):
        """
        Create a Request object

        :param str url: URL
        :param str method: request method
        :param dict params: request parameters
        :param dict data: form data
        :param dict files: mulitpart form data
        :param dict headers: custom request headers

        """
        self.url = url
        self.method = method
        self.params = params
        self.data = data
        self.files = files
        self.headers = headers


class Response(object):
    """
    Formatted API response class

    :ivar bool state: whether API access is successful
    :ivar dict content: result content
    """

    def __init__(self, state, content):
        self.state = state
        self.content = content


class API(object):
    """
    Request and response interface

    :ivar passport: :class:`Passport` object associated with this interface
    :ivar http: :class:`RequestHandler` object associated with this
        interface
    :cvar int num_tasks_per_page: default number of tasks per page/request
    """

    num_tasks_per_page = 30
    web_api_url = 'http://web.api.115.com/files'

    def __init__(self):
        self.passport = None
        self.http = RequestHandler()
        self._signatures = {}
        self._upload_url = None
        self._lixian_timestamp = None
        self._downloads_directory = None
        self._torrents_directory = None

    def login(self, username=None, password=None,
              section='default'):
        """
        Created the passport with ``username`` and ``password`` and log in.
        If either ``username`` or ``password`` is None or omitted, the
        credentials file will be parsed.

        :param str username: username to login (email, phone number or user ID)
        :param str password: password
        :param str section: section name in the credential file
        :raise: raises :class:`APIError` if failed to login
        """
        if username is None or password is None:
            credential = conf.get_credential(section)
            username = credential['username']
            password = credential['password']

        passport = Passport(username, password)
        r = self.http.post(passport.login_url, passport.form)

        if r.state is True:
            # Bind this passport to API
            self.passport = passport
            passport.data = r.content['data']
            passport.user_id = r.content['data']['USER_ID']
            passport.status = 'LOGGED_IN'
            return True
        else:
            msg = None
            if 'err_name' in r.content:
                if r.content['err_name'] == 'account':
                    msg = 'Account does not exist.'
                elif r.content['err_name'] == 'passwd':
                    msg = 'Password is incorrect.'
            passport.status = 'FAILED'
            error = APIError(msg)
            raise error

    def has_logged_in(self):
        """Check whether the API has logged in"""
        if self.passport is not None and self.passport.user_id is not None:
            params = {'user_id': self.passport.user_id}
            r = self.http.get(self.passport.checkpoint_url, params=params)
            if r.state is False:
                return True
        return False

    def logout(self):
        """Log out"""
        self.http.get(self.passport.logout_url)
        self.passport.status = 'LOGGED_OUT'
        return True

    @property
    def downloads_directory(self):
        """Default directory for downloaded files"""
        if self._downloads_directory is None:
            self._load_lixian_space()
        return self._downloads_directory

    @property
    def torrents_directory(self):
        """Default directory that stores uploaded torrents"""
        if self._torrents_directory is None:
            self._load_lixian_space()
        return self._torrents_directory

    def get_tasks(self, count=30):
        """
        Get ``count`` number of tasks

        :param int count: number of tasks to get
        :return: a list of :class:`Task` objects
        """

        return self._load_tasks(count)

    def add_task_bt(self, filename):
        """
        Added a new BT task

        :param str filename: path to torrent file to upload
        """

        u = self.upload(filename, self.torrents_directory)
        t = self._load_torrent(u)
        t.submit()

    def add_task_url(self):
        """Added a new URL task (VIP only)"""
        raise NotImplementedError

    def delete_task(self):
        pass

    def get_storage_info(self, human=False):
        """
        Get storage info
        :param bool human: whether return human-readable size
        :return: total and used storage
        :rtype: dict
        """
        res = self._req_get_storage_info()
        if human:
            res['total'] = humanize.naturalsize(res['total'], binary=True)
            res['used'] = humanize.naturalsize(res['used'], binary=True)
        return res

    def upload(self, filename, directory=None):
        """
        Upload a file ``filename`` to ``directory``

        :param str filename: path to the file to upload
        :param directory: destionation :class:`Directory`, defaults to
            :class:`API.downloads_directory` if None
        :return: the uploaded file
        :rtype: :class:`File`
        """

        if directory is None:
            directory = self.downloads_directory

        # First request
        res1 = self._req_upload(filename, directory)
        data1 = res1['data']
        file_id = data1['file_id']

        # Second request
        res2 = self._req_file(file_id)
        data2 = res2['data'][0]
        data2.update(**data1)
        return _instantiate_uploaded_file(self, data2)

    def _req_offline_space(self):
        """Required before accessing lixian tasks"""
        url = 'http://115.com/'
        params = {
            'ct': 'offline',
            'ac': 'space',
            '_': utils.get_timestamp(13)
        }
        req = Request(url=url, params=params)
        r = self.http.send(req)
        if r.state:
            self._signatures['offline_space'] = r.content['sign']
            self._lixian_timestamp = r.content['time']

    def _req_lixian_task_lists(self, page=1):
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'task_lists'}
        if 'offline_space' not in self._signatures:
            self._req_offline_space()
        data = {
            'page': page,
            'uid': self.passport.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content['tasks']

    def _req_lixian_get_id(self, torrent=False):
        """Get `cid' of lixian space directory"""
        url = 'http://115.com/lixian/'
        params = {
            'ct': 'lixian',
            'ac': 'get_id',
            'torrent': 1 if torrent else None,
            '_': utils.get_utcdatetime(13)
        }
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        return res.content

    def _req_lixian_torrent(self, u):
        """
        :param u: uploaded torrent file
        """

        url = 'http://115.com/lixian/'
        params = {
            'ct': 'lixian',
            'ac': 'torrent',
        }
        data = {
            'pickcode': u.pickcode,
            'sha1': u.sha,
            'uid': self.passport.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise APIError('Failed to open torrent.')

    def _req_lixian_add_task_bt(self, t):
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'add_task_bt'}
        _wanted = []
        for i, b in enumerate(t.files):
            if b.selected:
                _wanted.append(str(i))
        wanted = ','.join(_wanted)
        data = {
            'info_hash': t.info_hash,
            'wanted': wanted,
            'savepath': t.name,
            'uid': self.passport.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return True
        else:
            print res.content.get('error_msg')
            raise APIError('Failed to create new task.')

    def _req_files(self, cid, offset, limit, o='user_ptime', asc=0, aid=1,
                   show_dir=1, code=None, scid=None, snap=0, natsort=None,
                   source=None):
        params = locals()
        del params['self']
        req = Request(method='GET', url=self.web_api_url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise APIError('Failed to access files API.')

    def _req_file(self, file_id):
        url = self.web_api_url + '/file'
        data = {'file_id': file_id}
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise APIError('Failed to access files API.')

    def _req_directory(self, cid):
        """Return name and pid of by cid"""
        res = self._req_files(cid=cid, offset=0, limit=1)
        path = res['path']
        for d in path:
            if str(d['cid']) == cid:
                return {'cid': cid, 'name': d['name'], 'pid': d['pid']}

    def _req_files_download_url(self, pickcode):
        url = self.web_api_url + '/download'
        params = {'pickcode': pickcode, '_': utils.get_timestamp(13)}
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content['file_url']

    def _req_get_storage_info(self):
        url = 'http://115.com'
        params = {
            'ct': 'ajax',
            'ac': 'get_storage_info',
            '_': utils.get_timestamp(13),
        }
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        return res.content['1']

    def _req_upload(self, filename, directory):
        """Raw request to upload a file ``filename``"""
        self._upload_url = self._load_upload_url()
        self.http.get('http://upload.115.com/crossdomain.xml')
        b = os.path.basename(filename)
        target = 'U_1_' + str(directory.cid)
        files = {
            'Filename': ('', b, ''),
            'target': ('', target, ''),
            'Filedata': (b, open(filename, 'rb'), ''),
            'Upload': ('', 'Submit Query', ''),
        }
        req = Request(method='POST', url=self._upload_url, files=files)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            msg = None
            if res.content['code'] == 990002:
                msg = 'Invalid parameter.'
            elif res.content['code'] == 1001:
                msg = 'Torrent upload failed. Please try again later.'
            raise APIError(msg)

    def _load_tasks(self, count, page=1, tasks=None):
        if tasks is None:
            tasks = []
        loaded_tasks = [
            _instantiate_task(self, t) for t in
            self._req_lixian_task_lists(page)[:count]
        ]
        if count <= self.num_tasks_per_page:
            return tasks + loaded_tasks
        else:
            return self._load_tasks(count - self.num_tasks_per_page,
                                    page + 1, tasks + loaded_tasks)

    def _load_directory(self, cid):
        kwargs = self._req_directory(cid)
        if str(kwargs['pid']) != str(cid):
            return Directory(api=self, **kwargs)

    def _load_lixian_space(self):
        """Load downloads and torrents directory"""
        r = self._req_lixian_get_id(torrent=False)
        downloads_cid = r['dest_cid']
        torrent_cid = r['cid']
        self._downloads_directory = self._load_directory(downloads_cid)
        self._torrents_directory = self._load_directory(torrent_cid)

    def _load_upload_url(self):
        res = self._parse_src_js_var('upload_config_h5')
        return res['url']

    def _load_torrent(self, u):
        res = self._req_lixian_torrent(u)
        return _instantiate_torrent(self, res)

    def _parse_src_js_var(self, variable):
        """Parse JavaScript variables in the source page"""

        src_url = 'http://115.com'
        r = self.http.get(src_url)
        soup = BeautifulSoup(r.content)
        text = soup.find_all('script')[6].text
        pattern = "%s = (.*);" % (variable.upper())
        m = re.search(pattern, text)
        return json.loads(m.group(1).strip())


class Base(object):
    def __repr__(self):
        try:
            u = self.__str__()
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode data]'
        repr_type = type(u)
        return repr_type('<%s: %s>' % (self.__class__.__name__, u))

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return unicode(self).encode('utf-8')
        return '%s object' % self.__class__.__name__


class Passport(Base):
    """
    Passport for user authentication

    :ivar str username: username
    :ivar str password: user password
    :ivar dict form: a dictionary of POST data to login
    :ivar int user_id: user ID of the authenticated user
    :ivar dict data: data returned upon login
    :ivar str status: status of this passport

        * `NEW`: passport is newly created
        * `LOGGED_IN`: successfully logged in with this passport
        * `LOGGED_OUT`: logged out
        * `FAILED`: failed to log in

    """
    login_url = 'http://passport.115.com/?ct=login&ac=ajax&is_ssl=1'
    logout_url = 'http://passport.115.com/?ac=logout'
    checkpoint_url = 'http://passport.115.com/?ct=ajax&ac=ajax_check_point'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.form = self._form()
        self.user_id = None
        self.data = None
        self.status = 'NEW'

    def _form(self):
        vcode = self._vcode()
        f = {
            'login[ssoent]': 'A1',
            'login[version]': '2.0',
            'login[ssoext]': vcode,
            'login[ssoln]': self.username,
            'login[ssopw]': self._ssopw(vcode),
            'login[ssovcode]': vcode,
            'login[safe]': '1',
            'login[time]': '0',
            'login[safe_login]': '0',
            'goto': 'http://115.com/',
        }
        return f

    def _vcode(self):
        s = '%.6f' % time.time()
        whole, frac = map(int, s.split('.'))
        res = '%.8x%.5x' % (whole, frac)
        return res

    def _ssopw(self, vcode):
        p = sha1(self.password).hexdigest()
        u = sha1(self.username).hexdigest()
        return sha1(sha1(p + u).hexdigest() + vcode.upper()).hexdigest()

    def __unicode__(self):
        return self.username


class BaseFile(Base):
    def __init__(self, api, cid, name):
        """
        :param API api: associated API object
        :param int cid: integer
            for file: this represents the directory it belongs to;
            for directory: this represents itself
        :param str name: originally named `n`

        NOTICE
            cid, fid and pid are in string format at this time
        """
        self.api = api
        self.cid = cid
        self.name = name

    def __unicode__(self):
        return self.name


class File(BaseFile):
    """
    File in a directory

    :ivar int fid: file id
    :ivar int cid: cid of the current directory
    :ivar int size: size in bytes
    :ivar str file_type: originally named `ico`
    :ivar str sha: SHA1 hash
    :ivar datetime.datetime date_created: in "%Y-%m-%d %H:%M:%S" format,
        originally named `t`
    :ivar str thumbnail: thumbnail URL, originally named `u`
    :ivar str pickcode: originally named `pc`
    """

    def __init__(self, api, fid, cid, name, size, file_type, sha,
                 date_created, thumbnail, pickcode, *args, **kwargs):

        super(File, self).__init__(api, cid, name)

        self.fid = fid
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.file_type = file_type
        self.sha = sha
        self.date_created = date_created
        self.thumbnail = thumbnail
        self.pickcode = pickcode
        self._directory = None
        self._download_url = None

    @property
    def directory(self):
        """Directory that holds this file"""
        if self._directory is None:
            self._directory = self.api._load_directory(self.cid)
        return self._directory

    def get_download_url(self):
        """Get this file's download URL"""
        if self._download_url is None:
            self._download_url = \
                self.api._req_files_download_url(self.pickcode)
        return self._download_url

    @property
    def url(self):
        """Alias for :func:`File.get_download_url`"""
        return self.get_download_url()

    @property
    def is_torrent(self):
        return self.file_type == 'torrent'

    @property
    def open_torrent(self):
        if self.is_torrent:
            return self.api._load_torrent(self)


class Directory(BaseFile):
    """
    :ivar int cid: cid of this directory
    :ivar int pid: represents the parent directory it belongs to
    :ivar datetime.datetime date_created: integer, originally named `t`
    :ivar str pickcode: string, originally named `pc`

    """
    max_entries_per_load = 30

    def __init__(self, api, cid, name, pid, date_created=None, pickcode=None,
                 *args, **kwargs):
        super(Directory, self).__init__(api, cid, name)

        self.pid = pid
        if date_created is not None:
            self.date_created = date_created
        self.pickcode = pickcode
        self._parent = None

    @property
    def parent(self):
        """Parent directory that holds this directory"""
        if self._parent is None:
            if self.pid is not None:
                self._parent = self.api._load_directory(self.pid)
        return self._parent

    def reload(self):
        """Reload directory info (name and pid)"""
        r = self.api._req_directory(self.cid)
        self.pid = r['pid']
        self.name = r['name']

    def _load_entries(self, count, page, order, asc, entries=None):
        """
        Similar to API._load_tasks, but differs in that `page' is actually
        `offset' and starts from 0 instead of 1
        """
        if entries is None:
            entries = []
        loaded_entries = [
            entry for entry in
            self.api._req_files(cid=self.cid,
                                offset=page,
                                limit=self.max_entries_per_load,
                                o=order,
                                asc=asc)['data'][:self.max_entries_per_load]
        ]
        if count <= self.max_entries_per_load:
            return entries + loaded_entries
        else:
            return self._load_entries(count - self.max_entries_per_load,
                                      page + 1, order, asc,
                                      entries + loaded_entries)

    def list(self, count=30, order='user_ptime', asc=False):
        """
        List directory contents

        :param str order: originally named `o`
        :param bool asc:

        Return a list of :class:`.File` or :class:`Directory` objects
        """
        asc = 1 if asc is True else 0
        entries = self._load_entries(count, page=0, order=order, asc=asc)
        res = []
        for entry in entries:
            if 'pid' in entry:
                res.append(_instantiate_directory(self.api, entry))
            else:
                res.append(_instantiate_file(self.api, entry))
        return res


class Task(Directory):
    """
    BitTorrent or URL task

    :ivar datetime.datetime add_time: integer to datetiem object
    :ivar str file_id: equivalent to `cid` of :class:`Directory`
    :ivar str info_hash: hashed value
    :ivar datetime.datetime last_update:
    :ivar int left_time: left time
    :ivar int move: 1 (transferred) or 0 (not transferred)
    :ivar str name: name of this task
    :ivar int peers: number of peers
    :ivar int percent_done: <=100, originally named `percentDone`
    :ivar int rate_download: originally named `rateDownload`
    :ivar int size: size of task
    :ivar str size_human: human-readable size
    :ivar int status: status code

    """

    def __init__(self, api, add_time, file_id, info_hash, last_update,
                 left_time, move, name, peers, percent_done, rate_download,
                 size, status, cid, pid):
        super(Task, self).__init__(api, cid, name, pid)

        self.add_time = add_time
        self.file_id = file_id
        self.info_hash = info_hash
        self.last_update = last_update
        self.left_time = left_time
        self.move = move
        self.peers = peers
        self.percent_done = percent_done
        self.rate_download = rate_download
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.status = status

    def is_transferred(self):
        """
        :return: whether this tasks has been transferred
        :rtype: bool
        """
        return self.move == 1

    @property
    def status_human(self):
        """
        :return: human readable status

            * `BEING TRANSFERRED`: the tasks is being transferred
            * `TRANSFERRED`: the tasks has been transferred to downloads \
                    directory
            * `SEARCHING RESOURCES`
            * `FAILED`
            * `UNKNOWN STATUS`

        :rtype: str

        """
        res = None
        if self.status == 2:
            if self.move == 0:
                res = 'BEING TRANSFERRED'
            elif self.move == 1:
                res = 'TRANSFERRED'
        elif self.status == 4:
            res = 'SEARCHING RESOURCES'
        elif self.status == -1:
            res = 'FAILED'
        if res is not None:
            return res
        return 'UNKNOWN STATUS'


class Torrent(Base):
    """
    Opened torrent before becoming a task

    :ivar api: associated API object
    :ivar str name: task name, originally named `torrent_name`
    :ivar int size: task size, originally named `torrent_size`
    :ivar str info_hash: hashed value
    :ivar int file_count: number of files included
    :ivar list files: files included (list of :class:`TorrentFile`),
        originally named `torrent_filelist_web`
    """

    def __init__(self, api, name, size, info_hash, file_count, files,
                 *args, **kwargs):
        self.name = name
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.info_hash = info_hash
        self.file_count = file_count
        self.files = files
        self.submitted = False

    def submit(self):
        """Submit this torrent and create a new task"""
        if self.api._req_lixian_add_task_bt(self):
            self.submitted = True
            return True

    @property
    def selected_files(self):
        return [f for f in self.files if f.selected]

    @property
    def unselected_files(self):
        return [f for f in self.files if not f.selected]

    def __unicode__(self):
        return self.name


def TorrentFile(Base):
    """
    File in the torrent file list

    :param torrent: the torrent that holds this file
    :type torrent: :class:`Torrent`
    :param str path: file path in the torrent
    :param int size: file size
    :param bool selected: whether this file is selected
    """
    def __init__(self, torrent, path, size, selected, *args, **kwargs):
        self.torrent = torrent
        self.path = path
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.selected = selected

    def __unicode__(self):
        return '[%s] %s' ('*' if self.selected else ' ', self.path)


# Internal functions


def _instantiate_task(api, kwargs):
    """Create a Task object from raw kwargs"""
    kwargs['rate_download'] = kwargs['rateDownload']
    kwargs['percent_done'] = kwargs['percentDone']
    kwargs['add_time'] = utils.get_utcdatetime(kwargs['add_time'])
    kwargs['last_update'] = utils.get_utcdatetime(kwargs['last_update'])
    kwargs['cid'] = kwargs['file_id']
    is_transferred = (kwargs['status'] == 2 and kwargs['move'] == 1)
    if is_transferred:
        kwargs['pid'] = api.downloads_directory.cid
    else:
        kwargs['pid'] = None
    del kwargs['rateDownload']
    del kwargs['percentDone']
    task = Task(api, **kwargs)
    if is_transferred:
        task._parent = api.downloads_directory
    return task


def _instantiate_file(api, kwargs):
    kwargs['file_type'] = kwargs['ico']
    kwargs['date_created'] = utils.string_to_datetime(kwargs['t'])
    kwargs['pickcode'] = kwargs['pc']
    kwargs['name'] = kwargs['n']
    kwargs['thumbnail'] = kwargs.get('u')
    kwargs['size'] = kwargs['s']
    del kwargs['ico']
    del kwargs['t']
    del kwargs['pc']
    del kwargs['u']
    del kwargs['s']
    return File(api, **kwargs)


def _instantiate_directory(api, kwargs):
    kwargs['name'] = kwargs['n']
    kwargs['date_created'] = utils.get_utcdatetime(float(kwargs['t']))
    kwargs['pickcode'] = kwargs.get('pc')
    return Directory(api, **kwargs)


def _instantiate_uploaded_file(api, kwargs):
    kwargs['fid'] = kwargs['file_id']
    kwargs['name'] = kwargs['file_name']
    kwargs['pickcode'] = kwargs['pick_code']
    kwargs['size'] = kwargs['file_size']
    kwargs['sha'] = kwargs['sha1']
    kwargs['date_created'] = utils.get_utcdatetime(kwargs['file_ptime'])
    kwargs['thumbnail'] = None
    _, ft = os.path.splitext(kwargs['name'])
    kwargs['file_type'] = ft[1:]
    return File(api, **kwargs)


def _instantiate_torrent(api, kwargs):
    kwargs['size'] = kwargs['torrent_size']
    kwargs['name'] = kwargs['torrent_name']
    file_list = kwargs['torrent_filelist_web']
    kwargs['files'] = [_instantiate_torrent_file(f) for f in file_list]
    del kwargs['torrent_size']
    del kwargs['torrent_name']
    del kwargs['torrent_filelist_web']
    return Torrent(api, **kwargs)


def _instantiate_torrent_file(kwargs):
    kwargs['selected'] = True if kwargs['wanted'] == 1 else False
    del kwargs['selected']
    return TorrentFile(**kwargs)


class APIError(Exception):
    """Error related to API access"""
    pass
