import time
import concurrent.futures
from .running.conf import App
from .utils.log import logger


class Elem(object):
    """Android / iOS 双平台元素定义。"""

    def __init__(self,
                 title,
                 android=None,
                 ios=None
                 ):
        """
        @param tag: 元素名称，方便后续维护
        """
        self._driver = None
        self.tag = title
        if not self.tag:
            raise KeyError('title不能为空')
        self.loc_key = None
        self.loc_value = None
        if App.platform == 'ios':
            self.loc_key, self.loc_value = ios
        else:
            self.loc_key, self.loc_value = android


    def __get__(self, instance, owner):
        """po模式中element初始化不需要带driver的关键"""
        if instance is None:
            return None

        self._driver = instance.driver
        return self

    def _match(self, loc_elem):
        """
        判断元素是否存在当前页面
        @return:
        """
        try:
            loc_title, loc_key, loc_value = loc_elem
        except:
            raise KeyError('弹窗定位方式格式错误，应该是("元素描述", "key", "value")')
        if loc_key == 'xpath':
            _element = self._driver.d.xpath(loc_value)
        else:
            _element = self._driver.d(**{loc_key: loc_value})

        if App.platform == 'ios':
            wait_option = _element.wait(timeout=0.1, raise_error=False)
        else:
            wait_option = _element.wait(timeout=0.1)
        if wait_option:
            _element.click_exists(timeout=0.1)
            return loc_title
        return None

    def pop_check(self, timeout=3):

        loc_list = App.pop_list
        # 弹窗设置为None时，不走后续检测逻辑
        if loc_list is None:
            return

        logger.info(f"开始弹窗检测: {loc_list}")
        # 多线程match，如果match到，获取第一个非None内容，进行点击
        # match完休息1s，如果休息3s也没有match到，就停止（定义一个flag，match到就清零）
        # 如果3s内仍然能match到就继续（如果flag大于3就停止）
        flag = timeout
        while flag > 0:
            logger.info(f"检测弹弹窗中: {loc_list}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(self._match, loc_list)
                results = [item for item in results if item is not None]
            if results:
                logger.info(f"检测到弹窗: {results}")
                flag = timeout
            else:
                logger.info("未检测到弹窗或蒙层")

            flag -= 1
            time.sleep(1)
        logger.info("结束检测")

    def find(self, timeout=5, retry=True, error_screen=True):
        """
        针对元素定位失败的情况，抛出KError异常
        @param timeout:
        @param n: 重试次数
        ["允许", "同意"]
        @return:
        """
        if 'xpath' == self.loc_key:
            _element = self._driver.d.xpath(self.loc_value)
        else:
            _element = self._driver.d(**{self.loc_key:self.loc_value})


        if _element.wait(timeout=timeout) and (App.platform != 'ios' or _element.visible):
            logger.info(f"查找成功")
            return _element
        else:
            logger.info(f"查找失败")
            if retry:
                # 加入重试机制
                for i in range(3):
                    logger.info(f"第{i + 1}次重试")
                    # 进行蒙层及弹窗处理
                    self.pop_check()
                    if App.platform == 'ios':
                        visible_value = _element.visible
                    else:
                        visible_value = True
                    if _element.wait(timeout=timeout) and visible_value is True:
                        logger.info(f"第{i + 1}次重试成功")
                        return _element
                    else:
                        logger.info(f"第{i + 1}次重试失败")
                        i += 1
                # 重试失败
                logger.info("3次重试失败")

        if error_screen:
            self._driver.shot(f"{self.tag}_查找失败")
        raise Exception(f"{self.tag}, 查找失败")



    def get_text(self, timeout=5):
        logger.info(f"获取{self.tag}的文本")
        return self.find(timeout=timeout).text

    def exists(self, timeout=5, retry=False):
        """
        判断元素是否存在当前页面
        @param timeout:
        @return:
        """
        logger.info(f"判断{self.tag}是否存在")
        try:
            self.find(timeout=timeout, retry=retry, error_screen=False)
        except:
            logger.info(f"元素{self.tag}不存在")
            return False
        else:
            logger.info(f"元素{self.tag}存在")
            return True

    def clear(self):
        logger.info(f'清空输入框：{self.tag}')
        self.find().clear_text()

    def click(self, timeout=5):
        """
        单击
        @param: timeout，每次重试超时时间
        """
        if 'image' in self.loc_key:
            from .core.img.element import ImgElem

            ImgElem(self._driver, file=self.loc_value).click()
            return

        if 'ocr' in self.loc_key:
            from .core.ocr.element import OcrElem

            OcrElem(self._driver, keyword=self.loc_value).click()
            return

        logger.info(f'点击{self.tag}')
        self.find(timeout=timeout).click()
        logger.info("点击完成")

    def click_exists(self, timeout=5):
        """
        存在才进行点击操作，暂时不支持image和ocr识别
        """
        if self.exists(timeout=timeout):
            logger.info(f"{self.tag}存在，进行点击")
            self.click(timeout=timeout)
        else:
            logger.info(f"{self.tag}不存在，跳过点击操作")

    def input(self, text, timeout=5):
        """输入内容"""
        logger.info(f"定位到{self.tag}并输入: {text}")
        self.find(timeout=timeout).set_text(text)
        logger.info("输入完成")



















