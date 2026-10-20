"""
@Author: kang.yang
@Date: 2025/4/9 16:03
"""
import allure
import wda
import os
import time
import subprocess

from .local_wda import LocalWdaInit

from kyapp.utils.log import logger
from kyapp.utils.common import general_file_path, general_video_path
from .recorder import WdaMjpegRecorder


class Driver(object):
    """
    https://github.com/openatx/facebook-wda
    """

    def __init__(
            self,
            udid: str,
            bundle_id: str = None,
        ):
        """
        手机udid
        @param udid: tidevice list获取
        @param bundle_id: tidevice applist获取
        """
        self.udid = udid
        self.bundle_id = bundle_id
        logger.info(f"初始化本地wda: {udid}")
        # tunnel-info 端口由框架自动分配（每台设备自动错开），无需传入
        self._wda = LocalWdaInit(udid)
        self.p1, self.p2, self.p3, self.wda_url = self._wda.run()
        self.tunnel_info_port = self._wda.tunnel_info_port
        print(self.wda_url)
        self._recorder = None
        self._new_client()
        if self.d.is_ready():
            logger.info('wda已就绪')
        else:
            logger.info('wda未就绪, 请检查wda服务')

    def _new_client(self):
        """
        新建一个 wda 客户端
        - 端口转发每次重建都会换本机端口，所以重连后必须换客户端，否则一直打到已经死掉的端口
        - facebook-wda 的 HTTP 请求超时是模块级 HTTP_TIMEOUT（默认 180s）：
          链路断开后一次元素查询能卡 3 分钟，这里收紧，让断链尽快抛出来交给上层恢复
          （可用 KYAPP_WDA_TIMEOUT 调整，注意 App 冷启动等慢请求也要留够时间）
        """
        if hasattr(wda, "HTTP_TIMEOUT"):
            wda.HTTP_TIMEOUT = float(os.environ.get("KYAPP_WDA_TIMEOUT", "60"))
        self.d = wda.Client(self.wda_url)
        return self.d

    def uninstall_app(self, bundle_id: str = None):
        """
        卸载应用
        @return:
        """
        if self.bundle_id is None:
            if bundle_id is None:
                raise KeyError('bundle_id不能为空')
            else:
                self.bundle_id = bundle_id

        cmd = f"tidevice -u {self.udid} uninstall {self.bundle_id}"
        print(cmd)
        output = subprocess.getoutput(cmd)
        if "Complete" in output.split()[-1]:
            logger.info(f"{self.udid} 卸载应用成功")
            return
        else:
            logger.info(f"{self.udid} 卸载应用成功")

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

        cmd = f"tidevice -u {self.udid} install {ipa_url}"
        print(cmd)
        output = subprocess.getoutput(cmd)
        if "Complete" in output.split()[-1]:
            logger.info(f"{self.udid} 安装应用成功")
            return
        else:
            logger.info(f"{self.udid} 安装应用失败")

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
        try:
            self.d.app_start(self.bundle_id)
        except Exception as e:
            logger.error(str(e))
            self.close()

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
        清除tunner、wda、relay进程
        @return:
        """
        # try:
        #     self.stop_record()
        # except Exception:
        #     pass
        try:
            self.p1.kill()
            self.p2.kill()
            self.p3.kill()
        except Exception as e:
            print(str(e))

    def reconnect(self):
        """断链后重建 tunnel/wda/端口转发，并换掉指向旧端口的 wda 客户端"""
        logger.info(f"reconnect wda for device： {self.udid}")
        self.close()
        # 重新拉起时端口由框架自动重新分配；tunnel 与 runwda 始终用同一个端口
        self._wda = LocalWdaInit(self.udid)
        self.p1, self.p2, self.p3, self.wda_url = self._wda.run()
        self.tunnel_info_port = self._wda.tunnel_info_port
        self._new_client()
        if self.d.is_ready():
            logger.info(f"{self.udid} wda 已重新就绪")
        return self.wda_url

    def is_alive(self, timeout: float = 3) -> bool:
        """
        tunnel + WDA 是否都还活着（轻量探针，不用等元素查询卡到超时才发现断链）
        @param timeout: tunnel 探针超时
        """
        if not self._wda.tunnel_alive(timeout):
            logger.warning(f"{self.udid} 的 tunnel 已断开")
            return False
        if not self.d.is_ready():
            logger.warning(f"{self.udid} 的 wda 无响应")
            return False
        return True

    def ensure_alive(self) -> bool:
        """
        断链检测 + 重建，用例开始前调一次即可（批次级重启的挂载点）
        @return: 链路是否可用；重建失败会记录日志并返回 False，不抛异常
        """
        if self.is_alive():
            return True
        logger.warning(f"{self.udid} 的 wda 链路不可用，重建 tunnel/wda/端口转发")
        try:
            self.reconnect()
        except Exception as e:
            logger.error(f"{self.udid} 重建失败：{str(e).splitlines()[0]}")
            return False
        return self.d.is_ready()

    def input(self, text: str):
        self.d.send_keys(text)

    def click(self, x, y):
        logger.info(f"点击坐标：{x}, {y}")
        self.d.click(x, y)

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

    def scale(self):
        return self.d.scale

    def unlock(self):
        self.d.unlock()

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

    def back(self):
        logger.info("返回上一页")
        self.d.swipe(0.01, 0.3, 0.9, 0.3, duration=1)

    def start_record(self, file_name: str = "record"):
        """
        开始录屏
        @param file_name: 录屏文件名
        @return: 录像路径；录制没起来返回 None（最终产物以 stop_record 的返回值为准）
        """
        if self._recorder is not None:
            self.stop_record()
        try:
            self.d.appium_settings({"mjpegServerFramerate": 10})
        except Exception as e:
            logger.warning(f"设置 mjpeg 帧率失败: {e}")
        file_path = general_video_path(file_name, self.udid)
        self._recorder = WdaMjpegRecorder(self.udid)
        if not self._recorder.start(file_path):
            # 没起来：原因已由 recorder 打成 ERROR，这里返回 None，别让调用方以为正在录
            self._recorder = None
            return None
        return file_path

    def stop_record(self):
        """
        停止录屏并上传allure
        @return:
        """
        if self._recorder is None:
            return None
        file_path = self._recorder.stop()
        self._recorder = None
        return file_path
