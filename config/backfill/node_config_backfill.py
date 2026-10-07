"""
节点配置回填模块

职责：

    根据各层 UNIT 配置中的 child_node_list，
    将父级 UnitNodeConfig 的 css / xpath
    回填到对应子节点 NormalNodeConfig 的：

        father_css
        father_xpath

回填规则：

    UnitNodeConfig.child_node_list（list[str]，加载期已按逗号切分）
        ↓
    查找对应 NormalNodeConfig.node_name
        ↓
    回填父级搜索范围：

        NormalNodeConfig.father_css
        NormalNodeConfig.father_xpath

说明：

    本模块只负责“回填关系”，
    不负责配置文件解析。

    UNIT 配置和普通节点配置都完成加载后，
    由上层统一调用：

        backfill_unit_node_parent_filters(config)

    再进入 Parser / Processor 等运行阶段。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable

from config.loader.base.base_loader import parse_filter_value_range
from config.loader.common.config_loader_utils import parse_node_name_suffix
from config.loader.unit.unit_loader import UnitConfigError
from config.model.node.normal_node_config import NormalNodeConfig
from config.model.node.unit_node_config import UnitNodeConfig

if TYPE_CHECKING:
    from config.loader.script_config import ScriptConfig


logger = logging.getLogger(__name__)


# ==========================================================
# 常量
# ==========================================================

_CHILD_NODE_LIST_SEPARATOR = ","

# 各层 CHILD_NODE_LIST 引用名必须以此前缀开头
_LAYER_PREFIX = {
    "CATE_LEVEL": "CATE_LEVEL_",
    "CATE_LIST": "CATE_LIST_",
    "DETAIL": "DETAIL_",
}


# ==========================================================
# 公共入口
# ==========================================================


def backfill_unit_node_parent_filters(
    config: ScriptConfig,
) -> None:
    """
    根据 ScriptConfig 中的 UNIT 配置，
    回填所有对应 NormalNodeConfig 的父级搜索范围。

    回填范围包括：

        CATE_LEVEL
        CATE_LIST
        DETAIL

    Args:
        config:
            完整的 ScriptConfig。

    Returns:
        None

    注意：
        该函数直接修改 ScriptConfig 中已有的
        NormalNodeConfig 对象，不创建新的配置对象。
    """

    # ------------------------------------------------------
    # CATE_LEVEL
    # ------------------------------------------------------

    _backfill_from_unit_group(
        unit_items=_iter_cate_level_units(config),
        normal_nodes=_iter_cate_level_nodes(config),
    )

    # ------------------------------------------------------
    # CATE_LIST
    # ------------------------------------------------------

    _backfill_from_unit_group(
        unit_items=_iter_cate_list_units(config),
        normal_nodes=_iter_cate_list_nodes(config),
    )

    # ------------------------------------------------------
    # DETAIL
    # ------------------------------------------------------

    _backfill_from_unit_group(
        unit_items=_iter_detail_units(config),
        normal_nodes=_iter_detail_nodes(config),
    )


# ==========================================================
# 各配置层节点收集
# ==========================================================


def _iter_cate_level_units(
    config: ScriptConfig,
) -> Iterable[UnitNodeConfig]:
    """
    获取 CATE_LEVEL 的所有 UnitNodeConfig。
    """

    return (
        config.cate_level_unit.unit0,
        config.cate_level_unit.unit1,
        config.cate_level_unit.unit2,
        config.cate_level_unit.unit3,
        config.cate_level_unit.unit4,
    )


def _iter_cate_level_nodes(
    config: ScriptConfig,
) -> Iterable[NormalNodeConfig]:
    """
    获取 CATE_LEVEL 的所有 NormalNodeConfig。
    """

    return (
        config.cate_level.level1.link,
        config.cate_level.level1.name,
        config.cate_level.level2.link,
        config.cate_level.level2.name,
        config.cate_level.level3.link,
        config.cate_level.level3.name,
        config.cate_level.level4.link,
        config.cate_level.level4.name,
    )


def _iter_cate_list_units(
    config: ScriptConfig,
) -> Iterable[UnitNodeConfig]:
    """
    获取 CATE_LIST 的所有 UnitNodeConfig。
    """

    return (
        config.cate_list_unit.unit0,
        config.cate_list_unit.unit1,
        config.cate_list_unit.unit2,
        config.cate_list_unit.unit3,
        config.cate_list_unit.unit4,
    )


def _iter_cate_list_nodes(
    config: ScriptConfig,
) -> Iterable[NormalNodeConfig]:
    """
    获取当前内容类型 CATE_LIST 配置中的所有 NormalNodeConfig。
    """

    item = config.get_cate_list_item()

    return _iter_normal_nodes_from_item(item)


def _iter_detail_units(
    config: ScriptConfig,
) -> Iterable[UnitNodeConfig]:
    """
    获取 DETAIL 的所有 UnitNodeConfig。
    """

    return (
        config.detail_unit.unit0,
        config.detail_unit.unit1,
        config.detail_unit.unit2,
        config.detail_unit.unit3,
        config.detail_unit.unit4,
    )


def _iter_detail_nodes(
    config: ScriptConfig,
) -> Iterable[NormalNodeConfig]:
    """
    获取当前内容类型 DETAIL 配置中的所有 NormalNodeConfig。
    """

    item = config.get_detail_item()

    return _iter_normal_nodes_from_item(item)


# ==========================================================
# 通用 Item 节点收集
# ==========================================================


def _iter_normal_nodes_from_item(
    item: object,
) -> Iterable[NormalNodeConfig]:
    """
    获取 CATE_LIST / DETAIL Item 中所有 NormalNodeConfig。

    Item 结构统一为：

        common
        product / article
        raw

    每个配置对象内部的字段均为 NormalNodeConfig。
    """

    groups = (
        item.common,
        getattr(item, "product", None),
        getattr(item, "article", None),
        item.raw,
    )

    for group in groups:
        if group is None:
            continue

        for field_name in getattr(
            type(group),
            "__dataclass_fields__",
            {},
        ):
            node = getattr(group, field_name, None)

            if isinstance(node, NormalNodeConfig):
                yield node


# ==========================================================
# 单组回填
# ==========================================================


def _backfill_from_unit_group(
    unit_items: Iterable[UnitNodeConfig],
    normal_nodes: Iterable[NormalNodeConfig],
) -> None:
    """
    根据一组 UnitNodeConfig，
    回填对应的一组 NormalNodeConfig。
    """

    normal_node_map = _build_normal_node_map(normal_nodes)

    for unit in unit_items:
        _backfill_from_unit(
            unit=unit,
            normal_node_map=normal_node_map,
        )


# ==========================================================
# 普通节点映射
# ==========================================================
def _build_normal_node_map(
    normal_nodes: Iterable[NormalNodeConfig],
) -> dict[str, NormalNodeConfig]:
    """
    建立：

        node_name -> NormalNodeConfig

    映射。

    这样 UNIT 的 child_node_list
    可以直接通过 node_name 找到对应普通节点。

    要求：
        node_name 在当前层必须唯一。
        如果发现重复 node_name，视为配置错误并抛出 UnitConfigError。
    """

    normal_node_map: dict[str, NormalNodeConfig] = {}

    for node in normal_nodes:
        node_name = node.node_name.strip()

        if not node_name:
            continue

        if node_name in normal_node_map:
            raise UnitConfigError(f"发现重复 NormalNodeConfig.node_name：{node_name}")

        normal_node_map[node_name] = node

    return normal_node_map


# ==========================================================
# 单个 Unit 回填
# ==========================================================


def _backfill_from_unit(
    unit: UnitNodeConfig,
    normal_node_map: dict[str, NormalNodeConfig],
) -> None:
    """
    根据一个 UnitNodeConfig，
    将其父级选择器回填到 child_node_list 指定的普通节点。

    回填规则按父节点 _CHILD_BLOCK 取值分流：

        child_block == 1（默认）
            块提取：子节点在父节点提取出的元素列表内逐元素提取，
            不需要 father_css / father_xpath 再次定位父节点，故跳过回填。

        child_block == 0
            独立提取：子节点单独提取，需要通过 father_css / father_xpath
            定位父级搜索范围，按原逻辑回填。
    """

    child_names = _parse_child_node_list(unit.all_child_node_list)

    if not child_names:
        return

    # _CHILD_BLOCK == 1：块提取，不回填 father_css / father_xpath / father_child_max_count
    if unit.child_block == 1:
        logger.debug(
            "跳过回填（CHILD_BLOCK=1，块提取）：unit=%s",
            unit.node_name,
        )
        return

    for child_name in child_names:
        child_node = normal_node_map.get(child_name)

        if child_node is None:
            logger.warning(
                "UNIT child_node_list 指定的子节点不存在：%s",
                child_name,
            )
            continue

        child_node.father_css = unit.css
        child_node.father_xpath = unit.xpath
        child_node.father_child_max_count = unit.child_max_count

        logger.debug(
            "回填父级搜索范围：child=%s, father_css=%s, father_xpath=%s, father_child_max_count=%s",
            child_name,
            unit.css,
            unit.xpath,
            unit.child_max_count,
        )


# ==========================================================
# child_node_list 解析
# ==========================================================


def _parse_child_node_list(
    child_node_list: list[str],
) -> list[str]:
    """
    解析 UnitNodeConfig.child_node_list。

    child_node_list 在配置加载期已按逗号切分为 list[str]，
    此处仅做防御性清洗：去除首尾空白、忽略空节点名。

    返回：
        list[str] 节点名称清单。
    """

    if not child_node_list:
        return []

    child_names = []

    for name in child_node_list:
        name = name.strip()

        if not name:
            continue

        child_names.append(name)

    return child_names


# ==========================================================
# CHILD_NODE_LIST 合法性校验
# ==========================================================


def validate_unit_child_filters(config: ScriptConfig) -> None:
    """
    校验三层各 UNIT 的 CHILD_NODE_LIST 引用合法性。

    检查：
        1. 引用名必须以当前层前缀开头（CATE_LEVEL_ / CATE_LIST_ / DETAIL_）；
        2. 引用节点必须存在于当前层，且 node_name 非空。

    NormalNodeConfig 自身的基础属性由配置加载阶段负责校验。

    校验失败抛 UnitConfigError，包含层级、UNIT、配置项、节点名。
    """

    _validate_layer_child_filters(
        _iter_cate_level_units(config),
        _iter_cate_level_nodes(config),
        "CATE_LEVEL",
    )
    _validate_layer_child_filters(
        _iter_cate_list_units(config),
        _iter_cate_list_nodes(config),
        "CATE_LIST",
    )
    _validate_layer_child_filters(
        _iter_detail_units(config),
        _iter_detail_nodes(config),
        "DETAIL",
    )


def _validate_layer_child_filters(
    unit_items: Iterable[UnitNodeConfig],
    normal_nodes: Iterable[NormalNodeConfig],
    layer: str,
) -> None:
    """校验单层各 UNIT 的 CHILD_NODE_LIST。"""

    layer_prefix = _LAYER_PREFIX[layer]
    node_map = _build_normal_node_map(normal_nodes)

    for unit in unit_items:
        child_names = _parse_child_node_list(unit.all_child_node_list)
        if not child_names:
            continue

        for child_name in child_names:
            # 前缀校验：只能引用本层节点
            if not child_name.startswith(layer_prefix):
                raise UnitConfigError(
                    f"{layer} 层 UNIT child_node_list 引用了非本层节点："
                    f"{unit.node_name}_CHILD_NODE_LIST={child_name}，"
                    f"必须以 {layer_prefix} 前缀开头"
                )

            # 节点存在性校验。
            # NormalNodeConfig 的基础属性由配置加载阶段负责校验。
            if child_name not in node_map:
                raise UnitConfigError(
                    f"{layer} 层 UNIT child_node_list 引用了不存在的节点："
                    f"{unit.node_name}_CHILD_NODE_LIST={child_name}，"
                    f"该节点未在当前层配置中定义"
                )


# ==========================================================
# NormalNode 列表构建
# ==========================================================


def build_normal_node_lists(config: ScriptConfig) -> None:
    """
    为三层分别构建 all_normal_node_list 与各类启用节点列表。

    all_normal_node_list：
        纳入当前层已配置（node_name 非空）的 NormalNodeConfig 节点名称，
        包含纯 _COMBINE 节点。

    enable_locator_node_list：
        纳入加载期已判定 locator_enabled=True 的节点。

    enable_combine_node_list：
        纳入加载期已判定 combine_enabled=True 的节点。

    locator_enabled / combine_enabled 均由 set_node_config_field
    在配置加载期根据节点属性组合规则计算得到。
    """

    # CATE_LEVEL
    config.cate_level.all_node_list = _build_all_node_list(_iter_cate_level_nodes(config))
    config.cate_level.enable_locator_node_list = _build_enable_locator_node_list(_iter_cate_level_nodes(config))
    config.cate_level.enable_combine_node_list = _build_enable_combine_node_list(_iter_cate_level_nodes(config))

    # CATE_LIST（当前 content_type）
    cate_list_item = config.get_cate_list_item()
    cate_list_item.all_node_list = _build_all_node_list(_iter_normal_nodes_from_item(cate_list_item))
    cate_list_item.enable_locator_node_list = _build_enable_locator_node_list(
        _iter_normal_nodes_from_item(cate_list_item)
    )
    cate_list_item.enable_combine_node_list = _build_enable_combine_node_list(
        _iter_normal_nodes_from_item(cate_list_item)
    )

    # DETAIL（当前 content_type）
    detail_item = config.get_detail_item()
    detail_item.all_node_list = _build_all_node_list(_iter_normal_nodes_from_item(detail_item))
    detail_item.enable_locator_node_list = _build_enable_locator_node_list(_iter_normal_nodes_from_item(detail_item))
    detail_item.enable_combine_node_list = _build_enable_combine_node_list(_iter_normal_nodes_from_item(detail_item))


def _build_all_node_list(
    nodes: Iterable[NormalNodeConfig],
) -> list[str]:
    """遍历一组节点，构建 all_normal_node_list（已配置节点的名称列表）。

    收录条件：node_name 非空（即 script.txt 中出现过该节点的四键之一）。
    不判断 is_enabled，故含纯 _COMBINE 节点。
    """

    all_normal_node_list: list[str] = []

    for node in nodes:
        node_name = node.node_name.strip()
        if not node_name:
            continue
        all_normal_node_list.append(node_name)

    return all_normal_node_list


def _build_enable_locator_node_list(
    nodes: Iterable[NormalNodeConfig],
) -> list[str]:
    """
    遍历一组节点，构建 enable_locator_node_list（已启用 locator 的节点名称列表）。

    收录条件：node_name 非空且 locator_enabled 为 True。
    locator_enabled 由 set_node_config_field
    在配置加载期根据节点属性组合规则计算得到。
    """

    enable_locator_node_list: list[str] = []

    for node in nodes:
        node_name = node.node_name.strip()
        if not node_name:
            continue
        if not node.locator_enabled:
            continue
        enable_locator_node_list.append(node_name)

    return enable_locator_node_list


def _build_enable_combine_node_list(
    nodes: Iterable[NormalNodeConfig],
) -> list[str]:
    """
    遍历一组节点，构建 enable_combine_node_list（已启用 combine 的节点名称列表）。

    收录条件：
        1. node_name 非空；
        2. combine_enabled 为 True。

    combine_enabled 由 set_node_config_field 在加载期根据 COMBINE
    非空且 CSS/XPATH 均为空的条件置位。
    """

    enable_combine_node_list: list[str] = []

    for node in nodes:
        node_name = node.node_name.strip()
        if not node_name:
            continue

        if not node.combine_enabled:
            continue

        enable_combine_node_list.append(node_name)

    return enable_combine_node_list


# ==========================================================
# Unit 子节点启用列表构建
# ==========================================================


def build_normal_child_lists(config: ScriptConfig) -> None:
    """
    为三层每个 UnitNodeConfig 构建 enable_locator_child_list /
    enable_combine_child_list。

    依据：unit.child_node_list 中引用的子节点名，
    结合当前层 NormalNodeConfig 的 locator_enabled / combine_enabled 取值筛选。

    每层 UNIT_COUNT 个 unit（索引 0 ~ UNIT_COUNT-1）。
    locator_enabled / combine_enabled 均由 set_node_config_field
    在配置加载期根据节点属性组合规则计算得到。
    """

    # CATE_LEVEL
    cate_level_node_map = _build_normal_node_map(_iter_cate_level_nodes(config))
    for unit in _iter_cate_level_units(config):
        unit.enable_locator_child_node_list = _build_enable_locator_child_node_list(unit, cate_level_node_map)
        unit.enable_combine_child_node_list = _build_enable_combine_child_node_list(unit, cate_level_node_map)

    # CATE_LIST（当前 content_type）
    cate_list_item = config.get_cate_list_item()
    cate_list_node_map = _build_normal_node_map(_iter_normal_nodes_from_item(cate_list_item))
    for unit in _iter_cate_list_units(config):
        unit.enable_locator_child_node_list = _build_enable_locator_child_node_list(unit, cate_list_node_map)
        unit.enable_combine_child_node_list = _build_enable_combine_child_node_list(unit, cate_list_node_map)

    # DETAIL（当前 content_type）
    detail_item = config.get_detail_item()
    detail_node_map = _build_normal_node_map(_iter_normal_nodes_from_item(detail_item))
    for unit in _iter_detail_units(config):
        unit.enable_locator_child_node_list = _build_enable_locator_child_node_list(unit, detail_node_map)
        unit.enable_combine_child_node_list = _build_enable_combine_child_node_list(unit, detail_node_map)


def _build_enable_locator_child_node_list(
    unit: UnitNodeConfig,
    normal_node_map: dict[str, NormalNodeConfig],
) -> list[str]:
    """
    遍历 unit.child_node_list 中引用的子节点名，
    纳入对应 NormalNodeConfig.locator_enabled 为 True 的名称。

    收录条件：
        1. 子节点名非空；
        2. 子节点名能在当前层 normal_node_map 中找到对应 NormalNodeConfig；
        3. 该 NormalNodeConfig.locator_enabled 为 True。

    引用了不存在的节点（node is None）直接跳过，
    合法性由 validate_unit_child_filters 负责。
    """

    enable_locator_child_list: list[str] = []

    for child_name in unit.all_child_node_list:
        child_name = child_name.strip()
        if not child_name:
            continue

        node = normal_node_map.get(child_name)
        if node is None:
            continue
        if not node.locator_enabled:
            continue

        enable_locator_child_list.append(child_name)

    return enable_locator_child_list


def _build_enable_combine_child_node_list(
    unit: UnitNodeConfig,
    normal_node_map: dict[str, NormalNodeConfig],
) -> list[str]:
    """
    遍历 unit.child_node_list 中引用的子节点名，
    纳入对应 NormalNodeConfig.combine_enabled 为 True 的名称。

    收录条件：
        1. 子节点名非空；
        2. 子节点名能在当前层 normal_node_map 中找到对应 NormalNodeConfig；
        3. 该 NormalNodeConfig.combine_enabled 为 True。

    引用了不存在的节点（node is None）直接跳过，
    合法性由 validate_unit_child_filters 负责。
    """

    enable_combine_child_list: list[str] = []

    for child_name in unit.all_child_node_list:
        child_name = child_name.strip()
        if not child_name:
            continue

        node = normal_node_map.get(child_name)
        if node is None:
            continue
        if not node.combine_enabled:
            continue

        enable_combine_child_list.append(child_name)

    return enable_combine_child_list


# ==========================================================
# DEFAULT_VALUE 合法性校验
# ==========================================================


def validate_layer_default_values(config: ScriptConfig) -> None:
    """
    校验三层 DEFAULT_VALUE 配置。

    每层校验：
        1. default_value_node_list 与 default_value_value_list 同时为空或同时非空；
        2. 两者数量一致；
        3. node_list 中每个节点名必须是带后缀的完整配置键名，
           后缀为 _CSS / _XPATH / _ATTR / _REGEX 之一，不得为 _COMBINE；
        4. 节点名必须以当前层前缀开头；
        5. 剥离后缀后的逻辑名必须在当前层 node_map 中存在。

    node_map 复用 _build_normal_node_map。
    CATE_LIST / DETAIL 用当前 content_type 的节点集合。
    """

    _validate_layer_default_value(
        _iter_cate_level_nodes(config),
        config.cate_level,
        "CATE_LEVEL",
    )
    _validate_layer_default_value(
        _iter_normal_nodes_from_item(config.get_cate_list_item()),
        config.get_cate_list_item(),
        "CATE_LIST",
    )
    _validate_layer_default_value(
        _iter_normal_nodes_from_item(config.get_detail_item()),
        config.get_detail_item(),
        "DETAIL",
    )


def _validate_layer_default_value(
    normal_nodes: Iterable[NormalNodeConfig],
    item: object,
    layer: str,
) -> None:
    """校验单层 DEFAULT_VALUE。"""

    node_list = getattr(item, "default_value_node_list", [])
    value_list = getattr(item, "default_value_value_list", [])

    has_node = bool(node_list)
    has_value = bool(value_list)

    # 1. 成对：同时为空或同时非空
    if has_node != has_value:
        raise UnitConfigError(
            f"{layer} 层 DEFAULT_VALUE 配置错误："
            f"DEFAULT_VALUE_NODE_LIST 与 DEFAULT_VALUE_VALUE_LIST 必须同时为空或同时有值"
            f"（当前 node_list={node_list}，value_list={value_list}）"
        )

    if not has_node:
        return

    # 2. 数量一致
    if len(node_list) != len(value_list):
        raise UnitConfigError(
            f"{layer} 层 DEFAULT_VALUE 配置错误："
            f"NODE_LIST 与 VALUE_LIST 数量不一致"
            f"（node_list 有 {len(node_list)} 项，value_list 有 {len(value_list)} 项）"
        )

    layer_prefix = _LAYER_PREFIX[layer]
    node_map = _build_normal_node_map(normal_nodes)

    for node_name in node_list:
        _validate_node_reference(node_name, layer, layer_prefix, node_map, "DEFAULT_VALUE_NODE_LIST")


# ==========================================================
# FILTER 合法性校验
# ==========================================================


def validate_layer_filters(config: ScriptConfig) -> None:
    """
    校验三层 FILTER 配置。

    节点类配置（ALLOW_VALUE_NODE / REJECT_VALUE_NODE /
    AND_NOT_EMPTY_NODE_LIST / OR_NOT_EMPTY_NODE_LIST）：
        后缀 + 当前层前缀 + 存在性（同 DEFAULT_VALUE）。

    范围类配置（ALLOW_VALUE_RANGE / REJECT_VALUE_RANGE）：
        调用 parse_filter_value_range 校验格式与左右值大小。
    """

    _validate_layer_filter(
        _iter_cate_level_nodes(config),
        config.cate_level,
        "CATE_LEVEL",
    )
    _validate_layer_filter(
        _iter_normal_nodes_from_item(config.get_cate_list_item()),
        config.get_cate_list_item(),
        "CATE_LIST",
    )
    _validate_layer_filter(
        _iter_normal_nodes_from_item(config.get_detail_item()),
        config.get_detail_item(),
        "DETAIL",
    )


def _validate_layer_filter(
    normal_nodes: Iterable[NormalNodeConfig],
    item: object,
    layer: str,
) -> None:
    """校验单层 FILTER。"""

    layer_prefix = _LAYER_PREFIX[layer]
    node_map = _build_normal_node_map(normal_nodes)

    # 节点类：单个 str
    # FILTER 允许裸逻辑名（如 CATE_LIST_PRODUCT_PRICE），故 allow_bare=True
    for attr, config_key in (
        ("filter_allow_value_node", f"{layer}_FILTER_ALLOW_VALUE_NODE"),
        ("filter_reject_value_node", f"{layer}_FILTER_REJECT_VALUE_NODE"),
    ):
        node_name = getattr(item, attr, "")
        if node_name:
            _validate_node_reference(
                node_name,
                layer,
                layer_prefix,
                node_map,
                config_key,
                allow_bare=True,
            )

    # 节点类：list[str]
    for attr, config_key in (
        ("filter_and_not_empty_node_list", f"{layer}_FILTER_AND_NOT_EMPTY_NODE_LIST"),
        ("filter_or_not_empty_node_list", f"{layer}_FILTER_OR_NOT_EMPTY_NODE_LIST"),
    ):
        node_names = getattr(item, attr, [])
        for name in node_names:
            _validate_node_reference(
                name,
                layer,
                layer_prefix,
                node_map,
                config_key,
                allow_bare=True,
            )

    # 范围类：str，调用 parse_filter_value_range
    for attr, config_key in (
        ("filter_allow_value_range", f"{layer}_FILTER_ALLOW_VALUE_RANGE"),
        ("filter_reject_value_range", f"{layer}_FILTER_REJECT_VALUE_RANGE"),
    ):
        range_value = getattr(item, attr, "")
        if range_value:
            try:
                parse_filter_value_range(range_value)
            except ValueError as e:
                raise UnitConfigError(f"{layer} 层 {config_key} 配置错误：{e}（当前值为 {range_value!r}）")


# ==========================================================
# 节点引用通用校验（DEFAULT_VALUE / FILTER 共用）
# ==========================================================


def _validate_node_reference(
    node_name: str,
    layer: str,
    layer_prefix: str,
    node_map: dict[str, NormalNodeConfig],
    config_key: str,
    *,
    allow_bare: bool = False,
) -> None:
    """
    校验单个节点引用的合法性。

    规则：
        1. 节点名必须以当前层前缀开头（CATE_LEVEL_ / CATE_LIST_ / DETAIL_）；
        2. 节点名后缀必须是 _CSS / _XPATH / _ATTR / _REGEX 之一，不得为 _COMBINE；
        3. 剥离后缀后的逻辑名必须在当前层 node_map 中存在。

    allow_bare：
        True 时（FILTER），允许直接写裸逻辑名（不带后缀，
        如 CATE_LIST_PRODUCT_PRICE），等价于引用该节点已配置的
        任一定位/提取后缀；此时额外要求该节点至少配置了一项
        _CSS / _XPATH / _ATTR / _REGEX（纯 _COMBINE 节点不可引用）。
        False 时（DEFAULT_VALUE），维持原契约：必须带后缀。
    """

    node_name = node_name.strip()
    if not node_name:
        return

    # 1. 当前层前缀
    if not node_name.startswith(layer_prefix):
        raise UnitConfigError(
            f"{layer} 层 {config_key} 配置错误：节点 {node_name} 不属于当前层（必须以 {layer_prefix} 前缀开头）"
        )

    # 2. 后缀校验
    suffix = parse_node_name_suffix(node_name)

    if suffix is None:
        # 无后缀：仅 FILTER（allow_bare=True）允许，视为裸逻辑名
        if not allow_bare:
            raise UnitConfigError(
                f"{layer} 层 {config_key} 配置错误：节点 {node_name} 缺少定位/提取后缀"
                f"（必须以 _CSS / _XPATH / _ATTR / _REGEX 结尾）"
            )
        logical_name = node_name
    else:
        if suffix == "COMBINE":
            raise UnitConfigError(
                f"{layer} 层 {config_key} 配置错误：节点 {node_name} 是 _COMBINE 节点"
                f"（不允许引用 _COMBINE 节点，只能引用普通定位/提取节点）"
            )
        # 剥离后缀得逻辑名
        logical_name = node_name[: -(len(suffix) + 1)]

    # 3. 存在性：查 node_map
    node = node_map.get(logical_name)
    if node is None:
        raise UnitConfigError(
            f"{layer} 层 {config_key} 配置错误：节点 {node_name} 在当前层未定义"
            f"（剥离后缀后的节点名 {logical_name} 未在当前层配置中出现）"
        )

    # 4. 裸名引用时：该节点必须至少配置了一项定位/提取器，
    #    纯 _COMBINE 节点不可被 FILTER 引用。
    if suffix is None and allow_bare:
        if not (node.css or node.xpath or node.attr or node.regex):
            raise UnitConfigError(
                f"{layer} 层 {config_key} 配置错误：节点 {node_name} "
                f"未配置任何定位/提取后缀"
                f"（_CSS / _XPATH / _ATTR / _REGEX 至少需一项有值，"
                f"纯 _COMBINE 节点不可用于 FILTER）"
            )
