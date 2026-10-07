"""
人类行为模拟模块

职责：
    - 模拟真人浏览行为（随机滚动、鼠标移动）
    - 替代旧 PlaywrightMiddleware._simulate_human_behavior 的内联逻辑

设计原则：
    - 纯 Python 异步组件，不依赖 Scrapy
    - 不放在 PageLoader（保持 PageLoader 职责单一：仅负责 goto + 就绪检测）
    - 不放在 utils（与鼠标 / 行为相关，归 mouse_tracks）
    - 可被 Processor、滑块验证码、风控等场景复用

调用方：
    CateLevelProcessor（页面加载后可选调用）、
    mouse_tracks/slider_* 等需要预热人类行为的场景
"""

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class HumanBehaviorSimulator:
    """
    人类行为模拟器

    Example:
        >>> simulator = HumanBehaviorSimulator()
        >>> await simulator.simulate(page)
    """

    DEFAULT_SCROLL_ROUNDS = 3
    DEFAULT_MOUSE_MOVES = 5

    async def simulate(
        self,
        page,
        *,
        scroll_rounds: int = DEFAULT_SCROLL_ROUNDS,
        mouse_moves: int = DEFAULT_MOUSE_MOVES,
    ) -> None:
        """
        模拟人类浏览行为：随机滚动 + 随机鼠标移动

        Args:
            page: Playwright 页面对象
            scroll_rounds: 随机滚动次数
            mouse_moves: 随机鼠标移动次数
        """
        viewport = page.viewport_size
        if not viewport:
            logger.debug("无 viewport，跳过人类行为模拟")
            return

        try:
            width = viewport["width"]
            height = viewport["height"]

            # 随机滚动
            for _ in range(scroll_rounds):
                scroll_y = random.randint(100, 500)
                await page.mouse.wheel(0, scroll_y)
                await asyncio.sleep(random.uniform(0.5, 1.5))

            # 随机鼠标移动
            for _ in range(mouse_moves):
                x = random.randint(100, max(101, width - 100))
                y = random.randint(100, max(101, height - 100))
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            logger.debug("已模拟人类行为")

        except Exception as e:
            logger.error("模拟人类行为失败：%s", e)
