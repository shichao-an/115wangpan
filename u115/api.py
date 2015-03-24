# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

import humanize
import json
import os
import re
import requests
import time
from hashlib import sha1
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar
from u115 import conf
from u115.utils import (get_timestamp, get_utcdatetime, string_to_datetime,
                        eval_path, quote, unquote, utf8_encode, txt_type, PY3)
from homura import download

if PY3:
    from http import cookiejar as cookielib
else:
    import cookielib

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'
LOGIN_URL = 'http://passport.115.com/?ct=login&ac=ajax&is_ssl=1'
LOGOUT_URL = 'http://passport.115.com/?ac=logout'
CHECKPOINT_URL = 'http://passport.115.com/?ct=ajax&ac=ajax_check_point'


class RequestsLWPCookieJar(cookielib.LWPCookieJar, RequestsCookieJar):
    """RequestsCookieJar compatible LWPCookieJar"""
    pass


class RequestsMozillaCookieJar(cookielib.MozillaCookieJar, RequestsCookieJar):
    """RequestsCookieJar compatible RequestsMozillaCookieJar"""
    pass


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
        :param bool expect_json: if True, raise :class`.InvalidAPIAccess` if
            response is not in JSON format
        """
        if r.ok:
            try:
                j = r.json()
                return Response(j.get('state'), j)
            except ValueError:
                # No JSON-encoded data returned
                if expect_json:
                    print(r.content)
                    raise InvalidAPIAccess('Invalid API access.')
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

    :ivar passport: :class:`.Passport` object associated with this interface
    :ivar http: :class:`.RequestHandler` object associated with this
        interface
    :cvar int num_tasks_per_page: default number of tasks per page/request
    """

    num_tasks_per_page = 30
    web_api_url = 'http://web.api.115.com/files'
    aps_natsort_url = 'http://aps.115.com/natsort/files.php'

    def __init__(self, auto_logout=True, persistent=False,
                 cookies_filename=None, cookies_type='LWPCookieJar'):
        """
        :param bool auto_logout: whether to logout automatically when
            :class:`.API` object is destroyed
        :param bool persistent: whether to use persistent session that stores
            cookies on disk
        :param str cookies_filename: path to the cookies file, use default
            path (`~/.115cookies`) if none
        :param str cookies_type: a string representing
            :class:`cookielib.FileCookieJar` subclass,
            `LWPCookieJar` (default) or `MozillaCookieJar`
        """
        self.auto_logout = auto_logout
        self.persistent = persistent
        self.cookies_filename = cookies_filename
        self.cookies_type = cookies_type
        self.passport = None
        self.http = RequestHandler()
        # Cached variabled to decrease API hits
        self._user_id = None
        self._username = None
        self._signatures = {}
        self._upload_url = None
        self._lixian_timestamp = None
        self._root_directory = None
        self._downloads_directory = None
        self._torrents_directory = None
        self._task_count = None
        self._task_quota = None
        if self.persistent:
            self.load_cookies()

    def __del__(self):
        if self.auto_logout and self.has_logged_in:
            self.logout()
        if not self.auto_logout and self.has_logged_in:
            if self.persistent:
                self.save_cookies()

    def _reset_cache(self):
        self._user_id = None
        self._username = None
        self._signatures = {}
        self._upload_url = None
        self._lixian_timestamp = None
        self._root_directory = None
        self._downloads_directory = None
        self._torrents_directory = None
        self._task_count = None
        self._task_quota = None

    def _init_cookies(self):
        # RequestsLWPCookieJar or RequestsMozillaCookieJar
        cookies_class = globals()['Requests' + self.cookies_type]
        f = self.cookies_filename or conf.COOKIES_FILENAME
        self.cookies = cookies_class(f)

    def load_cookies(self, ignore_discard=True, ignore_expires=True):
        """Load cookies from the file"""
        self._init_cookies()
        if os.path.exists(self.cookies.filename):
            self.cookies.load(ignore_discard=ignore_discard,
                              ignore_expires=ignore_expires)
            self._reset_cache()

    def save_cookies(self, ignore_discard=True, ignore_expires=True):
        """Save cookies to the file"""
        if not isinstance(self.cookies, cookielib.FileCookieJar):
            m = 'Cookies must be a cookielib.FileCookieJar object to be saved.'
            raise APIError(m)
        self.cookies.save(ignore_discard=ignore_discard,
                          ignore_expires=ignore_expires)

    @property
    def cookies(self):
        """Cookies getter shortcut"""
        return self.http.session.cookies

    @cookies.setter
    def cookies(self, cookies):
        """Cookies setter shortcut"""
        self.http.session.cookies = cookies

    def login(self, username=None, password=None,
              section='default'):
        """
        Created the passport with ``username`` and ``password`` and log in.
        If either ``username`` or ``password`` is None or omitted, the
        credentials file will be parsed.

        :param str username: username to login (email, phone number or user ID)
        :param str password: password
        :param str section: section name in the credential file
        :raise: raises :class:`.AuthenticationError` if failed to login
        """
        if self.has_logged_in:
            return True
        if username is None or password is None:
            credential = conf.get_credential(section)
            username = credential['username']
            password = credential['password']

        passport = Passport(username, password)
        r = self.http.post(LOGIN_URL, passport.form)

        if r.state is True:
            # Bind this passport to API
            self.passport = passport
            passport.data = r.content['data']
            self._user_id = r.content['data']['USER_ID']
            return True
        else:
            msg = None
            if 'err_name' in r.content:
                if r.content['err_name'] == 'account':
                    msg = 'Account does not exist.'
                elif r.content['err_name'] == 'passwd':
                    msg = 'Password is incorrect.'
            raise AuthenticationError(msg)

    def get_user_info(self):
        return self._req_get_user_aq()

    @property
    def user_id(self):
        if self._user_id is None:
            if self.has_logged_in:
                self._user_id = self._req_get_user_aq()['data']['uid']
            else:
                raise AuthenticationError('Not logged in.')
        return self._user_id

    @property
    def username(self):
        if self._username is None:
            if self.has_logged_in:
                self._username = self._get_username()
            else:
                raise AuthenticationError('Not logged in.')
        return self._username

    @property
    def has_logged_in(self):
        """Check whether the API has logged in"""
        r = self.http.get(CHECKPOINT_URL)
        if r.state is False:
            return True
        # If logged out, flush cache
        self._reset_cache()
        return False

    def logout(self):
        """Log out"""
        self.http.get(LOGOUT_URL)
        self._reset_cache()
        return True

    @property
    def root_directory(self):
        """Root directory"""
        if self._root_directory is None:
            self._load_root_directory()
        return self._root_directory

    @property
    def downloads_directory(self):
        """Default directory for downloaded files"""
        if self._downloads_directory is None:
            self._load_downloads_directory()
        return self._downloads_directory

    @property
    def torrents_directory(self):
        """Default directory that stores uploaded torrents"""
        if self._torrents_directory is None:
            self._load_torrents_directory()
        return self._torrents_directory

    @property
    def task_count(self):
        """
        Number of tasks created
        """
        self._req_lixian_task_lists()
        return self._task_count

    @property
    def task_quota(self):
        """
        Task quota (monthly)
        """
        self._req_lixian_task_lists()
        return self._task_quota

    def get_tasks(self, count=30):
        """
        Get ``count`` number of tasks

        :param int count: number of tasks to get
        :return: a list of :class:`.Task` objects
        """

        return self._load_tasks(count)

    def add_task_bt(self, filename, select=False):
        """
        Added a new BT task

        :param str filename: path to torrent file to upload
        :param bool select: whether to select files in the torrent.

            * If True, it returns the opened torrent (:class:`.Torrent`) and
                can then iterate files in :attr:`.Torrent.files` and
                select/unselect them before calling :func:`Torrent.submit`
            * If False, it will submit the torrent with default selected files

        """
        filename = eval_path(filename)
        u = self.upload(filename, self.torrents_directory)
        t = self._load_torrent(u)
        if select:
            return t
        return t.submit()

    def add_task_url(self, target_url):
        """
        :param str target_url: the URL of the file that to be downloaded

        """
        return self._req_lixian_add_task_url(target_url)

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
        :param directory: destionation :class:`.Directory`, defaults to
            :class:`.API.downloads_directory` if None
        :return: the uploaded file
        :rtype: :class:`.File`
        """
        filename = eval_path(filename)
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

    def download(self, obj, path=None, show_progress=True, resume=True,
                 auto_retry=True):
        """
        Download a file

        :param obj: :class:`.File` object
        :param str path: local path
        :param bool show_progress: whether to show download progress
        :param bool resume: whether to resume on unfinished downloads
            identified by filename
        :param bool auto_retry: whether to retry automatically upon closed
            transfer until the file's download is finished
        """
        download(obj.url, path=path, session=self.http.session,
                 show_progress=show_progress, resume=resume,
                 auto_retry=auto_retry)

    def search(self, keyword, count=30):
        """
        Search files or directories

        :param str keyword: keyword
        :param int count: number of entries to be listed
        """
        kwargs = {}
        kwargs['search_value'] = keyword
        root = self.root_directory
        entries = root._load_entries(func=self._req_files_search,
                                     count=count, page=1, **kwargs)

        res = []
        for entry in entries:
            if 'pid' in entry:
                res.append(_instantiate_directory(self, entry))
            else:
                res.append(_instantiate_file(self, entry))
        return res

    def _req_offline_space(self):
        """Required before accessing lixian tasks"""
        url = 'http://115.com/'
        params = {
            'ct': 'offline',
            'ac': 'space',
            '_': get_timestamp(13)
        }
        req = Request(url=url, params=params)
        r = self.http.send(req)
        if r.state:
            self._signatures['offline_space'] = r.content['sign']
            self._lixian_timestamp = r.content['time']
        else:
            msg = 'Failed to retrieve signatures.'
            raise RequestFailure(msg)

    def _req_lixian_task_lists(self, page=1):
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'task_lists'}
        self._load_signatures()
        data = {
            'page': page,
            'uid': self.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            self._task_count = res.content['count']
            self._task_quota = res.content['quota']
            return res.content['tasks']
        else:
            msg = 'Failed to get tasks.'
            raise RequestFailure(msg)

    def _req_lixian_get_id(self, torrent=False):
        """Get `cid` of lixian space directory"""
        url = 'http://115.com/'
        params = {
            'ct': 'lixian',
            'ac': 'get_id',
            'torrent': 1 if torrent else None,
            '_': get_timestamp(13)
        }
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        return res.content

    def _req_lixian_torrent(self, u):
        """
        :param u: uploaded torrent file
        """

        self._load_signatures()
        url = 'http://115.com/lixian/'
        params = {
            'ct': 'lixian',
            'ac': 'torrent',
        }
        data = {
            'pickcode': u.pickcode,
            'sha1': u.sha,
            'uid': self.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to open torrent.')

    def _req_lixian_add_task_bt(self, t):

        self._load_signatures()
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
            'uid': self.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return True
        else:
            print(res.content.get('error_msg'))
            raise RequestFailure('Failed to create new task.')

    def _req_lixian_add_task_url(self, target_url):

        self._load_signatures()
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'add_task_url'}
        data = {
            'url': target_url,
            'uid': self.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return True
        else:
            print(res.content.get('error_msg'))
            raise RequestFailure('Failed to create new task.')

    def _req_lixian_task_del(self, t):

        self._load_signatures()
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'task_del'}
        data = {
            'hash[0]': t.info_hash,
            'uid': self.user_id,
            'sign': self._signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return True
        else:
            raise RequestFailure('Failed to delete the task.')

    def _req_aps_natsort_files(self, cid, offset, limit, o='file_name',
                               asc=1, aid=1, show_dir=1, code=None, scid=None,
                               snap=0, natsort=1, source=None, type=0,
                               format='json', star=None, is_share=None):
        """
        When :func:`API._req_files` is called with `o='filename'` and
            `natsort=1`, API access will fail
            and :func:`API._req_aps_natsort_files` is subsequently called with
            the same kwargs. Refer to the implementation in
            :func:`Directory.list`
        """
        params = locals()
        del params['self']
        req = Request(method='GET', url=self.aps_natsort_url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_files(self, cid, offset, limit, o='user_ptime', asc=1, aid=1,
                   show_dir=1, code=None, scid=None, snap=0, natsort=1,
                   source=None, type=0, format='json', star=None,
                   is_share=None):
        """
        :param int type: type of files to be displayed

            * '' (empty string): marked
            * None: all
            * 0: all
            * 1: documents
            * 2: images
            * 3: music
            * 4: video
            * 5: zipped
            * 6: applications
            * 99: files only
        """
        params = locals()
        del params['self']
        req = Request(method='GET', url=self.web_api_url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_files_search(self, offset, limit, search_value, aid=-1,
                          date=None, pick_code=None, source=None, type=0,
                          format='json'):
        params = locals()
        del params['self']
        url = self.web_api_url + '/search'
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_files_edit(self, fid, file_name=None, is_mark=0):
        """Edit a file or directory"""
        url = self.web_api_url + '/edit'
        data = locals()
        del data['self']
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_files_add(self, pid, cname):
        """
        Add a directory
        :param int pid: parent directory id
        :param str cname: directory name
        """
        url = self.web_api_url + '/add'
        data = locals()
        del data['self']
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_files_move(self, pid, fids):
        """
        Move files or directories
        :param int pid: target directory id
        :param list fids: a list of ids of files or directories to be moved
        """
        url = self.web_api_url + '/move'
        data = {}
        data['pid'] = pid
        for i, fid in enumerate(fids):
            data['fid[%d]' % i] = fid
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_file(self, file_id):
        url = self.web_api_url + '/file'
        data = {'file_id': file_id}
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content
        else:
            raise RequestFailure('Failed to access files API.')

    def _req_directory(self, cid):
        """Return name and pid of by cid"""
        res = self._req_files(cid=cid, offset=0, limit=1, show_dir=1)
        path = res['path']
        count = res['count']
        for d in path:
            if str(d['cid']) == str(cid):
                res = {
                    'cid': d['cid'],
                    'name': d['name'],
                    'pid': d['pid'],
                    'count': count,
                }
                return res
        else:
            raise RequestFailure('No directory found.')

    def _req_files_download_url(self, pickcode):
        url = self.web_api_url + '/download'
        params = {'pickcode': pickcode, '_': get_timestamp(13)}
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        if res.state:
            return res.content['file_url']
        else:
            raise RequestFailure('Failed to get download URL.')

    def _req_get_storage_info(self):
        url = 'http://115.com'
        params = {
            'ct': 'ajax',
            'ac': 'get_storage_info',
            '_': get_timestamp(13),
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
            'Filename': ('', quote(b), ''),
            'target': ('', target, ''),
            'Filedata': (quote(b), open(filename, 'rb'), ''),
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
            raise RequestFailure(msg)

    def _req_rb_delete(self, fcid, pid):

        url = 'http://web.api.115.com/rb/delete'
        data = {
            'pid': pid,
            'fid[0]': fcid,
        }
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return True
        else:
            msg = 'Failed to delete this file or directory.'
            if 'errno' in res.content:
                if res.content['errno'] == 990005:
                    raise JobError()
            print(res.content['error'])
            raise APIError(msg)

    def _req_get_user_aq(self):
        url = 'http://my.115.com/'
        data = {
            'ct': 'ajax',
            'ac': 'get_user_aq'
        }
        req = Request(method='POST', url=url, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content

    def _load_signatures(self, force=True):
        if not self._signatures or force:
            self._req_offline_space()

    def _load_tasks(self, count, page=1, tasks=None):
        if tasks is None:
            tasks = []
        req_tasks = self._req_lixian_task_lists(page)
        loaded_tasks = []
        if req_tasks is not None:
            loaded_tasks = [
                _instantiate_task(self, t) for t in req_tasks[:count]
            ]
        if count <= self.num_tasks_per_page or req_tasks is None:
            return tasks + loaded_tasks
        else:
            return self._load_tasks(count - self.num_tasks_per_page,
                                    page + 1, tasks + loaded_tasks)

    def _load_directory(self, cid):
        kwargs = self._req_directory(cid)
        if str(kwargs['pid']) != str(cid):
            return Directory(api=self, **kwargs)

    def _load_root_directory(self):
        """
        Load root directory, which has a cid of 0
        """
        kwargs = self._req_directory(0)
        self._root_directory = Directory(api=self, **kwargs)

    def _load_torrents_directory(self):
        """
        Load torrents directory

        If it does not exist yet, this request will cause the system to create
        one
        """
        r = self._req_lixian_get_id(torrent=True)
        self._downloads_directory = self._load_directory(r['cid'])

    def _load_downloads_directory(self):
        """
        Load downloads directory

        If it does not exist yet, this request will cause the system to create
        one
        """
        r = self._req_lixian_get_id(torrent=False)
        self._downloads_directory = self._load_directory(r['cid'])

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
        scripts = [script.text for script in soup.find_all('script')]
        text = '\n'.join(scripts)
        pattern = "%s = (.*);" % (variable.upper())
        m = re.search(pattern, text)
        if not m:
            msg = 'Cannot parse source JavaScript for %s.' % variable
            raise APIError(msg)
        return json.loads(m.group(1).strip())

    def _get_username(self):
        return unquote(self.cookies.get('OOFL'))


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
            if PY3:
                return self.__unicode__()
            else:
                return unicode(self).encode('utf-8')
        return txt_type('%s object' % self.__class__.__name__)


class Passport(Base):
    """
    Passport for user authentication

    :ivar str username: username
    :ivar str password: user password
    :ivar dict form: a dictionary of POST data to login
    :ivar int user_id: user ID of the authenticated user
    :ivar dict data: data returned upon login

    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.form = self._form()
        self.data = None

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
        p = sha1(utf8_encode(self.password)).hexdigest()
        u = sha1(utf8_encode(self.username)).hexdigest()
        v = vcode.upper()
        pu = sha1(utf8_encode(p + u)).hexdigest()
        return sha1(utf8_encode(pu + v)).hexdigest()

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
        self._deleted = False

    def delete(self):
        """
        Delete this file or directory

        :return: whether deletion is successful
        :raise: :class:`.APIError` if this file or directory is already deleted

        """
        fcid = None
        pid = None

        if isinstance(self, File):
            fcid = self.fid
            pid = self.cid
        elif isinstance(self, Directory):
            fcid = self.cid
            pid = self.pid
        else:
            raise APIError('Invalid BaseFile instance.')

        if not self._deleted:
            if self.api._req_rb_delete(fcid, pid):
                self._deleted = True
                return True
        else:
            raise APIError('This file or directory is already deleted.')

    @property
    def is_deleted(self):
        """Whether this file or directory is deleted"""
        return self._deleted

    def __unicode__(self):
        return self.name


