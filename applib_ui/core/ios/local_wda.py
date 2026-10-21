import contextlib
import fcntl
import json
import os
import shutil
import signal
import time
import subprocess
import urllib.error
import urllib.request

from applib_ui.utils.log import logger
from applib_ui.utils.common import get_free_port

# tunnel-info 端口被占用、或隧道没建出来时，重建 agent 的重试次数
_TUNNEL_RESTART_RETRY = 2
# 等本设备隧道真正可用的上限（秒）
# go-ios 的 `tunnel start` 只保证 HTTP-API 起来，隧道是后台异步建的，
# 且首轮建失败后会退避 30s 再试，所以这里必须大于 30s，否则会在退避窗口内误判失败
_TUNNEL_READY_TIMEOUT = 40
# ---------------- tunnel-info 端口池 ----------------
# go-ios 的 tunnel-info 端口和 userspace 数据面端口是"连号"关系：
#   数据面端口 = tunnel-info-port + 1、+2、+3…（内部 portOffset 从 1 起，且只增不减）
# 所以这个端口绝不能从 get_free_port() 里取：它拿的是内核 ephemeral 端口
# （macOS net.inet.ip.portrange.first=49152），而且基本是连号下发，两台设备必然互相踩：
#   A 的 tunnel-info=50518、B 的 tunnel-info=50517
#   → B 的数据面要 listen 50518，正好是 A 的 HTTP 端口 → bind: address already in use
# 因此改成：每台设备固定占一个"窗口"，窗口整体落在 ephemeral 范围之外，
# 窗口内 100 个端口预留给该设备的连号数据面端口，窗口之间互不重叠。
# 起始端口可用 APPLIB_UI_TUNNEL_PORT_BASE 调整。
_PORT_POOL_BASE = int(os.environ.get("APPLIB_UI_TUNNEL_PORT_BASE", "21800"))
_PORT_POOL_STRIDE = 100
_PORT_POOL_SIZE = 20
_PORT_REGISTRY = os.path.join(os.path.expanduser("~"), ".applib-ui", "tunnel_ports.json")
# 每台设备的 pair record 独立目录
# go-ios 默认把 pair record 写到当前工作目录，多个 tunnel 进程共用同一 CWD 会互相干扰，
# 这里按 udid 隔离（也顺带避开 macOS 26 对 default 路径的限制）
_PAIR_RECORD_ROOT = os.path.join(os.path.expanduser("~"), ".applib-ui", "go-ios")
# 子进程输出目录，按 udid 分开；tunnel/runwda 的失败原因都落在里面
_LOG_ROOT = os.path.join(os.path.expanduser("~"), ".applib-ui", "logs")


@contextlib.contextmanager
def _port_pool_lock():
    """端口池注册表的跨进程互斥（multiprocessing 下多个子进程会同时分配）"""
    os.makedirs(os.path.dirname(_PORT_REGISTRY), exist_ok=True)
    with open(f"{_PORT_REGISTRY}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _read_port_registry() -> dict:
    try:
        with open(_PORT_REGISTRY) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _alloc_tunnel_port(udid: str, avoid: set = None) -> int:
    """
    给设备分配一个固定的 tunnel-info 端口窗口首端口
    @param udid: 设备udid
    @param avoid: 需要避开的端口（重试换窗口时传入）
    """
    avoid = avoid or set()
    with _port_pool_lock():
        registry = _read_port_registry()
        slot = registry.get(udid)
        if slot is not None:
            port = _PORT_POOL_BASE + slot * _PORT_POOL_STRIDE
            if port not in avoid:
                return port
        used = set(registry.values())
        for slot in range(_PORT_POOL_SIZE):
            port = _PORT_POOL_BASE + slot * _PORT_POOL_STRIDE
            if slot in used or port in avoid:
                continue
            registry[udid] = slot
            with open(_PORT_REGISTRY, "w") as f:
                json.dump(registry, f, indent=2)
            return port
    raise RuntimeError(
        f"tunnel-info 端口池已用尽（{_PORT_POOL_SIZE} 个窗口 × {_PORT_POOL_STRIDE}），"
        f"可用 APPLIB_UI_TUNNEL_PORT_BASE 调整起始端口"
    )


# ---------------- 子进程环境与进程查找 ----------------
def _child_env() -> dict:
    """
    给 go-ios 子进程用的环境变量

    go-ios 的 configureCLI 对**每条**命令都会跑 startAgentFromEnvironment()：
    只要环境里有 ENABLE_GO_IOS_AGENT=user/kernel，它就会在默认端口(28100)上再起一个
    **不带 --udid** 的 agent，那个 agent 会给所有已连设备建隧道，
    于是同一条 udid 会同时存在两条隧道；而且它的命令行里没有 --udid，按 udid 匹配根本杀不掉。
    框架自己管理 per-device agent，所以这几个变量必须从子进程环境里摘掉。
    """
    ignored = ("ENABLE_GO_IOS_AGENT", "GO_IOS_AGENT_HOST", "GO_IOS_AGENT_PORT", "GO_IOS_UDID")
    dropped = [key for key in ignored if key in os.environ]
    if dropped:
        logger.debug(f"已从 go-ios 子进程环境里摘掉: {dropped}")
    return {key: value for key, value in os.environ.items() if key not in ignored}


def _cmdlines(pattern: str) -> dict:
    """
    按命令行找进程：pgrep -fl 一次就能拿到「pid + 完整命令行」，比 pgrep 再逐个 ps 少一堆 fork
    @param pattern: pgrep -f 的正则（匹配整条命令行）
    @return: {pid: 参数 token 列表}
    """
    output = subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True).stdout
    cmdlines = {}
    for line in output.splitlines():
        pid, _, cmdline = line.strip().partition(" ")
        if pid.isdigit() and cmdline.strip():
            cmdlines[int(pid)] = cmdline.split()
    return cmdlines


