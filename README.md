# kyapp 0.0.22

安卓 / iOS 自动化测试框架。本仓库归档本机已安装的 `kyapp==0.0.22` 源码，以当前安装目录中的文件为准，并非上游原始发行包的完整 Git 历史。

- 来源：`lute-app-test/.venv/lib/python3.13/site-packages/kyapp`
- 原作者：杨康
- 上游主页：https://gitee.com/bluepang2021/kyapp_project
- Python 要求与依赖版本均沿用已安装包的元数据。

## 安装

```bash
python -m pip install .
```

依赖含固定版本，安装时需要匹配的 Python 和系统环境。本次归档验证源码语法和打包内容，未进行 Android / iOS 真机测试，也未验证所有依赖在新环境中的兼容性。

## 目录

- `kyapp/core/adr/`：Android 驱动、元素、录屏和远程设备支持。
- `kyapp/core/ios/`：iOS 驱动、WDA、元素和录屏支持。
- `kyapp/core/img/`、`kyapp/core/ocr/`：图像与 OCR 支持。
- `kyapp/running/`：运行入口与默认配置。
- `kyapp/utils/`：通用工具。

## 归档处理

源码保留本地安装版本的行为。仅清空 Nacos 示例中的服务器、命名空间和登录凭据，将远程 WDA 示例中的设备标识与登录信息替换为占位值，并将 Swagger 内网示例地址替换为 localhost。使用这些工具时请显式传入实际参数，不要提交真实凭据。

`pyproject.toml` 根据已安装发行包的元数据补建，并包含默认 YAML 配置。原发行包的命令入口为 `kytest = kytest.cli:main`，但本包只提供 `kyapp`；此历史不一致保持原样，`kytest` 命令无法单独依靠本包运行。

未包含虚拟环境、字节码缓存、业务测试用例、运行日志和报告。原安装包未提供许可证文件，本仓库未额外声明许可证。
