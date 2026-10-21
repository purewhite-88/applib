"""设备连接的创建与释放，供 pytest fixture 使用。"""

from .running.conf import App


def create_driver():
    if App.platform not in ('android', 'ios'):
        raise ValueError('请通过 --app-platform 或 app_platform 配置 android / ios')
    if not App.did:
        raise ValueError('请通过 --app-device 或 app_device 配置设备标识')

    if App.platform == 'android':
        if App.sonic_host:
            from .core.android.remote_driver import RemoteDriver

            return RemoteDriver(
                serial=App.did, package=App.pkg, sonic_host=App.sonic_host,
                sonic_user=App.sonic_user, sonic_pwd=App.sonic_pwd,
            )
        from .core.android.driver import Driver

        return Driver(serial=App.did, package=App.pkg)

    if App.sonic_host:
        from .core.ios.remote_driver import RemoteDriver

        return RemoteDriver(
            udid=App.did, bundle_id=App.pkg, sib_path=App.sib_path,
            sonic_host=App.sonic_host, sonic_user=App.sonic_user, sonic_pwd=App.sonic_pwd,
        )
    from .core.ios.driver import Driver
    from .core.ios.local_wda import LocalWdaInit

    LocalWdaInit(App.did).kill_wda_server()
    driver = Driver(udid=App.did, bundle_id=App.pkg)
    try:
        if not driver.ensure_alive():
            raise RuntimeError('iOS WDA 连接不可用')
    except BaseException:
        driver.close()
        raise
    return driver


def release_driver(driver):
    try:
        stop_record = getattr(driver, 'stop_record', None)
        if stop_record is not None:
            stop_record()
    finally:
        close = getattr(driver, 'close', None)
        if close is not None:
            close()
