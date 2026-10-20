"""
pip install pycryptodome==3.14.1
@Author: kang.yang
@Date: 2024/3/18 14:46
"""
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64


def encode(key, src_str):
    """
    AES加密，一种对称加密算法
    @param key: 事先定好的秘钥（必须是16字节、24字节或32字节）
    @param src_str: 需要加密的字符串
    @return: 加密后的Base64字符串
    """
    # 确保密钥是字节类型
    key = key.encode('utf-8')

    # 创建AES加密器
    aes = AES.new(key, AES.MODE_ECB)

    # 将源字符串编码为字节，并使用PKCS7填充
    src_bytes = src_str.encode('utf-8')
    padded_data = pad(src_bytes, AES.block_size)

    # 加密填充后的数据
    encrypted_data = aes.encrypt(padded_data)

    # 将加密后的数据转换为Base64字符串
    encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')

    return encrypted_base64


def decode(key, ciphertext):
    """
    AES解密，一种对称加密算法
    @param key: 事先定好的秘钥
    @param ciphertext: 需要解密的密文
    @return:
    """
    aes = AES.new(str.encode(key), AES.MODE_ECB)
    decrypt_str = (aes.decrypt(base64.decodebytes(ciphertext.encode(encoding='utf-8'))).
                   decode().replace('@', ''))
    return decrypt_str


