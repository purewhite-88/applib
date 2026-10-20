# 'pip install opencv-python==4.6.0.66'
import time

from .driver import ImageDiscern
from kyapp.utils.log import logger


class ImgElem(object):
    """图像识别定位"""

    def __init__(self, driver=None, file: str = None):
        """

        @param driver: 设备驱动
        @param file: 图片文件路径
        """
        self.driver = driver
        self.target_image = file
        # if hasattr(self.driver, 'scale') is True:
        #     self.scale = self.driver.scale
        # else:
        #     self.scale = None

    def __get__(self, instance, owner):
        if instance is None:
            return None

        self.driver = instance.driver
        return self

    def wait(self, timeout=1):
        logger.info(f'图像识别判断: {self.target_image} 是否存在')
        time.sleep(timeout)
        source_image = self.driver.shot("图像识别中")
        res = ImageDiscern(self.target_image, source_image).get_coordinate()
        logger.debug(res)
        # logger.error(self.scale)
        # logger.error(self.driver.d.scale)
        # logger.error(self.driver.d.screen_info())
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
        logger.info(f'图像如果存在则点击: {self.target_image}')
        res = self.wait(timeout=timeout)
        if res is not False:
            self.driver.click(*res)
            # logger.info(f"点击({res})")
        else:
            logger.info("图像不存在，不进行点击")

    def click(self, retry=3, timeout=3):
        logger.info(f'图像识别点击: {self.target_image}')
        for i in range(retry):
            logger.info(f'第{i + 1}次查找:')
            res = self.wait(timeout=timeout)
            if res is not False:
                self.driver.click(*res)
                logger.info(f"点击{res}")
                break
        else:
            self.driver.shot(f'图像识别定位失败')
            raise Exception('未识别到图片，无法进行点击')