class File(BaseFile):
    """
    File in a directory

    :ivar int fid: file id
    :ivar int cid: cid of the current directory
    :ivar int size: size in bytes
    :ivar str size_human: human-readable size
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

    def download(self, path=None, show_progress=True, resume=True,
                 auto_retry=True):
        """Download this file"""
        self.api.download(self, path, show_progress, resume, auto_retry)

    @property
    def is_torrent(self):
        """Whether the file is a torrent"""
        return self.file_type == 'torrent'

    def open_torrent(self):
        """
        Open the torrent (if it is a torrent)

        :return: opened torrent
        :rtype: :class:`.Torrent`
        """
        if self.is_torrent:
            return self.api._load_torrent(self)


class Directory(BaseFile):
    """
    :ivar int cid: cid of this directory
    :ivar int pid: represents the parent directory it belongs to
    :ivar int count: number of entries in this directory
    :ivar datetime.datetime date_created: integer, originally named `t`
    :ivar str pickcode: string, originally named `pc`

    """

    max_entries_per_load = 24  # Smaller than 24 may cause abnormal result

    def __init__(self, api, cid, name, pid, count=-1,
                 date_created=None, pickcode=None, is_root=False,
                 *args, **kwargs):
        super(Directory, self).__init__(api, cid, name)

        self.pid = pid
        self._count = count
        if date_created is not None:
            self.date_created = date_created
        self.pickcode = pickcode
        self._parent = None

    @property
    def is_root(self):
        """Whether this directory is the root directory"""
        return int(self.cid) == 0

    @property
    def parent(self):
        """Parent directory that holds this directory"""
        if self._parent is None:
            if self.pid is not None:
                self._parent = self.api._load_directory(self.pid)
        return self._parent

    @property
    def count(self):
        """Number of entries in this directory"""
        if self._count == -1:
            self.reload()
        return self._count

    def reload(self):
        """
        Reload directory info and metadata

        * `name`
        * `pid`
        * `count`

        """
        r = self.api._req_directory(self.cid)
        self.pid = r['pid']
        self.name = r['name']
        self._count = r['count']

    def _load_entries(self, func, count, page=1, entries=None, **kwargs):
        """
        Load entries

        :param function func: function (:func:`API._req_files` or
            :func:`API._req_search`) that returns entries
        :param int count: number of entries to load. This value should never
            be greater than self.count
        :param int page: page number (starting from 1)

        """
        if entries is None:
            entries = []
        res = \
            func(offset=(page - 1) * self.max_entries_per_load,
                 limit=self.max_entries_per_load,
                 **kwargs)
        loaded_entries = [
            entry for entry in res['data'][:count]
        ]
        total_count = res['count']
        # count should never be greater than total_count
        if count > total_count:
            count = total_count
        if count <= self.max_entries_per_load:
            return entries + loaded_entries
        else:
            cur_count = count - self.max_entries_per_load
            return self._load_entries(
                func=func, count=cur_count, page=page + 1,
                entries=entries + loaded_entries, **kwargs)

    def list(self, count=30, order='user_ptime', asc=False, show_dir=True,
             natsort=True):
        """
        List directory contents

        :param int count: number of entries to be listed
        :param str order: order of entries, originally named `o`. This value
            may be one of `user_ptime` (default), `file_size` and `file_name`
        :param bool asc: whether in ascending order
        :param bool show_dir: whether to show directories
        :param bool natsort: whether to use natural sort

        Return a list of :class:`.File` or :class:`.Directory` objects
        """
        if self.cid is None:
            return False
        kwargs = {}
        # `cid` is the only required argument
        kwargs['cid'] = self.cid
        kwargs['asc'] = 1 if asc is True else 0
        kwargs['show_dir'] = 1 if show_dir is True else 0
        kwargs['natsort'] = 1 if natsort is True else 0
        kwargs['o'] = order
        if self.count <= count:
            # count should never be greater than self.count
            count = self.count
        try:
            entries = self._load_entries(func=self.api._req_files,
                                         count=count, page=1, **kwargs)
        # When natsort=1 and order='file_name', API access will fail
        except RequestFailure as e:
            if natsort is True and order == 'file_name':
                entries = \
                    self._load_entries(func=self.api._req_aps_natsort_files,
                                       count=count, page=1, **kwargs)
            else:
                raise e
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

    :ivar datetime.datetime add_time: added time
    :ivar str file_id: equivalent to `cid` of :class:`.Directory`. This value
        may be None if the task is failed and has no corresponding directory
    :ivar str info_hash: hashed value
    :ivar datetime.datetime last_update: last updated time
    :ivar int left_time: left time ()
    :ivar int move: moving state

        * 0: not transferred
        * 1: transferred
        * 2: partially transferred

    :ivar str name: name of this task
    :ivar int peers: number of peers
    :ivar int percent_done: <=100, originally named `percentDone`
    :ivar int rate_download: download rate (B/s), originally named
        `rateDownload`
    :ivar int size: size of task
    :ivar str size_human: human-readable size
    :ivar int status: status code

        * -1: failed
        * 1: downloading
        * 2: downloaded
        * 4: searching resources

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
        self._directory = None
        self._deleted = False
        self._count = -1

    def delete(self):
        """
        Delete task (does not influence its corresponding directory)

        :return: whether deletion is successful
        :raise: :class:`.TaskError` if the task is already deleted
        """
        if not self._deleted:
            if self.api._req_lixian_task_del(self):
                self._deleted = True
                return True
        raise TaskError('This task is already deleted.')

    @property
    def is_deleted(self):
        return self._deleted

    @property
    def is_transferred(self):
        """
        :return: whether this tasks has been transferred
        :rtype: bool
        """
        return self.move == 1

    @property
    def status_human(self):
        """
        Human readable status

        :return:

            * `DOWNLOADING`: the task is downloading files
            * `BEING TRANSFERRED`: the task is being transferred
            * `TRANSFERRED`: the task has been transferred to downloads \
                    directory
            * `SEARCHING RESOURCES`: the task is searching resources
            * `FAILED`: the task is failed
            * `DELETED`: the task is deleted
            * `UNKNOWN STATUS`

        :rtype: str

        """
        res = None
        if self._deleted:
            return 'DELETED'
        if self.status == 1:
            res = 'DOWNLOADING'
        elif self.status == 2:
            if self.move == 0:
                res = 'BEING TRANSFERRED'
            elif self.move == 1:
                res = 'TRANSFERRED'
            elif self.move == 2:
                res = 'PARTIALLY TRANSFERRED'
        elif self.status == 4:
            res = 'SEARCHING RESOURCES'
        elif self.status == -1:
            res = 'FAILED'
        if res is not None:
            return res
        return 'UNKNOWN STATUS'

    @property
    def directory(self):
        """Corresponding directory to this task"""
        if self._directory is None:
            if self.is_transferred:
                self._directory = self.api._load_directory(self.cid)
        if self._directory is None:
            msg = 'No directory corresponding to this task: Task is %s.' % \
                self.status_human.lower()
            raise TaskError(msg)
        return self._directory

    @property
    def parent(self):
        """Parent directory of the corresponding directory"""
        return self.directory.parent

    @property
    def count(self):
        """Number of entries in the corresponding directory"""
        return self.directory.count

    def list(self, count=30, order='user_ptime', asc=False, show_dir=True):
        """
        List files of the corresponding directory to this task.

        :param int count: number of entries to be listed
        :param str order: originally named `o`
        :param bool asc: whether in ascending order
        :param bool show_dir: whether to show directories

        """
        return self.directory.list(count, order, asc, show_dir)


class Torrent(Base):
    """
    Opened torrent before becoming a task

    :ivar api: associated API object
    :ivar str name: task name, originally named `torrent_name`
    :ivar int size: task size, originally named `torrent_size`
    :ivar str info_hash: hashed value
    :ivar int file_count: number of files included
    :ivar list files: files included (list of :class:`.TorrentFile`),
        originally named `torrent_filelist_web`
    """

    def __init__(self, api, name, size, info_hash, file_count, files=None,
                 *args, **kwargs):
        self.api = api
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
        return False

    @property
    def selected_files(self):
        """List of selected :class:`.TorrentFile` objects of this torrent"""
        return [f for f in self.files if f.selected]

    @property
    def unselected_files(self):
        """List of unselected :class:`TorrentFile` objects of this torrent"""
        return [f for f in self.files if not f.selected]

    def __unicode__(self):
        return self.name


class TorrentFile(Base):
    """
    File in the torrent file list

    :param torrent: the torrent that holds this file
    :type torrent: :class:`.Torrent`
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

    def select(self):
        self.selected = True

    def unselect(self):
        self.selected = False

    def __unicode__(self):
        return '[%s] %s' % ('*' if self.selected else ' ', self.path)


