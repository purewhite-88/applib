import pytest

from applib_ui.running.conf import App


@pytest.fixture
def mobile_project(pytester):
    pytester.makeconftest('''
from pathlib import Path
from applib_ui import device

class Driver:
    def __init__(self):
        with Path('events').open('a') as f:
            f.write('connect\\n')
    def stop_record(self):
        with Path('events').open('a') as f:
            f.write('record stopped\\n')
    def close(self):
        with Path('events').open('a') as f:
            f.write('close\\n')
    def unlock(self):
        pass

def create_driver():
    return Driver()

device.create_driver = create_driver
''')
    return pytester


def test_plain_pytest_needs_no_device_or_platform_dependencies(pytester):
    pytester.makepyfile('''
import sys
from applib_ui import App, Elem, Page, TestCase

def test_plain():
    assert App.did is None
    assert 'uiautomator2' not in sys.modules
    assert 'wda' not in sys.modules
    assert 'natocr' not in sys.modules
    assert 'cv2' not in sys.modules
''')
    pytester.runpytest_subprocess('-q').assert_outcomes(passed=1)


def test_config_before_collection_and_cli_overrides_ini(pytester):
    pytester.makeini('''
[pytest]
app_platform = android
app_device = ini-device
app_package = ini-package
''')
    pytester.makepyfile('''
from applib_ui import App, Elem
button = Elem('按钮', android=('text', '安卓'), ios=('name', '苹果'))

def test_config(app_config):
    assert app_config is App
    assert App.platform == 'ios'
    assert App.did == 'cli-device'
    assert App.pkg == 'ini-package'
    assert button.loc_value == '苹果'
''')
    pytester.runpytest_subprocess('-q', '--app-platform=ios', '--app-device=cli-device').assert_outcomes(passed=1)


def test_collect_only_does_not_connect(pytester):
    pytester.makepyfile('''
from applib_ui import TestCase
class TestApp(TestCase):
    def test_app(self):
        assert False
''')
    result = pytester.runpytest_subprocess('--collect-only', '-q')
    assert result.ret == 0
    result.stdout.fnmatch_lines(['*1 test collected*'])


def test_missing_device_reports_configuration_error(pytester):
    pytester.makepyfile('def test_device(app_driver): pass')
    result = pytester.runpytest_subprocess('-q', '--app-platform=android')
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(['*请通过 --app-device*'])


def test_invalid_platform_is_usage_error(pytester):
    pytester.makeini('[pytest]\napp_platform = invalid')
    pytester.makepyfile('def test_plain(): pass')
    result = pytester.runpytest_subprocess('-q')
    assert result.ret == pytest.ExitCode.USAGE_ERROR


def test_function_fixture_releases_after_assertion_failure(mobile_project):
    mobile_project.makepyfile('''
def test_device(app_driver):
    assert False, 'test failure'
''')
    result = mobile_project.runpytest_subprocess('-q')
    result.assert_outcomes(failed=1)
    assert (mobile_project.path / 'events').read_text().splitlines() == ['connect', 'record stopped', 'close']


@pytest.mark.parametrize('hook', ['start', 'end'])
def test_class_hook_error_is_reported_and_driver_closed(mobile_project, hook):
    mobile_project.makepyfile(f'''
from applib_ui import TestCase
class TestApp(TestCase):
    def {hook}(self):
        raise RuntimeError('hook failed')
    def test_device(self):
        assert self.dr is not None
''')
    result = mobile_project.runpytest_subprocess('-q')
    result.assert_outcomes(errors=1, passed=int(hook == 'end'))
    assert (mobile_project.path / 'events').read_text().splitlines() == ['connect', 'record stopped', 'close']


def test_class_hooks_and_parametrization(mobile_project):
    mobile_project.makepyfile('''
import pytest
from pathlib import Path
from applib_ui import TestCase

class TestApp(TestCase):
    def start_class(self):
        Path('class_started').touch()
    def end_class(self):
        Path('class_ended').touch()
    @pytest.mark.parametrize('value', [1, 2])
    def test_device(self, value, app_driver):
        assert self.dr is app_driver
        assert Path('class_started').exists()
''')
    mobile_project.runpytest_subprocess('-q').assert_outcomes(passed=2)
    assert (mobile_project.path / 'class_ended').exists()
    assert (mobile_project.path / 'events').read_text().splitlines() == ['connect', 'record stopped', 'close'] * 2


def test_app_state_restored_between_in_process_runs(pytester):
    pytester.makepyfile('''
from applib_ui import App

def test_config():
    assert App.did == 'temporary-device'
''')
    before = (App.platform, App.did, App.pkg)
    pytester.runpytest_inprocess('-q', '--app-platform=android', '--app-device=temporary-device').assert_outcomes(passed=1)
    assert (App.platform, App.did, App.pkg) == before
