"""
@Author: kang.yang
@Date: 2025/4/14 15:22
pip install chardet==5.2.0
pip install baidu-aip==4.16.13
"""
import os
import requests
from natocr import OCR
from kyapp.running.conf import App
from kyapp.utils.log import logger

# OCR 语言：Vision 不会自动猜，不指定就是按 "en" 识别，
# 中文会被硬塞成拉丁/符号乱码（如 "宝宝现在大约和南瓜一样大" → "ÈŘIEŁ⅘]*#—#*"）。
# 默认 zh-Hans（实测对"简体中文 + 英文"的界面最准；用 auto 会跑成繁體，如 現在/大約/一祥）。
# 可用环境变量 KYAPP_OCR_LANG 覆盖，取值见 natocr：单个语言码（en-US / zh-Hans / zh-Hant / ja-JP…）
# 或 "auto"（macOS 13+ 由 Vision 逐行自动判语言）；注意不要传逗号串，只会被当成一个非法语言码。
_OCR_CACHE = {}


def _ocr_language() -> str:
    """OCR 识别语言：优先读项目配置，其次环境变量，最后回落到 zh-Hans"""
    language = getattr(App, "ocr_language", None)
    if language:
        return language
    return os.environ.get("KYAPP_OCR_LANG", "zh-Hans")


def _get_ocr(language: str = None) -> OCR:
    """按语言缓存 OCR 实例（每次重建都要重新初始化 Vision，白白拖慢每次识别）"""
    language = language or _ocr_language()
    if language not in _OCR_CACHE:
        _OCR_CACHE[language] = OCR(language=language)
    return _OCR_CACHE[language]


def _fallback_languages(keyword: str, language: str) -> list:
    """
    主语言没找到时，可以再补哪些语言

    中文模型（zh-Hans）能认常见英文（CozyLink 这种没问题），但连排小写字母/品牌名会掉字符
    —— 实测 momcozy 被认成 "momco："、整行 "nomeo" 直接漏掉，而英文模型能认对。
    所以关键词里含英文字母、且主语言不是英文时，允许用英文模型再补一次；
    只在第一次真的没找到时才多花一次 OCR。可用 KYAPP_OCR_FALLBACK_LANG 关掉（设为空）。
    """
    if language == "auto" or not any(ch.isascii() and ch.isalpha() for ch in keyword):
        return []
    fallback = os.environ.get("KYAPP_OCR_FALLBACK_LANG", "en-US")
    if not fallback or fallback == language:
        return []
    return [fallback]


def _recognize(source_img_path, language: str = None) -> list:
    """跑一次 OCR，返回 [{'text', 'left_x', 'left_y', 'width', 'height'}, ...]（像素坐标）"""
    ocr = _get_ocr(language)
    logger.info(f"使用natocr进行识别(language={ocr.language})")
    page = ocr.recognize(source_img_path)[0]  # 截图通常是单页
    result = []
    for element in page.elements:
        text = (element.text or '').strip()
        if not text:
            continue
        bounds = element.bounds.bounds
        print(text, bounds)
        result.append({
            'text': text,
            'left_x': bounds[0],
            'left_y': bounds[1],
            'width': bounds[2],
            'height': bounds[3]
        })
    logger.info(f"OCR识别到 {len(result)} 行文本")
    return result


def _match(result: list, keyword: str):
    """
    在识别结果里找关键词
    先精确匹配，再退化成包含匹配：OCR 常把一行里的多个元素连成一串（如"发现2个设备"），
    只用 == 比对基本必然落空
    @return: 命中的元素 dict，没命中返回 None
    """
    hits = [word for word in result if word['text'] == keyword]
    if not hits:
        hits = [word for word in result if keyword in word['text']]
    return hits[0] if hits else None


# def get_position(source_img_path, keyword: str):
#     """
#     @Author: kang.yang
#     @Date: 2025/4/14 14:50
#     """
#
#     # 初始化AipOcr
#     # APP_ID = FileConfig.get_ocr('app_id')
#     # API_KEY = FileConfig.get_ocr('api_key')
#     # SECRET_KEY = FileConfig.get_ocr('secret_key')
#     app_id = App.app_id
#     api_key = App.api_key
#     secret_key = App.secret_key
#     if app_id and api_key and secret_key:
#         client = AipOcr(app_id, api_key, secret_key)
#     else:
#         raise KeyError('OCR配置不能为空')
#
#     # 读取图片
#     def get_file_content(file_path):
#         with open(file_path, 'rb') as fp:
#             return fp.read()
#
#     image = get_file_content(source_img_path)  # 替换为你的图片路径
#
#     # 设置可选参数
#     options = {
#         "language_type": "CHN_ENG",  # 中英文混合
#         "detect_direction": "true",  # 检测图像方向
#         "detect_language": "true",  # 检测语言类型
#         "probability": "true"  # 返回识别结果中每一行的置信度信息
#     }
#
#     # 调用OCR服务
#     result = client.accurate(image, options)
#
#     # 打印识别结果
#     logger.info(json.dumps(result, indent=4, ensure_ascii=False))
#
#     # 解析识别结果，获取文字及其坐标
#     if 'words_result' in result:
#         for word in result['words_result']:
#             text = word['words']  # 文字内容
#             location = word['location']  # 坐标信息
#             print(f"Recognized Text: {text}")
#             print(f"Location: {location}")
#             if text == keyword:
#                 center_x = location['left'] + location['width'] // 2
#                 center_y = location['top'] + location['height'] // 2
#                 print(f'中心坐标: ({center_x}, {center_y})')
#                 return center_x, center_y
#         print('OCR识别失败')
#         return None
#     else:
#         print('OCR识别失败')
#         return None

def get_position(source_img_path, keyword: str, ocr_service=None):
    """
    OCR 定位关键词，返回像素坐标中心点
    @param source_img_path: 截图路径
    @param keyword: 关键词
    @param ocr_service: 远端 OCR 服务地址，传了就优先走服务
    @return: (center_x, center_y) 像素坐标；没找到返回 None
    """
    if ocr_service is not None:
        logger.info(f"请求ocr服务：{ocr_service}")
        try:
            r = requests.post(
                ocr_service,
                files={'image': (source_img_path, source_img_path, 'image/png')},
                data={'keyword': keyword}
            )
            result = r.json()['data']
        except Exception as e:
            logger.error(f'OCR识别失败: {e}')
            return None
        hit = _match(result, keyword)
    else:
        language = _ocr_language()
        result = _recognize(source_img_path, language)
        hit = _match(result, keyword)
        if hit is None:
            # 中文模型认英文会掉字符，用英文模型补一次（只有英文关键词才补）
            for fallback in _fallback_languages(keyword, language):
                logger.info(f"lang={language} 未命中，改用 {fallback} 补识别一次")
                result = _recognize(source_img_path, fallback)
                hit = _match(result, keyword)
                if hit is not None:
                    break

    if hit is None:
        logger.info(f'OCR中未识别到关键词: {keyword}（共 {len(result)} 行）')
        return None

    print(f"Recognized Text: {hit['text']}")
    center_x = int(hit['left_x'] + hit['width'] // 2)
    center_y = int(hit['left_y'] + hit['height'] // 2)
    print(f'中心坐标: ({center_x}, {center_y})')
    return center_x, center_y


