from .running.runner import main
from .running.conf import App
from .utils.config import FileConfig
from .utils.pytest_util import *
from .utils.allure_util import *
from .utils.log import logger
from .page import Page
from .element import Elem
from .case import TestCase


__version__ = "0.0.22"
__description__ = "安卓/IOS自动化测试框架"