def _instantiate_task(api, kwargs):
    """Create a Task object from raw kwargs"""
    file_id = kwargs['file_id']
    kwargs['file_id'] = file_id if str(file_id).strip() else None
    kwargs['cid'] = kwargs['file_id']
    kwargs['rate_download'] = kwargs['rateDownload']
    kwargs['percent_done'] = kwargs['percentDone']
    kwargs['add_time'] = get_utcdatetime(kwargs['add_time'])
    kwargs['last_update'] = get_utcdatetime(kwargs['last_update'])
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
    kwargs['date_created'] = string_to_datetime(kwargs['t'])
    kwargs['pickcode'] = kwargs['pc']
    kwargs['name'] = kwargs['n']
    kwargs['thumbnail'] = kwargs.get('u')
    kwargs['size'] = kwargs['s']
    del kwargs['ico']
    del kwargs['t']
    del kwargs['pc']
    del kwargs['s']
    if 'u' in kwargs:
        del kwargs['u']
    return File(api, **kwargs)


def _instantiate_directory(api, kwargs):
    kwargs['name'] = kwargs['n']
    kwargs['date_created'] = get_utcdatetime(float(kwargs['t']))
    kwargs['pickcode'] = kwargs.get('pc')
    return Directory(api, **kwargs)


def _instantiate_uploaded_file(api, kwargs):
    kwargs['fid'] = kwargs['file_id']
    kwargs['name'] = kwargs['file_name']
    kwargs['pickcode'] = kwargs['pick_code']
    kwargs['size'] = kwargs['file_size']
    kwargs['sha'] = kwargs['sha1']
    kwargs['date_created'] = get_utcdatetime(kwargs['file_ptime'])
    kwargs['thumbnail'] = None
    _, ft = os.path.splitext(kwargs['name'])
    kwargs['file_type'] = ft[1:]
    return File(api, **kwargs)


