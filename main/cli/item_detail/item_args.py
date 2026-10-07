"""
item_detail 命令行参数解析

负责：
    - argparse 定义
    - --dev / --pro 环境解析
    - id_p / id_u / id_i 键值解析
    - 参数组合校验（dev 全或无 / pro 必须全 / id_i=ut 与 id_u=-1 冲突）
    - 返回 ItemRunArgs

支持：
    python -m main.item_detail.item_detail
    python -m main.item_detail.item_detail --dev
    python -m main.item_detail.item_detail --dev id_p 1051-001 id_u 0 id_i -1
    python -m main.item_detail.item_detail --pro id_p 1051-001 id_u -1 id_i 0-9

环境与参数组合规则：
    dev + 全部不提供  → 使用预设（id_p=1051-001, id_u=-1, id_i=-1）
    dev + 全部提供    → 允许
    dev + 只提供部分  → 报错退出
    pro + 全部提供    → 允许
    pro + 全部不提供  → 报错退出
    pro + 只提供部分  → 报错退出
    id_i=ut 且 id_u=-1 → 报错（ut 需要用户，u -1 表示不使用用户）
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from main.cli.args_utils import parse_user_indexes, validate_project_id
from main.cli.item_detail.item_index_spec import (
    ITEM_INDEX_FORMAT_HELP,
    parse_item_index_spec,
)


def _exit_with_error(message: str) -> None:
    """打印参数错误并退出（不启动浏览器）。"""
    print(f"错误：{message}", file=sys.stderr)
    sys.exit(2)


# ============================================================
# 数据对象
# ============================================================


@dataclass
class ItemRunArgs:
    """
    item_detail 运行参数。

    item_index_spec 仅在 id_i 非 ut 时由 CLI 直接解析；
    id_i=ut 时此处只置 item_is_ut=True，最终 ItemIndexSpec 由
    main/item_detail/item_detail.py 预备层读取 user_pool 后解析。
    """

    env: str = "dev"
    project_id: str | None = None
    user_indexes: list[int] | None = None
    user_arg_raw: str = ""
    item_index_spec: object | None = None
    item_arg_raw: str = ""
    item_is_ut: bool = False
    preset: bool = False


# ============================================================
# dev 环境预设值
# ============================================================

PRESET_PROJECT_ID = "1051-001"
PRESET_USER_INDEXES = "-1"
PRESET_ITEM_INDEXES = "-1"


# ============================================================
# 帮助文本
# ============================================================


def build_item_help_text() -> str:
    return f"""
参数说明:


============================
环境参数
============================

--dev

    开发环境(默认)

    说明:

        id_p/id_u/id_i 必须同时提供或同时不提供，不能只提供一部分。

        若全部不提供，则使用预设值:

            id_p 1051-001

            id_u -1

            id_i -1


--pro

    生产环境

    说明:

        id_p/id_u/id_i 必须同时提供，不能省略，也不能只提供一部分。



============================
项目参数
============================


id_p PROJECT_ID

    格式: 数字-数字

    示例: id_p 1051-001



============================
用户参数
============================


id_u USER_INDEX

    支持: -1 / 非负整数 / N-M / 逗号列表

    -1        不启用用户(无用户模式)

    0         单个用户索引

    0-2       用户索引范围

    1,2,4     指定用户索引列表



============================
链接索引参数
============================


id_i ITEM_INDEX

{ITEM_INDEX_FORMAT_HELP}

    说明:

        id_i ut 与 id_u -1 冲突：id_u -1 表示不使用用户，
        而 id_i ut 表示使用用户表格(user_pool.xlsx)第 7 列的值，
        二者不能同时使用。
