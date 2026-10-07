"""
详情页(DETAIL) - 文章配置对象

本模块定义配置文件中 DETAIL_ARTICLE_ 前缀对应的数据结构。

职责：
    - 保存详情页文章专用采集配置
    - 对应 ScriptConfig 中 DETAIL_ARTICLE_* 配置
    - 不参与数据库存储

说明：
    本模块只定义文章专用字段的组织方式。
    具体节点配置统一使用 NormalNodeConfig。

引用：
    - NormalNodeConfig：通用普通节点配置
    - detail_common.DetailCommonConfig：商品、文章共有字段
    - detail_common.DetailRawCommonConfig：辅助字段
"""

from dataclasses import dataclass, field

from config.model.node.normal_node_config import NormalNodeConfig

from .detail_common import DetailCommonConfig, DetailRawCommonConfig

# ==========================================================
# DETAIL 文章专用字段配置
# ==========================================================


@dataclass(slots=True)
class DetailArticleConfig:
    """
    DETAIL_ARTICLE 配置对象

    对应配置文件中的 DETAIL_ARTICLE_* 字段。

    文章专用字段：
        - 其他作者名
        - 其他作者 ID
        - 其他作者链接

    每个字段实际使用 NormalNodeConfig。
    """

    # 其他作者名列表
    other_author_names: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 其他作者 ID 列表
    other_author_ids: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 其他作者链接列表
    other_author_links: NormalNodeConfig = field(default_factory=NormalNodeConfig)


# ==========================================================
# DETAIL_ARTICLE 配置对象
# ==========================================================


@dataclass(slots=True)
class DetailArticleItem:
    """
    DETAIL_ARTICLE 配置对象

    对应配置文件：

        DETAIL_COMMON_*（来自 detail_common）
            SUMMARY_*
            DESCRIPTION_*
            PUBLISH_TIME_*
            EDITED_TIME_*
            MAIN_OWNER_NAME_*
            MAIN_OWNER_ID_*
            MAIN_OWNER_LINK_*
            SUB_OWNER_NAME_*
            SUB_OWNER_ID_*
            SUB_OWNER_LINK_*

        DETAIL_ARTICLE_*
            OTHER_AUTHOR_NAMES_*
            OTHER_AUTHOR_IDS_*
            OTHER_AUTHOR_LINKS_*

        DETAIL_RAW_COMMON_*（来自 detail_common）
            TAGS_*
            ID_*
    """

    # 共用字段（商品、文章都有）
    common: DetailCommonConfig = field(default_factory=DetailCommonConfig)

    # 文章专用字段
    article: DetailArticleConfig = field(default_factory=DetailArticleConfig)

    # 辅助字段（原始数据）
    raw: DetailRawCommonConfig = field(default_factory=DetailRawCommonConfig)

    # 当前层已配置（node_name 非空）的普通节点名称列表（含纯 _COMBINE 节点）
    all_node_list: list = field(default_factory=list)

    # 当前层已激活的：定位器，的节点名称列表
    # 只有：css 或 xpath 至少有一项取值不为空时，并且：combine 值为空 或无 combine属性
    enable_locator_node_list: list = field(default_factory=list)

    # 只有：存在combine属性且combine不为空时，并且：css 或 xpath 均为空
    enable_combine_node_list: list = field(default_factory=list)

    # ========== 默认值配置（DETAIL_DEFAULT_VALUE_*） ==========

    # 默认值节点列表（节点名为带后缀的完整配置键名，如 DETAIL_COMMON_SUMMARY_CSS）
    default_value_node_list: list[str] = field(default_factory=list)

    # 默认值取值列表（与 default_value_node_list 一一对应）
    default_value_value_list: list[str] = field(default_factory=list)

    # ========== 过滤器配置（DETAIL_FILTER_*） ==========

    # 允许条件：节点名（裸逻辑名，如 DETAIL_COMMON_SUMMARY；也兼容带后缀的完整键名）
    filter_allow_value_node: str = ""
    # 允许条件：取值范围（-1 / 单一数值 / 数字1-数字2，支持小数）
    filter_allow_value_range: str = ""
    # 拒绝条件：节点名（裸逻辑名，如 DETAIL_COMMON_SUMMARY；也兼容带后缀的完整键名）
    filter_reject_value_node: str = ""
    # 拒绝条件：取值范围
    filter_reject_value_range: str = ""
    # 且非空节点列表（全部非空才通过）
    filter_and_not_empty_node_list: list[str] = field(default_factory=list)
    # 或非空节点列表（至少一个非空即通过）
    filter_or_not_empty_node_list: list[str] = field(default_factory=list)

    # ========== 层级采集上限（DETAIL_MAX_COUNT） ==========
    # -1 不限制；>0 限制最大采集数
    # 0、除 -1 外的负数、非整数均非法（校验在 detail_loader.parse_max_count）
    max_count: int = -1
