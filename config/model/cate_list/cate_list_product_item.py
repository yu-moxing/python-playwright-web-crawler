"""
分类列表(CATE_LIST) - 商品配置对象

本模块定义配置文件中 CATE_LIST_PRODUCT_ 前缀对应的数据结构。

职责：
    - 保存分类列表页商品专用采集配置
    - 对应 ScriptConfig 中 CATE_LIST_PRODUCT_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    CateListProductConfig：只有商品有的字段（价格、销量）
    CateListProductItem：组合共用字段 + 商品专用字段

    具体的普通网页节点配置统一使用 NormalNodeConfig。

引用：
    - normal_node_config.NormalNodeConfig
    - cate_list_common.CateListCommonConfig（商品、文章共有字段）
    - cate_list_common.CateListRawCommonConfig（辅助字段）
"""

from dataclasses import dataclass, field

from config.model.node.normal_node_config import NormalNodeConfig

from .cate_list_common import CateListCommonConfig, CateListRawCommonConfig

# ==========================================================
# CATE_LIST 商品专用字段配置
# ==========================================================


@dataclass(slots=True)
class CateListProductConfig:
    """
    CATE_LIST_PRODUCT 配置对象

    对应配置文件中的 CATE_LIST_PRODUCT_* 字段。

    包含：
        - 价格
        - 销量

    每个字段实际使用 NormalNodeConfig。
    """

    # ========== 价格相关 ==========

    # 价格数值
    price: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 价格货币单位（USD, CNY, TWD 等）
    price_currency: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 价格原始文本（如 "$99.99"）
    price_text: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 销量相关 ==========

    # 销量数值
    sales_count: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 销量原始文本（如 "5万+"、"2千"）
    sales_text: NormalNodeConfig = field(default_factory=NormalNodeConfig)


# ==========================================================
# CATE_LIST_PRODUCT 配置对象
# ==========================================================


@dataclass(slots=True)
class CateListProductItem:
    """
    CATE_LIST_PRODUCT 配置对象

    对应配置文件：

        CATE_LIST_COMMON_*（来自 cate_list_common）
            MAIN_TITLE_*
            SUB_TITLE_*
            MAIN_IMAGE_*
            SUB_IMAGES_*
            VIEW_COUNT_*
            FAVORITE_COUNT_*
            COMMENT_COUNT_*
            MAIN_OWNER_NAME_*
            MAIN_OWNER_ID_*
            MAIN_OWNER_LINK_*
            SUB_OWNER_NAME_*
            SUB_OWNER_ID_*
            SUB_OWNER_LINK_*

        CATE_LIST_PRODUCT_*
            PRICE_*
            PRICE_CURRENCY_*
            PRICE_TEXT_*
            SALES_COUNT_*
            SALES_TEXT_*

        CATE_LIST_RAW_COMMON_*（来自 cate_list_common）
            TAGS_*
            ID_*
    """

    # 共用字段（商品、文章都有）
    common: CateListCommonConfig = field(default_factory=CateListCommonConfig)

    # 商品专用字段
    product: CateListProductConfig = field(default_factory=CateListProductConfig)

    # 辅助字段（原始数据）
    raw: CateListRawCommonConfig = field(default_factory=CateListRawCommonConfig)

    # 当前层已配置（node_name 非空）的普通节点名称列表（含纯 _COMBINE 节点）
    all_node_list: list[str] = field(default_factory=list)

    # 当前层已激活的：定位器，的节点名称列表
    # 只有：css 或 xpath 至少有一项取值不为空时，并且：combine 值为空 或无 combine属性
    enable_locator_node_list: list[str] = field(default_factory=list)

    # 只有：存在combine属性且combine不为空时，并且：css 或 xpath 均为空
    enable_combine_node_list: list[str] = field(default_factory=list)

    # ========== 默认值配置（CATE_LIST_DEFAULT_VALUE_*） ==========

    # 默认值节点列表（节点名为带后缀的完整配置键名，如 CATE_LIST_COMMON_MAIN_TITLE_CSS）
    default_value_node_list: list[str] = field(default_factory=list)

    # 默认值取值列表（与 default_value_node_list 一一对应）
    default_value_value_list: list[str] = field(default_factory=list)

    # ========== 过滤器配置（CATE_LIST_FILTER_*） ==========

    # 允许条件：节点名（裸逻辑名，如 CATE_LIST_PRODUCT_PRICE；也兼容带后缀的完整键名）
    filter_allow_value_node: str = ""
    # 允许条件：取值范围（-1 / 单一数值 / 数字1-数字2，支持小数）
    filter_allow_value_range: str = ""
    # 拒绝条件：节点名（裸逻辑名，如 CATE_LIST_PRODUCT_PRICE；也兼容带后缀的完整键名）
    filter_reject_value_node: str = ""
    # 拒绝条件：取值范围
    filter_reject_value_range: str = ""
    # 且非空节点列表（全部非空才通过）
    filter_and_not_empty_node_list: list[str] = field(default_factory=list)
    # 或非空节点列表（至少一个非空即通过）
    filter_or_not_empty_node_list: list[str] = field(default_factory=list)

    # ========== 层级采集上限（CATE_LIST_MAX_COUNT） ==========
    # -1 不限制；>0 限制最大采集数
    # 0、除 -1 外的负数、非整数均非法（校验在 cate_list_loader.parse_max_count）
    max_count: int = -1
