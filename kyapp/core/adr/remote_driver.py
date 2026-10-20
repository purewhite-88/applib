"""
@Author: kang.yang
@Date: 2025/4/10 10:59
"""
import allure
import time
import uiautomator2 as u2

from adbutils import adb
from .remote_adb import RemoteAdbInit
from kyapp.utils.log import logger
from kyapp.utils.common import general_file_path


class RemoteDriver:
    """
    https://github.com/openatx/adbutils
    """

    def __init__(
            self,
            serial: str,
            sonic_host: str,
            sonic_user: str,
            sonic_pwd: str,
            package: str = None
    ):
        """
        @param serial: 通过adb devices或者关于手机-序列号获取
        @param package: 通过adb shell pm list packages获取
        """
        logger.info(f'初始化远端设备连接: {serial}')
        self.serial = serial
        print('获取adb连接ip:port')
        self.remote_adb = RemoteAdbInit(serial, sonic_host, sonic_user, sonic_pwd)
        self.adb_server = self.remote_adb.occupy_device()
        print(self.adb_server)
        self.package = package
        print('连接远端adb服务')
        count = 15
        while count > 0:
            output = adb.connect(self.adb_server)
            print(output)
            if 'connected' in output:
                logger.info('adb服务已就绪')
                break
            else:
                logger.info('adb服务未就绪，1s后重试！')
                time.sleep(1)
        else:
            # 释放设备
            self.remote_adb.release_device()
            raise KeyError('adb服务连接超时！')

        device = adb.device(self.adb_server)
        self.d = u2.connect(device)

    def close(self):
        print('释放远端设备连接')
        # 释放设备
        self.remote_adb.release_device()
        # 断开adb连接
        output = adb.disconnect(self.adb_server)
        print(output)
        # 等待3s
        time.sleep(3)
        # 删除设备
        self.remote_adb.delete_offline_device()

    def uninstall_app(self, package: str = None):
        """
        卸载应用
        @return:
        """
        if self.package is None:
            if package is None:
                raise KeyError('package不能为空')
            else:
                self.d.app_uninstall(package)
        else:
            self.d.app_uninstall(self.package)

    def install_app(self, apk_url: str, package: str = None):
        """
        安装应用
        @return:
        """
        if self.package is None:
            if package is None:
                raise KeyError('package不能为空')
            else:
                self.d.app_install(package)
        else:
            self.d.app_install(self.package)
        self.d.app_install(apk_url)

    def start_app(self, package: str = None):
        """
        启动应用
        @return:
        """
        if self.package is None:
            if package is None:
                raise KeyError('package不能为空')
            else:
                self.d.app_start(package)
        else:
            self.d.app_start(self.package)

    def stop_app(self, package: str = None):
        """
        停止应用
        @return:
        """
        if self.package is None:
            if package is None:
                raise KeyError('package不能为空')
            else:
                self.d.app_stop(package)
        else:
            self.d.app_stop(self.package)

    def shot(self, file_name=None):
        """
        截图
        @param file_name:
        @return:
        """
        file_path = general_file_path(file_name, self.serial)
        logger.info(f"截图保存至: {file_path}")
        self.d.screenshot(file_path)

        logger.info("截图上传allure报告")
        allure.attach.file(
            file_path,
            attachment_type=allure.attachment_type.PNG,
            name=f"{file_path}",
        )
        return file_path

    def click(self, x, y):
        """
        点击坐标
        @param x:
        @param y:
        @return:
        """
        self.d.click(x, y)

    def input(self, *args, **kwargs):
        """
        输入
        @param args:
        @param kwargs:
        @return:
        """
        self.d.send_keys(*args, **kwargs)

    def shell(self, *args, **kwargs):
        """
        执行adb shell
        @param args:
        @param kwargs:
        @return:
        """
        self.d.shell(*args, **kwargs)

    def unlock(self):
        """
        解锁设备
        @return:
        """
        self.shell("input keyevent WAKEUP")
        self.d.swipe(0.1, 0.9, 0.9, 0.1)






