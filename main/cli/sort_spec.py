"""
so（sort and order）参数解析/校验模块

负责:

    - so 参数的 5 种格式解析与校验
    - 排序字段、排序顺序的成员校验（对照 script.txt 配置）

不负责:

    - argparse 参数定义
    - 命令行入口
    - so 与 u -1 的冲突（在 args_parser 中处理）

支持格式:

    -1            不使用排序字段
    0             使用默认排序字段
    ut            使用 user_pool.xlsx 第 9 列 so(sort and order) 的值
    "字段"        使用指定单个排序字段（须在 CATE_LIST_SORT_FIELDS 内）
    "字段|顺序"   字段+顺序（字段须同时在 CATE_LIST_SORT_FIELDS 与
                  CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS 内；
                  顺序须在 CATE_LIST_SORT_ORDER_VALUES 内）

说明:

    本模块需要 script_config.cate_list 的三个列表（sort_fields /
    sort_order_supported_fields / sort_order_values）作为成员校验依据，
    因此在 cate_list.py 的 load_configs 之后调用。

    so=ut 时，第 9 列取出的值需用 allow_ut=False 再次调用本模块校验
    （第 9 列的值不能再是 ut，否则“表格里再用表格”）。
"""

from __future__ import annotations

from dataclasses import dataclass

from config.context.pro_var import build_sort_program_vars


@dataclass
class SoSpec:
    """
    so 参数解析结果

    Attributes:
        mode: "none"(-1) | "default"(0) | "ut" | "field"(格式4) | "field_order"(格式5)
        field: 排序字段（mode 为 field/field_order 时有值）
        order: 排序顺序（仅 mode 为 field_order 时有值）
        raw: 原始字符串
    """

    mode: str
    field: str | None = None
    order: str | None = None
    raw: str = ""

    def to_sort_program_vars(self) -> dict:
        """
        由 so 解析结果产出排序相关项目变量，供运行期对含
        ${PRO_CATE_LEVEL_SORT_FIELD} / ${PRO_CATE_LEVEL_SORT_ORDER} 占位符的
        配置值（如 redis head_key 前缀模板）做二次替换。

        各 mode 下的产出：
            field_order : field / order 原值
            field       : field 有值，order 为空串
            none/default/ut : 两者均空串
            （ut 仅为"按用户取表"的标记，实际替换用的是逐用户解析后的 spec，
             不会拿 ut 标记本身去替换。）
        """
        return build_sort_program_vars(self.field, self.order)


class SoValidationError(Exception):
    """so 参数校验错误"""


def parse_and_validate_so(
    value: str,
    *,
    sort_fields: list[str],
    sort_order_supported_fields: list[str],
    sort_order_values: list[str],
    allow_ut: bool = True,
) -> SoSpec:
    """
    解析并校验 so 参数值。

    Args:
        value: so 参数原始字符串。
        sort_fields: CATE_LIST_SORT_FIELDS 列表。
        sort_order_supported_fields: CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS 列表。
        sort_order_values: CATE_LIST_SORT_ORDER_VALUES 列表。
        allow_ut: 是否允许值为 ut（命令行值允许；第 9 列取出的值不允许）。

    Returns:
        SoSpec

    Raises:
        SoValidationError: 格式或成员校验失败。
    """
    v = (value or "").strip()

    # 格式一：-1 → 不使用排序字段
    if v == "-1":
        return SoSpec(mode="none", raw=v)

    # 格式二：0 → 默认排序字段
    if v == "0":
        return SoSpec(mode="default", raw=v)

    # 格式三：ut → 使用用户表第 9 列的值
    if v.lower() == "ut":
        if not allow_ut:
            raise SoValidationError("用户表第9列读取出的值不能再是：ut（表格里再用表格）。")
        return SoSpec(mode="ut", raw=v)

    # 格式五：字段|顺序
    if "|" in v:
        parts = v.split("|")
        if len(parts) > 2:
            raise SoValidationError('so参数的值，"|"单竖符号，只能出现0次，或1次。')

        field, order = parts[0], parts[1]

        if not field and not order:
            raise SoValidationError("排序字段和排序顺序都不能为空。")
        if not field:
            raise SoValidationError("排序字段不能为空。")
        if not order:
            raise SoValidationError("排序顺序不能为空。")

        if "," in field:
            raise SoValidationError(
                "so 参数仅支持单字段排序，不支持逗号分隔、也不支持多字段排序。"
                "CATE_LIST_SORT_FIELDS 是可以配置多个字段，但 so 命令参数一次"
                "只能选择其中一个字段，作为排序字段。"
            )

        _validate_field_membership(field, sort_fields)
        _validate_supported_field_membership(field, sort_order_supported_fields)
        _validate_order_membership(order, sort_order_values)

        return SoSpec(mode="field_order", field=field, order=order, raw=v)

    # 格式四：单个排序字段
    if "," in v:
        raise SoValidationError(
            "so 参数仅支持单字段排序，不支持逗号分隔、也不支持多字段排序。"
            "CATE_LIST_SORT_FIELDS 是可以配置多个字段，但 so 命令参数一次"
            "只能选择其中一个字段，作为排序字段。"
        )

    _validate_field_membership(v, sort_fields)
    return SoSpec(mode="field", field=v, raw=v)


# ============================================================
# 成员校验
# ============================================================


def _validate_field_membership(field: str, sort_fields: list[str]) -> None:
    """校验排序字段是否在 CATE_LIST_SORT_FIELDS 内（格式四之情况二 / 格式五共用）。"""
    if field not in sort_fields:
        raise SoValidationError(f'排序字段："{field}" 在：CATE_LIST_SORT_FIELDS 排序字段列表中，查找不到。')


def _validate_supported_field_membership(field: str, sort_order_supported_fields: list[str]) -> None:
    """校验排序字段是否在 CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS 内（格式五之情况一）。"""
    if field not in sort_order_supported_fields:
        raise SoValidationError(
            f'so 参数的排序字段"{field}" 在：CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS 排序字段列表中，查找不到。'
        )


def _validate_order_membership(order: str, sort_order_values: list[str]) -> None:
    """校验排序顺序是否在 CATE_LIST_SORT_ORDER_VALUES 内（格式五之情况二）。"""
    if order not in sort_order_values:
        raise SoValidationError(
            f'so 参数的排序顺序"{order}" 在：CATE_LIST_SORT_ORDER_VALUES 排序顺序列表中，查找不到。'
        )
