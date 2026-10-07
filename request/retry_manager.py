"""
异步重试管理模块

职责：
    - 对任意异步函数做异常重试
    - 替代旧 ErrorRetryMiddleware 的 Scrapy 思维（request.copy() / response.status）

设计原则：
    - 纯 Python 异步组件，不依赖 Scrapy
    - 不复制 Request、不依赖 response.status
    - 支持最大次数 + 重试间延迟（可随机）
    - on_retry 回调可记录日志 / 上报指标

职责分离（避免双重重试）：
    - PageLoader.load 已内置页面加载重试（goto / timeout / network），
      严禁再用 RetryManager 包裹 PageLoader.load，否则会产生 3×3=9 次双重重试。
    - RetryManager 仅用于业务流程步骤：登录、解析、数据库写入等。

调用方：
    Processor（登录 / 解析 / 数据库写入等业务步骤）
"""

import inspect
import logging
from typing import Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 重试回调签名：(attempt_index, exception) -> None 或 coroutine
RetryCallback = Callable[[int, BaseException], None]


class RetryManager:
    """
    异步重试管理器

    Example:
        >>> rm = RetryManager()
        >>> html = await rm.execute(lambda attempt: fetch_html(url), max_retry=3)
    """

    @staticmethod
    async def execute(
        func: Callable[[int], Awaitable[T]],
        max_retry: int = 3,
        delay: float = 0.0,
        randomize_delay: bool = False,
        on_retry: Optional[RetryCallback] = None,
    ) -> T:
        """
        执行异步函数，失败时重试

        Args:
            func: 接收 attempt 索引（从 0 开始）的异步函数，返回任意结果
            max_retry: 最大重试次数（总尝试 = max_retry + 1）
            delay: 每次重试前等待秒数；<=0 不等待
            randomize_delay: True 时延迟随机化（[0.5*delay, 1.5*delay]）
            on_retry: 每次重试前的回调（同步或异步均可）

        Returns:
            func 的返回值

        Raises:
            最后一次仍失败时抛出原异常
        """
        last_exception: Optional[BaseException] = None

        for attempt in range(max_retry + 1):
            try:
                return await func(attempt)
            except Exception as e:
                last_exception = e

                if attempt >= max_retry:
                    logger.error(
                        "达到最大重试次数 %d：%s: %s",
                        max_retry,
                        type(e).__name__,
                        e,
                    )
                    raise

                logger.warning(
                    "第 %d 次重试：%s: %s",
                    attempt + 1,
                    type(e).__name__,
                    e,
                )

                if on_retry is not None:
                    result = on_retry(attempt, e)
                    if inspect.isawaitable(result):
                        await result

                if delay > 0:
                    from utils.delay_manager import DelayManager

                    await DelayManager.delay(delay, randomize=randomize_delay)

        # 理论不可达：循环要么 return 要么 raise
        assert last_exception is not None
        raise last_exception
