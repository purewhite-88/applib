"""
基于本机 scrcpy 命令行的安卓录屏。
"""
import os
import shutil
import signal
import subprocess
import tempfile
import time

import allure

from kyapp.utils.log import logger


def _find_scrcpy():
    path = shutil.which("scrcpy")
    if path:
        return path
    for candidate in ("/opt/homebrew/bin/scrcpy", "/usr/local/bin/scrcpy"):
        if os.path.isfile(candidate):
            return candidate
    return None


class ScrcpyRecorder:
    #: 启动失败后重启 scrcpy 的重试次数（adb 抖动、设备被占用等偶发问题）
    START_RETRY = 2

    def __init__(self, serial: str):
        self.serial = serial
        self.file_path = None
        self.proc = None
        self._log_file = None

    def start(self, file_path: str, timeout: float = 10) -> bool:
        """
        启动录屏：等录屏文件真正开始写数据才算成功，失败会重启 scrcpy 重试
        @param file_path: 输出文件
        @param timeout: 单次等待"文件开始写入"的上限
        @return: 是否成功启动；最终失败只记日志不抛异常（录屏是辅助能力，不该让功能用例失败）
        """
        scrcpy_bin = _find_scrcpy()
        if not scrcpy_bin:
            raise FileNotFoundError(
                "未找到 scrcpy，请先执行: brew install scrcpy"
            )

        self.file_path = file_path
        base_cmd = [
            scrcpy_bin,
            "-s", self.serial,
            "--record", file_path,
            "--no-playback",
            "--no-audio",
        ]
        last_error = ""
        for attempt in range(1, self.START_RETRY + 1):
            logger.info(f"开始录屏({attempt}/{self.START_RETRY}): {file_path}")
            # 每次重试前清掉上一次的残留文件，否则"文件非空"的判断会被旧文件骗过去
            if os.path.exists(file_path):
                os.remove(file_path)
            try:
                self._launch(base_cmd, timeout)
                logger.info(f"录屏已开始: {file_path}")
                return True
            except RuntimeError as e:
                last_error = str(e)
                logger.warning(f"第 {attempt}/{self.START_RETRY} 次启动录屏失败：{last_error}")
                # 清掉半死的进程，避免多个 scrcpy 抢同一个设备
                self._terminate(timeout=5)
                if attempt < self.START_RETRY:
                    time.sleep(0.5)

        logger.error(f"scrcpy 录屏没起来，本次不会生成录屏文件：{last_error}")
        return False

    def _launch(self, base_cmd, timeout: float):
        """起 scrcpy 并等它真的开始写文件（含 --no-window 不被支持时的回退）"""
        self.proc = self._popen(base_cmd + ["--no-window"])
        time.sleep(0.3)
        if self.proc.poll() is not None:
            log = self._read_log()
            if "unknown" in log.lower() or "unrecognized" in log.lower():
                logger.warning("当前 scrcpy 不支持 --no-window，回退后再启动")
                self.proc = self._popen(base_cmd)
            else:
                raise RuntimeError(f"scrcpy 启动失败: {log}")

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"scrcpy 启动失败: {self._read_log()}")
            if os.path.exists(self.file_path) and os.path.getsize(self.file_path) > 0:
                return
            time.sleep(0.2)
        raise RuntimeError(f"等待录屏文件写入超时({timeout}s)")

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

    def _signal_group(self, sig):
        if self.proc is None:
            return
        try:
            os.killpg(self.proc.pid, sig)
        except ProcessLookupError:
            pass

    def _terminate(self, timeout: float = 15):
        """SIGINT → SIGTERM → SIGKILL，逐级结束 scrcpy 进程组"""
        if self.proc is None or self.proc.poll() is not None:
            return
        self._signal_group(signal.SIGINT)
        try:
            self.proc.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            logger.warning("scrcpy SIGINT 未退出，尝试 SIGTERM")
        self._signal_group(signal.SIGTERM)
        try:
            self.proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            logger.error("scrcpy 停止超时，强制结束进程")
        self._signal_group(signal.SIGKILL)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    def stop(self):
        self._terminate(timeout=15)
        if self.proc is not None and self.proc.poll() not in (0, None, -signal.SIGINT, -signal.SIGTERM):
            logger.error(f"scrcpy 退出异常(returncode={self.proc.returncode}): {self._read_log()}")
        # 关掉日志前留一份，便于定位"为什么没录上"
        scrcpy_log = self._read_log()
        self.proc = None
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

        logger.error("录屏文件为空或不存在" + (f"；scrcpy 日志: {scrcpy_log[-300:]}" if scrcpy_log else ""))
        return None
