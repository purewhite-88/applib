import os
import yaml

local_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.dirname(local_path)
file_path = os.path.join(root_path, 'running', 'conf.yml')


class FileConfig:
    @staticmethod
    def get_common(key):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        try:
            return yaml_data['common'][key]
        except:
            return None

    @staticmethod
    def get_api(key):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        try:
            return yaml_data['api'][key]
        except:
            return None

    @staticmethod
    def get_ai(key):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        try:
            return yaml_data['ai'][key]
        except:
            return None

    @staticmethod
    def get_web(key):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        try:
            return yaml_data['web'][key]
        except:
            return None

    @staticmethod
    def get_ocr(key):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        try:
            return yaml_data['ocr'][key]
        except:
            return None

    @staticmethod
    def set_common(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['common'][key] = value
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def set_api(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['api'][key] = value
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def set_ai(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['ai'][key] = value
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def append_ai(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['ai'][key].append(value)
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def set_web(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['web'][key] = value
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def set_ocr(key, value):
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['web'][key] = value
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)

    @staticmethod
    def reset():
        with open(file_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.load(f.read(), Loader=yaml.FullLoader)
        yaml_data['api'] = {
            'base_url': None,
            'headers': None,
        }
        yaml_data['ai'] = {
            'base_url': None,
            'api_key': None,
            'repaired': []
        }
        yaml_data['web'] = {
            'headers': None,
            'web_url': None,
            'browser': 'chrome',
            'headless': False,
            'state': None,
            'maximized': False,
            'window_size': None
        }
        yaml_data['ocr'] = {
            'app_id': None,
            'api_key': None,
            'secret_key': None,
        }
        with open(file_path, 'w', encoding="utf-8") as f:
            yaml.dump(yaml_data, f)




