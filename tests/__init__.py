from unittest import TestCase
from u115 import API
from u115 import conf

LARGER_THAN_TASK_COUNT = 999
SMALLER_THAN_TASK_COUNT = 5
LARGER_THAN_DIR_COUNT = 999


class TestAPI(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAPI, self).__init__(*args, **kwargs)
        self.api = API()
        self.api.login(section='test')

    def test_login_logout(self):
        credential = conf.get_credential('test')
        username = credential['username']
        password = credential['password']
        if self.api.has_logged_in:
            assert self.api.logout()
        assert self.api.login(username, password)

    def test_login_credentials(self):
        if self.api.has_logged_in:
            assert self.api.logout()
        assert self.api.login(section='test')

    def test_tasks_directories(self):
        task_count = self.api.task_count
        tasks = self.api.get_tasks(LARGER_THAN_TASK_COUNT)
        self.assertEqual(len(tasks), task_count)
        tasks = self.api.get_tasks(SMALLER_THAN_TASK_COUNT)
        self.assertEqual(len(tasks), SMALLER_THAN_TASK_COUNT)
        t = tasks[0]
        dd = self.api.downloads_directory
        if t.status_human == 'TRANSFERRED':
            d = t.directory
            p = t.parent
            assert d.parent is p
            assert p.cid == dd.cid
            assert t.count == len(t.list(LARGER_THAN_DIR_COUNT))

    def test_storage_info(self):
        res = self.api.get_storage_info()
        assert 'total' in res
        assert 'used' in res

        res = self.api.get_storage_info(human=True)
        assert 'total' in res
        assert 'used' in res


class TestPrivateAPI(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestPrivateAPI, self).__init__(*args, **kwargs)
        self.api = API()
        self.api.login(section='test')

    def test_req_offline_space(self):
        self.api._signatures = {}
        self.api._lixian_timestamp = None
        func = getattr(self.api, '_req_offline_space')
        func()
        assert 'offline_space' in self.api._signatures
        assert self.api._lixian_timestamp is not None

    def test_load_upload_url(self):
        url = self.api._load_upload_url()
        assert url
