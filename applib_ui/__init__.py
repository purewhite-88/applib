from .running.runner import main
from .running.conf import App
from .utils.config import FileConfig
from .utils.pytest_util import *
from .utils.allure_util import *
from .utils.log import logger
from .page import Page
from .element import Elem
from .case import TestCase


__version__ = "0.0.1"
__description__ = "Android / iOS 通用 UI 自动化测试框架"
