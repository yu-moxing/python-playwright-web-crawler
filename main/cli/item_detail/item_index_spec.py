"""
item_detail id_i 索引规格解析

与 main.cli.index_spec.parse_index_spec 的区别：

    - 不支持逗号列表（item_detail 的 id_i 只定义 -1 / 非负整数 / N-M）
    - 范围 N-M 要求严格 end > start（拒绝 5-5）

支持的 id_i 格式：
    -1        不限制（全部链接）
    N         单个非负整数
    N-M       范围 [N, M]，且 M > N

非法示例：
    -2        除 -1 外的负数
    5-5       范围终点等于起点
    9-0       范围终点小于起点
    -1-5      范围格式错误
    1--5      范围格式错误
    abc       非数字
    ut-1      非数字
    1,2,4     不支持逗号列表

注：ut 不由本模块解析，由 CLI 预备层读取 user_pool 后再调用本模块。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

ITEM_INDEX_FORMAT_HELP = """
id_i 支持的格式：

    -1        不限制（采集全部链接）

    0         单个非负整数

    0-9       范围（0 至 9，要求 数字2 > 数字1）

    ut        使用 user_pool.xlsx 中对应用户的 id_i 值

（不支持逗号列表；除 -1 外不接受负数。）
"""


@dataclass
class ItemIndexSpec:
    """
    id_i 索引规格。

    Attributes:
        all: True 表示不限制（-1），采集 item_list_link.txt 全部链接。
        indexes: all=False 时需要采集的具体索引列表。
    """

    all: bool
    indexes: list[int]


def parse_item_index_spec(value: str) -> ItemIndexSpec:
    """
    解析 id_i 索引规格。

    Raises:
        argparse.ArgumentTypeError: 格式非法。
    """
    raw = value.strip()

    # -1：不限制
    if raw == "-1":
        return ItemIndexSpec(all=True, indexes=[])

    # 范围 N-M
    if "-" in raw:
        parts = raw.split("-")

        # 范围必须恰好两段，多段（如 1-2-3 / -1-5 / 1--5）非法
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise argparse.ArgumentTypeError(_format_error("id_i 范围格式错误"))

        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            raise argparse.ArgumentTypeError(_format_error("id_i 范围格式错误"))

        if start < 0 or end < 0:
            raise argparse.ArgumentTypeError(_format_error("id_i 索引不能为负数"))

        if end <= start:
            raise argparse.ArgumentTypeError(_format_error("id_i 范围终点必须大于起点（end > start）"))

        return ItemIndexSpec(all=False, indexes=list(range(start, end + 1)))

    # 单个非负整数
    try:
        index = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(_format_error("id_i 索引格式错误"))

    if index < 0:
        raise argparse.ArgumentTypeError(_format_error("id_i 索引不能为负数"))

    return ItemIndexSpec(all=False, indexes=[index])


def _format_error(reason: str) -> str:
    return f"{reason}。\n{ITEM_INDEX_FORMAT_HELP}"
