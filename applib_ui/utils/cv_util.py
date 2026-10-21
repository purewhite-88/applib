import cv2
import time
import allure

from applib_ui.utils.log import logger


def draw_red_by_rect(image_path: str, rect: tuple):
    """在图片上画框，范围是左上角坐标和宽高"""
    # 读取图像
    image = cv2.imread(image_path)

    # 定义标记范围的坐标
    x, y, w, h = rect

    # 在图像上绘制矩形
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # 保存标记后的图像
    cv2.imwrite(image_path, image)


def draw_red_by_coordinate(image_path: str, rect: tuple):
    """在图片上画框，范围是左上角坐标和右上角坐标"""
    """x_top_left, y_top_left, x_bottom_right, y_bottom_right"""
    # 读取图像
    image = cv2.imread(image_path)

    # 定义标记范围的坐标
    x, y, x1, y1 = rect

    # 在图像上绘制矩形
    cv2.rectangle(image, (x, y), (x1, y1), (0, 0, 255), 2)

    # 保存标记后的图像
    cv2.imwrite(image_path, image)


def cut_half(image, position):
    """把图片分成上下两半"""
    if position == "up":
        return image[:image.shape[0] // 2, :]
    elif position == "down":
        return image[image.shape[0] // 2:, :]
    else:
        raise KeyError("position传值错误")


def cut_by_position(image_path: str, position: str):
    """把图片按左上、左下、右上、右下进行分割"""
    logger.info(position)
    # 读取图像
    logger.info("分割图片")
    start = time.time()
    image = cv2.imread(image_path)
    # 获取图像的宽度和高度
    height, width, _ = image.shape
    logger.debug(f'{height}, {width}')
    # 计算每个切割区域的宽度和高度
    sub_width = width // 2
    sub_height = height // 2
    # 切割图像成上下左右四个等份
    if position == 'TL':
        image_content = image[0:sub_height, 0:sub_width]
    elif position == 'TR':
        image_content = image[0:sub_height, sub_width:width]
    elif position == 'BL':
        image_content = image[sub_height:height, 0:sub_width]
    elif position == 'BR':
        image_content = image[sub_height:height, sub_width:width]
    else:
        raise KeyError(f"position传值错误 all: {position}")

    new_path = f"{image_path.split('.')[0]}_{position}.{image_path.split('.')[1]}"
    logger.debug(new_path)
    cv2.imwrite(new_path, image_content)
    cut_height, cut_width, _ = image_content.shape
    logger.debug(f'{cut_height, cut_width}')
    end = time.time()
    logger.info(f"分割成功， 耗时: {end - start}s")
    info = {
        "path": new_path,
        "height": height,
        "width": width,
        "cut_height": cut_height
    }
    logger.debug(info)
    return info


def cut_and_upload(file_path, position: str = None):
    # 对图片进行分割
    info = None
    if position is not None:
        info = cut_by_position(file_path, position)
        file_path = info.get("path")
    # 上传allure报告
    allure.attach.file(
        file_path,
        attachment_type=allure.attachment_type.PNG,
        name=f"{file_path}",
    )
    if position is not None:
        return info
    else:
        return file_path




