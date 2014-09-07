from unittest import TestCase
from u115 import API
from u115 import conf


class TestAPI(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAPI, self).__init__(*args, **kwargs)
        self.api = API()

    def test_login(self):
        credential = conf.get_credential('test')
        username = credential['username']
        password = credential['password']
        assert self.api.login(username, password)
        assert self.api.logout()

    def test_login_credentials(self):
        assert self.api.login(section='test')
