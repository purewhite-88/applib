"""
@Author: kang.yang
@Date: 2023/10/26 09:48
"""
import time

from .driver import Driver
from .remote_driver import RemoteDriver

from kyapp.running.conf import App
from kyapp.utils.log import logger

class TestCase:
    """
    测试用例基类，所有测试用例需要继承该类
    """

    dr = None

    # ---------------------初始化-------------------------------
    def start_class(self):
        """
        Hook method for setup_class fixture
        :return:
        """
        pass

    def end_class(self):
        """
        Hook method for teardown_class fixture
        :return:
        """
        pass

    @classmethod
    def setup_class(cls):
        try:
            cls().start_class()
        except BaseException as e:
            logger.error(f"start_class Exception: {e}")

    @classmethod
    def teardown_class(cls):
        try:
            cls().end_class()
        except BaseException as e:
            logger.error(f"end_class Exception: {e}")

    def start(self):
        """
        Hook method for setup_method fixture
        :return:
        """
        pass

    def end(self):
        """
        Hook method for teardown_method fixture
        :return:
        """
        pass

    def setup_method(self):

        # 驱动初始化
        if App.sonic_host is not None:
            self.dr = RemoteDriver(
                serial=App.did,
                package=App.pkg,
                sonic_host=App.sonic_host,
                sonic_user=App.sonic_user,
                sonic_pwd=App.sonic_pwd
            )
        else:
            self.dr = Driver(
                serial=App.did,
                package=App.pkg
            )
        # 解锁设备
        self.dr.unlock()

        self.start()

    def teardown_method(self):
        self.end()
        if isinstance(self.dr, RemoteDriver):
            self.dr.close()

    # 公共方法
    @staticmethod
    def sleep(n: float):
        logger.info(f"暂停: {n}s")
        time.sleep(n)

    def shot(self, name: str, delay=0):
        if delay:
            self.sleep(delay)
        self.dr.shot(name)

    def start_app(self, force=True):
        if force:
            self.stop_app()
        self.dr.start_app()

    def stop_app(self):
        self.dr.stop_app()


