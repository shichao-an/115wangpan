from __future__ import print_function, absolute_import
import datetime
import os
import six
import sys
import time
import pycurl
from requests.utils import quote as _quote
from requests.utils import unquote as _unquote
from humanize import naturalsize

PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.parse import urlparse
    bin_type = bytes
    txt_type = str
else:
    from urlparse import urlparse
    bin_type = str
    txt_type = unicode

str_types = (bin_type, txt_type)


def get_timestamp(length):
    """Get a timestamp of `length` in string"""
    s = '%.6f' % time.time()
    whole, frac = map(int, s.split('.'))
    res = '%d%d' % (whole, frac)
    return res[:length]


def get_utcdatetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp)


def string_to_datetime(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")


def eval_path(path):
    return os.path.abspath(os.path.expanduser(path))


def quote(s):
    res = s
    if isinstance(res, six.text_type):
        res = s.encode('utf-8')
    return _quote(res)


def unquote(s):
    res = s
    if not PY3:
        if isinstance(res, six.text_type):
            res = s.encode('utf-8')
    return _unquote(res)


def utf8_encode(s):
    res = s
    if isinstance(res, six.text_type):
        res = s.encode('utf-8')
    return res


def pjoin(*args):
    """Short cut for os.path.join"""
    return os.path.join(*args)


class DownloadManager(object):
    """Donwload manager that displays progress"""
    progress_template = \
        '%(percent)6d%% %(downloaded)12s %(speed)15s %(eta)18s ETA\r'
    eta_limit = 2592000  # 30 days

    def __init__(self, url, path=None, session=None, show_progress=True,
                 resume=True, auto_retry=True):
        """
        :param str url: URL of the file to be downloaded
        :param str path: local path for the downloaded file; if None, it will
            be the URL base name
        :param session: session used to download
        :type session: `class:requests.Session`
        :param bool show_progress: whether to show download progress
        :param bool resume: whether to resume download (by
            filename)
        :param bool auto_retry: whether to retry automatically upon closed
            transfer until the file's download is finished
        """
        self.url = url
        self.path = self._get_path(path)
        self.session = session
        self.show_progress = show_progress
        self.resume = resume
        self.auto_retry = auto_retry
        self.start_time = None
        self.content_length = 0
        self.downloaded = 0
        self._cookie_header = self._get_cookie_header()

    def __del__(self):
        self.done()

    def _get_cookie_header(self):
        if self.session is not None:
            cookie = dict(self.session.cookies)
            res = []
            for k, v in cookie.items():
                s = '%s=%s' % (k, v)
                res.append(s)
            if not res:
                return None
            return '; '.join(res)

    def _get_path(self, path=None):
        if path is None:
            o = urlparse(self.url)
            path = os.path.basename(o.path)
            return unquote(path)
        else:
            return eval_path(path)

    def curl(self):
        """Sending cURL request to download"""
        c = pycurl.Curl()
        # Resume download
        if os.path.exists(self.path) and self.resume:
            mode = 'ab'
            self.downloaded = os.path.getsize(self.path)
            c.setopt(pycurl.RESUME_FROM, self.downloaded)
        else:
            mode = 'wb'
        with open(self.path, mode) as f:
            c.setopt(c.URL, self.url)
            c.setopt(c.WRITEDATA, f)
            if self._cookie_header is not None:
                h = 'Cookie: %s' % self._cookie_header
                c.setopt(pycurl.HTTPHEADER, [h])
            c.setopt(c.NOPROGRESS, 0)
            c.setopt(c.PROGRESSFUNCTION, self.progress)
            c.perform()

    def start(self):
        """Start downloading"""
        if not self.auto_retry:
            self.curl()
            return
        while not self.is_finished:
            try:
                self.curl()
            except pycurl.error as e:
                # transfer closed with n bytes remaining to read
                if e.args[0] == 18:
                    pass
                else:
                    raise e

    def progress(self, download_t, download_d, upload_t, upload_d):
        if int(download_t) == 0:
            return
        if self.content_length == 0:
            self.content_length = self.downloaded + int(download_t)
        if not self.show_progress:
            return
        if self.start_time is None:
            self.start_time = time.time()
        duration = time.time() - self.start_time + 1
        speed = download_d / duration
        speed_s = naturalsize(speed, binary=True)
        speed_s += '/s'
        eta = int((download_t - download_d) / speed)
        if eta < self.eta_limit:
            eta_s = str(datetime.timedelta(seconds=eta))
        else:
            eta_s = 'n/a'
        downloaded = self.downloaded + download_d
        downloaded_s = naturalsize(downloaded, binary=True)
        percent = int(downloaded / (self.content_length) * 100)
        params = {
            'downloaded': downloaded_s,
            'percent': percent,
            'speed': speed_s,
            'eta': eta_s,
        }
        p = self.progress_template % params
        sys.stderr.write(p)
        sys.stderr.flush()

    @property
    def is_finished(self):
        if os.path.exists(self.path):
            return self.content_length == os.path.getsize(self.path)

    def done(self):
        sys.stderr.write('\n')
        sys.stderr.flush()


def download(url, path=None, session=None, show_progress=True,
             resume=True, auto_retry=True):
    """Download using download manager"""
    dm = DownloadManager(url, path, session, show_progress, resume, auto_retry)
    dm.start()
