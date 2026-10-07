"""
分类层数据验证模块

职责：
    - 校验分类层 Item 的完整性与格式
    - 自动补全缺失的 "##ID" 后缀

设计原则：
    - 纯 Python 类，不依赖 Scrapy
    - 操作普通 dict
    - 校验失败抛 ValueError
    - 校验通过返回补全后的 item（就地修改并返回）

调用方：
    当前未被 cate_level 运行链路使用（CateLevelProcessor 未导入本模块），为预留校验模块。
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# 分类层 Item 的层级字段
LEVEL_FIELDS = ["level_0", "level_1", "level_2", "level_3"]

# 空值占位符（与 create_item 保持一致）
EMPTY_PLACEHOLDER = "00"

# 标题与 ID 的分隔符
ID_SEPARATOR = "##"

Item = Dict[str, str]


class CateLevelValidator:
    """
    分类层 Item 验证器

    校验规则：
        1. item_detail 必须是 dict
        2. level_0 不可为空 / "00"（主分类必须存在），否则 raise ValueError
        3. level_0 缺少 "##" 时自动补全 "##0"
        4. level_1~3 非 "00" 且缺少 "##" 时自动补全 "##0"

    Example:
        >>> validator = CateLevelValidator()
        >>> item_detail = {"level_0": "女装", "level_1": "00", "level_2": "00", "level_3": "00"}
        >>> validator.validate(item_detail)
        {'level_0': '女装##0', 'level_1': '00', 'level_2': '00', 'level_3': '00'}
    """

    def validate(self, item: Item) -> Item:
        """
        校验并补全 item_detail

        Args:
            item: 待校验的 dict

        Returns:
            补全后的 item_detail（就地修改并返回）

        Raises:
            ValueError: item_detail 非 dict，或 level_0 为空
        """
        if not isinstance(item, dict):
            raise ValueError(f"无效的数据类型：{type(item)}，期望 dict")

        # 校验 level_0（主分类）
        level_0 = item.get("level_0", EMPTY_PLACEHOLDER)
        if not level_0 or level_0 == EMPTY_PLACEHOLDER:
            raise ValueError("主分类（level_0）为空")

        if ID_SEPARATOR not in level_0:
            logger.warning(f"主分类格式错误：{level_0}，自动补全 {ID_SEPARATOR}0")
            item["level_0"] = f"{level_0}{ID_SEPARATOR}0"

        # 校验 level_1~3（可为 "00"）
        for level in LEVEL_FIELDS[1:]:
            value = item.get(level, EMPTY_PLACEHOLDER)
            if value and value != EMPTY_PLACEHOLDER and ID_SEPARATOR not in value:
                logger.warning(f"{level} 格式错误：{value}，自动补全")
                item[level] = f"{value}{ID_SEPARATOR}0"

        logger.debug(f"验证通过：{item}")
        return item
