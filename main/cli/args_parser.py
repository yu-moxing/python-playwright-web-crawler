"""
分类采集命令行参数解析模块

负责:

    - argparse定义
    - 环境参数解析
    - p/u/{cate_keyword}参数流程控制
    - 返回CateRunArgs


支持:

环境:
    --dev
    --pro


项目:

    p 1001-001


用户:

    u 0-2

    u -1

    u 1,2,4

    u 3


分类:

    {cate_keyword} -1>-1

    {cate_keyword} 0>-1

    {cate_keyword} 0>1-3

    {cate_keyword} 1>2,4,7

    {cate_keyword} -1>1-3

    {cate_keyword} 0-2>1,3

    {cate_keyword} ut           使用用户表格(user_pool.xlsx)对应列的值


说明:

    本模块为 cate_level（clli）与 cate_list（clii）共用解析器，通过 cate_keyword
    参数区分关键字。两者的解析规则与判断一/二/三完全一致，仅关键字名与 ut 读取的
    用户表格列不同（由各入口自行读取，本解析器只置 cli_is_ut 标志）。

    注：原“判断四（含 > 的值必须双引号包裹）”因 PowerShell 等 Shell 会在
    Python 收到原始命令行前消费掉引号、无法可靠区分加引号与否，已移除，
    以保证合法命令 clli/clii "-1>-1" 正常通过。


示例:

python cate_level.py

python cate_level.py --dev p 1001-001 u 0-2

python cate_level.py --pro p 1001-001 u 0-2 clli "0>1-3"

python cate_level.py --dev p 1001-001 u 0-2 clli ut
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from .args_utils import (
    parse_cate_indexes,
    parse_user_indexes,
    validate_project_id,
)


def _exit_with_error(message: str) -> None:
    """
    打印参数错误信息并退出程序

    Args:
        message: 错误信息（含正确格式参考）
    """
    print(f"参数错误：{message}", file=sys.stderr)
    sys.exit(2)


# ============================================================
# 数据对象
# ============================================================


@dataclass
class CateRunArgs:
    """
    分类采集运行参数
    """

    # 环境
    env: str = "dev"

    # 项目编号
    project_id: str | None = None

    # 用户索引
    user_indexes: list[int] | None = None

    # 用户索引原始参数字符串（用于错误信息引用，如 "-1" / "2-4" / "2" / "1,2,4"）
    user_arg_raw: str = ""

    # 分类索引（cate 关键字为 父级>子级 格式时解析得到的字典；cate=ut 时为 None，按用户解析）
    cate_indexes: dict | None = None

    # 分类参数原始字符串（用于错误信息引用，如 "0>1-3" / "ut"）
    cli_arg_raw: str = ""

    # 是否为 cate=ut 模式（使用用户表格 user_pool.xlsx 对应列的值）
    cli_is_ut: bool = False

    # so（sort and order）参数原始字符串（仅 cate_list 使用；cate_level 始终为 ""）
    so_arg_raw: str = ""

    # 是否为 so=ut 模式（使用用户表格 user_pool.xlsx 第 9 列 so 的值）
    so_is_ut: bool = False

    # 是否使用了 dev 预设值（仅 dev 环境且 p/u/{cate_keyword} 全部未提供时为 True）
    preset: bool = False


# ============================================================
# dev 环境预设值
# ============================================================

# 当 --dev（或默认）且未提供 p/u/c 时使用
PRESET_PROJECT_ID = "1001-001"
PRESET_USER_INDEXES = "0-2"
PRESET_CATE_INDEXES = "0>1-3"
# dev 预设的 so 值（仅 sort_keyword 非空时套用）：-1 表示不使用排序
PRESET_SO = "-1"


# ============================================================
# Help说明
# ============================================================


def build_help_text(
    cate_keyword: str,
    cate_label: str,
    sort_keyword: str | None = None,
) -> str:
    """
    生成帮助文本（按 cate_keyword/cate_label 替换关键字与说明）。

    Args:
        cate_keyword: 分类参数关键字，如 "clli" / "clii"。
        cate_label:   分类参数全称，如 "cate level link index" / "cate level index id"。
        sort_keyword: 排序参数关键字（仅 cate_list 传 "so"；cate_level 传 None）。
    """
    kw = cate_keyword

    if sort_keyword:
        sk = sort_keyword
        sort_section = f"""

