# 'pip install opencv-python==4.6.0.66'
import os
import cv2
import numpy as np


class ImageDiscern:
    def __init__(self, target_image, source_image, grade=0.8, gauss_num=111) -> None:
        """__init__ [处理图片识别]
        Args:
            target_image (str): 被识别的目标图片
            grade (float, optional): 分数. Defaults to 0.8.
            gauss_num (int, optional): 过滤值. Defaults to 111.
        """
        self.source_image = source_image
        self.target_image = target_image
        if not os.path.exists(self.source_image):
            raise FileNotFoundError(f"文件: {self.source_image} 不存在")
        if not os.path.exists(self.target_image):
            raise FileNotFoundError(f"文件: {self.target_image} 不存在")

        self.grade = grade
        self.gauss_num = gauss_num

    # 降噪处理（高斯滤波）
    def __coordinate(self, image):
        return cv2.GaussianBlur(image, (self.gauss_num, self.gauss_num), 0)

    # 获取坐标图片坐标
    def get_coordinate(self):
        # 这里不用imread，解决中文目录无法读取的问题
        screen = cv2.imdecode(np.fromfile(self.source_image, dtype=np.uint8), 1)
        target = cv2.imdecode(np.fromfile(self.target_image, dtype=np.uint8), 1)
        result = cv2.matchTemplate(self.__coordinate(screen),
                                   self.__coordinate(target),
                                   cv2.TM_CCOEFF_NORMED)
        min, max, min_loc, max_loc = cv2.minMaxLoc(result)
        if max <= self.grade:
            return None
        else:
            x = max_loc[0] + int(target.shape[1] / 2)
            y = max_loc[1] + int(target.shape[0] / 2)
            return (x, y)
