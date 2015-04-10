# -*- coding: utf-8 -*-
import datetime
import os
import sys
import time
from unittest import TestCase
from u115.api import API, Torrent, Directory, File, TaskError
from u115.utils import pjoin
from u115 import conf

PY3 = sys.version_info[0] == 3
if PY3:
    from unittest.mock import Mock
else:
    from mock import Mock


LARGE_COUNT = 999
SMALL_COUNT = 2
TEST_DIR = pjoin(conf.PROJECT_PATH, 'tests')
DATA_DIR = pjoin(TEST_DIR, 'data')

# This torrent's directory contains a single file
TEST_TORRENT1 = {
    'filename': pjoin(DATA_DIR, u'SAOII_10.torrent'),
    'info_hash': '6bcc605d8fd8629b4df92202d554e5812e78df25',
}

# This torrent's directory contains files and directories
# - BK/
#   - (11 files)
# - MP3/
#   - Disc_1/
#     - (23 files)
#   - Disc_2/
#     - (19 files)
# - Cover.jpg

TEST_TORRENT2 = {
    'filename': pjoin(DATA_DIR, u'Rozen_Maiden_OST.torrent'),
    'info_hash': 'd1fc55cc7547881884d01c56ffedd92d39d48847',
}

# This HTTP url has no associated directory
TEST_TARGET_URL1 = {
    'url': 'http://download.thinkbroadband.com/1MB.zip',
    'info_hash': '5468537b4e05bd8f69bfe17e59e7ad85115',
}

# This Magnet url has an associated directory
TEST_TARGET_URL2 = {
    'url': open(pjoin(DATA_DIR, 'magnet.txt')).read().strip(),
    'info_hash': '1f9f293e5e4ef63eba76d3485fe54577737df0e8',
}
TEST_COOKIE_FILE = pjoin(DATA_DIR, '115cookies')
TASK_TRANSFERRED_TIMEOUT = 60


def is_task_created(tasks, info_hash):
    """
    Check if a task is created against a hash value

    :param list tasks: a list of :class:`API.Task` objects
    :param str info_hash: hash value of the target task

    """
    for task in tasks:
        if task.info_hash == info_hash:
            return True
    else:
        return False


def wait_task_transferred(task):
    """
    Wait until a 'BEING TRANSFERRED' task transferred
    """
    seconds = 0
    if (task.status_human != 'TRANSFERRED' or
            task.status_human == 'BEING TRANSFERRED'):
        raise Exception('Task cannot be transferred.')
    while (task.status_human == 'BEING TRANSFERRED' and
           seconds < TASK_TRANSFERRED_TIMEOUT):
        time.sleep(5)
        seconds += 5
    if (seconds == TASK_TRANSFERRED_TIMEOUT and
            task.status_human != 'TRANSFERRED'):
        raise Exception('Task transferred timeout.')


class TaskTests(TestCase):
    """Test general task interface"""
    def setUp(self):
        # Initialize a new API instance
        self.api = API()
        self.api.login(section='test')

    def test_get_tasks(self):
        filename1 = TEST_TORRENT1['filename']
        filename2 = TEST_TORRENT2['filename']
        url1 = TEST_TARGET_URL1['url']
        url2 = TEST_TARGET_URL2['url']
        # Test creation
        assert self.api.add_task_bt(filename1)
        assert self.api.add_task_bt(filename2)
        assert self.api.add_task_url(url1)
        assert self.api.add_task_url(url2)
        # Test count
        tasks = self.api.get_tasks()
        assert len(tasks) == 4
        tasks = self.api.get_tasks(3)
        assert len(tasks) == 3

    def test_task_attrs(self):
        filename1 = TEST_TORRENT1['filename']
        url1 = TEST_TARGET_URL1['url']
        assert self.api.add_task_bt(filename1)
        assert self.api.add_task_url(url1)
        tasks = self.api.get_tasks()
        for task in tasks:
            assert isinstance(task.add_time, datetime.datetime)
            assert isinstance(task.last_update, datetime.datetime)
            assert isinstance(task.left_time, int)
            assert task.name
            assert task.move in [0, 1, 2]
            assert task.peers >= 0
            assert task.percent_done >= 0
            assert task.size >= 0
            assert task.size_human
            assert isinstance(task.status, int)
            assert task.status_human

    def tearDown(self):
        # Clean up all tasks
        tasks = self.api.get_tasks()
        for task in tasks:
            task.delete()


