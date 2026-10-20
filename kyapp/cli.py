import click
from . import __version__
from .core.ios.local_wda import LocalWdaInit

@click.group()
@click.version_option(version=__version__, help="Show version.")
# 老是变，等最后定下来再搞，目前也没啥用
def main():
    pass


@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def restart_wda(udid):
    """
    重启wda
    @param udid: IOS设备udid
    @return:
    """
    LocalWdaInit(udid=udid).restart_wda()

@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def start_wda(udid):
    """
    启动wda
    @param udid: IOS设备udid
    @return:
    """
    LocalWdaInit(udid=udid).run()

@main.command()
@click.option('-u', '--udid', help="Specify the udid.")
def stop_wda(udid):
    """
    杀掉wda
    @param udid: IOS设备udid
    @return:
    """
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

