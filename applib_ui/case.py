import time

import pytest

from .running.conf import App
from .utils.log import logger


class TestCase:
    """pytest 测试基类；也可以直接在测试函数中使用 app_driver fixture。"""

    dr = None

    def start_class(self):
        pass

    def end_class(self):
        pass

    @classmethod
    def setup_class(cls):
        cls().start_class()

    @classmethod
    def teardown_class(cls):
        cls().end_class()

    def start(self):
        pass

    def end(self):
        pass

    @pytest.fixture(autouse=True)
    def _app_lifecycle(self, app_driver):
        self.dr = app_driver
        try:
            if getattr(self, '_platform', None) is not None:
                self.dr.unlock()
            self.start()
            yield
        finally:
            self.end()

    @staticmethod
    def sleep(n: float):
        logger.info(f"暂停: {n}s")
        time.sleep(n)

    def shot(self, name: str, delay=0):
        if delay:
            self.sleep(delay)
        return self.dr.shot(name)

    def start_record(self, video_name='record'):
        """开始录屏"""
        return self.dr.start_record(video_name)

    def stop_record(self):
        """结束录屏并上传 allure"""
        return self.dr.stop_record()

    def start_app(self, force=True, activity=None, use_monkey=False):
        if force:
            self.stop_app()
        if App.platform == 'ios':
            self.dr.start_app()
        elif activity is not None:
            self.dr.start_app(activity=activity)
        elif use_monkey:
            self.dr.start_app(use_monkey=True)
        else:
            self.dr.start_app()

    def stop_app(self):
        self.dr.stop_app()

    def back(self):
        self.dr.back()
