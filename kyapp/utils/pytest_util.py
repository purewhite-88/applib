import pytest
# import json
# import yaml


def order(index):
    """
    指定用例执行顺序, pip install pytest-ordering==0.6
    doc: https://blog.csdn.net/weixin_43880991/article/details/116221362
    """
    return pytest.mark.run(order=index)


def depend(depends: list or str = None, name=None):
    """
    设置用例依赖关系, pip install pytest-dependency==0.5.1
    doc: https://www.cnblogs.com/se7enjean/p/13513131.html
    """
    if isinstance(depends, str):
        depends = [depends]
    return pytest.mark.dependency(name=name, depends=depends)


# 参数化数据
def data(out_name, list_data: list):
    """
    必须传入一个list，使用时通过在参数列表传入parma进行调用
    """
    return pytest.mark.parametrize(out_name, list_data)


# # 从json文件获取数据进行参数化
# def file_data(file=None, key=None):
#     # logger.debug(config.get_env())
#
#     """
#     感觉excel和csv不常用，去掉
#     @param file: 文件名
#     @param key: 针对json和yaml文件
#     """
#     file_path = file  # 去掉文件查找机制，不好理解，用处也不大
#
#     # logger.debug(file_path)
#     if file_path.endswith(".json"):
#         content = read_json(file_path, key)
#     elif file_path.endswith(".yml"):
#         content = read_yaml(file_path, key)
#     # elif file_path.endswith(".csv"):
#     #     content = read_csv(file_path, row)
#     # elif file_path.endswith(".xlsx"):
#     #     content = read_excel(file_path, row)
#     else:
#         raise TypeError("不支持的文件类型，仅支持json、yml")
#
#     if content:
#         return data(content)
#     else:
#         raise ValueError('数据不能为空')


# def read_json(file_path, key=None):
#     """
#     读取json文件中的指定key
#     @return
#     """
#     with open(file_path, 'r', encoding='utf-8') as f:
#         json_data = json.load(f)
#     if isinstance(json_data, list):
#         return json_data
#     else:
#         if key:
#             return json_data[key]
#         raise ValueError('key不能为空')
#
#
# def read_yaml(file_path, key=None):
#     """
#     读取yaml文件中的指定key
#     @param file_path:
#     @param key:
#     """
#     with open(file_path, 'r', encoding='utf-8') as f:
#         yaml_data = yaml.load(f, Loader=yaml.FullLoader)
#     if isinstance(yaml_data, list):
#         return yaml_data
#     else:
#         if key:
#             return yaml_data[key]
#         raise ValueError('key不能为空')