============================
排序参数
============================


{sk} SORT_AND_ORDER


支持五种格式:

1. -1

    不使用排序字段。


2. 0

    使用默认排序字段。


3. ut

    使用用户表格(user_pool.xlsx)第 9 列 so(sort and order) 的值。
    （取出的值需重新按格式 1/2/4/5 校验，且不能再是 ut。）


4. "排序字段"

    使用指定单个排序字段；字段须在 CATE_LIST_SORT_FIELDS 内。
    仅支持单字段，不支持逗号分隔、不支持多字段。


5. "排序字段|排序顺序"

    用 | 切分（最多 1 个）；字段须同时在 CATE_LIST_SORT_FIELDS 与
    CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS 内；排序顺序须在
    CATE_LIST_SORT_ORDER_VALUES 内；两侧不能为空。


说明:

    {sk} ut 与 u -1 冲突：u -1 表示不使用用户，
    而 {sk} ut 表示使用用户表格中的值，二者不能同时使用。

    排序字段、排序顺序得是 script.txt 中 CATE_LIST_SORT_FIELDS /
    CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS / CATE_LIST_SORT_ORDER_VALUES 列出的。
"""
        sort_rule = f"p/u/{kw}/{sk}"
        sort_preset = f"{sk} -1"
        sort_pro_rule = f"p/u/c/{sk}"
    else:
        sort_section = ""
        sort_rule = f"p/u/{kw}"
        sort_preset = ""
        sort_pro_rule = "p/u/c"

    return f"""

参数说明:


============================
环境参数
============================

--dev

    开发环境(默认)

    说明:

        {sort_rule} 必须同时提供或同时不提供，不能只提供一部分。

        若全部不提供，则使用预设值:

            p 1001-001

            u 0-2

            {kw} 0>1-3

{f"            {sk} -1" if sort_keyword else ""}


--pro

    生产环境

    说明:

        {sort_pro_rule} 必须同时提供，不能省略，也不能只提供一部分。



============================
项目参数
============================


p PROJECT_ID


格式:

    数字-数字


示例:

    p 1001-001



============================
用户参数
============================


u USER_INDEX


支持三种格式 + 单个整数:

1. 范围:

    u 0-2

表示: 使用索引0至2用户


2. 不启用用户:

    u -1


3. 指定索引列表:

    u 1,2,4


4. 单个整数:

    u 3

表示: 使用索引3用户


============================
分类参数
============================


{kw} CATE_INDEX


格式一: 父级>子级，左右两侧均独立支持三种格式 + 单个整数


三种格式:

    -1        不限制

    0-2       范围

    1,2,4     指定索引列表

（单个非负整数视为单元素列表）


支持:


1. 全部分类:

    {kw} -1>-1


2. 指定 level0 下全部子分类:

    {kw} 0>-1


3. 指定 level0 下子分类范围:

    {kw} 0>1-3


4. 指定 level0 下子分类列表:

    {kw} 1>2,4,7


5. 全部 level0，每级只采指定子分类:

    {kw} -1>1-3


6. level0 范围，每级只采指定子分类:

    {kw} 0-2>1,3


格式二: ut

    {kw} ut

使用用户表格(user_pool.xlsx)对应列的值，
作为该用户的分类采集范围。

说明:

    {kw} 无 > 号时，只能取 ut（大小写不敏感）。

    {kw} ut 与 u -1 冲突：u -1 表示不使用用户，
    而 {kw} ut 表示使用用户表格中的值，二者不能同时使用。
{sort_section}

============================
示例
============================


开发环境:

    python cate_level.py


开发环境指定项目:


    python cate_level.py --dev p 1001-001 u 0-2


生产环境:


    python cate_level.py --pro p 1001-001 u 0-2 {kw} "0>1-3"


使用用户表格分类索引:


    python cate_level.py --dev p 1001-001 u 0-2 {kw} ut

