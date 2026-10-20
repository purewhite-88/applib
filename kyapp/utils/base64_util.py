"""
@Author: kang.yang
@Date: 2024/8/27 17:01
"""
import base64


def encode(image_path: str):
    """
    图片内容加密成base64字符串
    @return:
    """
    # 读取图片内容
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    # 用base64进行加密
    encoded_image = base64.b64encode(image_data)  # 编码
    encoded_image_str = encoded_image.decode('utf-8')  # 转成字符串

    # 给加密串前面拼上前缀
    prefix = image_path.split('.')[-1]
    base64_image_with_prefix = f"data:image/{prefix};base64,{encoded_image_str}"

    return base64_image_with_prefix