def _instantiate_torrent(api, kwargs):
    kwargs['size'] = kwargs['file_size']
    kwargs['name'] = kwargs['torrent_name']
    file_list = kwargs['torrent_filelist_web']
    del kwargs['file_size']
    del kwargs['torrent_name']
    del kwargs['torrent_filelist_web']
    torrent = Torrent(api, **kwargs)
    torrent.files = [_instantiate_torrent_file(torrent, f) for f in file_list]
    return torrent


def _instantiate_torrent_file(torrent, kwargs):
    kwargs['selected'] = True if kwargs['wanted'] == 1 else False
    del kwargs['wanted']
    return TorrentFile(torrent, **kwargs)


class APIError(Exception):
    """General error related to API"""
    def __init__(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        self.content = content
        super(APIError, self).__init__(*args, **kwargs)


class TaskError(APIError):
    """Task has unstable status or no directory operation"""
    pass


class AuthenticationError(APIError):
    """Authentication error"""
    pass


class InvalidAPIAccess(APIError):
    """Invalid and forbidden API access"""
    pass


class RequestFailure(APIError):
    """Request failure"""
    pass


class JobError(APIError):
    """Job running error (request multiple similar jobs simultaneously)"""
    def __init__(self, *args, **kwargs):
        content = kwargs.pop('content', None)
        self.content = content
        if not args:
            msg = 'Your account has a similar job running. Try again later.'
            args = (msg,)
        super(JobError, self).__init__(*args, **kwargs)
