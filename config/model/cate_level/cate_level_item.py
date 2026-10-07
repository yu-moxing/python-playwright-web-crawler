"""
分类层(CATE_LEVEL) 配置对象

本模块仅定义配置文件中 CATE_LEVEL_ 前缀对应的数据结构。

职责：
    - 保存分类层采集配置
    - 对应 ScriptConfig 中 CATE_LEVEL_* 配置
    - 不参与分类树计算
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    普通网页节点配置统一使用 NormalNodeConfig。

    URL 参数顺序、排序字段、翻页配置已迁移到
    config.model.cate_list.cate_list_item（CateListItem / CateListPageConfig）。
"""

from dataclasses import dataclass, field
from typing import List

from config.model.node.normal_node_config import NormalNodeConfig

# ==========================================================
# 0级分类入口
# ==========================================================


@dataclass(slots=True)
class CateLevel0Entry:
    """
    0级分类入口。

    配置格式：

        URL>>>限制Level0分类ID>分类
        URL>>>限制Level0分类ID>大分类||子分类
        URL>>>限制Level0分类ID>大分类||子分类||三级分类

    例如：

        https://e.dangdang.com/list-XS2-dd_sale-0-1.html>>>-1>小说

        https://e.dangdang.com/list-XS2-dd_sale-0-1.html>>>15>小说||言情小说

        https://e.dangdang.com/list-XS2-dd_sale-0-1.html>>>15>小说||言情小说||古代言情

    其中：

        -1
            不限制 Level 0 分类。

        > 0
            限制在指定的 Level 0 分类 ID 下进行分类。
    """

    # 当前入口 URL
    url: str = ""

    # 限制当前入口只能在指定的 Level 0 分类 ID 下进行分类。
    #
    # -1：不限制
    # >0：限制在指定 Level 0 分类 ID
    limit_cate_level_0_id: int = -1

    # 当前入口名称
    #
    # 取分类路径最后一级。
    name: str = ""

    # 完整分类路径
    category_names: List[str] = field(default_factory=list)


# ==========================================================
# 单层分类提取配置
# ==========================================================


@dataclass(slots=True)
class CateLevelConfig:
    """
    单层分类提取配置。

    对应：

        CATE_LEVEL_1_*
        CATE_LEVEL_2_*
        CATE_LEVEL_3_*
        CATE_LEVEL_4_*

    link 和 name 都属于普通网页节点，
    因此统一使用 NormalNodeConfig。
    """

    # ======================================================
    # 分类链接
    # ======================================================

    link: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 分类 ID 提取规则
    #
    # 从分类链接中进一步提取分类 ID。
    link_id_regex: str = ""

    # ======================================================
    # 分类名称
    # ======================================================

    name: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ======================================================
    # 层级采集上限（CATE_LEVEL_MAX_COUNT，广播到 level1~4）
    # ======================================================

    # -1 不限制；>0 限制最大采集数
    # 0、除 -1 外的负数、非整数均非法（校验在 cate_level_loader.parse_max_count）
    max_count: int = -1


# ==========================================================
# CATE_LEVEL 配置
# ==========================================================


@dataclass(slots=True)
class CateLevelItem:
    """
    CATE_LEVEL 配置对象

    对应配置文件：

        CATE_LEVEL_0

        CATE_LEVEL_1_*
        CATE_LEVEL_2_*
        CATE_LEVEL_3_*
        CATE_LEVEL_4_*

    URL 参数顺序、排序字段、翻页配置已迁出至
    config.model.cate_list.cate_list_item（CateListItem）。
    """

    # ======================================================
    # 分层采集控制
    # ======================================================

    # 分层采集开关
    floor_open: list[bool] = field(default_factory=lambda: [True, False, False, False, False])

    # 分层采集有效最大索引
    last_floor_id: int = 0

    # ======================================================
    # 0级分类入口
    # ======================================================

    level0_list: List[CateLevel0Entry] = field(default_factory=list)

    # 0级链接正则
    #
    # 单一配置，作用于全部 0 级入口 URL。
    # 空表示不替换。
    level0_link_regex: str = ""

    # ======================================================
    # 1~4级分类规则
    # ======================================================

    level1: CateLevelConfig = field(default_factory=CateLevelConfig)

    level2: CateLevelConfig = field(default_factory=CateLevelConfig)

    level3: CateLevelConfig = field(default_factory=CateLevelConfig)

    level4: CateLevelConfig = field(default_factory=CateLevelConfig)

    # ======================================================
    # 普通节点清单（按配置顺序记录已配置的普通节点）
    # ======================================================

    # 当前层已配置（node_name 非空）的普通节点名称列表（含纯 _COMBINE 节点）
    all_node_list: list = field(default_factory=list)

    # 当前层已激活的：定位器，的节点名称列表
    # 只有：css 或 xpath 至少有一项取值不为空时，并且：combine 值为空 或无 combine属性
    enable_locator_node_list: list = field(default_factory=list)

    # 只有：存在combine属性且combine不为空时，并且：css 或 xpath 均为空
    enable_combine_node_list: list = field(default_factory=list)

    # ======================================================
    # 默认值配置（CATE_LEVEL_DEFAULT_VALUE_*）
    # ======================================================

    # 默认值节点列表（节点名为带后缀的完整配置键名，如 CATE_LEVEL_1_LINK_CSS）
    default_value_node_list: list[str] = field(default_factory=list)

    # 默认值取值列表（与 default_value_node_list 一一对应）
    default_value_value_list: list[str] = field(default_factory=list)

    # ======================================================
    # 过滤器配置（CATE_LEVEL_FILTER_*）
    # ======================================================

    # 允许条件：节点名（裸逻辑名，如 CATE_LEVEL_1_NAME；也兼容带后缀的完整键名）
    filter_allow_value_node: str = ""
    # 允许条件：取值范围（-1 / 单一数值 / 数字1-数字2，支持小数）
    filter_allow_value_range: str = ""
    # 拒绝条件：节点名（裸逻辑名，如 CATE_LEVEL_1_NAME；也兼容带后缀的完整键名）
    filter_reject_value_node: str = ""
    # 拒绝条件：取值范围
    filter_reject_value_range: str = ""
    # 且非空节点列表（全部非空才通过）
    filter_and_not_empty_node_list: list[str] = field(default_factory=list)
    # 或非空节点列表（至少一个非空即通过）
    filter_or_not_empty_node_list: list[str] = field(default_factory=list)
