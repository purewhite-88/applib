from ...case import TestCase as BaseTestCase


class TestCase(BaseTestCase):
    """iOS pytest 测试基类。"""

    _platform = 'ios'