"""


# ============================================================
# argparse入口
# ============================================================


def parse_cli_args(
    *,
    cate_keyword: str = "clli",
    cate_label: str = "cate level link index",
    sort_keyword: str | None = None,
    sort_label: str = "sort and order",
) -> CateRunArgs:
    """
    解析命令行参数

    Args:
        cate_keyword: 分类参数关键字（cate_level 用 "clli"，cate_list 用 "clii"）。
        cate_label:   分类参数全称（用于错误/帮助文案）。
        sort_keyword: 排序参数关键字（仅 cate_list 传 "so"；cate_level 传 None，
                      此时 so 不被识别，传入会报“未知参数”）。
        sort_label:   排序参数全称（用于错误文案）。

    返回:

        CateRunArgs
    """

    parser = argparse.ArgumentParser(
        description="Python-PlayWright-Web 分类采集程序",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=build_help_text(cate_keyword, cate_label, sort_keyword),
    )

    # --------------------------------------------------------
    # 环境参数
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 其他参数
    #
    # p/u/{cate_keyword}采用键值模式:
    #
    # p 1001-001
    # u 0-2
    # {cate_keyword} 0>1-3
    #
    # --------------------------------------------------------

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

    cate_indexes = None

    cli_arg_raw = ""

    cli_is_ut = False

    so_arg_raw = ""

    so_is_ut = False

    params = args.params

    index = 0

    # --------------------------------------------------------
    # 解析p/u/{cate_keyword}
    # --------------------------------------------------------

    while index < len(params):
        key = params[index]

        if key == "p":
            if index + 1 >= len(params):
                _exit_with_error("p 参数缺少项目编号")

            try:
                project_id = validate_project_id(params[index + 1])
            except argparse.ArgumentTypeError as e:
                _exit_with_error(str(e))

            index += 2

        elif key == "u":
            if index + 1 >= len(params):
                _exit_with_error("u 参数缺少用户索引")

            try:
                user_indexes = parse_user_indexes(params[index + 1])
            except argparse.ArgumentTypeError as e:
                _exit_with_error(str(e))

            user_arg_raw = params[index + 1]
            index += 2

        elif key == cate_keyword:
            if index + 1 >= len(params):
                _exit_with_error(f"{cate_keyword} 参数缺少分类参数")

            cli_value = params[index + 1]
            cli_arg_raw = cli_value

            if ">" in cli_value:
                # 格式一：父级>子级
                try:
                    cate_indexes = parse_cate_indexes(cli_value)
                except argparse.ArgumentTypeError as e:
                    _exit_with_error(str(e))

                cli_is_ut = False
            else:
                # 格式二：无 > 号，只允许 ut
                if len(cli_value) == 2 and cli_value.isalpha():
                    if cli_value.lower() == "ut":
                        cli_is_ut = True
                        cate_indexes = None
                    else:
                        # 判断一：2 位字母但不等于 ut
                        _exit_with_error(
                            f"{cate_keyword} 的值必须只能取以下两种格式之一：\n"
                            "格式一：包含 > 号（父级>子级，如 0>1-3）\n"
                            "格式二：无 > 号时，只能取：ut"
                        )
                else:
                    # 判断三：无 > 号且不是 2 位字母
                    _exit_with_error(f"{cate_keyword} 的值无>号时，只能取：ut")

            index += 2

        elif sort_keyword and key == sort_keyword:
            if index + 1 >= len(params):
                _exit_with_error(f"{sort_keyword} 参数缺少排序参数")

            so_value = params[index + 1]
            so_arg_raw = so_value
            # 仅标记是否 ut（用于与 u -1 冲突判断）；格式与成员校验交由
            # main.cli.sort_spec.parse_and_validate_so（需 script_config，在
            # load_configs 之后执行）。
            so_is_ut = so_value.strip().lower() == "ut"
            index += 2

        else:
            _exit_with_error(f"未知参数: {key}")

    # --------------------------------------------------------
    # 判断二之一：cate=ut 时，u 不能为 -1
    #
    # u -1 表示不使用用户，而 {cate_keyword} ut 表示使用用户表格(user_pool.xlsx)
    # 对应列的值，二者冲突。
    # --------------------------------------------------------

    if cli_is_ut and user_arg_raw == "-1":
        _exit_with_error(
            f"启动参数：u -1 和 {cate_keyword} ut 冲突；\n"
            f"其中：u -1 表示不使用用户，而 {cate_keyword} 参数( {cate_label} 的缩写 ) "
            "的值为：ut , 表示使用用户表格（user_pool.xlsx）中的值。"
        )

    # --------------------------------------------------------
    # 判断：so=ut 时，u 不能为 -1（同 clii=ut 规则）
    # --------------------------------------------------------

    if so_is_ut and user_arg_raw == "-1":
        _exit_with_error(
            f"启动参数：u -1 和 {sort_keyword} ut 冲突；\n"
            f"其中：u -1 表示不使用用户，而 {sort_keyword} 参数( {sort_label} 的缩写 ) "
            "的值为：ut , 表示使用用户表格（user_pool.xlsx）中的值。"
        )

    # --------------------------------------------------------
    # 统计已提供的参数数量（None 视为未提供）
    # --------------------------------------------------------

    provided_count = (
        sum(1 for v in (project_id, user_indexes) if v is not None)
        + (1 if cli_arg_raw else 0)
        + (1 if so_arg_raw else 0)
    )

    # 期望参数数：p/u/{cate_keyword} 共 3 个，sort_keyword 非空时再加 1 个 so
    expected_count = 3 + (1 if sort_keyword else 0)

    # --------------------------------------------------------
    # dev 环境校验：p/u/{cate_keyword}[/{sort_keyword}] 必须同时提供或同时不提供
    # --------------------------------------------------------

    if env == "dev" and provided_count not in (0, expected_count):
        rule = f"p/u/{cate_keyword}" + (f"/{sort_keyword}" if sort_keyword else "")
        example_full = f'python cate_level.py --dev p 1001-001 u 0-2 {cate_keyword} "0>1-3"' + (
            f" {sort_keyword} -1" if sort_keyword else ""
        )
        parser.error(
            f"--dev 环境下 {rule} 必须同时提供或同时不提供，"
            "不能只提供其中一部分。\n"
            "示例:\n"
            "    全部不提供(使用预设): python cate_level.py --dev\n"
            f"    全部提供:             {example_full}"
        )

    # --------------------------------------------------------
    # dev 环境预设值：全部未提供时套用预设
    # --------------------------------------------------------

    preset = False

    if env == "dev" and provided_count == 0:
        project_id = validate_project_id(PRESET_PROJECT_ID)
        user_indexes = parse_user_indexes(PRESET_USER_INDEXES)
        user_arg_raw = PRESET_USER_INDEXES
        cate_indexes = parse_cate_indexes(PRESET_CATE_INDEXES)
        cli_arg_raw = PRESET_CATE_INDEXES
        cli_is_ut = False
        if sort_keyword:
            so_arg_raw = PRESET_SO
            so_is_ut = False
        preset = True

    # --------------------------------------------------------
    # pro 环境参数检查：p/u/{cate_keyword}[/{sort_keyword}] 必须同时提供
    # --------------------------------------------------------

    if env == "pro":
        if not project_id:
            parser.error("--pro 环境必须指定: p 项目编号")

        if user_indexes is None:
            parser.error("--pro 环境必须指定: u 用户索引")

        if not cli_arg_raw:
            parser.error(f"--pro 环境必须指定: {cate_keyword} 分类范围")

        if sort_keyword and not so_arg_raw:
            parser.error(f"--pro 环境必须指定: {sort_keyword} 排序参数")

    return CateRunArgs(
        env=env,
        project_id=project_id,
        user_indexes=user_indexes or [],
        user_arg_raw=user_arg_raw,
        cate_indexes=cate_indexes,
        cli_arg_raw=cli_arg_raw,
        cli_is_ut=cli_is_ut,
        so_arg_raw=so_arg_raw,
        so_is_ut=so_is_ut,
        preset=preset,
    )
