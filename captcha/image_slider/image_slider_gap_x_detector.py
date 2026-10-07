"""
图片滑块验证码缺口X坐标检测器。

基于：
    Playwright 渲染截图
    +
    OpenCV 图像分析

不依赖网站 JS 偏移值。
"""

import cv2
import numpy as np

from captcha.image_slider.gap_x_result import GapXResult


class ImageSliderGapXDetector:
    """
    图片滑块验证码缺口X坐标检测器。

    负责：
        1. 获取验证码最终渲染截图
        2. 获取滑块元素实际位置
        3. OpenCV分析缺口X坐标
        4. 返回X轴移动距离

    支持：
        - 图片型滑块验证码
    """

    async def detect(self, page) -> GapXResult:
        """
        检测滑块缺口X坐标。

        Args:
            page:
                Playwright Page对象

        Returns:
            GapXResult
        """

        # 1. 获取渲染后的验证码截图
        screenshot = await self._capture(page)

        # 2. 获取滑块真实渲染位置
        slider_info = await self._get_slider_info(page)

        # 3. OpenCV检测缺口X坐标
        gap_x, confidence = self._detect_gap_x(screenshot, slider_info)

        slider_x = int(slider_info["left"])

        return GapXResult(
            gap_x=gap_x, slider_x=slider_x, distance=gap_x - slider_x, confidence=confidence, method="edge_projection"
        )

    async def _capture(self, page) -> bytes:
        """
        截取验证码区域。

        对应：

        <div id="imgWrap">
        """

        element = page.locator("#imgWrap")

        return await element.screenshot()

    async def _get_slider_info(self, page):
        """
        获取滑块实际渲染位置。

        对应：

        <img id="simg">

        """

        return await page.locator("#simg").evaluate(
            """
            el => {

                const r =
                    el.getBoundingClientRect();


                return {

                    left: r.left,

                    top: r.top,

                    width: r.width,

                    height: r.height
                }
            }
            """
        )

    def _detect_gap_x(self, screenshot: bytes, slider_info: dict):
        """
        根据渲染截图检测缺口X坐标。

        返回：

            gap_x
            confidence

        """

        # --------------------------
        # 1. screenshot -> OpenCV
        # --------------------------

        img_array = np.frombuffer(screenshot, dtype=np.uint8)

        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("验证码截图解析失败")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # --------------------------
        # 2. Canny边缘检测
        # --------------------------

        edges = cv2.Canny(gray, 80, 160)

        # --------------------------
        # 3. 根据滑块高度
        #    定位X轴检测区域
        # --------------------------

        top = int(slider_info["top"])

        height = int(slider_info["height"])

        roi = edges[top : top + height, :]

        # --------------------------
        # 4. X方向边缘强度投影
        # --------------------------

        score = np.sum(roi, axis=0)

        score = cv2.GaussianBlur(score.reshape(1, -1), (15, 1), 0)[0]

        # --------------------------
        # 5. 排除滑块自身区域
        # --------------------------

        left = int(slider_info["left"])

        width = int(slider_info["width"])

        score[left : left + width] = 0

        # --------------------------
        # 6. 获取最大响应X坐标
        # --------------------------

        gap_x = int(np.argmax(score))

        # --------------------------
        # 7. 计算匹配可信度
        # --------------------------

        max_score = np.max(score)

        confidence = float(score[gap_x] / (max_score + 1e-6))

        return (gap_x, confidence)
