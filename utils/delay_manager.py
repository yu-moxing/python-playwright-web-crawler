"""
异步延迟管理模块

职责：
    - 提供固定 / 随机 / 范围三种异步延迟
    - 替代旧 RandomDelayMiddleware 的同步 time.sleep（time.sleep 会阻塞事件循环）

设计原则：
    - 纯 Python 异步组件，不依赖 Scrapy
    - 复用 asyncio.sleep，不阻塞事件循环
    - 延迟不专属于请求层（Processor 也会用），故置于 utils 而非 request
    - 可与 BROWSER_*_DELAY_TIME_RANGE（min, max 范围模型）配合

调用方：
    Processor / PageLoader / RetryManager 等
"""

import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class DelayManager:
    """
    异步延迟管理器

    Example:
        >>> dm = DelayManager()
        >>> await dm.delay(3)                 # 随机 1.5~4.5s
        >>> await dm.delay(3, randomize=False)  # 固定 3s
        >>> await dm.delay_range(1.0, 2.5)    # 范围 1.0~2.5s
    """

    @staticmethod
    async def delay(seconds: float, randomize: bool = True) -> float:
        """
        异步延迟

        Args:
            seconds: 基础延迟秒数；<=0 时直接返回 0
            randomize: True 时在 [0.5*seconds, 1.5*seconds] 内随机（与旧中间件一致）

        Returns:
            实际延迟秒数
        """
        if seconds <= 0:
            return 0.0

        actual = random.uniform(0.5 * seconds, 1.5 * seconds) if randomize else seconds

        logger.debug("延迟 %.2f 秒", actual)
        await asyncio.sleep(actual)
        return actual

    @staticmethod
    async def delay_range(min_seconds: float, max_seconds: float) -> float:
        """
        范围随机延迟（配合 BROWSER_*_DELAY_TIME_RANGE 的 (min, max) 模型）

        Args:
            min_seconds: 最小延迟秒数
            max_seconds: 最大延迟秒数

        Returns:
            实际延迟秒数
        """
        if max_seconds <= min_seconds:
            actual = max(min_seconds, 0.0)
        else:
            actual = random.uniform(min_seconds, max_seconds)

        logger.debug("范围延迟 %.2f 秒", actual)
        await asyncio.sleep(actual)
        return actual
