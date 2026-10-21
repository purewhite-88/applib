# applib-ui

基于 pytest 的 Android / iOS 自动化测试库，提供设备驱动、页面对象、双平台元素定位、截图、录屏和 Allure 报告支持。Python 要求为 3.10 及以上。

## 安装

在业务测试项目的虚拟环境中安装对应平台的依赖：

```bash
python -m pip install 'applib-ui[android]'
# iOS
python -m pip install 'applib-ui[ios]'
# 双平台、图像识别及 OCR
python -m pip install 'applib-ui[android,ios,image,ocr]'
```

基础包安装命令为 `python -m pip install applib-ui`，Python 导入名为 `applib_ui`。

如需从源码开发安装：

```bash
python -m pip install -e '/path/to/applib-ui[android]'
# iOS
python -m pip install -e '/path/to/applib-ui[ios]'
# 双平台、图像识别及 OCR
python -m pip install -e '/path/to/applib-ui[android,ios,image,ocr]'
```

仅安装基础包 `python -m pip install -e /path/to/applib-ui` 即可使用 pytest 插件与通用工具。设备驱动和识别库按实际使用的功能安装。

Android 需要可用的 adb 及已授权设备；iOS 需要 macOS、已签名且可运行的 WDA，以及现有 WDA 启动流程所需的 tidevice / go-ios 工具。录屏还需要对应平台使用的 scrcpy / ffmpeg。

## 使用 pytest

安装后插件自动加载，无需在业务项目中编写 `pytest_plugins`。插件通过标准的 [pytest 插件入口](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#making-your-plugin-installable-by-others)注册。

```python
# tests/test_app.py

def test_launch(app_driver):
    app_driver.start_app()
```

```bash
pytest tests/test_app.py --app-platform android --app-device SERIAL --app-package com.example.app
pytest tests/test_app.py --app-platform ios --app-device UDID --app-package com.example.app
# 筛选、参数化和报告使用 pytest 自身的参数
pytest tests -k launch --app-platform android --app-device SERIAL --alluredir report
# 仅收集，不连接设备
pytest tests --collect-only --app-platform android
```

`app_driver` 是函数级 fixture，每条用例建立一个设备驱动，用例结束后停止未结束的录屏并释放连接。普通测试无需配置设备。`app_config` fixture 返回当前的 `App` 配置。

也可以在业务项目的 `pytest.ini` 中设置默认参数：

```ini
[pytest]
app_platform = android
app_device = SERIAL
app_package = com.example.app
```

三个命令行参数分别覆盖对应的 INI 配置。平台配置在用例收集前生效，供页面元素选择对应定位方式。会话结束后恢复运行前的配置，同一进程连续运行不会留下本次参数。一次 pytest 会话对应一个平台和一台设备；多设备请分别启动进程。

如果主动设置了 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，需要显式加 `-p applib_ui.pytest_plugin`；使用报告参数时还需加载 Allure 插件。

## 页面对象与测试类

```python
from applib_ui import Elem, Page, TestCase


class HomePage(Page):
    login = Elem(
        '登录',
        android=('text', '登录'),
        ios=('name', '登录'),
    )


class TestLogin(TestCase):
    def start(self):
        self.start_app()

    def test_login(self):
        HomePage(self.dr).login.click()
```

保留 `start_class` / `end_class`、`start` / `end` 扩展钩子，异常会交由 pytest 报告。驱动释放由 fixture 负责，`start` / `end` 失败时仍执行清理。新用例可以直接使用普通测试函数和 fixture，无需继承基类。

平台专用接口分别从 `applib_ui.core.android`、`applib_ui.core.ios` 导入。专用 `TestCase` 要求配置匹配的平台，并会在每条用例开始前解锁设备。Sonic 远程连接可通过业务 `conftest.py` 设置 `App.sonic_host`、`App.sonic_user`、`App.sonic_pwd`；iOS 远程连接还需要设置 `App.sib_path`。

## 其他入口

```bash
applib-ui --version
applib-ui run tests --app-platform android --app-device SERIAL --app-package com.example.app
applib-ui start-wda -u UDID
applib-ui stop-wda -u UDID
applib-ui restart-wda -u UDID
```

`applib-ui run` 透传 pytest 参数并返回 pytest 退出码。程序调用方式：

```python
from applib_ui import main

exit_code = main(
    case_path='tests',
    report_path='report',  # 传 None 关闭此入口默认添加的 Allure 输出
    did='SERIAL',
    pkg='com.example.app',
    platform='android',
    pytest_args=['-k', 'login'],
)
raise SystemExit(exit_code)
```

## 配置与目录

- `applib_ui/core/android/`：Android 本地 / 远程驱动、元素及录屏。
- `applib_ui/core/ios/`：iOS 驱动、WDA、元素及录屏。
- `applib_ui/core/img/`、`applib_ui/core/ocr/`：图像及 OCR。
- `applib_ui/pytest_plugin.py`：pytest 参数、配置和 fixture。
- `applib_ui/running/`：程序入口及默认 YAML 配置。
- `applib_ui/utils/`：通用工具。

发布名和命令为 `applib-ui`，Python 导入名为 `applib_ui`，Android 目录和元素关键字统一为 `android`。升级业务用例时需同步修改导入和元素定义，不提供旧名称别名。

运行环境变量统一使用 `APPLIB_UI_` 前缀：`APPLIB_UI_WDA_TIMEOUT`、`APPLIB_UI_TUNNEL_PORT_BASE`、`APPLIB_UI_OCR_LANG`、`APPLIB_UI_OCR_FALLBACK_LANG`。iOS 端口注册、配对文件和日志使用 `~/.applib-ui/` 目录。

`order()`、`depend()` 仍分别依赖额外安装的 pytest-ordering、pytest-dependency；基础包不会自动安装这两个插件。数据参数化可直接用 `pytest.mark.parametrize` 或 `data()`。

## 开发验证

```bash
python -m pip install -e .
python -m pytest
```

仓库测试使用模拟驱动验证 pytest 接入、异常清理和退出码，不会连接设备。Android / iOS 真机行为需在具备上述设备环境的业务项目中验证。

本仓库未额外声明许可证。
