import typing
from .driver import Driver

from applib_ui.utils.log import logger
from uiautomator2 import UiObject
from uiautomator2.xpath import XPathSelector


# 链式调用临时存储定位方式
# class BaseLocator:
#
#     def __init__(self, **kwargs):
#         self.rid = kwargs.get('rid', None)
#         self.text = kwargs.get('text', None)
#         self.xpath = kwargs.get('xpath', None)
#         self.type = 'current'


class ChildLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'child'


class SiblingLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'sibling'


class LeftLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'left'


class RightLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'right'


class UpLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'up'


class DownLocator:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.type = 'down'


class Elem(object):
    """
    安卓控件定义
    https://github.com/openatx/uiautomator2
    """

    def __init__(self,
                 tag=None,
                 ):
        """
        @param tag: 元素名称，方面后续维护
        """
        self.tag = tag
        # self._kwargs = kwargs
        self._driver: Driver = None
        # self._xpath = kwargs.get('xpath', None)
        # self._watch = watch
        self._first_locator = None
        self._locators = []
        # if 'rid' in self._kwargs:
        #     self._kwargs['resourceId'] = self._kwargs.pop('rid')
        # self._pkg = App.pkg
        # if 'resourceId' in self._kwargs:
        #     if not self._kwargs['resourceId'].startswith(self._pkg):
        #         if not self._pkg:
        #             raise KeyError('应用包名不能为空')
        #         else:
        #             self._kwargs['resourceId'] = self._pkg + ":" + self._kwargs['resourceId']

    def __get__(self, instance, owner):
        """po模式中element初始化不需要带driver的关键"""
        if instance is None:
            return None

        self._driver = instance.driver
        return self

    # 链式调用方法
    # def get_by_rid(self, rid):
    #     self.locators.append(BaseLocator(rid=rid))
    #     return self
    #
    # def get_by_text(self, text):
    #     self.locators.append(BaseLocator(text=text))
    #     return self
    #
    # def get_by_xpath(self, xpath):
    #     self.locators.append(BaseLocator(xpath=xpath))
    #     return self

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

    def sibling(self, *args, **kwargs):
        self._locators.append(SiblingLocator(*args, **kwargs))
        return self

    def left(self, *args, **kwargs):
        self._locators.append(LeftLocator(*args, **kwargs))
        return self

    def right(self, *args, **kwargs):
        self._locators.append(RightLocator(*args, **kwargs))
        return self

    def up(self, *args, **kwargs):
        self._locators.append(UpLocator(*args, **kwargs))
        return self

    def down(self, *args, **kwargs):
        self._locators.append(DownLocator(*args, **kwargs))
        return self

    # # 公共方法
    # def watch_handler(self):
    #     """
    #     异常弹窗处理
    #     @return:
    #     """
    #     logger.info(f"开始弹窗检测: {self._watch}")
    #     ctx = self._driver.d.watch_context()
    #     for loc in self._watch:
    #         ctx.when(loc).click()
    #     ctx.wait_stable()
    #     ctx.close()
    #     logger.info("检测结束")

    def find(self, timeout=5):
        """
        增加截图的方法
        @param timeout: 每次查找时间
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
                elif loc_obj.type == 'sibling':
                    _element = _element.sibling(*loc_obj.args, **loc_obj.kwargs)
                elif loc_obj.type == 'left':
                    _element = _element.left(*loc_obj.args, **loc_obj.kwargs)
                elif loc_obj.type == 'right':
                    _element = _element.right(*loc_obj.args, **loc_obj.kwargs)
                elif loc_obj.type == 'up':
                    _element = _element.up(*loc_obj.args, **loc_obj.kwargs)
                elif loc_obj.type == 'down':
                    _element = _element.down(*loc_obj.args, **loc_obj.kwargs)

        if _element.wait(timeout=timeout):
            logger.info(f"查找成功")
            return _element
        else:
            logger.info("查找失败")
            self._driver.shot(f"{self.tag}_查找失败")
            raise Exception(f"{self.tag}, 查找失败")

    # 属性获取
    def get_text(self, timeout=5):
        logger.info(f"获取{self.tag}的文本")
        _elem = self.find(timeout=timeout)
        text = _elem.get_text()
        logger.info(f"获取成功: {text}")
        return text

    def get_texts(self, timeout=5):
        logger.info(f"获取{self.tag}的文本")
        _elem = self.find(timeout=timeout)
        texts = []
        if isinstance(_elem, XPathSelector):
            elems = _elem.all()
            for elem in elems:
                texts.append(elem.text)
        else:
            elems = list(_elem)
            for elem in elems:
                texts.append(elem.get_text())
        logger.info(f"获取成功: {texts}")
        return texts

    def exists(self, timeout=5):
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

    def center(self, timeout=5, *args, **kwargs):
        return self.find(timeout=timeout).center(*args, **kwargs)

    @staticmethod
    def _adapt_center(e: typing.Union[UiObject, XPathSelector],
                      offset=(0.5, 0.5)):
        """
        修正控件中心坐标
        """
        if isinstance(e, UiObject):
            return e.center(offset=offset)
        else:
            return e.offset(offset[0], offset[1])

    # 操作
    def click_exists(self, timeout=5):
        logger.info(f"{self.tag}存在才点击")
        try:
            element = self.find(timeout=timeout)
            x, y = self._adapt_center(element)
            self._driver.click(x, y)
            logger.info("点击完成")
        except:
            logger.info("不存在，不进行操作")

    def click(self, timeout=5):
        logger.info(f"{self.tag}点击")
        element = self.find(timeout=timeout)
        x, y = self._adapt_center(element)
        self._driver.click(x, y)
        logger.info("点击完成")

    def input(self, text, timeout=5, clear=False, pwd_check=False):
        logger.info(f"{self.tag}输入: {text}")
        element = self.find(timeout=timeout)
        # 清空输入框
        if clear is True:
            element.clear_text()
        # 点击输入框
        x, y = self._adapt_center(element)
        self._driver.click(x, y)
        # 输入
        if pwd_check is True:
            self._driver.d(focused=True).set_text(text)
        else:
            self._driver.input(text)
        logger.info("输入完成")









