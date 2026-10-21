import time
from applib_ui.running.conf import App
from applib_ui.utils.log import logger
from .driver import get_position


class OcrElem:

    def __init__(self, driver=None, keyword: str=None):
        self.driver = driver
        self.keyword = keyword
        self._service = App.ocr_service
        # if hasattr(self.driver, 'scale') is True:
        #     self.scale = self.driver.scale
        # else:
        #     self.scale = None

    def __get__(self, instance, owner):
        if instance is None:
            return None

        self.driver = instance.driver
        return self

    def exists(self, timeout=1):
        logger.info(f'ocr识别判断: {self.keyword} 是否存在')
        time.sleep(timeout)
        source_image = self.driver.shot("图像识别中")
        res = get_position(source_image, self.keyword, self._service)
        logger.debug(res)
        if isinstance(res, tuple):
            x, y = res[0], res[1]
            try:
                scale = self.driver.d.scale
            except:
                scale = None
            if scale is not None:
                """iphone的scale是3"""
                x, y = int(x / scale), int(y / scale)
            return x, y
        else:
            return False

    def click_exists(self, timeout=3):
        logger.info(f'ocr识别如果存在则点击: {self.keyword}')
        res = self.exists(timeout=timeout)
        if res is not False:
            self.driver.click(*res)
            logger.info(f"点击({res})")
        else:
            logger.info(f"{self.keyword}不存在，不进行点击")

    def click(self, retry=3, timeout=3):
        logger.info(f'ocr识别点击图片: {self.keyword}')
        logger.info(f'ocr识别如果存在则点击: {self.keyword}')
        for i in range(retry):
            logger.info(f'第{i + 1}次查找:')
            res = self.exists(timeout=timeout)
            if res is not False:
                self.driver.click(*res)
                logger.info(f"点击({res})")
                return
        else:
            self.driver.shot(f'ocr识别定位失败')
            raise Exception('未识别到关键词，无法进行点击')