"""


# ============================================================
# argparse 入口
# ============================================================


def parse_item_cli_args() -> ItemRunArgs:
    """
    解析 item_detail 命令行参数。

    Returns:
        ItemRunArgs
    """
    parser = argparse.ArgumentParser(
        description="Python-PlayWright-Web item_detail 详情采集程序",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=build_item_help_text(),
    )

    # 环境参数
    parser.add_argument(
        "--dev",
        action="store_true",
        help="使用开发环境(默认)",
    )
    parser.add_argument(
        "--pro",
        action="store_true",
        help="使用生产环境",
    )

    # id_p / id_u / id_i 采用键值模式（位置参数）
    parser.add_argument(
        "params",
        nargs="*",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # 环境检查
    # --------------------------------------------------------

    if args.dev and args.pro:
        parser.error("--dev 和 --pro 不能同时使用")

    env = "pro" if args.pro else "dev"

    # --------------------------------------------------------
    # 初始化参数
    # --------------------------------------------------------

    project_id = None
    user_indexes = None
    user_arg_raw = ""
    item_index_spec = None
    item_arg_raw = ""
    item_is_ut = False

    params = args.params
    index = 0

    # --------------------------------------------------------
    # 解析 id_p / id_u / id_i
    # --------------------------------------------------------

    while index < len(params):
        key = params[index]

        if key == "id_p":
            if index + 1 >= len(params):
                _exit_with_error("id_p 参数缺少项目编号")
            try:
                project_id = validate_project_id(params[index + 1])
            except argparse.ArgumentTypeError as e:
                _exit_with_error(str(e))
            index += 2

        elif key == "id_u":
            if index + 1 >= len(params):
                _exit_with_error("id_u 参数缺少用户索引")
            try:
                user_indexes = parse_user_indexes(params[index + 1])
            except argparse.ArgumentTypeError as e:
                _exit_with_error(str(e))
            user_arg_raw = params[index + 1]
            index += 2

        elif key == "id_i":
            if index + 1 >= len(params):
                _exit_with_error("id_i 参数缺少链接索引")
            id_i_value = params[index + 1]
            item_arg_raw = id_i_value

            # ut：仅置标志，最终解析在预备层（需 user_pool）
            if id_i_value.strip().lower() == "ut":
                item_is_ut = True
                item_index_spec = None
            else:
                try:
                    item_index_spec = parse_item_index_spec(id_i_value)
                except argparse.ArgumentTypeError as e:
                    _exit_with_error(
                        f"id_i 参数非法：{id_i_value}。\n允许的格式为：-1、非负整数、非负整数范围 start-end、ut。\n{e}"
                    )
                item_is_ut = False

            index += 2

        else:
            _exit_with_error(f"未知参数: {key}")

    # --------------------------------------------------------
    # 冲突校验：id_i=ut 与 id_u=-1 不能同时使用
    # --------------------------------------------------------

    if item_is_ut and user_arg_raw == "-1":
        _exit_with_error(
            "id_i ut 和 id_u -1 冲突；\n"
            "其中：id_u -1 表示不使用用户，而 id_i ut 表示使用"
            "用户表格（user_pool.xlsx）第 7 列的值，二者不能同时使用。"
        )

    # --------------------------------------------------------
    # 统计已提供的参数数量
    # --------------------------------------------------------

    provided_count = sum(1 for v in (project_id, user_indexes) if v is not None) + (1 if item_arg_raw else 0)
    expected_count = 3  # id_p / id_u / id_i

    # --------------------------------------------------------
    # dev 环境：必须同时提供或同时不提供
    # --------------------------------------------------------

    if env == "dev" and provided_count not in (0, expected_count):
        parser.error(
            "--dev 环境下 id_p/id_u/id_i 必须同时提供或同时不提供，"
            "不能只提供其中一部分。\n"
            "示例:\n"
            "    全部不提供(使用预设): python -m main.item_detail.item_detail --dev\n"
            "    全部提供: python -m main.item_detail.item_detail --dev "
            "id_p 1051-001 id_u 0 id_i -1"
        )

    # --------------------------------------------------------
    # dev 环境预设值：全部未提供时套用
    # --------------------------------------------------------

    preset = False

    if env == "dev" and provided_count == 0:
        project_id = validate_project_id(PRESET_PROJECT_ID)
        user_indexes = parse_user_indexes(PRESET_USER_INDEXES)
        user_arg_raw = PRESET_USER_INDEXES
        item_index_spec = parse_item_index_spec(PRESET_ITEM_INDEXES)
        item_arg_raw = PRESET_ITEM_INDEXES
        item_is_ut = False
        preset = True

    # --------------------------------------------------------
    # pro 环境：id_p/id_u/id_i 必须全部提供
    # --------------------------------------------------------

    if env == "pro":
        if not project_id:
            parser.error("--pro 环境必须指定: id_p 项目编号")
        if user_indexes is None:
            parser.error("--pro 环境必须指定: id_u 用户索引")
        if not item_arg_raw:
            parser.error("--pro 环境必须指定: id_i 链接索引")

    return ItemRunArgs(
        env=env,
        project_id=project_id,
        user_indexes=user_indexes or [],
        user_arg_raw=user_arg_raw,
        item_index_spec=item_index_spec,
        item_arg_raw=item_arg_raw,
        item_is_ut=item_is_ut,
        preset=preset,
    )
