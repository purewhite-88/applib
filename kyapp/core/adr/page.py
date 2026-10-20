"""
@Author: kang.yang
@Date: 2025/4/14 17:41
"""


class Page(object):
    """页面基类，用于pom模式封装"""

    def __init__(self, driver):
        self.driver = driver