class BitTorrentTaskTests(TestCase):
    """
    Test torrent-based BitTorrent tasks
    """
    def setUp(self):
        # Initialize a new API instance
        self.api = API()
        self.api.login(section='test')

    def test_add_task_bt_select_false(self):
        """
        `API.add_task_bt(filename, select=False)`
        """
        filename = TEST_TORRENT1['filename']
        info_hash = TEST_TORRENT1['info_hash']
        assert self.api.add_task_bt(filename)
        tasks = self.api.get_tasks()
        assert is_task_created(tasks, info_hash)

    def test_add_task_bt_select_true(self):
        """
        `API.add_task_bt(filename, select=True)`
        """
        filename = TEST_TORRENT2['filename']
        info_hash = TEST_TORRENT2['info_hash']
        torrent = self.api.add_task_bt(filename, select=True)
        assert isinstance(torrent, Torrent)
        torrent.files[0].unselect()
        torrent.files[1].unselect()
        assert len(torrent.selected_files) == torrent.file_count - 2
        assert torrent.submit()
        tasks = self.api.get_tasks()
        assert is_task_created(tasks, info_hash)

    def test_delete_tasks(self):
        """
        `Task.delete()`
        """
        filename = TEST_TORRENT2['filename']
        info_hash = TEST_TORRENT2['info_hash']
        assert self.api.add_task_bt(filename)
        tasks = self.api.get_tasks()
        is_task_created = False
        for task in tasks:
            if task.info_hash == info_hash:
                is_task_created = True
                assert not task.is_deleted
                assert task.delete()
                with self.assertRaises(TaskError) as cm:
                    task.delete()
                assert cm.exception.message == 'This task is already deleted.'
                assert task.is_deleted
                break
        else:
            assert is_task_created

    def tearDown(self):
        # Clean up all tasks
        tasks = self.api.get_tasks()
        for task in tasks:
            task.delete()


class URLTaskTests(TestCase):
    def setUp(self):
        # Initialize a new API instance
        self.api = API()
        self.api.login(section='test')

    def test_add_task_url_http(self):
        """
        `API.add_task_url(target_url=HTTP)`
        """
        url = TEST_TARGET_URL1['url']
        info_hash = TEST_TARGET_URL1['info_hash']
        assert self.api.add_task_url(url)
        tasks = self.api.get_tasks()
        is_task_created(tasks, info_hash)

    def test_add_task_url_magnet(self):
        """
        `API.add_task_url(target_url=MAGNET)`
        """
        url = TEST_TARGET_URL2['url']
        info_hash = TEST_TARGET_URL2['info_hash']
        assert self.api.add_task_url(url)
        tasks = self.api.get_tasks()
        is_task_created(tasks, info_hash)

    def tearDown(self):
        # Clean up all tasks
        tasks = self.api.get_tasks()
        for task in tasks:
            task.delete()


class DownloadsDirectoryTests(TestCase):
    """
    Test tasks and files within the downloads directory
    """
    def setUp(self):
        # Initialize a new API instance
        self.api = API()
        self.api.login(section='test')
        # Clean up all files in the downloads directory
        downloads_directory = self.api.downloads_directory
        entries = downloads_directory.list()
        for entry in entries:
            entry.delete()

    def test_transferred_task_directories(self):
        """
        Test the task with an associated directory
        """
        filename = TEST_TORRENT2['filename']
        info_hash = TEST_TORRENT2['info_hash']
        assert self.api.add_task_bt(filename)
        tasks = self.api.get_tasks()
        # Get the target task as `task`
        task = None
        for _task in tasks:
            if _task.info_hash == info_hash:
                task = _task
                break
        assert task
        # Wait until the task is transferred
        # Task.reload() must be implemented before wait_task_transferred()
        # can be used here
        #wait_task_transferred(task)
        assert task.status_human == 'TRANSFERRED'
        task_directory = task.directory
        entries = task_directory.list()
        dirs = []
        files = []
        for entry in entries:
            if isinstance(entry, File):
                files.append(entry)
            elif isinstance(entry, Directory):
                dirs.append(entry)
        assert len(dirs) == 2
        assert len(files) == 1
        for directory in dirs:
            if directory.name == 'BK':
                assert directory.count == 11
                assert len(directory.list()) == 11
            if directory.name == 'MP3':
                assert directory.count == 2
                assert len(directory.list()) == 2

    def tearDown(self):
        # Clean up all tasks
        tasks = self.api.get_tasks()
        for task in tasks:
            task.delete()
        # Clean up all files in the downloads directory
        downloads_directory = self.api.downloads_directory
        entries = downloads_directory.list()
        for entry in entries:
            entry.delete()


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
        time.sleep(5)  # Avoid 'Task is being transferred'
        task_count = self.api.task_count
        tasks = self.api.get_tasks(LARGE_COUNT)
        self.assertEqual(len(tasks), task_count)
        tasks = self.api.get_tasks(SMALL_COUNT)
        self.assertEqual(len(tasks), SMALL_COUNT)
        t = None
        for tt in tasks:
            if isinstance(tt, Directory):
                t = tt
                break
        else:
            return
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
                d2 = d1.list()[0]
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

    def test_search(self):
        """Directory is assumed to have more than 40 torrent files"""
        keyword = 'torrent'
        s1 = self.api.search(keyword)
        assert len(s1) == 30
        s2 = self.api.search(keyword, 10)
        assert len(s2) == 10
        s3 = self.api.search(keyword, 40)
        assert len(s3) == 40


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


class TestCookies(TestCase):
    def setUp(self):
        if os.path.exists(TEST_COOKIE_FILE):
            os.remove(TEST_COOKIE_FILE)
        self.api = API(auto_logout=False, persistent=True,
                       cookies_filename=TEST_COOKIE_FILE)
        self.api.login(section='test')

    def test_cookies(self):
        self.api.__del__()
        self.api = API(auto_logout=False, persistent=True,
                       cookies_filename=TEST_COOKIE_FILE)
        assert self.api.has_logged_in
