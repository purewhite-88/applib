import pytest
from click.testing import CliRunner

from applib_ui import main
from applib_ui.cli import main as cli
from applib_ui.running.conf import App
from applib_ui.running import runner


def test_programmatic_runner_preserves_paths_exit_code_and_state(monkeypatch):
    before = (App.platform, App.did, App.pkg, App.pop_list)
    captured = []

    def fake_main(args):
        captured.extend(args)
        assert App.did == 'device'
        return pytest.ExitCode.TESTS_FAILED

    monkeypatch.setattr(runner.pytest, 'main', fake_main)
    result = main('tests with spaces/test_app.py', 'report with spaces',
                  did='device', platform='android', pkg='com.example', pytest_args=['-k', 'login'])
    assert result == pytest.ExitCode.TESTS_FAILED
    assert captured == ['tests with spaces/test_app.py', '-sv', '--app-platform', 'android',
                        '--app-device', 'device', '--app-package', 'com.example',
                        '--alluredir', 'report with spaces', '--clean-alluredir', '-k', 'login']
    assert (App.platform, App.did, App.pkg, App.pop_list) == before


def test_runner_restores_state_on_exception(monkeypatch):
    before = (App.platform, App.did, App.pkg, App.pop_list)

    def fail(args):
        raise RuntimeError('pytest failed')

    monkeypatch.setattr(runner.pytest, 'main', fail)
    with pytest.raises(RuntimeError, match='pytest failed'):
        main('tests', did='device', platform='ios')
    assert (App.platform, App.did, App.pkg, App.pop_list) == before


def test_cli_passes_arguments_and_exit_code(monkeypatch):
    captured = []
    monkeypatch.setattr(runner.pytest, 'main', lambda args: captured.extend(args) or 1)
    result = CliRunner().invoke(cli, ['run', 'tests with spaces', '--app-platform', 'android', '-k', 'login'])
    assert result.exit_code == 1
    assert captured == ['tests with spaces', '--app-platform', 'android', '-k', 'login']
