"""
分类层统计模块

职责：
    - 累计各级分类的计数与唯一值
    - 输出统计结果

设计原则：
    - 纯 Python 类，不依赖 Scrapy
    - 不读写文件，不打日志（由调用方决定如何展示 summary）

调用方：
    当前未被 cate_level 运行链路使用（CateLevelProcessor 未导入本模块），为预留统计模块。
"""

from typing import Dict, Set

EMPTY_PLACEHOLDER = "00"

LEVEL_FIELDS = ["level_0", "level_1", "level_2", "level_3", "level_4"]


class CateLevelStats:
    """
    分类层统计器

    统计字段：
        - total_items: 总条数
        - level_x_count: 各级非空条数
        - unique_level_x: 各级唯一值数量

    Example:
        >>> stats = CateLevelStats()
        >>> stats.add({"level_0": "女装##1", "level_1": "00", "level_2": "00", "level_3": "00", "level_4": "00"})
        >>> stats.summary()
        {'total_items': 1, 'level_0_count': 1, 'level_1_count': 0, ...,
         'unique_level_0': 1, 'unique_level_1': 0, ...}
    """

    def __init__(self) -> None:
        self.total_items: int = 0
        self.level_counts: Dict[str, int] = {f: 0 for f in LEVEL_FIELDS}
        self.unique_values: Dict[str, Set[str]] = {f: set() for f in LEVEL_FIELDS}

    def add(self, item: Dict[str, str]) -> None:
        """
        增加一条统计

        Args:
            item: 已通过校验的 item_detail
        """
        self.total_items += 1
        for level in LEVEL_FIELDS:
            value = item.get(level, EMPTY_PLACEHOLDER)
            if value and value != EMPTY_PLACEHOLDER:
                self.level_counts[level] += 1
                self.unique_values[level].add(value)

    def summary(self) -> Dict[str, int]:
        """
        返回统计结果

        Returns:
            统计字典，包含 total_items / level_x_count / unique_level_x
        """
        result: Dict[str, int] = {"total_items": self.total_items}
        for level in LEVEL_FIELDS:
            result[f"{level}_count"] = self.level_counts[level]
            result[f"unique_{level}"] = len(self.unique_values[level])
        return result

    def reset(self) -> None:
        """重置统计"""
        self.total_items = 0
        self.level_counts = {f: 0 for f in LEVEL_FIELDS}
        self.unique_values = {f: set() for f in LEVEL_FIELDS}
