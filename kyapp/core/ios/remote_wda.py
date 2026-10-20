"""
@Author: kang.yang
@Date: 2025/4/9 16:05
"""
import requests

from kyapp.utils.common import get_free_port


class RemoteWdaInit:
    """
    远端wda初始化
    """

    def __init__(self, udid: str, sonic_host: str, sonic_user: str, sonic_pwd: str):
        self.udid = udid
        self.host = sonic_host
        # 登录获取登录态请求头
        body = {"userName": sonic_user, "password": sonic_pwd}
        res = requests.post(self.host + '/server/api/controller/users/login', json=body)
        print(res.text)
        token = res.json()['data']
        self.headers = {
            'sonictoken': token
        }

    def occupy_device(self):
        try:
            body = {
                "udId": self.udid,
                "sibRemotePort": get_free_port(),
                "wdaServerRemotePort": get_free_port(),
            }
            res = requests.post(self.host + '/server/api/controller/devices/occupy', json=body, headers=self.headers)
            print(res.text)
            res_json = res.json()
            data = res_json['data']
            sib_cmd = data['sib']
            wda_url = data['wdaServer']
            return sib_cmd, wda_url
        except Exception as e:
            print(f'设备占用失败: \n + {str(e)}')

    def release_device(self):
        try:
            query = {'udId': self.udid}
            res = requests.get(self.host + '/server/api/controller/devices/release', params=query, headers=self.headers)
            print(res.json())
        except Exception as e:
            print(f'设备释放失败：\n + {str(e)}')


if __name__ == '__main__':
    rw = RemoteWdaInit('YOUR_DEVICE_UDID', 'http://localhost:3000', 'YOUR_USERNAME', 'YOUR_PASSWORD')
    rw.occupy_device()
    rw.release_device()


