# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import os
import logging
from u115.utils import pjoin, eval_path

_d = os.path.dirname(__file__)
user_dir = eval_path('~')
PROJECT_PATH = os.path.abspath(pjoin(_d, os.pardir))
PROJECT_CREDENTIALS = pjoin(PROJECT_PATH, '.credentials')
USER_CREDENTIALS = pjoin(user_dir, '.115')
CREDENTIALS = None
COOKIES_FILENAME = pjoin(user_dir, '.115cookies')

LOGGING_API_LOGGER = 'API'
LOGGING_FORMAT = "%(levelname)s:%(name)s:%(funcName)s: %(message)s"
LOGGING_LEVEL = logging.ERROR
DEBUG_REQ_FMT = """
  TYPE: Request
  FUNC: %s
   URL: %s
METHOD: %s
PARAMS: %s
  DATA: %s
"""

DEBUG_RES_FMT = """
   TYPE: Response
   FUNC: %s
  STATE: %s
CONTENT: %s
"""

# Initialize logger
logger = logging.getLogger(LOGGING_API_LOGGER)
handler = logging.StreamHandler()
formatter = logging.Formatter(LOGGING_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(LOGGING_LEVEL)

if os.path.exists(PROJECT_CREDENTIALS):
    CREDENTIALS = PROJECT_CREDENTIALS
elif os.path.exists(USER_CREDENTIALS):
    CREDENTIALS = USER_CREDENTIALS

CONFIG = configparser.ConfigParser()


def get_credential(section='default'):
    if os.environ.get('TRAVIS_TEST'):
        username = os.environ.get('TEST_USER_USERNAME')
        password = os.environ.get('TEST_USER_PASSWORD')
        if username is None or password is None:
            msg = 'No credentials environment variables found.'
            raise ConfigError(msg)
    elif CREDENTIALS is not None:
        CONFIG.read(CREDENTIALS)
        if CONFIG.has_section(section):
            items = dict(CONFIG.items(section))
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
