import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import json


# 钉钉机器人
class DingTalk:
    """消息格式参考：https://open.dingtalk.com/document/robots/custom-robot-access"""

    def __init__(self, secret=None, url=None):
        self.secret = secret
        self.url = url

    # 生成时间戳timestamp和签名数据sign用于钉钉机器人的请求
    def __gen_timestamp_and_sign(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    # 发送钉钉机器人通知
    def send_msg(self, msg_data):
        """
        参考：https://open.dingtalk.com/document/robots/custom-robot-access
        @param msg_data:
        @return:
        """
        # 从gen_timestamp_and_sign方法获取timestamp和sign
        timestamp, sign = self.__gen_timestamp_and_sign()
        # 机器人url
        robot_url = self.url
        # 拼接请求url
        url = '{0}&timestamp={1}&sign={2}'.format(robot_url, timestamp, sign)
        print(url)
        # 请求头
        headers = {'Content-Type': 'application/json'}
        # 发送请求
        ret = requests.post(url, headers=headers, data=json.dumps(msg_data), verify=False)
        # 判断请求结果
        ret_dict = ret.json()
        if ret_dict.get('errcode') == 0:
            print('消息发送成功')
        else:
            print('消息发送失败: {}'.format(ret_dict.get('errmsg')))