def _pid_alive(pid: int) -> bool:
    """
    进程是否还在
    注：僵尸进程这里也会返回 True（父进程还没收尸），所以调用方要先给自家子进程 poll() 收尸
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 存在，但不属于当前用户


def _cmd_udid(cmd: list):
    """
    取命令行里的 --udid 值

    必须同时认两种写法：`--udid=xxx`（docopt 等号式，框架自己用）和 `--udid xxx`（空格式，
    手工敲的 / 别的工具起的常见这样）。只认等号式的话，残留的手工 agent 会被判定成
    "不是本设备"，于是清理时被跳过 —— 这正是"一个 udid 两条 tunnel 且杀不掉"的原因之一。
    @param cmd: 命令行 token 列表
    @return: udid 或 None
    """
    for index, token in enumerate(cmd):
        if token.startswith("--udid="):
            return token.split("=", 1)[1]
        if token == "--udid" and index + 1 < len(cmd):
            return cmd[index + 1]
    return None


def tunnel_processes() -> dict:
    """机器上所有 ios tunnel start 进程（含手工起的、不带 --udid 的全局 agent）"""
    return {pid: cmd for pid, cmd in _cmdlines("ios tunnel start").items()
            if "tunnel" in cmd and "start" in cmd}


def _kill_pids(pids: list, tag: str, timeout: float = 8, reap=None) -> bool:
    """
    先 SIGTERM，超时再 SIGKILL，并确认进程真的退出了
    @param pids: 目标进程
    @param tag: 日志里的人类可读描述
    @param timeout: 等 SIGTERM 生效的上限
    @param reap: 可选，收尸回调（收自己起的子进程，避免僵尸被误判成还活着）
    @return: 是否已清理干净
    """
    if not pids:
        return True
    logger.info(f"清理 {tag}: {pids}")

    def signal_pid(pid, sig):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass  # 已经退了
        except PermissionError:
            logger.warning(f"没有权限结束进程 {pid}（如果是 sudo 起的，需要手工清理）")

    for pid in pids:
        signal_pid(pid, signal.SIGTERM)
    alive = pids
    deadline = time.time() + timeout
    while alive and time.time() < deadline:
        if reap is not None:
            reap()
        alive = [pid for pid in alive if _pid_alive(pid)]
        time.sleep(0.2)
    if alive:
        logger.warning(f"{tag} 收到 SIGTERM 后未退出，补 SIGKILL: {alive}")
        for pid in alive:
            signal_pid(pid, signal.SIGKILL)
        time.sleep(0.5)
        if reap is not None:
            reap()
        alive = [pid for pid in alive if _pid_alive(pid)]
    if alive:
        logger.error(f"[✗] {tag} 未清理干净，仍在运行: {alive}")
        return False
    logger.info(f"[✓] 已清理 {tag}")
    return True


def kill_all_tunnels(keep_udid: str = None) -> list:
    """
    清掉机器上所有 tunnel agent（含手工起的、不带 --udid 的全局 agent）

    用途：重跑前把双 tunnel 清干净（`python -m applib_ui.core.ios.local_wda kill-all`）
    @param keep_udid: 保留该设备的 agent，其余照杀
    @return: 被清理的 pid 列表
    """
    killed = []
    for pid, cmd in tunnel_processes().items():
        udid = _cmd_udid(cmd)
        if keep_udid is not None and udid == keep_udid:
            logger.info(f"保留 {keep_udid} 的 tunnel agent(pid={pid})")
            continue
        _kill_pids([pid], f"tunnel agent(pid={pid}, udid={udid or '全局'})")
        killed.append(pid)
    return killed


class LocalWdaInit:
    """
    本地wda初始化

    多真机并发说明：
        go-ios 的 tunnel-info HTTP-API 是主机级资源，不随 udid 隔离。
        每台设备必须用不同的 --tunnel-info-port，且 runwda 必须用同一个端口查询隧道信息，
        否则 runwda 找不到自己的隧道。
        （官方建议：one per device on its own --tunnel-info-port）
        另外这个端口只是"窗口首端口"：go-ios 会用 port+1、port+2… 做 userspace 数据面监听，
        所以端口必须按窗口分配、且整体落在系统 ephemeral 范围之外，
        否则两台设备的连号区间会互相踩（详见 _PORT_POOL_BASE 处的注释）。

    就绪判定说明：
        `ios tunnel start` 打印 "Tunnel server started" 只代表 HTTP-API 起来了，
        此时隧道可能还在异步建立（失败还会退避 30s 再重试）。
        而 `ios runwda` 在 /tunnel/<udid> 查不到隧道时既不等待也不报错，
        会静默退化成"没有隧道的设备"，随后在连 testmanagerd 时失败退出，
        表现到外层就是 "wda启动失败"。
        所以启动 runwda 之前必须轮询 /tunnel/<udid>，不能靠 sleep 猜时间。
    """

    def __init__(self, udid: str):
        """
        @param udid: 设备udid
        """
        self.udid = udid
        # tunnel-info 端口从固定窗口池里按 udid 分配（每台设备一个窗口，不会互相踩）
        self.tunnel_info_port = None
        # 本次已经失败过的窗口端口，重试时避开
        self._failed_ports = set()
        # 本实例起过的子进程，用于收尸（避免僵尸进程被 _pid_alive 误判成还活着）
        self._children = []
        # pair record 目录固定到 ~/.applib-ui/go-ios/<udid>，避免 go-ios 默认写入当前工作目录
        self.pair_record_dir = os.path.join(_PAIR_RECORD_ROOT, udid)
        # 进程日志目录固定到 ~/.applib-ui/logs/<udid>
        self.log_dir = os.path.join(_LOG_ROOT, udid)

    # ---------------- 命令构造 ----------------
    def _tunnel_cmd(self, tunnel_info_port: int):
        ios_path = shutil.which('ios')
        return (f"{ios_path} tunnel start --userspace --udid={self.udid} "
                f"--tunnel-info-port={tunnel_info_port} "
                f"--pair-record-path={self.pair_record_dir}")

    def _wda_cmd(self, tunnel_info_port: int):
        ios_path = shutil.which('ios')
        # --tunnel-info-port 必须与 tunnel 一致，否则 runwda 查不到本设备的隧道
        return (f"{ios_path} runwda --udid={self.udid} "
                f"--tunnel-info-port={tunnel_info_port} "
                f"--bundleid=com.lute.WebDriverAgentRunner.xctrunner "
                f"--testrunnerbundleid=com.lute.WebDriverAgentRunner.xctrunner "
                f"--xctestconfig=WebDriverAgentRunner.xctest "
                f"--env USE_PORT=8100 "
                f"--env MJPEG_SERVER_PORT=9100 "
                f"--nojson")

    # ---------------- 日志与探针 ----------------
    def _log_path(self, name: str) -> str:
        return os.path.join(self.log_dir, f"{name}.log")

    def _open_log(self, name: str):
        """打开本设备某个子进程的日志文件，返回 (文件对象, 本次写入的起始偏移)"""
        os.makedirs(self.log_dir, exist_ok=True)
        path = self._log_path(name)
        start = os.path.getsize(path) if os.path.exists(path) else 0
        fd = open(path, "ab")
        fd.write(f"\n{'=' * 20} {time.strftime('%Y-%m-%d %H:%M:%S')} {name} {'=' * 20}\n".encode())
        fd.flush()
        return fd, start

    def _log_tail(self, name: str, start: int = 0, lines: int = 15) -> str:
        """读取某次启动之后的日志末尾若干行，用来拼进异常信息"""
        try:
            with open(self._log_path(name), "rb") as f:
                f.seek(start)
                content = f.read().decode("utf-8", "ignore")
        except OSError:
            return ""
        return "\n".join(content.splitlines()[-lines:])

    @staticmethod
    def _tunnel_api(tunnel_info_port: int, path: str, timeout: float = 2):
        """
        访问 go-ios 的 tunnel-info HTTP-API
        @return: (状态码, JSON)；进程没起来或连不上时返回 (None, None)
        """
        url = f"http://127.0.0.1:{tunnel_info_port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                body = resp.read()
                return resp.status, json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            # 404/503 都是正常语义（隧道还没建好 / 首轮设备更新没结束），不算连不上
            return e.code, None
        except Exception:
            return None, None

    def tunnel_alive(self, timeout: float = 3) -> bool:
        """
        本设备的隧道在 agent 里是否还在（轻量探针，用于断链检测）
        链路断了以后没必要等元素查询卡到 HTTP 超时才反应
        """
        if self.tunnel_info_port is None:
            return False
        status, info = self._tunnel_api(self.tunnel_info_port, f"/tunnel/{self.udid}", timeout)
        return status == 200 and bool(info and info.get("udid"))

    def _wait_tunnel_ready(self, proc: subprocess.Popen, tunnel_info_port: int, start: int,
                           timeout: float = _TUNNEL_READY_TIMEOUT):
        """
        等 tunnel 进程活着、HTTP-API 就绪、并且本设备的隧道确实建出来了
        @param proc: tunnel 子进程
        @param tunnel_info_port: tunnel-info 端口
        @param start: 本次日志起始偏移，用于超时时截取日志
        @param timeout: 等待上限（秒）
        """
        deadline = time.time() + timeout
        api_ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"tunnel进程已退出(returncode={proc.returncode}, "
                    f"tunnel-info-port={tunnel_info_port})，"
                    f"日志({self._log_path('tunnel')})末尾：\n{self._log_tail('tunnel', start)}"
                )
            if not api_ready:
                # /ready 返回 200 只代表首轮设备更新跑完了，隧道仍可能在后台建
                status, _ = self._tunnel_api(tunnel_info_port, "/ready")
                api_ready = status == 200
            if api_ready:
                status, info = self._tunnel_api(tunnel_info_port, f"/tunnel/{self.udid}")
                if status == 200 and info and info.get("udid"):
                    logger.info(f"隧道已就绪(tunnel-info-port={tunnel_info_port}): {info}")
                    return
            time.sleep(0.5)
        raise RuntimeError(
            f"等待隧道就绪超时({timeout}s, tunnel-info-port={tunnel_info_port})，"
            f"日志({self._log_path('tunnel')})末尾：\n{self._log_tail('tunnel', start)}"
        )

    # ---------------- 进程启动 ----------------
    def _start_tunnel(self, tunnel_info_port: int):
        # 起新的之前先清干净本设备残留的 agent（不限端口）：
        # 原来只在"当前端口被占用"时才清理，残留 agent 蹲在别的窗口（换窗口重试之后）就漏杀了，
        # 于是同一个 udid 会同时存在两条隧道
        self.kill_ios_tunnel()
        tunner_cmd_str = self._tunnel_cmd(tunnel_info_port)
        print(tunner_cmd_str)
        log_fd, start = self._open_log("tunnel")
        p1 = subprocess.Popen(
            tunner_cmd_str.split(),
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            env=_child_env(),
        )
        self._children.append(p1)
        # 子进程已持有 fd 副本，父进程这份直接关掉
        log_fd.close()
        try:
            self._wait_tunnel_ready(p1, tunnel_info_port, start)
        except RuntimeError:
            p1.kill()
            raise
        logger.info(f"tunner启动成功(tunnel-info-port={tunnel_info_port})，日志: {self._log_path('tunnel')}")
        return p1

    def _start_wda(self, tunnel_info_port: int):
        wda_cmd_str = self._wda_cmd(tunnel_info_port)
        print(wda_cmd_str)
        log_fd, start = self._open_log("runwda")
        p2 = subprocess.Popen(
            wda_cmd_str.split(),
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            env=_child_env(),
        )
        self._children.append(p2)
        log_fd.close()
        time.sleep(3)
        if p2.poll() is not None:
            raise RuntimeError(
                f"wda启动失败(returncode={p2.returncode}, tunnel-info-port={tunnel_info_port})，"
                f"日志({self._log_path('runwda')})末尾：\n{self._log_tail('runwda', start)}"
            )
        logger.info(f"wda启动成功，日志: {self._log_path('runwda')}")
        return p2

    def _start_relay(self):
        """端口转发：设备侧 8100 -> 本机空闲端口"""
        local_port = get_free_port()
        tidevice_path = shutil.which("tidevice")
        proxy_cmd_str = f'{tidevice_path} -u {self.udid} relay {local_port} 8100'
        print(proxy_cmd_str)
        log_fd, start = self._open_log("relay")
        p3 = subprocess.Popen(
            proxy_cmd_str.split(),
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            env=_child_env(),
        )
        self._children.append(p3)
        log_fd.close()
        time.sleep(3)
        if p3.poll() is not None:
            raise RuntimeError(
                f"proxy启动失败(returncode={p3.returncode})，"
                f"日志({self._log_path('relay')})末尾：\n{self._log_tail('relay', start)}"
            )
        logger.info(f"proxy启动成功，日志: {self._log_path('relay')}")
        return p3, local_port

    def run(self):
        """
        启动 tunnel、wda、端口转发
        @return: p1(tunnel), p2(wda), p3(relay), wda_url
        """
        p1 = p2 = p3 = None
        os.makedirs(self.pair_record_dir, exist_ok=True)
        try:
            # 启动tunnel：端口从固定窗口池按 udid 分配（每设备一个窗口），失败就换窗口重建 agent
            for attempt in range(_TUNNEL_RESTART_RETRY):
                if self.tunnel_info_port is None:
                    self.tunnel_info_port = _alloc_tunnel_port(self.udid, self._failed_ports)
                try:
                    p1 = self._start_tunnel(self.tunnel_info_port)
                    break
                except RuntimeError as e:
                    self._failed_ports.add(self.tunnel_info_port)
                    if attempt == _TUNNEL_RESTART_RETRY - 1:
                        raise
                    logger.warning(f"{e}\n隧道未建起，换端口窗口重建 agent 重试({attempt + 1}/{_TUNNEL_RESTART_RETRY})")
                    self.tunnel_info_port = None
                    time.sleep(1)

            # 启动wda：隧道已确认就绪，用与 tunnel 相同的 tunnel-info-port
            p2 = self._start_wda(self.tunnel_info_port)

            p3, local_port = self._start_relay()

            wda_url = f'http://localhost:{local_port}'
            logger.info(wda_url)
            return p1, p2, p3, wda_url
        except Exception as e:
            # 控制台只打一行摘要，完整现场在 ~/.applib-ui/logs/<udid>/ 下的日志里
            logger.error(f"wda初始化失败：{str(e).splitlines()[0]}")
            # 三个进程都要尝试收掉：任何一个为 None 都不能让后面两个漏杀
            for p in (p1, p2, p3):
                try:
                    if p is not None:
                        p.kill()
                except Exception:
                    pass
            self._reap_children()
            logger.info("wda清理完毕")
            # 必须抛出原始异常：上层是 `p1, p2, p3, url = self._wda.run()`，
            # 吞掉异常只会让上层报 unpack 失败，真正的失败原因就丢了
            raise

    # ---------------- 进程清理 ----------------
    def _reap_children(self):
        """给本实例起过的子进程收尸（poll 顺带 reap），否则僵尸进程会被当成还活着"""
        self._children = [proc for proc in self._children if proc.poll() is None]

    def _kill_pids(self, pids: list, name: str, timeout: float = 8) -> bool:
        """清掉本设备的某类进程（先 SIGTERM，超时补 SIGKILL，确认退出后才算成功）"""
        return _kill_pids(pids, f"{self.udid} 的{name}", timeout, reap=self._reap_children)

    def _tunnel_agent_pids(self) -> list:
        """本设备自己的 tunnel agent（--udid=X / --udid X 两种写法都认，含所有窗口端口）"""
        return [pid for pid, cmd in tunnel_processes().items() if _cmd_udid(cmd) == self.udid]

    @staticmethod
    def _global_agent_pids() -> list:
        """不带 udid 的全局 agent（go-ios 的 RunAgent 起的，会给所有设备建隧道）"""
        return [pid for pid, cmd in tunnel_processes().items() if _cmd_udid(cmd) is None]

    def kill_ios_tunnel(self) -> bool:
        """
        清掉本设备所有 tunnel agent（不区分窗口端口）

        注意：go-ios 自己也可能起一个"不带 --udid"的全局 agent（见 _child_env 的说明），
        它会给所有设备建隧道，和框架的 per-device agent 一起造成"一个 udid 两条隧道"；
        但它的命令行里没有 --udid，按 udid 匹配杀不到，也不该由框架代杀（可能是别的工具在用），
        所以这里只做告警。
        """
        global_pids = self._global_agent_pids()
        if global_pids:
            logger.warning(
                f"检测到不带 --udid 的全局 tunnel agent: {global_pids}，"
                f"它会给所有已连设备建隧道，导致同一台设备出现两条隧道"
                f"（常见原因是环境变量 ENABLE_GO_IOS_AGENT=user/kernel）；"
                f"它不是本设备专属进程，框架不代为清理，需要时请手工 kill"
            )
        return self._kill_pids(self._tunnel_agent_pids(), "tunnel")

    def kill_ios_wda(self) -> bool:
        """清掉本设备的 runwda（--udid=X / --udid X 两种写法都认）"""
        pids = [pid for pid, cmd in _cmdlines("ios runwda").items()
                if "runwda" in cmd and _cmd_udid(cmd) == self.udid]
        return self._kill_pids(pids, "wda")

    def kill_tidevice_relay(self) -> bool:
        """清掉本设备的 WDA 端口转发（只清 8100 那条，别误杀录屏用的 9100）"""
        pids = [pid for pid, cmd in _cmdlines(f"tidevice -u {self.udid} relay").items()
                if "relay" in cmd and self.udid in cmd and "8100" in cmd]
        return self._kill_pids(pids, "端口转发")

    def kill_wda_server(self):
        self.kill_ios_tunnel()
        self.kill_ios_wda()
        self.kill_tidevice_relay()

    def restart_wda(self):
        logger.info(f"重启设备{self.udid}的wda服务")
        self.kill_wda_server()
        # 复用已分配的 tunnel-info 端口，保证与后续 runwda 查询一致
        return self.run()


def _print_tunnel_status():
    procs = tunnel_processes()
    if not procs:
        print("当前没有 ios tunnel 进程")
        return
    print(f"当前有 {len(procs)} 个 ios tunnel 进程：")
    for pid, cmd in procs.items():
        print(f"  pid={pid}  udid={_cmd_udid(cmd) or '(全局，无 --udid)'}")
        print(f"      {' '.join(cmd)}")


if __name__ == '__main__':
    import sys

    usage = ("用法: python -m applib_ui.core.ios.local_wda <命令>\n"
             "  status                  列出机器上所有 ios tunnel 进程（含手工起的）\n"
             "  kill-all [<udid>]       清掉所有 tunnel agent（给 udid 则保留该设备的）\n"
             "  restart <udid>          重建某台设备的 tunnel/wda/端口转发")
    args = sys.argv[1:]
    action = args[0] if args else "status"
    if action == "status":
        _print_tunnel_status()
    elif action == "kill-all":
        keep = args[1] if len(args) > 1 else None
        killed = kill_all_tunnels(keep)
        print(f"已清理 {len(killed)} 个 tunnel agent" + (f"，保留 {keep}" if keep else ""))
    elif action == "restart" and len(args) > 1:
        LocalWdaInit(args[1]).restart_wda()
    else:
        print(usage)
