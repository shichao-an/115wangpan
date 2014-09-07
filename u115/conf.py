import ConfigParser
import os

_d = os.path.dirname(__file__)
user_dir = os.path.join(os.path.expanduser('~'))
project_path = os.path.abspath(os.path.join(_d, os.pardir))
project_credentials = os.path.join(project_path, '.credentials')
user_credentials = os.path.join(user_dir, '.115')

credentials = None

if os.path.exists(project_credentials):
    credentials = project_credentials
elif os.path.exists(user_credentials):
    credentials = user_credentials

config = ConfigParser.ConfigParser()


def get_credential(section='default'):
    if credentials is not None:
        config.read(credentials)
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
