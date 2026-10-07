import cv2
import numpy as np

from ..base import ImageMatcher


class TransparencyMatcher(ImageMatcher):
    """
    基于模板匹配 + 透明度处理的滑块识别器
    适用场景：滑块带有半透明阴影、边缘模糊、或背景干扰较大的情况
    """

    def match(self, background, target):
        # 1. 读取图像
        bg_img = self._read_img(background)
        tg_img = self._read_img(target)

        if bg_img is None or tg_img is None:
            raise ValueError("无法读取背景图或目标图")

        # 2. 预处理：转灰度 + 透明度/阴影增强
        # 核心逻辑：将半透明的灰色阴影强制转为高对比度特征
        bg_gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
        tg_gray = cv2.cvtColor(tg_img, cv2.COLOR_BGR2GRAY)

        # 【关键步骤】自适应阈值二值化
        # 把滑块中“半透明”的部分变成纯黑(0)，背景变成纯白(255)
        # 这样能消除阴影对匹配的干扰，只保留滑块的实体形状
        _, tg_bin = cv2.threshold(tg_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        _, bg_bin = cv2.threshold(bg_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 3. 粗搜：缩小尺寸快速定位
        scale_factor = 0.6  # 稍微提高一点精度，防止小滑块丢失
        bg_small = cv2.resize(bg_bin, None, fx=scale_factor, fy=scale_factor)
        tg_small = cv2.resize(tg_bin, None, fx=scale_factor, fy=scale_factor)

        res_small = cv2.matchTemplate(bg_small, tg_small, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc_small = cv2.minMaxLoc(res_small)

        # 4. 精修：在原图局部搜索
        x_s, y_s = max_loc_small
        h_tg, w_tg = tg_bin.shape[:2]

        # 计算原图搜索范围（增加一点冗余量）
        margin = 30
        x_start = max(0, int(x_s / scale_factor) - margin)
        y_start = max(0, int(y_s / scale_factor) - margin)
        x_end = min(bg_bin.shape[1], int((x_s + w_tg) / scale_factor) + margin)
        y_end = min(bg_bin.shape[0], int((y_s + h_tg) / scale_factor) + margin)

        # 裁剪局部区域进行精确匹配
        bg_roi = bg_bin[y_start:y_end, x_start:x_end]
        res_final = cv2.matchTemplate(bg_roi, tg_bin, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res_final)

        # 5. 还原最终坐标
        final_x = x_start + max_loc[0]
        final_y = y_start + max_loc[1]

        return {"x": final_x, "y": final_y, "score": float(max_val)}

    def _read_img(self, img_path_or_array):
        if isinstance(img_path_or_array, str):
            return cv2.imread(img_path_or_array)
        elif isinstance(img_path_or_array, np.ndarray):
            return img_path_or_array
        return None
