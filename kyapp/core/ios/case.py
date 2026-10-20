"""
@Author: kang.yang
@Date: 2023/10/26 09:48
"""
import time

from .remote_driver import RemoteDriver
from .driver import Driver
from .elem import Elem

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
                udid=App.did,
                sib_path=App.sib_path,
                sonic_host=App.sonic_host,
                sonic_user=App.sonic_user,
                sonic_pwd=App.sonic_pwd,
                bundle_id=App.pkg
            )
        else:
            self.dr = Driver(
                udid=App.did,
                bundle_id=App.pkg,
                wda_project_path=App.wda_project_path
            )
        # 设备解锁
        self.dr.unlock()

        self.start()

    def teardown_method(self):
        self.end()
        self.dr.close()
        print('休眠5s，防止释放设备过慢的情况！')
        self.sleep(5)

    # 公共方法
    @staticmethod
    def sleep(n: float):
        """休眠"""
        logger.info(f"暂停: {n}s")
        time.sleep(n)

    def shot(self, name: str, delay=0):
        """截图"""
        if delay:
            self.sleep(delay)
        self.dr.shot(name)

    # # UI方法
    # def elem(self, **kwargs):
    #     return Elem(driver=self.dr, **kwargs)

    def start_app(self, force=True):
        if force is True:
            self.stop_app()
        self.dr.start_app()

    def stop_app(self):
        self.dr.stop_app()

