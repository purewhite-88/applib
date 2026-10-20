import pytest
from .conf import App
from kyapp.utils.log import logger

# 支持的平台：case.py / element.py 都是按 `App.platform == 'ios'` 分叉的，
# 写错（iOS / android 拼错）会静默落进 Android 分支，拿着 iPhone 的 udid 去连 adb
_PLATFORMS = ('ios', 'android')
# 一次运行期内由入口设置、其它地方直接读的"会话参数"
_APP_FIELDS = ('did', 'pkg', 'platform', 'pop_list')


class TestMain(object):
    """
    测试框架入口

    会话参数（did/pkg/platform/watch_list）统一在这里落到 App 上，用的时候直接读 App 即可，
    不必层层透传；只在本层用一次的参数（case_path/report_path/rerun）保持函数参数，不进 App。
    注意 App 是**进程级**全局：多进程（multiprocessing）下每个子进程要各自调一次入口，
    否则 App 是空的。
    """

    def __init__(
            self,
            case_path: str = None,
            report_path: str = 'report',
            did: str = None,
            pkg: str = None,
            platform: str = None,
            pop_list: list = None,
    ):
        logger.info("kyapp start.")
        # 探针：进来之前 App 上还有值，说明是上一轮没清空、或 fork 子进程把父进程的快照带过来了
        # （spawn 下子进程是重新导入，这里一定是空的）。真出现时通常是"子进程没自己传参数"，
        # 不拦、只告警，因为本次传入的参数马上会覆盖它
        stale = [field for field in _APP_FIELDS if getattr(App, field, None) not in (None, [])]
        if stale:
            logger.warning(f"入口前 App 上仍残留会话参数 {stale}，"
                           f"可能是 fork 继承了父进程的值或上一轮没清空；本次会用传入的参数覆盖")
        # 入口处一次性校验，别等跑到很深的地方才因为 None/拼错炸掉
        if platform not in _PLATFORMS:
            raise KeyError(f"platform 必须是 {_PLATFORMS} 之一，当前: {platform!r}")
        if not did:
            raise KeyError('设备标识不能为空（ios 传 udid，android 传 serial）')
        if not case_path:
            raise KeyError('测试用例路径不能为空')
        if not pkg:
            logger.warning("pkg 为空，涉及启动/卸载 App 的用例会失败")

        # APP测试设置
        App.did = did
        App.pkg = pkg
        App.platform = platform
        App.pop_list = pop_list

        cmd_list = f'{case_path} -sv --alluredir {report_path} --clean-alluredir'.split()
        try:
            pytest.main(cmd_list)
        finally:
            # 用完必须清空：同进程连续跑（多设备串行、多轮）时漏一个字段就会串到下一次运行，
            # 而且原来的写法在 pytest.main 抛异常时会被直接跳过
            for field in _APP_FIELDS:
                setattr(App, field, None)


main = TestMain

if __name__ == '__main__':
    main()
