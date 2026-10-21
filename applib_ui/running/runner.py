import os

import pytest

from .conf import App


_APP_FIELDS = ('did', 'pkg', 'platform', 'pop_list')


def main(case_path=None, report_path='report', did=None, pkg=None,
         platform=None, pop_list=None, pytest_args=None):
    """程序入口，返回 pytest 退出码；额外参数通过 pytest_args 传入。"""
    if platform not in ('android', 'ios'):
        raise ValueError('platform 必须是 android 或 ios')
    if not did:
        raise ValueError('设备标识不能为空（ios 传 udid，android 传 serial）')
    if not case_path:
        raise ValueError('测试用例路径不能为空')

    previous = {field: getattr(App, field) for field in _APP_FIELDS}
    App.did, App.pkg, App.platform, App.pop_list = did, pkg, platform, pop_list
    args = [os.fspath(case_path), '-sv', '--app-platform', platform, '--app-device', did]
    if pkg is not None:
        args.extend(['--app-package', pkg])
    if report_path is not None:
        args.extend(['--alluredir', os.fspath(report_path), '--clean-alluredir'])
    args.extend(pytest_args or [])
    try:
        return pytest.main(args)
    finally:
        for field, value in previous.items():
            setattr(App, field, value)
