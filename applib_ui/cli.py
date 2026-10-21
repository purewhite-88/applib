import click
from . import __version__

@click.group()
@click.version_option(version=__version__, help="Show version.")
def main():
    """applib-ui 移动端自动化工具。"""


@main.command(context_settings={'ignore_unknown_options': True})
@click.argument('pytest_args', nargs=-1, type=click.UNPROCESSED)
def run(pytest_args):
    """运行 pytest，透传路径、筛选条件和报告等参数。"""
    import pytest

    raise SystemExit(pytest.main(list(pytest_args)))


@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def restart_wda(udid):
    """
    重启wda
    @param udid: IOS设备udid
    @return:
    """
    from .core.ios.local_wda import LocalWdaInit

    LocalWdaInit(udid=udid).restart_wda()

@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def start_wda(udid):
    """
    启动wda
    @param udid: IOS设备udid
    @return:
    """
    from .core.ios.local_wda import LocalWdaInit

    LocalWdaInit(udid=udid).run()

@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def stop_wda(udid):
    """
    杀掉wda
    @param udid: IOS设备udid
    @return:
    """
    from .core.ios.local_wda import LocalWdaInit

    LocalWdaInit(udid=udid).kill_wda_server()


# @main.command()
# @click.option('-p', '--platform', help="Specify the platform.")
# @click.option('-u', '--url', help="Specify the url.")
# def inspector(platform, url):
#     """
#     获取元素定位信息
#     @param platform: 平台，android、ios、web
#     @param url：针对web，需要录制的页面的url
#     @return:
#     """
#     import os
#     if platform in ['android', 'ios', 'web']:
#         os.system('weditor')
#     elif platform == 'web':
#         if not url:
#             raise KeyError('url不能为空')
#         os.system(f'playwright codegen {url}')
#     else:
#         raise KeyError('只支持android、ios、web')

