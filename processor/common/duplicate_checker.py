"""
通用数据去重模块

职责：
    - 基于唯一 Key 进行内存去重
    - 支持预填已有数据
    - 不负责业务 Key 的生成
    - 不负责文件 I/O

设计原则：
    - 纯 Python 类
    - 不依赖具体业务模型
    - 不依赖 Scrapy
    - 不读写文件
    - 调用方负责生成业务唯一 Key
    - seen_keys 保存当前生命周期内已经出现的 Key

典型用法：

    checker = DuplicateChecker()

    key = "id:XS2"

    if checker.is_duplicate(key):
        return

    checker.add(key)

也可以使用：

    if not checker.check_and_add(key):
        return

    # 新数据
    ...

历史数据可以通过 seed() 预填：

    checker.seed([
        "id:XS2",
        "id:ZTXYTL",
    ])

这样后续 check_and_add() 会同时识别：
    - 已有历史数据
    - 本次运行中已经采集的数据
"""

import logging
from typing import Iterable, Set

logger = logging.getLogger(__name__)


class DuplicateChecker:
    """
    通用内存去重器。

    只负责保存和判断唯一 Key，
    不负责决定业务上的“什么算重复”。

    业务层应先将对象转换为唯一 Key，
    再交给本类处理。

    Example:
        >>> checker = DuplicateChecker()

        >>> checker.is_duplicate("id:XS2")
        False

        >>> checker.add("id:XS2")

        >>> checker.is_duplicate("id:XS2")
        True

        >>> checker.is_duplicate("id:ZTXYTL")
        False
    """

    def __init__(self) -> None:
        """
        初始化去重器。
        """
        self.seen_keys: Set[str] = set()

    def seed(self, keys: Iterable[str]) -> None:
        """
        预填已有唯一 Key。

        通常用于：
            - 已有输出文件中的数据
            - 数据库中已有数据
            - 其他历史数据

        Args:
            keys:
                已有数据对应的唯一 Key。
        """
        count = 0

        for key in keys:
            if not key:
                continue

            self.seen_keys.add(key)
            count += 1

        if count:
            logger.info(
                "去重器预填已有数据：%d 条，唯一 Key %d 个",
                count,
                len(self.seen_keys),
            )

    def is_duplicate(self, key: str) -> bool:
        """
        判断 Key 是否已经存在。

        注意：
            本方法只查询，不登记。

        Args:
            key:
                待检查的唯一 Key。

        Returns:
            True:
                Key 已经存在。

            False:
                Key 尚未存在。
        """
        return key in self.seen_keys

    def add(self, key: str) -> None:
        """
        登记一个唯一 Key。

        Args:
            key:
                待登记的唯一 Key。
        """
        if not key:
            return

        self.seen_keys.add(key)

    def is_duplicate_key(self, key: str) -> bool:
        """
        判断业务唯一 Key 是否已经存在。

        该方法是 is_duplicate() 的语义别名，
        用于业务代码中明确表达：

            当前判断的是“业务唯一 Key”。

        注意：
            本方法只查询，不登记。

        Args:
            key:
                待检查的业务唯一 Key。

        Returns:
            True:
                Key 已经存在。

            False:
                Key 尚未存在。
        """
        return self.is_duplicate(key)

    def add_key(self, key: str) -> None:
        """
        登记业务唯一 Key。

        该方法是 add() 的语义别名，
        用于业务代码中明确表达：

            当前登记的是“业务唯一 Key”。

        Args:
            key:
                待登记的业务唯一 Key。
        """
        self.add(key)

    def check_and_add(self, key: str) -> bool:
        """
        判断并登记 Key。

        如果 Key 已存在：
            返回 False，并且不做任何修改。

        如果 Key 不存在：
            登记 Key，并返回 True。

        Args:
            key:
                待检查的唯一 Key。

        Returns:
            True:
                新 Key，已经成功登记。

            False:
                已存在，属于重复数据。
        """
        if not key:
            return False

        if key in self.seen_keys:
            return False

        self.seen_keys.add(key)
        return True

    def clear(self) -> None:
        """
        清空当前所有已登记的 Key。
        """
        self.seen_keys.clear()

    def __len__(self) -> int:
        """
        返回当前唯一 Key 数量。
        """
        return len(self.seen_keys)
