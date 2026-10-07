"""CATE_LIST 数据项过滤。"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.model.cate_list.cate_list_article_item import CateListArticleItem
    from config.model.cate_list.cate_list_product_item import CateListProductItem
    from parser.cate_list.cate_list_parser import CateListParsedItem


def filter_cate_list_items(
    *,
    records: list[CateListParsedItem],
    cate_list_item: CateListProductItem | CateListArticleItem,
) -> tuple[
    list[CateListParsedItem],
    list[CateListParsedItem],
]:
    """
    根据 CATE_LIST_FILTER_* 配置过滤解析结果。

    过滤规则：

        1. FILTER_ALLOW_VALUE：
           指定节点值必须落在允许范围内。

        2. FILTER_REJECT_VALUE：
           指定节点值落在拒绝范围内时，记录无效。

        3. FILTER_AND_NOT_EMPTY_NODE_LIST：
           指定节点全部非空。

        4. FILTER_OR_NOT_EMPTY_NODE_LIST：
           指定节点至少一个非空。

    各过滤条件之间统一使用 AND 关系。

    Args:
        records:
            已经完成解析的 CATE_LIST 数据项。

        cate_list_item:
            CATE_LIST 配置项。
            根据 content_type 不同，可以是：
                - CateListProductItem
                - CateListArticleItem

    Returns:
        (
            valid_records,
            invalid_records,
        )

        valid_records:
            满足所有已配置过滤条件的记录。

        invalid_records:
            未满足任意一个过滤条件的记录。
    """

    valid_records: list[CateListParsedItem] = []
    invalid_records: list[CateListParsedItem] = []

    # ======================================================
    # 预解析数值范围
    # ======================================================

    allow_value_range = _parse_cate_list_filter_value_range(
        cate_list_item.filter_allow_value_range,
    )

    reject_value_range = _parse_cate_list_filter_value_range(
        cate_list_item.filter_reject_value_range,
    )

    # ======================================================
    # 逐条过滤
    # ======================================================

    for record in records:
        is_valid = _is_cate_list_item_valid(
            record=record,
            cate_list_item=cate_list_item,
            allow_value_range=allow_value_range,
            reject_value_range=reject_value_range,
        )

        if is_valid:
            valid_records.append(record)
        else:
            invalid_records.append(record)

    return valid_records, invalid_records


def _is_cate_list_item_valid(
    *,
    record: CateListParsedItem,
    cate_list_item: CateListProductItem | CateListArticleItem,
    allow_value_range: tuple[Decimal, Decimal] | None,
    reject_value_range: tuple[Decimal, Decimal] | None,
) -> bool:
    """
    判断单条 CateListParsedItem 是否通过 CATE_LIST FILTER。

    所有已经配置的过滤条件必须同时满足。
    """

    # ======================================================
    # 1. ALLOW_VALUE
    # ======================================================

    allow_value_node = cate_list_item.filter_allow_value_node.strip()

    if allow_value_range is not None:
        if not allow_value_node:
            return False

        allow_value = _get_cate_list_filter_node_value(
            record=record,
            node_name=allow_value_node,
        )

        if not _is_cate_list_filter_value_in_range(
            value=allow_value,
            value_range=allow_value_range,
        ):
            return False

    # ======================================================
    # 2. REJECT_VALUE
    # ======================================================

    reject_value_node = cate_list_item.filter_reject_value_node.strip()

    if reject_value_range is not None:
        if not reject_value_node:
            return False

        reject_value = _get_cate_list_filter_node_value(
            record=record,
            node_name=reject_value_node,
        )

        if _is_cate_list_filter_value_in_range(
            value=reject_value,
            value_range=reject_value_range,
        ):
            return False

    # ======================================================
    # 3. AND_NOT_EMPTY
    # ======================================================

    and_not_empty_node_list = cate_list_item.filter_and_not_empty_node_list

    if and_not_empty_node_list:
        for node_name in and_not_empty_node_list:
            node_name = node_name.strip()

            if not node_name:
                continue

            value = _get_cate_list_filter_node_value(
                record=record,
                node_name=node_name,
            )

            if not value.strip():
                return False

    # ======================================================
    # 4. OR_NOT_EMPTY
    # ======================================================

    or_not_empty_node_list = cate_list_item.filter_or_not_empty_node_list

    if or_not_empty_node_list:
        has_not_empty_value = False

        for node_name in or_not_empty_node_list:
            node_name = node_name.strip()

            if not node_name:
                continue

            value = _get_cate_list_filter_node_value(
                record=record,
                node_name=node_name,
            )

            if value.strip():
                has_not_empty_value = True
                break

        if not has_not_empty_value:
            return False

    # ======================================================
    # 所有过滤条件均通过
    # ======================================================

    return True


def _get_cate_list_filter_node_value(
    *,
    record: CateListParsedItem,
    node_name: str,
) -> str:
    """
    根据 CATE_LIST FILTER 节点名，从 CateListParsedItem 中取得实际值。

    Filter 配置使用完整节点键名，例如：

        CATE_LIST_COMMON_MAIN_TITLE_CSS
        CATE_LIST_COMMON_ID_CSS
        CATE_LIST_PRODUCT_PRICE_CSS
        CATE_LIST_RAW_COMMON_TAGS_CSS

    NormalNodeConfig.node_name 不包含 CSS / XPATH / ATTR /
    REGEX / COMBINE 后缀，因此这里先去掉后缀，再映射到
    CateListParsedItem 的实际数据字段。
    """

    full_node_name = node_name.strip().upper()

    if not full_node_name:
        return ""

    # ======================================================
    # 去掉选择器 / COMBINE 后缀
    # ======================================================

    suffixes = (
        "_CSS",
        "_XPATH",
        "_ATTR",
        "_REGEX",
        "_COMBINE",
    )

    base_node_name = full_node_name

    for suffix in suffixes:
        if base_node_name.endswith(suffix):
            base_node_name = base_node_name[: -len(suffix)]
            break

    # ======================================================
    # CATE_LIST_COMMON
    # ======================================================

    common_prefix = "CATE_LIST_COMMON_"

    if base_node_name.startswith(common_prefix):
        field_name = base_node_name[len(common_prefix) :].lower()

        # COMMON_ID 最终保存到 CateListParsedItem.id
        if field_name == "id":
            return str(record.id or "")

        value = getattr(
            record.common,
            field_name,
            "",
        )

        return str(value or "")

    # ======================================================
    # CATE_LIST_PRODUCT
    # ======================================================

    product_prefix = "CATE_LIST_PRODUCT_"

    if base_node_name.startswith(product_prefix):
        field_name = base_node_name[len(product_prefix) :].lower()

        if record.product is None:
            return ""

        value = getattr(
            record.product,
            field_name,
            "",
        )

        return str(value or "")

    # ======================================================
    # CATE_LIST_RAW_COMMON
    # ======================================================

    raw_common_prefix = "CATE_LIST_RAW_COMMON_"

    if base_node_name.startswith(raw_common_prefix):
        field_name = base_node_name[len(raw_common_prefix) :].lower()

        # RAW_COMMON_ID
        if field_name == "id":
            return str(record.raw_id or "")

        # RAW_COMMON_TAGS
        if field_name == "tags":
            return str(record.tags or "")

        raise ValueError(f"不支持的 CATE_LIST FILTER RAW_COMMON 节点：{node_name!r}")

    # ======================================================
    # 当前 CateListParsedItem 没有 ARTICLE 数据对象
    # ======================================================

    article_prefix = "CATE_LIST_ARTICLE_"

    if base_node_name.startswith(article_prefix):
        raise ValueError(f"当前 CateListParsedItem 不支持 ARTICLE FILTER 节点：{node_name!r}")

    # ======================================================
    # 未知节点
    # ======================================================

    raise ValueError(f"无法解析 CATE_LIST FILTER 节点：{node_name!r}")


def _parse_cate_list_filter_value_range(
    range_text: str,
) -> tuple[Decimal, Decimal] | None:
    """
    解析 CATE_LIST FILTER VALUE_RANGE。

    支持：

        空字符串：
            不启用过滤。

        -1：
            不启用过滤。

        100：
            只允许 / 拒绝数值 100。

        100.5：
            只允许 / 拒绝数值 100.5。

        100-200：
            100 <= value <= 200。

        100.5-200.5：
            100.5 <= value <= 200.5。

    Returns:
        (min_value, max_value)

        未配置或 -1：
            None
    """

    range_text = range_text.strip()

    if not range_text:
        return None

    if range_text == "-1":
        return None

    range_pattern = re.fullmatch(
        r"(-?\d+(?:\.\d+)?)\s*(?:-\s*(-?\d+(?:\.\d+)?))?",
        range_text,
    )

    if range_pattern is None:
        raise ValueError(f"非法 CATE_LIST FILTER VALUE_RANGE：{range_text!r}")

    min_text = range_pattern.group(1)
    max_text = range_pattern.group(2)

    try:
        min_value = Decimal(min_text)

        if max_text is None:
            max_value = min_value
        else:
            max_value = Decimal(max_text)

    except InvalidOperation as exc:
        raise ValueError(f"非法 CATE_LIST FILTER VALUE_RANGE：{range_text!r}") from exc

    if min_value > max_value:
        raise ValueError(f"CATE_LIST FILTER VALUE_RANGE 左边界不能大于右边界：{range_text!r}")

    return min_value, max_value


def _is_cate_list_filter_value_in_range(
    *,
    value: str,
    value_range: tuple[Decimal, Decimal],
) -> bool:
    """
    判断节点值是否落在指定数值范围内。

    范围为闭区间：

        min_value <= value <= max_value

    空值或非数字：
        返回 False。
    """

    value = value.strip()

    if not value:
        return False

    try:
        numeric_value = Decimal(value)

    except InvalidOperation:
        return False

    min_value, max_value = value_range

    if numeric_value < min_value:
        return False

    if numeric_value > max_value:
        return False

    return True
