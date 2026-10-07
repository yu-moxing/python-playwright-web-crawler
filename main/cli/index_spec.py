"""
索引规格公共解析模块

负责:

    - 三种格式 + 单个整数的索引规格解析
    - 供 u 参数、c 参数 > 左右两侧复用


不负责:

    - argparse 参数定义
    - 命令行入口


支持格式:

    -1        不限制

    0-2       范围（0 至 2）

    1,2,4     指定索引列表

    3         单个非负整数（视为单元素列表）

"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

# ============================================================
# 公共格式参考
# ============================================================


INDEX_FORMAT_HELP = """
支持三种格式:

    -1        不限制

    0-2       范围（0 至 2）

    1,2,4     指定索引列表

（单个非负整数视为单元素列表，如 3 等价于 3,）
"""


# ============================================================
# 索引规格
# ============================================================


@dataclass
class IndexSpec:
    """
    索引规格

    Attributes:
        all: True 表示不限制（-1）
        indexes: all=False 时的具体索引列表
    """

    all: bool
    indexes: list[int]


# ============================================================
# 解析入口
# ============================================================


def parse_index_spec(value: str) -> IndexSpec:
    """
    解析索引规格

    支持:

        -1        → all=True（不限制）

        0-2       → range [0, 1, 2]

        1,2,4     → list [1, 2, 4]

        3         → 单个非负整数 [3]

    Raises:
        argparse.ArgumentTypeError: 非以上格式或出现负数（-1 除外）
    """

    # --------------------------------------------------------
    # 不限制
    #
    # -1
    #
    # --------------------------------------------------------

    if value == "-1":
        return IndexSpec(all=True, indexes=[])

    # --------------------------------------------------------
    # 指定索引列表
    #
    # 示例:
    #     1,2,4
    #
    # --------------------------------------------------------

    if "," in value:
        parts = value.split(",")

        try:
            indexes = [int(x) for x in parts]

        except ValueError:
            raise argparse.ArgumentTypeError(_format_error("索引格式错误"))

        # 列表中不允许出现负数（-1 仅作为整体表示不限制）
        if any(i < 0 for i in indexes):
            raise argparse.ArgumentTypeError(_format_error("索引不能为负数"))

        return IndexSpec(all=False, indexes=indexes)

    # --------------------------------------------------------
    # 范围
    #
    # 示例:
    #     0-2
    #
    # --------------------------------------------------------

    if "-" in value:
        parts = value.split("-")

        # 范围必须恰好两段，如 0-2；多段如 1-2-3 非法
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(_format_error("范围格式错误"))

        try:
            start = int(parts[0])
            end = int(parts[1])

        except ValueError:
            raise argparse.ArgumentTypeError(_format_error("范围格式错误"))

        if start < 0 or end < 0:
            raise argparse.ArgumentTypeError(_format_error("索引不能为负数"))

        if start > end:
            raise argparse.ArgumentTypeError(_format_error("范围起点大于终点"))

        return IndexSpec(all=False, indexes=list(range(start, end + 1)))

    # --------------------------------------------------------
    # 单个非负整数
    #
    # 示例:
    #     3
    #
    # -1 已在前面处理，此处负数非法
    # --------------------------------------------------------

    try:
        index = int(value)

    except ValueError:
        raise argparse.ArgumentTypeError(_format_error("索引格式错误"))

    if index < 0:
        raise argparse.ArgumentTypeError(_format_error("索引不能为负数"))

    return IndexSpec(all=False, indexes=[index])


# ============================================================
# 错误信息
# ============================================================


def _format_error(reason: str) -> str:
    """
    组装带格式参考的错误信息

    Args:
        reason: 错误原因

    Returns:
        含三种格式参考的错误信息
    """

    return f"{reason}。\n{INDEX_FORMAT_HELP}"
