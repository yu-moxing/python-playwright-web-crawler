"""
分类采集命令行参数工具模块

负责:

    - 项目编号校验
    - 用户索引解析
    - 分类索引解析


不负责:

    - argparse参数定义
    - 命令行入口


支持格式（u 参数、c 参数 > 左右两侧均适用）:

    -1        不限制

    0-2       范围（0 至 2）

    1,2,4     指定索引列表

    3         单个非负整数（视为单元素列表）

其中:

    u 参数的 -1 表示不启用用户（无用户模式）

    c 参数的 -1 表示不限制分类索引（采集全部）

    c 参数格式为 父级>子级，左右两侧均独立支持上述格式
"""

from __future__ import annotations

import argparse
import re

from .index_spec import INDEX_FORMAT_HELP, parse_index_spec

# ============================================================
# 项目编号解析
# ============================================================


def validate_project_id(
    project_id: str,
) -> str:
    """
    校验项目编号

    格式:
        数字-数字

    示例:
        1001-001
    """

    pattern = r"^\d+-\d+$"

    if not re.match(pattern, project_id):
        raise argparse.ArgumentTypeError("项目编号格式错误。\n正确格式示例:\n    p 1001-001")

    return project_id


# ============================================================
# 用户索引解析
# ============================================================


def parse_user_indexes(
    value: str,
) -> list[int]:
    """
    解析用户索引

    支持（三种格式 + 单个整数）:

        -1        不启用用户（无用户模式）

        0-2       范围

        1,2,4     指定索引列表

        3         单个非负整数

    """

    try:
        spec = parse_index_spec(value)

    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(f"用户参数错误。\n{INDEX_FORMAT_HELP}\n说明: -1 表示不启用用户")

    # -1 表示不启用用户，返回空列表
    if spec.all:
        return []

    return spec.indexes


# ============================================================
# 分类解析
# ============================================================


def parse_cate_indexes(
    value: str,
) -> dict:
    """
    解析分类参数

    格式: 父级>子级，左右两侧均独立支持三种格式 + 单个整数。

    示例:

        -1>-1       全部分类

        0>-1        level0=0 下全部子分类

        0>1-3       level0=0 下 1~3 号子分类

        1>2,4,7     level0=1 下 2,4,7 号子分类

        -1>1-3      全部 level0，每级只采 1~3 号子分类

        0-2>1,3     level0 0~2，每级只采 1,3 号子分类

    Returns:
        {"parents": "all" | list[int], "children": "all" | list[int]}
    """

    # 必须恰好一个 ">"，分隔父级与子级
    if value.count(">") != 1:
        raise argparse.ArgumentTypeError(cate_help())

    parent_part, child_part = value.split(">", 1)

    # 左右两侧为空非法
    if not parent_part or not child_part:
        raise argparse.ArgumentTypeError(cate_help())

    try:
        parent_spec = parse_index_spec(parent_part)
        child_spec = parse_index_spec(child_part)

    except argparse.ArgumentTypeError:
        raise argparse.ArgumentTypeError(cate_help())

    return {
        "parents": "all" if parent_spec.all else parent_spec.indexes,
        "children": "all" if child_spec.all else child_spec.indexes,
    }


# ============================================================
# 分类错误提示
# ============================================================


def cate_help() -> str:
    """
    分类错误提示
    """

    return (
        "分类参数错误。\n\n"
        "格式: 父级>子级，左右两侧均独立支持:\n"
        f"{INDEX_FORMAT_HELP}\n"
        "示例:\n"
        "    c -1>-1        全部分类\n"
        "    c 0>-1         指定 level0 下全部子分类\n"
        "    c 0>1-3        指定 level0 下 1~3 号子分类\n"
        "    c 1>2,4,7      指定 level0 下 2,4,7 号子分类\n"
        "    c -1>1-3       全部 level0，每级只采 1~3 号子分类\n"
        "    c 0-2>1,3      level0 0~2，每级只采 1,3 号子分类"
    )
