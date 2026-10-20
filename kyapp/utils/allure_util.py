import json
import os.path
import time

from urllib.parse import urlparse
from allure import story, title, step, feature


class AllureData:
    """解析allure_results的数据"""

    def __init__(self, result_path='report'):
        self.result_path = result_path

    def get_files(self):
        """获取以result.json结尾的文件列表"""
        file_list = []
        for filename in os.listdir(self.result_path):
            if filename.endswith('result.json'):
                file_list.append(filename)

        if not file_list:
            raise KeyError('报告数据为空')

        return [os.path.join(self.result_path, item)
                for item in os.listdir(self.result_path)
                if item.endswith('result.json')]

    @staticmethod
    def get_file_content(file_path):
        """获取文件内容并转成json"""
        with open(file_path, 'r', encoding='UTF-8') as f:
            content = json.load(f)
        return content

    def parser_content(self, content):
        """解析单个json内容"""
        project = '未知项目'
        module = '未知模块'
        labels = content["labels"]
        for label in labels:
            if label['name'] == 'feature':
                project = label['value']
            if label['name'] == 'story':
                module = label['value']

        name = content['name']
        full_name = content['fullName']
        parameters = content.get('parameters', [])

        status = content['status']
        log_path = ''
        screen_path = []
        attachments = content['attachments']
        for attach in attachments:
            if attach['type'] == 'text/plain' and attach['name'] == 'log':
                log_path = os.path.join(self.result_path, attach['source'])
            if attach['type'] == 'image/png':
                screen_path.append(os.path.join(self.result_path, attach['source']))

        interfaces = []
        if log_path:
            log_content = open(log_path, 'r', encoding='utf8').read()
            for line in log_content.split("\n"):
                if 'url]: ' in line:
                    interface = line.strip().split('url]: ')[1].split()[0]
                    parsed_url = urlparse(interface)
                    path = parsed_url.path
                    method = line.strip().split('[method]: ')[1].split()[0].lower()
                    cost = line.strip().split('[cost]: ')[1]
                    interfaces.append((method, path, cost))

        start = content.get('start')
        end = content.get('stop')
        start_time, end_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.localtime(start / 1000)), \
                               time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.localtime(end / 1000))
        cost = (end - start) / 1000
        if cost > 60:
            cost = '{}min'.format(round(cost / 60, 1))
        else:
            cost = '{}s'.format(round((end - start) / 1000, 1))

        case_data = {
            "project": project,
            "module": module,
            "name": name,
            "full_name": full_name,
            "parameters": parameters,
            "status": status,
            "log": log_path,
            "interfaces": interfaces,
            "shots": screen_path,
            'start_stamp': start,
            'start_time': start_time,
            'end_time': end_time,
            'end_stamp': end,
            'cost': cost
        }
        return case_data

#     @staticmethod
#     def remove_duplicate(json_contents):
#         """去除失败重试的重复结果"""
#         case_list = []
#         no_repeat_tags = []
#         for item in json_contents:
#             full_name = item["full_name"]
#             parameters = item["parameters"]
#             if (full_name, parameters) not in no_repeat_tags:
#                 no_repeat_tags.append((full_name, parameters))
#                 case_list.append(item)
#             else:
#                 for case in case_list:
#                     if case['full_name'] == full_name and case['parameters'] == parameters:
#                         if case['status'] != 'passed':
#                             case_list.remove(case)
#                             case_list.append(item)
#         return case_list
#
    def get_result_list(self):
        """返回处理后的测试明细"""
        file_list = self.get_files()
        result_list = []
        for file in file_list:
            content = self.get_file_content(file)
            parser_content = self.parser_content(content)
            result_list.append(parser_content)
        return result_list
#
#     def get_api_list(self):
#         """获取接口列表"""
#         tests = self.get_result_list()
#         apis = []
#         for test in tests:
#             apis.extend(test["interfaces"])
#         return list(set(apis))
#
#     def get_statistical_data(self):
#         case_list = self.get_result_list()
#
#         # 获取用例统计数据
#         passed_list = []
#         fail_list = []
#         broken_list = []
#         skipped_list = []
#         unknown_list = []
#         for case in case_list:
#             status = case.get('status')
#             if status == 'passed':
#                 passed_list.append(case)
#             elif status == 'failed':
#                 fail_list.append(case)
#             elif status == 'broken':
#                 broken_list.append(case)
#             elif status == 'skipped':
#                 skipped_list.append(case)
#             else:
#                 unknown_list.append(case)
#         total = len(case_list)
#         passed = len(passed_list)
#         failed = len(fail_list)
#         broken = len(broken_list)
#         skipped = len(skipped_list)
#         unknown = len(unknown_list)
#         rate = round((passed / total) * 100, 2)
#
#         # 获取整个任务的开始和结束时间
#         start_time_timestamp, end_time_timestamp = \
#             case_list[0].get('start_stamp'), case_list[0].get('end_stamp')
#         for case in case_list:
#             inner_start = case.get('start_stamp')
#             inner_end = case.get('end_stamp')
#             if inner_start < start_time_timestamp:
#                 start_time_timestamp = inner_start
#             if inner_end > end_time_timestamp:
#                 end_time_timestamp = inner_end
#
#         # 时间戳转成日期
#         start_time, end_time = time.strftime("%Y-%m-%d %H:%M:%S",
#                                              time.localtime(start_time_timestamp / 1000)), \
#                                time.strftime("%Y-%m-%d %H:%M:%S",
#                                              time.localtime(end_time_timestamp / 1000))
#         cost = (end_time_timestamp - start_time_timestamp) / 1000
#         if cost > 60:
#             cost = '{}min'.format(round(cost / 60, 1))
#         else:
#             cost = '{}s'.format(round((end_time_timestamp - start_time_timestamp) / 1000, 1))
#
#         return {
#             'total': total,
#             'passed': passed,
#             'failed': failed,
#             'broken': broken,
#             'skipped': skipped,
#             'unknown': unknown,
#             'rate': rate,
#             'start': start_time,
#             'end': end_time,
#             'cost': cost,
#             'tests': case_list
#         }
#
#
# def get_allure_data(result_path):
#     """兼容邮件和钉钉的调用"""
#     return AllureData(result_path).get_statistical_data()


if __name__ == '__main__':
    pass

