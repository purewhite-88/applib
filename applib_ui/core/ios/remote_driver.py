import shutil

import allure
import wda
import time
import subprocess

from .remote_wda import RemoteWdaInit

from applib_ui.utils.log import logger
from applib_ui.utils.common import general_file_path


class RemoteDriver:
    def __init__(
            self,
            udid: str,
            sib_path: str,
            sonic_host: str,
            sonic_user: str,
            sonic_pwd: str,
            bundle_id: str = None,
    ):
        if not sib_path:
            raise KeyError('sib_path不能为空')
        self.udid = udid
        self.bundle_id = bundle_id
        self.sib_path = sib_path
        logger.info(f"初始化远端wda: {udid}")
        # 占用设备，获取sib和wda连接信息
        self.remote_wda = RemoteWdaInit(udid, sonic_host, sonic_user, sonic_pwd)
        sib_cmd, wda_url = self.remote_wda.occupy_device()
        sib_cmd = sib_cmd.replace('sib', sib_path)
        self.sib_disconnect_cmd = sib_cmd.replace('connect', 'disconnect')
        # 通过sib连接
        print(sib_cmd)
        count = 60
        while count > 0:
            output = subprocess.getoutput(sib_cmd)
            print(output)
            if 'succeeded' in output:
                logger.info('sib已就绪')
                break
            else:
                logger.info('sib未就绪，5s后重试！')
            time.sleep(5)
            count -= 5
        else:
            # 释放设备
            self.remote_wda.release_device()
            raise KeyError('sib连接超时！')
        # 通过wda连接
        print(wda_url)
        count = 60
        while count > 0:
            output = subprocess.getoutput(sib_cmd)
            print(output)
            self.d = wda.Client(wda_url)
            if self.d.is_ready():
                logger.info('wda已就绪')
                break
            else:
                logger.info('wda未就绪, 5s后重试！')
            time.sleep(5)
            count -= 5
        else:
            # 释放设备
            self.remote_wda.release_device()
            raise KeyError('wda连接超时！')

    def uninstall_app(self, bundle_id: str):
        """
        卸载应用
        @return:
        """
        if self.bundle_id is None:
            if bundle_id is None:
                raise KeyError('bundle_id不能为空')
            else:
                self.bundle_id = bundle_id

        cmd = f"{self.sib_path} -u {self.udid} app uninstall -b {self.bundle_id}"
        print(cmd)
        output = subprocess.getoutput(cmd)
        print(output)

    def install_app(self, ipa_url, bundle_id: str = None):
        """
        安装应用
        @param ipa_url:
        @param bundle_id
        @return:
        """
        if self.bundle_id is None:
            if bundle_id is None:
                raise KeyError('bundle_id不能为空')
            else:
                self.bundle_id = bundle_id
        self.uninstall_app(self.bundle_id)
        cmd = f"{self.sib_path} -u {self.udid} app install -p {ipa_url}"
        print(cmd)
        output = subprocess.getoutput(cmd)
        print(output)

    def start_app(self, bundle_id: str = None):
        """
        启动应用
        @return:
        """
        if self.bundle_id is None:
            if bundle_id is None:
                raise KeyError('bundle_id不能为空')
            else:
                self.bundle_id = bundle_id
        logger.info(f"启动应用: {self.bundle_id}")
        self.d.app_start(self.bundle_id)

    def stop_app(self, bundle_id: str = None):
        """
        停止应用
        @return:
        """
        if self.bundle_id is None:
            if bundle_id is None:
                raise KeyError('bundle_id不能为空')
            else:
                self.bundle_id = bundle_id
        logger.info(f"停止应用: {self.bundle_id}")
        self.d.app_stop(self.bundle_id)

    def close(self):
        """
        清除xctest和relay进程
        @return:
        """
        # 释放sib连接
        output = subprocess.getoutput(self.sib_disconnect_cmd)
        print(output)
        # 释放设备
        self.remote_wda.release_device()

    def input(self, text: str):
        self.d.send_keys(text)

    def click(self, x, y):
        self.d.tap(x, y)

    def shot(self, file_name=None):
        file_path = general_file_path(file_name, self.udid)
        logger.info(f"截图保存至: {file_path}")
        self.d.screenshot(file_path)

        logger.info("截图上传allure报告")
        allure.attach.file(
            file_path,
            attachment_type=allure.attachment_type.PNG,
            name=f"{file_path}",
        )
        return file_path

    def unlock(self):
        self.d.unlock()

    def scale(self):
        return self.d.scale

    def _match(self, text):
        """
        判断元素是否存在当前页面
        @return:
        """
        _element = self.d(text=text)
        result = text if _element.wait(timeout=0.1,
                                       raise_error=False) else None
        return result

    def pop_check(self, watch_list: list, timeout=3):
        logger.info(f"开始弹窗检测: {watch_list}")
        # 多线程match，如果match到，获取第一个非None内容，进行点击
        # match完休息1s，如果休息3s也没有match到，就停止（定义一个flag，match到就清零）
        # 如果3s内仍然能match到就继续（如果flag大于3就停止）
        _build_info = ["允许", "使用App时允许", "始终允许"]
        if watch_list is True:
            loc_list = _build_info
        else:
            loc_list = list(set(_build_info + watch_list))
        flag = timeout
        while flag > 0:
            import concurrent.futures

            logger.info(f"匹配: {loc_list}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(self._match, loc_list)
                results = [item for item in results if item is not None]

            if results:
                logger.info(f"匹配到: {results}")
                try:
                    self.d(text=results[0]).click_exists(timeout=1)
                except:
                    pass
                logger.info("点击成功")
                flag = timeout
            else:
                logger.info("匹配失败")

            flag -= 1
            time.sleep(1)
        logger.info("结束检测")











