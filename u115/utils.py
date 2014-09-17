from __future__ import print_function, absolute_import
import datetime
import os
import six
import sys
import time
import requests
from requests.utils import quote as _quote
from clint.textui import progress

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


def download(url, path=None, session=None, chunk_size=1024):
    """Download a file, typically very large, showing progress"""
    if session is not None:
        r = session.get(url, stream=True)
    else:
        r = requests.get(url, stream=True)
    if r.ok:
        if path is None:
            o = urlparse(url)
            path = os.path.basename(o.path)
        total_length = int(r.headers.get('content-length'))
        if total_length > 1024 * 1024:
            chunk_size = 1024 * 1024
        expected_size = total_length / chunk_size + 1
        label = '(KB)'
        if chunk_size == 1024 * 1024:
            label = '(MB)'
        with open(path, 'wb') as f:
            for chunk in progress.bar(r.iter_content(chunk_size=chunk_size),
                                      expected_size=expected_size,
                                      label=label):
                if chunk:
                    f.write(chunk)
    else:
        r.raise_for_status()
