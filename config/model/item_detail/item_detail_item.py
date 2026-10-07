"""
item_detail Script Config 数据模型

保存 item_detail 的 script.txt 解析结果。

与 cate_list/detail 的配置模型区别：
    - 无 NormalNodeConfig 字段抽取节点（_CSS/_XPATH/_ATTR/_REGEX/_COMBINE）
    - 有 Network Response 配置
    - 有按用户等级（USER_LEVEL_0..4）分组的 range 配置
    - 有 cookie_domain / home_url / 布尔开关等顶层配置

后续阶段接入字段抽取节点时，可在本模型扩展 NormalNodeConfig 组。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from constants.item_detail.user_const import (
    MAX_USER_LEVEL_INDEX,
    MIN_USER_LEVEL_INDEX,
)


@dataclass
class ItemDetailUserLevelRange:
    """
    单个用户等级（0..4）的五项 range 配置。

    每项为 (low, high) 元组：
        (-1, -1)   表示禁用 / 不限制
        (N, N)     表示固定值 N（N > 0）
        (N, M)     表示在 [N, M] 内随机（M > N）
    """

    item_detail_crawl_max_range: Tuple[int, int] = (-1, -1)
    browser_default_load_delay_range_ms: Tuple[int, int] = (-1, -1)
    browser_default_scroll_duration_range_ms: Tuple[int, int] = (-1, -1)
    browser_item_detail_load_delay_range_ms: Tuple[int, int] = (-1, -1)
    browser_item_detail_scroll_duration_range_ms: Tuple[int, int] = (-1, -1)


@dataclass
class ItemDetailScriptConfig:
    """
    item_detail script.txt 完整配置。

    布尔字段为 int（仅 0/1）。
    user_level_ranges 初始化为 0..USER_LEVEL_COUNT-1 各一项空 range。
    """

    cookie_domain: str = ""
    home_url: str = ""
    access_home_page: int = 0
    headless: int = 0

    network_response_intercept_enable: int = 0
    network_response_name: str = ""
    network_response_regex: str = ""
    network_response_json_nodes: str = ""

    user_level_ranges: Dict[int, ItemDetailUserLevelRange] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 确保 0..MAX_USER_LEVEL_INDEX 每一级都有条目
        for level in range(MIN_USER_LEVEL_INDEX, MAX_USER_LEVEL_INDEX + 1):
            if level not in self.user_level_ranges:
                self.user_level_ranges[level] = ItemDetailUserLevelRange()

    def get_user_level_range(self, level: int) -> ItemDetailUserLevelRange:
        """按等级取 range；越界报错。"""
        if level < MIN_USER_LEVEL_INDEX or level > MAX_USER_LEVEL_INDEX:
            raise ValueError(f"用户等级 {level} 越界，合法范围 {MIN_USER_LEVEL_INDEX}..{MAX_USER_LEVEL_INDEX}")
        return self.user_level_ranges[level]
