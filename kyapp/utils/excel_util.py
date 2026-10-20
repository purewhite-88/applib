"""
pip install pandas==1.3.4
pip install openpyxl==3.0.9
pip install numpy==1.26.2
pip install xlrd==2.0.1 --- 用于解析.xls文件
@Author: kang.yang
@Date: 2024/3/16 09:23
"""
import xlrd
import pandas as pd


class Excel(object):

    def __init__(self, file_name: str):
        self.file_name = file_name

    def read(self, sheet_name=0, header=0, usecols: list = None):
        """
        读取
        @param header: 指定哪行是标题
        @param sheet_name: 0 or 'Sheet1'
        @param usecols:['A', 'B', 'C'] or [0, 2] or 'A:D'
        @return:
        """
        if self.file_name.endswith(".xls"):
            workbook = xlrd.open_workbook(self.file_name, ignore_workbook_corruption=True)
            if usecols:
                df = pd.read_excel(workbook, sheet_name=sheet_name, usecols=usecols, header=header)
            else:
                df = pd.read_excel(workbook, sheet_name=sheet_name, header=header)
        else:
            if usecols:
                df = pd.read_excel(self.file_name, sheet_name=sheet_name, usecols=usecols, header=header)
            else:
                df = pd.read_excel(self.file_name, sheet_name=sheet_name, header=header)
        return df.values.tolist()

    def write(self, sheet_dict: dict, append=False):
        """
        写入
        :param sheet_dict:
        数据格式: {
            'sheet1_name': {'标题列1': ['张三', '李四'], '标题列2': [80, 90]},
            'sheet2_name': {'标题列3': ['王五', '郑六'], '标题列4': [100, 110]}
        }
        :param append: 是否追加，默认覆盖
        """
        df_dict = {}
        for sheet_name, sheet_data in sheet_dict.items():
            df_dict[sheet_name] = pd.DataFrame(sheet_data)

        writer = pd.ExcelWriter(self.file_name)
        for sheet_name, sheet_data in sheet_dict.items():
            _df = pd.DataFrame(sheet_data)
            if append:
                _df = df_dict[sheet_name].append(_df)
            _df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.save()


class CSV(object):

    def __init__(self, file_name):
        self.file_name = file_name

    def read(self, usecols: list = None):
        """
        读取
        @param usecols:['A', 'B', 'C'] or [0, 2] or 'A:D'
        @return:
        """
        if usecols:
            df = pd.read_csv(self.file_name, usecols=usecols)
        else:
            df = pd.read_csv(self.file_name)

        return df.values.tolist()

    def write(self, data: dict, append=False):
        """
        写入
        :param data:
        数据格式：{
            '标题列1': ['张三', '李四'],
            '标题列2': [80, 90]
        }
        :param append: 是否追加，默认覆盖
        """
        df = pd.DataFrame(data)
        if append:
            _df = pd.read_csv(self.file_name)
            df = _df.append(df)
        df.to_csv(self.file_name, index=False)


if __name__ == '__main__':
    pass





