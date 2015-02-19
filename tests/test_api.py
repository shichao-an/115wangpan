# -*- coding: utf-8 -*-
import time
from unittest import TestCase
from u115.api import API, Torrent, Directory, File, TaskError, RequestFailure
from u115.utils import pjoin
from u115 import conf


LARGE_COUNT = 999
SMALL_COUNT = 2
TEST_DIR = pjoin(conf.PROJECT_PATH, 'tests')
DATA_DIR = pjoin(TEST_DIR, 'data')
TEST_TORRENT1 = {
    'filename': pjoin(DATA_DIR, u'SAOII_10.torrent'),
    'info_hash': '6bcc605d8fd8629b4df92202d554e5812e78df25',
}

TEST_TORRENT2 = {
    'filename': pjoin(DATA_DIR, u'Rozen_Maiden_OST.torrent'),
    'info_hash': 'd1fc55cc7547881884d01c56ffedd92d39d48847',
}

TEST_TARGET_URL = 'http://download.thinkbroadband.com/1MB.zip'


class TestAPI(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestAPI, self).__init__(*args, **kwargs)
        self.api = API()
        self.api.login(section='test')

    def test_storage_info(self):
        res = self.api.get_storage_info()
        assert 'total' in res
        assert 'used' in res

        res = self.api.get_storage_info(human=True)
        assert 'total' in res
        assert 'used' in res

    def test_tasks_directories(self):
        time.sleep(5)
        task_count = self.api.task_count
        tasks = self.api.get_tasks(LARGE_COUNT)
        self.assertEqual(len(tasks), task_count)
        tasks = self.api.get_tasks(SMALL_COUNT)
        self.assertEqual(len(tasks), SMALL_COUNT)
        t = tasks[0]
        dd = self.api.downloads_directory
        if t.status_human == 'TRANSFERRED':
            d = t.directory
            p = t.parent
            assert d.parent is p
            assert p.cid == dd.cid
            assert t.count == len(t.list(LARGE_COUNT))
        for t in tasks:
            if t.info_hash == TEST_TORRENT2['info_hash']:
                td = t.directory
                entries = td.list()
                for entry in entries:
                    if isinstance(entry, Directory):
                        entry.list()
                    elif isinstance(entry, File):
                        assert entry.url

    def test_delete_file(self):
        tasks = self.api.get_tasks()
        for t in tasks:
            if t.info_hash == TEST_TORRENT2['info_hash']:
                # Delete file
                try:
                    d1 = t.directory
                except TaskError:
                    time.sleep(20)
                try:
                    d1 = t.directory
                except TaskError:
                    return
                d1_count = d1.count
                d2 = d1.list()[1]
                d2_count = d2.count
                files = d2.list()
                f1 = files[0]
                assert f1.delete()
                d2.reload()
                assert d2.count == d2_count - 1
                # Sleep to avoid JobError
                time.sleep(2)
                assert d2.delete()
                d1.reload()
                assert d1.count == d1_count - 1

    def test_add_delete_task_bt(self):
        h1 = TEST_TORRENT1['info_hash']
        h2 = TEST_TORRENT2['info_hash']
        tasks = self.api.get_tasks(LARGE_COUNT)
        for task in tasks:
            if task.info_hash == h1:
                assert task.delete()
            if task.info_hash == h2:
                assert task.delete()
        assert self.api.add_task_bt(TEST_TORRENT1['filename'])
        u = self.api.add_task_bt(TEST_TORRENT2['filename'], select=True)
        assert isinstance(u, Torrent)
        files = u.files
        file_count = u.file_count
        files[0].unselect()
        files[1].unselect()
        assert len(u.selected_files) == file_count - 2
        assert u.submit()

    def test_add_task_url(self):
        '''
        NOT FINISHED YET!
        TODO:
            * Check the target_url is not in the task list already.
            * add the target_url
            * checked it added successfully
        '''
        try:
            self.api.add_task_url(TEST_TARGET_URL)
        except RequestFailure:
            pass


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
