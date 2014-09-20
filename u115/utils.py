from __future__ import print_function, absolute_import
import datetime
import os
import six
import sys
import time
import pycurl
from requests.utils import quote as _quote
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
        '%(percent)10d%% %(downloaded)10s %(speed)15s %(eta)15s ETA\r'
    eta_limit = 2592000  # 30 days

    def __init__(self, url, path=None, session=None, show_progress=True):
        """
        :param str url: URL of the file to be downloaded
        :param str path: local path for the downloaded file; if None, it will
            be the URL base name
        :param session: session used to download
        :type session: `class:requests.Session`
        :param bool show_progress: whether to show download progress
        """
        self.url = url
        self.path = self._get_path(path)
        self.session = session
        self.show_progress = show_progress
        self.start_time = None
        self._cookie_header = self._get_cookie_header()

    def __del__(self):
        self.done()

    def _get_cookie_header(self):
        if self.session is not None:
            cookie = dict(self.session.cookies)
            res = []
            for k, v in cookie.iteritems():
                s = '%s=%s' % (k, v)
                res.append(s)
            if not res:
                return None
            return '; '.join(res)

    def _get_path(self, path=None):
        if path is None:
            o = urlparse(self.url)
            path = os.path.basename(o.path)
            return path
        else:
            return eval_path(path)

    def curl(self):
        """Sending cURL request to download"""
        with open(self.path, 'wb') as f:
            c = pycurl.Curl()
            c.setopt(c.URL, self.url)
            c.setopt(c.WRITEDATA, f)
            c.setopt(c.NOPROGRESS, 0)
            if self._cookie_header is not None:
                h = 'Cookie: %s' % self._cookie_header
                c.setopt(pycurl.HTTPHEADER, [h])
            c.setopt(c.PROGRESSFUNCTION, self.progress)
            c.perform()

    def progress(self, download_t, download_d, upload_t, upload_d):
        if int(download_t) == 0:
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
        if int(download_d) == 0:
            download_d == 0.01
        download_ds = naturalsize(download_d, binary=True)
        params = {
            'downloaded': download_ds,
            'percent': int(download_d / download_t * 100),
            'speed': speed_s,
            'eta': eta_s,
        }
        p = self.progress_template % params
        sys.stderr.write(p)
        sys.stderr.flush()

    def done(self):
        sys.stderr.write('\n')
        sys.stderr.flush()


def download(url, path=None, session=None, show_progress=True):
    """Download using download manager"""
    dm = DownloadManager(url, path, session, show_progress)
    dm.curl()
