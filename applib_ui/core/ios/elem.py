import time
import threading

from applib_ui.utils.log import logger
from .driver import Driver


lock = threading.Lock()


# 链式调用临时存储定位方式
class ChildLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'child'


class Elem(object):
    """
    IOS原生元素定义
    https://github.com/openatx/facebook-wda
    """

    def __init__(self,
                 tag=None
                 ):
        """
        @param tag: 元素名称，方便后续维护
        """
        self._driver: Driver = None
        self.tag = tag
        if not self.tag:
            raise KeyError('tag不能为空')
        self._first_locator = None
        self._locators = []

    def __get__(self, instance, owner):
        """po模式中element初始化不需要带driver的关键"""
        if instance is None:
            return None

        self._driver = instance.driver
        return self

    # 链式调用方法
    def loc(self, **kwargs):
        if not kwargs:
            raise KeyError('定位方式不能为空')
        if 'xpath' in kwargs:
            self._first_locator = kwargs.pop('xpath')
        else:
            self._first_locator = kwargs
        return self

    def child(self, *args, **kwargs):
        self._locators.append(ChildLocator(*args, **kwargs))
        return self

    # def _match(self, text):
    #     """
    #     判断元素是否存在当前页面
    #     @return:
    #     """
    #     _element = self._driver.d(text=text)
    #     result = text if _element.wait(timeout=0.1,
    #                                    raise_error=False) else None
    #     return result
    #
    # def pop_check(self, timeout=3):
    #     logger.info(f"开始弹窗检测: {self._watch}")
    #     # 多线程match，如果match到，获取第一个非None内容，进行点击
    #     # match完休息1s，如果休息3s也没有match到，就停止（定义一个flag，match到就清零）
    #     # 如果3s内仍然能match到就继续（如果flag大于3就停止）
    #     _build_info = ["允许", "使用App时允许", "始终允许", "同意"]
    #     if self._watch is True:
    #         loc_list = _build_info
    #     else:
    #         loc_list = list(set(_build_info + self._watch))
    #     flag = timeout
    #     while flag > 0:
    #         import concurrent.futures
    #
    #         logger.info(f"匹配: {loc_list}")
    #         with concurrent.futures.ThreadPoolExecutor() as executor:
    #             results = executor.map(self._match, loc_list)
    #             results = [item for item in results if item is not None]
    #
    #         if results:
    #             logger.info(f"匹配到: {results}")
    #             self._driver.d(text=results[0]).click()
    #             logger.info("点击成功")
    #             flag = timeout
    #         else:
    #             logger.info("匹配失败")
    #
    #         flag -= 1
    #         time.sleep(1)
    #     logger.info("结束检测")

    def find(self, timeout=5):
        """
        针对元素定位失败的情况，抛出KError异常
        @param timeout:
        @param n: 重试次数
        ["允许", "同意"]
        @return:
        """
        logger.info(f"查找: {self.tag}")
        # 第一个定位
        if isinstance(self._first_locator, dict):
            _element = self._driver.d(**self._first_locator)
        else:
            _element = self._driver.d.xpath(self._first_locator)

        # 后面的定位
        if self._locators:
            for loc_obj in self._locators:
                if loc_obj.type == "child":
                    _element = _element.child(*loc_obj.args, **loc_obj.kwargs)
                else:
                    raise KeyError('不支持的子调用')

        if _element.wait(timeout=timeout):
            logger.info(f"查找成功")
            return _element
        else:
            logger.info("查找失败")
            self._driver.shot(f"{self.tag}_查找失败")
            raise Exception(f"{self.tag}, 查找失败")

    def get_text(self, timeout=5):
        logger.info(f"获取{self.tag}的文本")
        return self.find(timeout=timeout).text

    def exists(self, timeout=5):
        """
        判断元素是否存在当前页面
        @param timeout:
        @return:
        """
        logger.info(f"判断{self.tag}是否存在")
        result = False
        try:
            _element = self.find(timeout=timeout)
            result = True
        except:
            result = False
        finally:
            logger.info(result)
            return result

    def _adapt_center(self, timeout=5):
        """
        修正控件中心坐标
        """
        bounds = self.find(timeout=timeout).bounds
        left_top_x, left_top_y, width, height = \
            bounds.x, bounds.y, bounds.width, bounds.height
        center_x = int(left_top_x + width/2)
        center_y = int(left_top_y + height/2)
        logger.info(f'{center_x}, {center_y}')
        return center_x, center_y

    def click_exists(self, timeout=5):
        """
        存在才点击
        @param: retry，重试次数
        @param: timeout，每次重试超时时间
        """
        logger.info(f'{self.tag}存在才点击')
        try:
            x, y = self._adapt_center(timeout=timeout)
            self._driver.d.appium_settings({"snapshotMaxDepth": 0})
            self._driver.click(x, y)
            self._driver.d.appium_settings({"snapshotMaxDepth": 50})
            logger.info("点击完成")
        except:
            logger.info("不存在，不进行操作")

    def click(self, timeout=5):
        """
        单击
        @param: retry，重试次数
        @param: timeout，每次重试超时时间
        """
        logger.info(f'点击{self.tag}')
        x, y = self._adapt_center(timeout=timeout)
        logger.error('{x}, {y}')
        self._driver.d.appium_settings({"snapshotMaxDepth": 0})
        self._driver.click(x, y)
        self._driver.d.appium_settings({"snapshotMaxDepth": 50})
        logger.info("点击完成")

    def input(self, text, timeout=5, clear=False):
        """输入内容"""
        logger.info(f"定位到{self.tag}并输入: {text}")
        element = self.find(timeout=timeout)
        if clear is True:
            element.clear_text()
        element.set_text(text)
        logger.info("输入完成")



















