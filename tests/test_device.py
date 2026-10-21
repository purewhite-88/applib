import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from applib_ui import device
from applib_ui.running.conf import App


def test_android_only_loads_android_driver(monkeypatch):
    driver = Mock()
    factory = Mock(return_value=driver)
    monkeypatch.setattr(App, 'platform', 'android')
    monkeypatch.setattr(App, 'did', 'serial')
    monkeypatch.setattr(App, 'pkg', 'com.example')
    monkeypatch.setitem(sys.modules, 'applib_ui.core.android.driver', SimpleNamespace(Driver=factory))
    assert device.create_driver() is driver
    factory.assert_called_once_with(serial='serial', package='com.example')


def test_ios_health_check_failure_closes_driver(monkeypatch):
    driver = Mock()
    driver.ensure_alive.return_value = False
    monkeypatch.setattr(App, 'platform', 'ios')
    monkeypatch.setattr(App, 'did', 'udid')
    monkeypatch.setitem(sys.modules, 'applib_ui.core.ios.driver', SimpleNamespace(Driver=Mock(return_value=driver)))
    monkeypatch.setitem(sys.modules, 'applib_ui.core.ios.local_wda', SimpleNamespace(LocalWdaInit=Mock()))
    with pytest.raises(RuntimeError, match='WDA'):
        device.create_driver()
    driver.close.assert_called_once()


def test_close_runs_even_when_recording_cleanup_fails():
    driver = Mock()
    driver.stop_record.side_effect = RuntimeError('recording failed')
    with pytest.raises(RuntimeError, match='recording failed'):
        device.release_driver(driver)
    driver.close.assert_called_once()


def test_start_app_supports_remote_android_signature(monkeypatch):
    from applib_ui import TestCase as AppTestCase

    calls = []
    case = AppTestCase()
    case.dr = SimpleNamespace(start_app=lambda: calls.append('start'))
    monkeypatch.setattr(App, 'platform', 'android')
    case.start_app(force=False)
    assert calls == ['start']
