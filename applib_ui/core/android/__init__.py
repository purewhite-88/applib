"""android 平台接口，按需加载驱动依赖。"""

from importlib import import_module

__all__ = ['Elem', 'Page', 'Driver', 'RemoteDriver', 'TestCase']

_MODULES = {'Elem': 'element', 'Page': 'page', 'Driver': 'driver',
            'RemoteDriver': 'remote_driver', 'TestCase': 'case'}


def __getattr__(name):
    if name not in _MODULES:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    value = getattr(import_module(f'.{_MODULES[name]}', __name__), name)
    globals()[name] = value
    return value
