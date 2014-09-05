# -*- coding: utf-8 -*-
import humanize
import requests
import time
from hashlib import sha1
#import pdb
import utils

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.94 Safari/537.36'


class RequestHandler(object):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT

    def get(self, url, params=None):
        r = self.session.get(url, params=params)
        return self._response_parser(r, expect_json=False)

    def post(self, url, data, params=None):
        r = self.session.post(url, data=data, params=params)
        return self._response_parser(r, expect_json=False)

    def send(self, request):
        """Send a formatted API request"""
        r = self.session.request(method=request.method,
                                 url=request.url,
                                 params=request.params,
                                 data=request.data)
        return self._response_parser(r)

    def _response_parser(self, r, expect_json=True):
        """
        :param r: a response object of the Requests library
        :param expect_json: if True, raise APIError if response is not in JSON
            format
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
    def __init__(self, url, method='GET', params=None, data=None):
        self.url = url
        self.method = method
        self.params = params
        self.data = data


class Response(object):
    def __init__(self, state, content):
        self.state = state
        self.content = content


class API(object):
    """
    Request and response interface

    Functions:
        _req_*: send raw requests
        _load_*: usually wrapper of raw requests
    """

    num_tasks_per_page = 30
    web_api_url = 'http://web.api.115.com/files'

    def __init__(self):
        self.passport = None
        self.http = RequestHandler()
        self.signatures = {}
        self._lixian_timestamp = None
        self._downloads_directory = None
        self._torrents_directory = None

    def login(self, username, password):
        passport = Passport(username, password)
        r = self.http.post(passport.login_url, passport.form)
        # Login success
        if r.state is True:
            # Bind this passport to API
            self.passport = passport
            passport.data = r.content['data']
            passport.user_id = r.content['data']['USER_ID']
            passport.status = 'LOGGED_IN'
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
        if self.passport is not None and self.passport.user_id is not None:
            params = {'user_id': self.passport.user_id}
            r = self.http.get(self.passport.checkpoint_url, params=params)
            if r.state is False:
                return True
        return False

    def logout(self):
        self.http.get(self.passport.logout_url)
        self.passport.status = 'LOGGED_OUT'

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
            self.signatures['offline_space'] = r.content['sign']
            self._lixian_timestamp = r.content['time']

    def _req_lixian_task_lists(self, page=1):
        url = 'http://115.com/lixian/'
        params = {'ct': 'lixian', 'ac': 'task_lists'}
        if 'offline_space' not in self.signatures:
            self._req_offline_space()
        data = {
            'page': page,
            'uid': self.passport.user_id,
            'sign': self.signatures['offline_space'],
            'time': self._lixian_timestamp,
        }
        req = Request(method='POST', url=url, params=params, data=data)
        res = self.http.send(req)
        if res.state:
            return res.content['tasks']

    def _req_lixian_get_id(self):
        """Get `cid' of lixian space directory"""
        url = 'http://115.com/lixian/'
        params = {
            'ct': 'lixian',
            'ac': 'get_id',
            '_': utils.get_utcdatetime(13)
        }
        req = Request(method='GET', url=url, params=params)
        res = self.http.send(req)
        # res.content should include cid (torrent) and dest_cid (dl)
        return res

    def _req_files(self, cid, offset, limit, o='user_ptime', asc=0, aid=1,
                   show_dir=0, code=None, scid=None, snap=0, natsort=None,
                   source=None):
        params = locals()
        del params['self']
        req = Request(method='GET', url=self.web_api_url, params=params)
        res = self.http.send(req)
        return res

    def _req_directory(self, cid):
        """Return name and pid of by cid"""
        res = self._req_files(cid=cid, offset=0, limit=1)
        if res.state:
            path = res.content['path']
            for d in path:
                if str(d['cid']) == cid:
                    return {'cid': cid, 'name': d['name'], 'pid': d['pid']}

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
        res = self._req_lixian_get_id()
        cid = res.content['cid']
        dest_cid = res.content['dest_cid']
        self._downloads_directory = self._load_directory(dest_cid)
        self._torrents_directory = self._load_directory(cid)

    @property
    def downloads_directory(self):
        if self._downloads_directory is None:
            self._load_lixian_space()
        return self._downloads_directory

    @property
    def torrents_directory(self):
        if self._torrents_directory is None:
            self._load_lixian_space()
        return self._torrents_directory

    def get_tasks(self, count=30):
        return self._load_tasks(count)

    def add_task_bt(self):
        """
        Added a new BT task
        TODO:
            ac=get_id&torrent=1: get cid
            upload?debug: upload torrent file
            ac=torrent: torrent list
            ac=add_task_bt: send selected files

        """
        pass

    def add_task_url(self):
        """Added a new URL task (VIP only)"""
        pass

    def delete_task(self):
        pass


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
        :param api: associated API object
        :param cid: integer
            for file: this represents the directory it belongs to;
            for directory: this represents itself
        :param name: string, originally named `n'

        NOTICE
            cid, fid and pid are in string format at this time
        """
        self.api = api
        self.cid = cid
        self.name = name

    def __unicode__(self):
        return self.name


class File(BaseFile):
    def __init__(self, api, fid, cid, name, size, file_type, sha,
                 date_created, thumbnail, *args, **kwargs):
        super(File, self).__init__(api, cid, name)
        """
        Implemented parameters:
            :param fid: integer, file id
            :param cid: integer, cid of the current directory
            :param size: integer, size in bytes
            :param file_type: string, originally named `ico'
            :param sha: string, sha1 hash
            :param date_created: string, in "%Y-%m-%d %H:%M:%S" format
            :param thumbnail: string, URL

        Exhaustive original parameters:
            "aid": 1,
            "c": 0,
            "d": 1,
            "de": "",
            "e": "",
            "epos": "",
            "et": 0,
            "hdf": 0,
            "ico": "avi",
            "iv": 1,
            "m": 0,
            "n": "gepao.avi",
            "p": 0,
            "pc": "cm51cq8s1dfy0e4jl",
            "pt": "0",
            "q": 0,
            "s": 1122427036,
            "sh": 0,
            "sha": "A1915585290B9DDE0AE86A632C4B38E38C2C8FB",
            "sta": 1,
            "t": "2014-09-02 13:39",
            "u":
            "http://static.115.com/video/A1915585290B9DDE0AE86A632C4B38E38C2C8FB.jpg",
            "uid": 334902641
        """
        self.fid = fid
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.file_type = file_type
        self.sha = sha
        self.date_created = utils.string_to_datetime(date_created)
        self.thumbnail = thumbnail
        self._directory = None

    @property
    def directory(self):
        if self._directory is None:
            self._directory = self.api._load_directory(self.cid)
        return self._directory


class Directory(BaseFile):
    max_num_entries_per_load = 30

    def __init__(self, api, cid, name, pid, date_created=None,
                 *args, **kwargs):
        super(Directory, self).__init__(api, cid, name)
        """
        :param pid: integer, represents the parent directory it belongs to
        :param date_created: integer, originally named `t'

        """
        self.pid = pid
        if date_created is not None:
            self.date_created = utils.get_utcdatetime(date_created)
        self._parent = None

    @property
    def parent(self):
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
            _instantiate_task(self, t) for t in
            self.api._req_files(cid=self.cid,
                                offset=page,
                                limit=self.max_num_entries_per_load,
                                order=order,
                                asc=asc)[:self.max_num_entries_per_load]
        ]
        if count <= self.max_num_entrie_per_load:
            return entries + loaded_entries
        else:
            return self._load_entries(count - self.max_num_entries_per_load,
                                      page + 1, order, asc,
                                      loaded_entries + entries)

    def list(self, offset=0, limit=30, order='user_ptime', asc=False):
        """
        Required params:
            :param directory: a Directory object to be listed

        Implemented optional params:
            :param order: string, originally named `o'
            :param offset: integer
            :param limit: integer
            :param asc: boolean

        Exhaustive optional params:
            aid: 1
            o: user_ptime
            asc: 0
            offset: 1
            show_dir: 0
            limit: 2
            code:
            scid:
            snap: 0
            natsort: 1
            source:

        Return a list of File or Directory objects
        """
        asc = 1 if asc is True else 0
        res = self.api._req_files(self.cid, offset, limit, order, asc)
        if res.state:
            entries = res.content['data']
            res = []
            for entry in entries:
                if 'pid' in entry:
                    res.append(_instantiate_directory(self.api, entry))
                else:
                    res.append(_instantiate_file(self.api, entry))
            return res


class Task(Directory):
    def __init__(self, api, add_time, file_id, info_hash, last_update,
                 left_time, move, name, peers, percent_done, rate_download,
                 size, status, cid, pid):
        super(Task, self).__init__(api, cid, name, pid)

        """
        :param add_time: integer to datetiem object
        :param file_id: string, equivalent to `cid' in File of directory type
        :param info_hash: string
        :param last_update: integer to datetime object
        :param left_time: integer
        :param move: integer
        :param name: string
        :param peers: integer
        :param percent_done: integer (<=100), originally named `percentDone'
        :param rate_download: integer, originally named `rateDownload'
        :param size: integer
        :param status: integer
        """
        self.add_time = utils.get_utcdatetime(add_time)
        self.file_id = file_id
        self.info_hash = info_hash
        self.last_update = utils.get_utcdatetime(last_update)
        self.left_time = left_time
        self.move = move
        self.peers = peers
        self.percent_done = percent_done
        self.rate_download = rate_download
        self.size = size
        self.size_human = humanize.naturalsize(size, binary=True)
        self.status = status

    def is_transferred(self):
        return self.move == 1

    @property
    def status_human(self):
        if self.status == 2:
            if self.move == 0:
                return 'BEING TRANSFERRED'
            elif self.move == 1:
                return 'TRANSFERRED'
        return 'UNKNOWN STATUS'

    def __unicode__(self):
        return self.name


def _instantiate_task(api, kwargs):
    """Create a Task object from raw kwargs

    rateDownload => rate_download
    percentDone => percent_done
    """
    kwargs['rate_download'] = kwargs['rateDownload']
    kwargs['percent_done'] = kwargs['percentDone']
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
    """
    ico => file_type
    t => date_created
    n => name
    """
    print kwargs
    kwargs['file_type'] = kwargs['ico']
    kwargs['date_created'] = kwargs['t']
    kwargs['name'] = kwargs['n']
    kwargs['thumbnail'] = kwargs['u']
    kwargs['size'] = kwargs['s']
    return File(api, **kwargs)


def _instantiate_directory(api, kwargs):
    """
    n => name
    t => date_created
    u => thumbnail
    """
    kwargs['name'] = kwargs['n']
    kwargs['date_created'] = kwargs['t']
    return Directory(api, **kwargs)


class APIError(Exception):
    pass
