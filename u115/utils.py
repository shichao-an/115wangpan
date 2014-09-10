from __future__ import print_function, absolute_import
import datetime
import os
import six
import sys
import time
from requests.utils import quote as _quote


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

PY3 = sys.version_info[0] == 3

if PY3:
    import codecs
    from io import BytesIO as StringIO
    # return s converted to binary.  b('test') should be equivalent to b'test'
    def b(s):
        return codecs.latin_1_encode(s)[0]

    bin_type = bytes
    txt_type   = str
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

    # Conversion to binary only necessary in Python 3
    def b(s):
        return s

    bin_type = str
    txt_type = unicode

str_types = (bin_type, txt_type)
