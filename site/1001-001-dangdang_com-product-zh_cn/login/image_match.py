"""
当当滑块验证码图片匹配

负责:
    - 背景图与缺口图匹配
    - 计算缺口位置
    - 返回滑动距离
"""

import cv2


def match_slider_position(bg_image_path, slider_image_path):
    """
    计算滑块缺口位置

    Args:
        bg_image_path:
            背景图片路径

        slider_image_path:
            滑块图片路径

    Returns:
        dict:

        {
            "x": 缺口X坐标,
            "y": 缺口Y坐标,
            "confidence": 匹配度
        }

    """

    # 读取背景图
    bg = cv2.imread(bg_image_path)

    # 读取缺口图
    slider = cv2.imread(slider_image_path)

    if bg is None:
        raise FileNotFoundError(f"背景图片不存在: {bg_image_path}")

    if slider is None:
        raise FileNotFoundError(f"滑块图片不存在: {slider_image_path}")

    # 模板匹配
    result = cv2.matchTemplate(bg, slider, cv2.TM_CCOEFF_NORMED)

    # 获取最佳匹配位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    x, y = max_loc

    return {"x": x, "y": y, "confidence": max_val}


def calculate_drag_distance(match_x, image_width, slider_width):
    """
    将图片坐标转换成滑块移动距离


    Args:

        match_x:
            图片中缺口X坐标


        image_width:
            验证码图片显示宽度


        slider_width:
            滑轨实际宽度


    Returns:

        int:
            鼠标移动距离

    """

    distance = match_x * slider_width / image_width

    return int(distance)
