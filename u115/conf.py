# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, absolute_import

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import os
from u115.utils import pjoin, eval_path

_d = os.path.dirname(__file__)
user_dir = eval_path('~')
PROJECT_PATH = os.path.abspath(pjoin(_d, os.pardir))
PROJECT_CREDENTIALS = pjoin(PROJECT_PATH, '.credentials')
USER_CREDENTIALS = pjoin(user_dir, '.115')
CREDENTIALS = None

if os.path.exists(PROJECT_CREDENTIALS):
    CREDENTIALS = PROJECT_CREDENTIALS
elif os.path.exists(USER_CREDENTIALS):
    CREDENTIALS = USER_CREDENTIALS

config = configparser.ConfigParser()


def get_credential(section='default'):
    if CREDENTIALS is not None:
        config.read(CREDENTIALS)
        if config.has_section(section):
            items = dict(config.items(section))
            try:
                username = items['username']
                password = items['password']
            except KeyError as e:
                msg = 'Key "%s" not found in credentials file.' % e.args[0]
                raise ConfigError(msg)
        else:
            msg = 'No section named "%s" found in credentials file.' % section
            raise ConfigError(msg)
    else:
        msg = 'No credentials file found.'
        raise ConfigError(msg)
    return {'username': username, 'password': password}


class ConfigError(Exception):
    pass
