"""安装后由 pytest 自动加载；仅设备用例会建立连接。"""

import pytest

from . import device
from .running.conf import App


_OPTIONS = {'platform': 'platform', 'device': 'did', 'package': 'pkg'}
_STATE_KEY = pytest.StashKey[dict]()


def pytest_addoption(parser):
    group = parser.getgroup('applib-ui', '移动端自动化参数')
    for name in _OPTIONS:
        kwargs = {'choices': ('android', 'ios')} if name == 'platform' else {}
        group.addoption(f'--app-{name}', action='store', default=None, **kwargs,
                        help=f'覆盖 app_{name} 配置')
        parser.addini(f'app_{name}', f'applib-ui {name} 默认值', default='')


def pytest_configure(config):
    # 元素描述符会在收集用例时读取平台，因此不能等到 fixture 执行才配置。
    config.stash[_STATE_KEY] = {field: getattr(App, field) for field in _OPTIONS.values()}
    config.add_cleanup(lambda: _restore_app(config.stash[_STATE_KEY]))
    for name, field in _OPTIONS.items():
        value = config.getoption(f'app_{name}')
        if value is None:
            value = config.getini(f'app_{name}') or None
        if value is not None:
            setattr(App, field, value)
    if App.platform is not None and App.platform not in ('android', 'ios'):
        raise pytest.UsageError('app_platform 必须是 android 或 ios')


def _restore_app(state):
    for field, value in state.items():
        setattr(App, field, value)


@pytest.fixture
def app_config():
    """当前会话的设备配置。"""
    return App


@pytest.fixture
def app_driver(app_config, request):
    """每条用例一个驱动，失败或正常结束时均释放资源。"""
    platform = getattr(request.cls, '_platform', None)
    if platform is not None and app_config.platform != platform:
        raise pytest.UsageError(f'该测试类需要 --app-platform={platform}')
    driver = device.create_driver()
    try:
        yield driver
    finally:
        device.release_driver(driver)
