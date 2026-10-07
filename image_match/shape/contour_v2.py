import cv2
import numpy as np

from ..base import ImageMatcher


class ContourMatcher(ImageMatcher):
    """
    基于轮廓形状匹配的滑块验证码识别器（粗搜+精修优化版）
    """

    def match(self, background, target):
        # 1. 读取并预处理图像
        bg_img = self._read_img(background)
        tg_img = self._read_img(target)

        if bg_img is None or tg_img is None:
            raise ValueError("无法读取背景图或目标图")

        # 2. 提取轮廓特征（Canny边缘检测）
        bg_gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
        tg_gray = cv2.cvtColor(tg_img, cv2.COLOR_BGR2GRAY)

        bg_edges = cv2.Canny(bg_gray, 100, 200)
        tg_edges = cv2.Canny(tg_gray, 100, 200)

        # 3. 粗搜：缩小图像尺寸，快速定位大致区域
        scale_factor = 0.5  # 缩放比例，可根据实际情况调整
        bg_small = cv2.resize(bg_edges, None, fx=scale_factor, fy=scale_factor)
        tg_small = cv2.resize(tg_edges, None, fx=scale_factor, fy=scale_factor)

        result_small = cv2.matchTemplate(bg_small, tg_small, cv2.TM_CCOEFF_NORMED)
        _, max_val_small, _, max_loc_small = cv2.minMaxLoc(result_small)

        # 4. 精修：在原图上，以粗搜结果为中心，进行精细搜索
        x_small, y_small = max_loc_small
        h_tg, w_tg = tg_edges.shape[:2]

        # 计算原图上的搜索区域
        search_x_start = max(0, int(x_small / scale_factor) - 20)
        search_y_start = max(0, int(y_small / scale_factor) - 20)
        search_x_end = min(bg_edges.shape[1], int((x_small + w_tg) / scale_factor) + 20)
        search_y_end = min(bg_edges.shape[0], int((y_small + h_tg) / scale_factor) + 20)

        # 裁剪搜索区域
        bg_search = bg_edges[search_y_start:search_y_end, search_x_start:search_x_end]

        # 在搜索区域内进行模板匹配
        result = cv2.matchTemplate(bg_search, tg_edges, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # 5. 计算最终坐标
        final_x = search_x_start + max_loc[0]
        final_y = search_y_start + max_loc[1]

        return {"x": final_x, "y": final_y, "score": max_val}

    def _read_img(self, img_path_or_array):
        """读取图像，支持路径或numpy数组"""
        if isinstance(img_path_or_array, str):
            return cv2.imread(img_path_or_array)
        elif isinstance(img_path_or_array, np.ndarray):
            return img_path_or_array
        else:
            return None
