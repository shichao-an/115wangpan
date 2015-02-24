# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

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
COOKIES_FILENAME = pjoin(user_dir, '.115cookies')

if os.path.exists(PROJECT_CREDENTIALS):
    CREDENTIALS = PROJECT_CREDENTIALS
elif os.path.exists(USER_CREDENTIALS):
    CREDENTIALS = USER_CREDENTIALS

config = configparser.ConfigParser()


def get_credential(section='default'):
    if os.environ.get('TRAVIS_TEST'):
        username = os.environ.get('TEST_USER_USERNAME')
        password = os.environ.get('TEST_USER_PASSWORD')
        if username is None or password is None:
            msg = 'No credentials environment variables found.'
            raise ConfigError(msg)
    elif CREDENTIALS is not None:
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
