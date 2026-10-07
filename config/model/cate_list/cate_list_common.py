"""
分类列表(CATE_LIST) - 共用字段配置对象

本模块定义配置文件中 CATE_LIST_COMMON_、CATE_LIST_RAW_COMMON_ 前缀对应的数据结构。

职责：
    - 保存分类列表页共用采集配置
    - 对应 ScriptConfig 中 CATE_LIST_COMMON_*、CATE_LIST_RAW_COMMON_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    CateListCommonConfig：商品、文章共有字段（标题、图片、统计数据、所有者）
    CateListRawCommonConfig：辅助字段（标签、原始ID）

    具体的普通网页节点配置统一使用 NormalNodeConfig。

被引用：
    - cate_list_article_item.py（文章配置）
    - cate_list_product_item.py（商品配置）
"""

from dataclasses import dataclass, field

from config.model.node.normal_node_config import NormalNodeConfig

# ==========================================================
# CATE_LIST 共用字段配置（商品、文章都有）
# ==========================================================


@dataclass(slots=True)
class CateListCommonConfig:
    """
    CATE_LIST_COMMON 配置对象

    对应配置文件中的 CATE_LIST_COMMON_* 字段。

    包含：
        - 链接
        - 标题
        - 图片
        - 统计数据
        - 所有者

    链接的 CSS/XPATH/ATTR/REGEX 使用 NormalNodeConfig，
    ID（独立去重 ID）同样使用 NormalNodeConfig，从页面节点提取，
    替代旧版从链接派生的 LINK_ID_REGEX。
    """

    # ========== 链接相关 ==========

    # 分类列表链接
    link: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 独立去重 ID（从页面节点提取，替代旧版 LINK_ID_REGEX 的从链接派生）
    id: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 标题相关 ==========

    # 主标题
    main_title: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 副标题
    sub_title: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 图片相关 ==========

    # 主图 URL
    main_image: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 副图列表（最多5张，JSON字符串）
    sub_images: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 统计数据 ==========

    # 浏览数
    view_count: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 收藏数
    favorite_count: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 评价数/评论数
    comment_count: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 主所有者（商品时为店铺，文章时为作者） ==========

    # 主所有者--名
    main_owner_name: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 主所有者--ID
    main_owner_id: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 主所有者--链接
    main_owner_link: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 副所有者 ==========

    # 副所有者--名
    sub_owner_name: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 副所有者--ID
    sub_owner_id: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 副所有者--链接
    sub_owner_link: NormalNodeConfig = field(default_factory=NormalNodeConfig)


# ==========================================================
# CATE_LIST 辅助字段配置（原始数据）
# ==========================================================


@dataclass(slots=True)
class CateListRawCommonConfig:
    """
    CATE_LIST_RAW_COMMON 配置对象

    对应配置文件中的 CATE_LIST_RAW_COMMON_* 字段。

    包含：
        - 标签
        - 原始ID

    每个字段实际使用 NormalNodeConfig。
    """

    # ========== 标签/分类 ==========

    # 标签列表（JSON字符串）
    tags: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 原始ID ==========

    # 商品/文章的原始ID
    id: NormalNodeConfig = field(default_factory=NormalNodeConfig)
