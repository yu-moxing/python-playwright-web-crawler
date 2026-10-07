"""
详情页(DETAIL) - 单元配置

本模块定义 DETAIL_UNIT_[0-4] 对应的配置集合。

职责：
    - 保存 DETAIL 各层级的 UnitNodeConfig
    - 对应 ScriptConfig 中 DETAIL_UNIT_* 配置
    - 不参与数据库存储

说明：
    UnitNodeConfig 是通用的节点单元配置对象，
    本模块只负责将它组织成 DETAIL 所需的 0~4 级结构。
"""

from dataclasses import dataclass, field

from config.model.node.unit_node_config import UnitNodeConfig

# ==========================================================
# DETAIL 单元配置集合
# ==========================================================


@dataclass(slots=True)
class DetailUnitItem:
    """
    DETAIL_UNIT 配置对象集合

    对应配置文件：

        DETAIL_UNIT_0_*
        DETAIL_UNIT_1_*
        DETAIL_UNIT_2_*
        DETAIL_UNIT_3_*
        DETAIL_UNIT_4_*

    每一级实际使用通用的 UnitNodeConfig。
    """

    # 0级单元配置
    unit0: UnitNodeConfig = field(default_factory=UnitNodeConfig)

    # 1级单元配置
    unit1: UnitNodeConfig = field(default_factory=UnitNodeConfig)

    # 2级单元配置
    unit2: UnitNodeConfig = field(default_factory=UnitNodeConfig)

    # 3级单元配置
    unit3: UnitNodeConfig = field(default_factory=UnitNodeConfig)

    # 4级单元配置
    unit4: UnitNodeConfig = field(default_factory=UnitNodeConfig)
