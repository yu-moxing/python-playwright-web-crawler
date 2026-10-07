import cv2
import numpy as np

from ..base import ImageMatcher


class ContourMatcher(ImageMatcher):
    """
    基于轮廓形状匹配的滑块验证码识别器
    使用 Canny 边缘检测和 matchShapes 算法来寻找最佳匹配位置
    """

    def match(self, background, target):
        """
        在大图中寻找小图最相似的轮廓位置

        Args:
            background (str | np.ndarray): 背景大图路径或图像矩阵
            target (str | np.ndarray): 缺口/滑块小图路径或图像矩阵

        Returns:
            dict: {
                'x': int,      # 最佳匹配的左上角 X 坐标
                'y': int,      # 最佳匹配的左上角 Y 坐标
                'score': float # 匹配度得分 (越小越相似, 0为完全匹配)
            }
        """
        # 1. 读取并预处理图像
        bg_img = self._read_img(background)
        tg_img = self._read_img(target)

        if bg_img is None or tg_img is None:
            raise ValueError("无法读取背景图或目标图")

        # 2. 提取轮廓特征 (使用 Canny 边缘检测)
        bg_edges = self._get_edges(bg_img)
        tg_edges = self._get_edges(tg_img)

        # 3. 获取目标图的轮廓信息
        # 使用 RETR_EXTERNAL 模式，因为我们主要关心滑块的外轮廓。
        tg_contours, _ = cv2.findContours(tg_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not tg_contours:
            return {"x": 0, "y": 0, "score": -1}

        # 选取目标图中面积最大的轮廓作为主特征
        target_contour = max(tg_contours, key=cv2.contourArea)

        # 4. 在大图中滑动搜索最佳匹配位置
        h_bg, w_bg = bg_edges.shape
        h_tg, w_tg = tg_edges.shape

        min_score = float("inf")
        best_x, best_y = 0, 0

        # 步长(step)可以调整，1为逐像素搜索(最准但慢)，2或4可加速
        step = 1
        for y in range(0, h_bg - h_tg + 1, step):
            for x in range(0, w_bg - w_tg + 1, step):
                # 截取当前区域
                roi = bg_edges[y : y + h_tg, x : x + w_tg]

                # 寻找当前区域的轮廓
                roi_contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not roi_contours:
                    continue

                # 同样选取区域中最大的轮廓进行比对
                roi_contour = max(roi_contours, key=cv2.contourArea)

                # 计算形状匹配度 (CONTOURS_MATCH_I1 是基于 Hu 矩的算法)
                # 使用 cv2.matchShapes 计算两个轮廓的相似度。该方法基于 Hu 矩，对旋转、缩放和微小形变具有较好的鲁棒性。
                # 注意：matchShapes 返回的值越小，代表越相似。
                score = cv2.matchShapes(target_contour, roi_contour, cv2.CONTOURS_MATCH_I1, 0)

                # 结果返回：返回得分最低（最相似）时的坐标 x, y
                if score < min_score:
                    min_score = score
                    best_x = x
                    best_y = y

        return {"x": best_x, "y": best_y, "score": min_score}

    def _read_img(self, source):
        """兼容读取文件路径或直接传入 numpy 数组"""
        if isinstance(source, str):
            return cv2.imdecode(np.fromfile(source, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        elif isinstance(source, np.ndarray):
            # 如果传入的是彩色图，转为灰度
            if len(source.shape) == 3:
                return cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
            return source
        return None

    def _get_edges(self, img):
        """
        获取图像边缘
        使用高斯模糊去噪，然后 Canny 提取边缘
        """

        # 滑块验证码的背景通常很花哨（如你提供的红叶图）。直接对比像素容易受颜色干扰。
        # 使用 cv2.GaussianBlur 去除噪点。
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        # 使用 cv2.Canny 提取边缘信息。这样我们比对的是“形状”而不是“颜色”。
        edges = cv2.Canny(blurred, 100, 200)
        return edges
