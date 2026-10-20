"""
@Author: kang.yang
@Date: 2023/10/26 09:48
"""
import time

from .core.adr.driver import Driver as AdrDriver
from .core.ios.local_wda import LocalWdaInit
from .core.ios.driver import Driver as IosDriver

from .running.conf import App
from .utils.log import logger


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
        did = App.did
        pkg = App.pkg
        if App.platform == 'ios':
            LocalWdaInit(did).kill_wda_server() # 清除历史服务
            self.dr = IosDriver(udid=did, bundle_id=pkg)
            # 建好就做一次链路自检：USB 抖动/断链时立刻重建
            # 否则断链后元素查询会一直卡到 HTTP 超时，表现为用例长时间不动
            self.dr.ensure_alive()
        else:
            self.dr = AdrDriver(serial=did, package=pkg)

        try:
            self.start()
        except Exception as e:
            logger.error(f"setup_method start() failed: {e}")
            # 这里可以选择重新抛出异常，让测试失败，或者记录日志后继续

    def teardown_method(self):
        try:
            self.end()
        except Exception as e:
            logger.error(f"teardown_method end() failed: {e}")
            # 这里可以选择重新抛出异常，让测试失败，或者记录日志后继续
        if App.platform == 'ios':
            self.dr.close()
            print('休眠5s，防止释放设备过慢的情况！')
            self.sleep(5)

    # 公共方法
    @staticmethod
    def sleep(n: float):
        logger.info(f"暂停: {n}s")
        time.sleep(n)

    def shot(self, name: str, delay=0):
        if delay:
            self.sleep(delay)
        self.dr.shot(name)

    def start_record(self, video_name='record'):
        """开始录屏"""
        return self.dr.start_record(video_name)

    def stop_record(self):
        """结束录屏并上传allure"""
        return self.dr.stop_record()

    def start_app(self, force=True, activity=None, use_monkey=False):
        if force:
            self.stop_app()
        if App.platform == 'ios':
            self.dr.start_app()
        else:
            if activity is not None:
                self.dr.start_app(activity=activity)
            else:
                self.dr.start_app(use_monkey=use_monkey)

    def stop_app(self):
        self.dr.stop_app()

    def back(self):
        self.dr.back()

