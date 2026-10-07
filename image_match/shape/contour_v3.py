import cv2
import numpy as np

from ..base import ImageMatcher


class ContourMatcher(ImageMatcher):
    """
    工业级滑块验证码识别器 (粗搜+精修 + 自适应边缘检测)
    特点：
    1. 使用 Otsu 自适应阈值处理 Canny 边缘，适应不同对比度的验证码背景。
    2. 优化了“先粗搜再精修”的坐标映射逻辑，杜绝边界溢出导致的像素偏移。
    3. 增加了 ROI 有效性校验，防止极端情况下的匹配失败。
    """

    def match(self, background, target):
        # 1. 读取并预处理图像
        bg_img = self._read_img(background)
        tg_img = self._read_img(target)

        if bg_img is None or tg_img is None:
            raise ValueError("无法读取背景图或目标图")

        # 2. 提取轮廓特征（Otsu 自适应 Canny 边缘检测）
        bg_edges = self._get_adaptive_edges(bg_img)
        tg_edges = self._get_adaptive_edges(tg_img)

        # 3. 粗搜：缩小图像尺寸，快速定位大致区域
        # 提高缩放比例至 0.75，保证小尺寸滑块的粗搜精度
        scale_factor = 0.75
        bg_small = cv2.resize(bg_edges, None, fx=scale_factor, fy=scale_factor)
        tg_small = cv2.resize(tg_edges, None, fx=scale_factor, fy=scale_factor)

        result_small = cv2.matchTemplate(bg_small, tg_small, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc_small = cv2.minMaxLoc(result_small)

        # 4. 精修：在原图上，以粗搜结果为中心，进行精细搜索
        x_small, y_small = max_loc_small
        h_tg, w_tg = tg_edges.shape[:2]
        h_bg, w_bg = bg_edges.shape[:2]

        # 计算原图上的理论中心点
        center_x = int(x_small / scale_factor)
        center_y = int(y_small / scale_factor)

        # 动态设置搜索半径：至少为滑块宽度的一半，确保能覆盖到真实位置
        search_margin = max(30, w_tg // 2)

        # 【核心修复】严格钳制搜索区域边界，防止数组越界或ROI变形
        search_x_start = max(0, center_x - search_margin)
        search_y_start = max(0, center_y - search_margin)
        search_x_end = min(w_bg, center_x + w_tg + search_margin)
        search_y_end = min(h_bg, center_y + h_tg + search_margin)

        # 提取精确的搜索区域 (ROI)
        roi_bg = bg_edges[search_y_start:search_y_end, search_x_start:search_x_end]

        # 校验 ROI 是否有效（必须大于等于模板大小才能进行匹配）
        if roi_bg.shape[0] < h_tg or roi_bg.shape[1] < w_tg:
            # 如果粗搜位置极度离谱导致ROI无效，降级为全图匹配
            result = cv2.matchTemplate(bg_edges, tg_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            final_x, final_y = max_loc
        else:
            # 在安全区域内进行高精度模板匹配
            result = cv2.matchTemplate(roi_bg, tg_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # 【核心修复】绝对坐标系还原：局部坐标 + 区域起始坐标
            final_x = search_x_start + max_loc[0]
            final_y = search_y_start + max_loc[1]

        return {"x": int(final_x), "y": int(final_y), "score": float(max_val)}

    def _get_adaptive_edges(self, img):
        """
        使用 Otsu 算法自动计算 Canny 阈值的边缘检测
        解决不同网站验证码明暗差异大导致的边缘提取失败问题
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 高斯模糊去噪，防止 Otsu 算出极端的阈值
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Otsu 自动寻找最佳二值化阈值
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # 基于 Otsu 阈值推导 Canny 的高低阈值
        v = thresh
        lower = int(max(0, 0.5 * v))
        upper = int(min(255, 1.5 * v))
        return cv2.Canny(blurred, lower, upper)

    def _read_img(self, img_path_or_array):
        """读取图像，支持路径或 numpy 数组"""
        if isinstance(img_path_or_array, str):
            return cv2.imread(img_path_or_array)
        elif isinstance(img_path_or_array, np.ndarray):
            return img_path_or_array
        else:
            return None
