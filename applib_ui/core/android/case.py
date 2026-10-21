from ...case import TestCase as BaseTestCase


class TestCase(BaseTestCase):
    """Android pytest 测试基类。"""

    _platform = 'android'
