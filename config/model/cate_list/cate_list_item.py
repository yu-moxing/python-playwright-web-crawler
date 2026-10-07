"""
分类列表(CATE_LIST) - URL/排序/翻页 配置对象

本模块定义配置文件中 CATE_LIST_URL_、CATE_LIST_SORT_、CATE_LIST_ORDER_、
CATE_LIST_PAGE_ 前缀对应的数据结构。

职责：
    - 保存分类列表页的 URL 参数顺序、排序字段、翻页配置
    - 对应 ScriptConfig 中 CATE_LIST_URL_*、CATE_LIST_SORT_*、
      CATE_LIST_ORDER_PARAM_NAME、CATE_LIST_PAGE_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    这些配置原属 CATE_LEVEL 模块，现迁移到 CATE_LIST 模块。
    CateListPageConfig 的 CSS/XPath/Regex 属于分页业务配置，
    不是一个完整的 NormalNodeConfig，因此保持独立结构。
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class CateListPageConfig:
    """
    分类列表页面翻页配置。

    对应配置文件中的 CATE_LIST_PAGE_* 字段。

    这里的 CSS/XPath/Attr/Regex 属于分页业务配置，
    不是一个完整的 NormalNodeConfig，
    因此保持独立结构。
    """

    # 选择器配置
    css: str = ""
    xpath: str = ""
    attr: str = ""  # 提取属性（CATE_LIST_PAGE_ATTR，迁移时新增）
    regex: str = ""
    count_regex: str = ""

    # 分页参数配置
    param_name: str = ""  # URL 参数名（如 page）
    start_no: int = 0  # 起始页码
    hide_value: int = -1  # 隐藏页码值（-1表示不隐藏）
    offset_size: int = -1  # 偏移大小（-1表示普通模式）


@dataclass(slots=True)
class CateListItem:
    """
    CATE_LIST URL/排序/翻页 配置对象

    对应配置文件：

        CATE_LIST_URL_PARAM_ORDER_MODE
        CATE_LIST_URL_PARAM_ORDER_LIST

        CATE_LIST_SORT_FIELDS
        CATE_LIST_SORT_HIDE_FIELD
        CATE_LIST_SORT_ORDER_SUPPORTED_FIELDS
        CATE_LIST_SORT_ORDER_VALUES
        CATE_LIST_SORT_DEFAULT_ORDER
        CATE_LIST_SORT_HIDE_ORDER
        CATE_LIST_SORT_BY_PARAM_NAME
        CATE_LIST_ORDER_PARAM_NAME

        CATE_LIST_PAGE_*
            CSS / XPATH / ATTR / REGEX / COUNT_REGEX
            PARAM_NAME / START_NO / HIDE_VALUE / OFFSET_SIZE
    """

    # ========== 页面翻页 ==========
    page: CateListPageConfig = field(default_factory=CateListPageConfig)

    # ========== URL 参数排序 ==========
    url_param_order_mode: str = ""  # asc / desc / 0

    url_param_order_list: List[str] = field(default_factory=list)

    # ========== 排序字段配置 ==========
    sort_fields: List[str] = field(default_factory=list)

    sort_hide_field: str = ""

    sort_order_supported_fields: List[str] = field(default_factory=list)

    sort_order_values: List[str] = field(default_factory=list)

    sort_default_order: str = ""  # 空表示无默认

    sort_hide_order: str = ""  # 空表示无隐藏

    order_param_name: str = ""

    sort_by_param_name: str = ""
