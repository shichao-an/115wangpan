from __future__ import print_function, absolute_import
import datetime
import errno
import os
import six
import sys
import time
from requests.utils import quote as _quote
from requests.utils import unquote as _unquote

PY3 = sys.version_info[0] == 3
STREAM = sys.stderr
STRPTIME_FORMATS = ['%Y-%m-%d %H:%M', '%Y-%m-%d']

if PY3:
    bin_type = bytes
    txt_type = str
else:
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
    for f in STRPTIME_FORMATS:
        try:
            return datetime.datetime.strptime(s, f)
        except ValueError:
            pass
    msg = 'Time data %s does not match any formats in %s' \
        % (s, STRPTIME_FORMATS)
    raise ValueError(msg)


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


def mkdir_p(path):
    """mkdir -p path"""
    if PY3:
        return os.makedirs(path, exist_ok=True)
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
