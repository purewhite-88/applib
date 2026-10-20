"""
基于 WDA MJPEG(9100) + ffmpeg 的 iOS 录屏。
"""
import os
import shutil
import signal
import subprocess
import tempfile
import time

import allure

from kyapp.utils.common import get_free_port
from kyapp.utils.log import logger


def _find_ffmpeg():
    path = shutil.which("ffmpeg")
    if path:
        return path
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.isfile(candidate):
            return candidate
    return None


def _find_tidevice():
    path = shutil.which("tidevice")
    if path:
        return path
    for candidate in ("/opt/homebrew/bin/tidevice", "/usr/local/bin/tidevice"):
        if os.path.isfile(candidate):
            return candidate
    return None


class WdaMjpegRecorder:
    #: 启动失败后重启（端口转发 + ffmpeg）的重试次数
    START_RETRY = 2

    def __init__(self, udid: str):
        self.udid = udid
        self.file_path = None
        self.proc = None
        self.relay_proc = None
        self._log_file = None
        self.local_port = None

    def start(self, file_path: str, timeout: float = 15) -> bool:
        """
        启动录屏：等录屏文件真正开始写数据才算成功，失败会重建转发 + ffmpeg 重试
        @param file_path: 输出文件
        @param timeout: 单次等待"文件开始写入"的上限
        @return: 是否成功启动；最终失败只记日志不抛异常（录屏是辅助能力，不该让功能用例失败）
        """
        ffmpeg_bin = _find_ffmpeg()
        if not ffmpeg_bin:
            raise FileNotFoundError("未找到 ffmpeg，请先执行: brew install ffmpeg")
        tidevice_bin = _find_tidevice()
        if not tidevice_bin:
            raise FileNotFoundError("未找到 tidevice")

        self.file_path = file_path
        last_error = ""
        for attempt in range(1, self.START_RETRY + 1):
            logger.info(f"开始录屏({attempt}/{self.START_RETRY}): {file_path}")
            # 每次重试前清掉上一次的残留文件，否则"文件非空"的判断会被旧文件骗过去
            if os.path.exists(file_path):
                os.remove(file_path)
            try:
                self._launch(ffmpeg_bin, tidevice_bin, timeout)
                logger.info(f"录屏已开始: {file_path}")
                return True
            except RuntimeError as e:
                last_error = str(e)
                logger.warning(f"第 {attempt}/{self.START_RETRY} 次启动录屏失败：{last_error}")
                # 转发和 ffmpeg 都清掉，避免残留进程占着设备端口
                self._stop_proc(self.proc, "ffmpeg")
                self.proc = None
                self._stop_relay()
                if attempt < self.START_RETRY:
                    time.sleep(0.5)

        logger.error(f"iOS 录屏没起来，本次不会生成录屏文件：{last_error}")
        return False

    def _launch(self, ffmpeg_bin, tidevice_bin, timeout: float):
        """建端口转发 + 起 ffmpeg，并等它真的开始写文件"""
        self.local_port = get_free_port()
        logger.info(f"转发 WDA MJPEG: 本地 {self.local_port} -> 设备 9100")
        self.relay_proc = subprocess.Popen(
            [tidevice_bin, "-u", self.udid, "relay", str(self.local_port), "9100"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)
        if self.relay_proc.poll() is not None:
            raise RuntimeError("WDA MJPEG 端口转发失败")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "mjpeg",
            "-i", f"http://127.0.0.1:{self.local_port}",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            self.file_path,
        ]
        self.proc = self._popen(cmd)

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"ffmpeg 启动失败: {self._read_log()}")
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                return
            time.sleep(0.2)
        raise RuntimeError(f"等待录屏文件写入超时({timeout}s)；ffmpeg 日志: {self._read_log()[:300]}")

    def _popen(self, cmd):
        self._close_log()
        self._log_file = tempfile.TemporaryFile()
        return subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def _read_log(self):
        if self._log_file is None:
            return ""
        self._log_file.seek(0)
        return self._log_file.read().decode("utf-8", errors="ignore").strip()

    def _close_log(self):
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def _signal_group(self, proc, sig):
        if proc is None:
            return
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass

    def _stop_proc(self, proc, name):
        """SIGINT → SIGTERM → SIGKILL，逐级结束进程组"""
        if proc is None or proc.poll() is not None:
            return
        self._signal_group(proc, signal.SIGINT)
        try:
            proc.wait(timeout=15)
            return
        except subprocess.TimeoutExpired:
            logger.warning(f"{name} SIGINT 未退出，尝试 SIGTERM")
        self._signal_group(proc, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            logger.error(f"{name} 停止超时，强制结束进程")
        self._signal_group(proc, signal.SIGKILL)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    def _stop_relay(self):
        self._stop_proc(self.relay_proc, "tidevice relay")
        self.relay_proc = None

    def stop(self):
        self._stop_proc(self.proc, "ffmpeg")
        if self.proc is not None and self.proc.poll() not in (
            0, None, -signal.SIGINT, -signal.SIGTERM, 255
        ):
            logger.error(f"ffmpeg 退出异常(returncode={self.proc.returncode}): {self._read_log()}")
        # 关掉日志前留一份，便于定位"为什么没录上"
        ffmpeg_log = self._read_log()
        self.proc = None
        self._stop_relay()
        self._close_log()

        if self.file_path and os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
            logger.info(f"录屏保存至: {self.file_path}")
            logger.info("录屏上传allure报告")
            allure.attach.file(
                self.file_path,
                attachment_type=allure.attachment_type.MP4,
                name=self.file_path,
            )
            return self.file_path

        logger.error("录屏文件为空或不存在" + (f"；ffmpeg 日志: {ffmpeg_log[-300:]}" if ffmpeg_log else ""))
        return None
