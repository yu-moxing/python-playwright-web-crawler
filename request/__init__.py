"""
请求流辅助组件包

提供请求/业务流相关的通用异步组件：
    - RetryManager：异步重试（替代旧 ErrorRetryMiddleware 的 Scrapy request.copy()）

注：DelayManager 已迁至 utils/delay_manager.py
（延迟不专属于请求层，Processor 等也会用）。

均为纯 Python 异步组件，不依赖 Scrapy。
"""

from request.retry_manager import RetryManager

__all__ = ["RetryManager"]
