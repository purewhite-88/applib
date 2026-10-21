import random
import socket
import time
import os

# 本进程已经发出去过的路径，避免同一毫秒内两次调用拿到同一个文件名
_ISSUED_PATHS = set()


def _general_media_path(file_name, relative_path, suffix, tag=None):
    """
    生成截图/录屏的文件路径
    @param file_name: 业务侧传的名字
    @param relative_path: 存放目录
    @param suffix: 文件后缀
    @param tag: 设备标识（udid/serial）
    @return: 文件路径
    """
    if not file_name:
        raise ValueError("文件名不能为空")

    # 把文件名处理成test.png的样式
    file_name = str(file_name)
    if "." in file_name:
        file_name = file_name.split(r".")[0]
    # 不能先判断再 mkdir：多设备并发时两个进程会同时看到目录不存在，其中一个 mkdir 抛已存在
    os.makedirs(relative_path, exist_ok=True)

    # 时间戳精确到毫秒，再加设备标识
    # 多设备并发时两个进程会在同一秒内取时间戳，只精确到秒会算出同一个文件名，
    # 后写的把前面的覆盖掉（录屏尤其明显：两个 ffmpeg 写同一个文件，最后只剩一个）
    time_str = f"{time.strftime('%Y%m%d%H%M%S')}{int(time.time() * 1000) % 1000:03d}"
    stem = "_".join(part for part in (time_str, tag, file_name) if part)
    file_path = os.path.join(relative_path, f"{stem}{suffix}")
    # 撞车就补序号：文件已存在，或本进程已经发出过同名路径
    index = 2
    while os.path.exists(file_path) or file_path in _ISSUED_PATHS:
        file_path = os.path.join(relative_path, f"{stem}_{index}{suffix}")
        index += 1
    _ISSUED_PATHS.add(file_path)
    return file_path


def general_file_path(file_name, tag=None):
    """
    截图路径
    @param tag: 设备标识（udid/serial），多设备并发时用来区分文件
    """
    return _general_media_path(file_name, "shots", ".jpg", tag)


def general_video_path(file_name, tag=None):
    """
    录屏路径
    @param tag: 设备标识（udid/serial），多设备并发时用来区分文件
    """
    return _general_media_path(file_name, "videos", ".mp4", tag)


def is_port_in_use(port: int) -> bool:
    """判断端口是否已占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def get_free_port():
    """获取空闲端口"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        try:
            return s.getsockname()[1]
        finally:
            s.close()
    except OSError:
        # bind 0 will fail on Manjaro, fallback to random port
        # https://github.com/openatx/adbutils/issues/85
        for _ in range(20):
            port = random.randint(10000, 20000)
            if not is_port_in_use(port):
                return port
        raise RuntimeError("No free port found")


