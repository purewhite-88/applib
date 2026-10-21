import requests

from applib_ui.utils.common import get_free_port


class RemoteAdbInit:
    """
    远端adb连接初始化
    """

    def __init__(self, serial: str, sonic_host: str, sonic_user: str, sonic_pwd: str):
        self.serial = serial
        self.host = sonic_host
        # 登录获取登录态请求头
        print('sonic登录，获取token')
        body = {"userName": sonic_user, "password": sonic_pwd}
        res = requests.post(self.host + '/server/api/controller/users/login', json=body)
        print(res.text)
        token = res.json()['data']
        self.headers = {
            'sonictoken': token
        }

    def occupy_device(self):
        print('占用设备')
        try:
            body = {
                "udId": self.serial,
                "sasRemotePort": get_free_port(),
            }
            res = requests.post(self.host + '/server/api/controller/devices/occupy', json=body, headers=self.headers)
            print(res.text)
            res_json = res.json()
            data = res_json['data']
            print(data)
            # uia2 = data['uia2']
            sas = data['sas']
            adb_server = sas.split()[-1]
            return adb_server
        except Exception as e:
            print(f'设备占用失败: \n + {str(e)}')

    def release_device(self):
        print('释放设备')
        try:
            query = {'udId': self.serial}
            res = requests.get(self.host + '/server/api/controller/devices/release', params=query, headers=self.headers)
            print(res.json())
        except Exception as e:
            print(f'设备释放失败：\n + {str(e)}')

    def delete_offline_device(self):
        print('删除离线设备')
        try:
            # 查询离线设备
            res = requests.get(f'{self.host}/server/api/controller/devices/list?page=1&pageSize=12&status%5B%5D=DISCONNECTED', headers=self.headers)
            print(res.text)
            res_json = res.json()
            device_list = res_json['data']['content']
            # 删除离线设备
            for device in device_list:
                device_id = device['id']
                res = requests.delete(f'{self.host}/server/api/controller/devices?id={device_id}', headers=self.headers)
                print(res.text)
        except Exception as e:
            print(f"删除设备失败: {str(e)}")



