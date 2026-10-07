"""
详情页(DETAIL) - 共用字段配置对象

本模块定义配置文件中 DETAIL_COMMON_、DETAIL_RAW_COMMON_ 前缀对应的数据结构。

职责：
    - 保存详情页共用采集配置
    - 对应 ScriptConfig 中 DETAIL_COMMON_*、DETAIL_RAW_COMMON_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    DetailCommonConfig：商品、文章共有字段（内容、时间、所有者）
    DetailRawCommonConfig：辅助字段（标签、原始ID）

    具体的节点配置统一使用 NormalNodeConfig。

被引用：
    - detail_article_item.py（文章配置）
    - detail_product_item.py（商品配置）
"""

from dataclasses import dataclass, field

from config.model.node.normal_node_config import NormalNodeConfig

# ==========================================================
# DETAIL 共用字段配置（商品、文章都有）
# ==========================================================


@dataclass(slots=True)
class DetailCommonConfig:
    """
    DETAIL_COMMON 配置对象

    对应配置文件中的 DETAIL_COMMON_* 字段。

    包含：
        - 内容
        - 时间
        - 主所有者
        - 副所有者

    每个字段实际使用 NormalNodeConfig。
    """

    # ========== 内容相关 ==========

    # 商品/文章总结
    summary: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 商品/文章描述
    description: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # ========== 时间相关 ==========

    # 发布时间（秒级时间戳）
    publish_time: NormalNodeConfig = field(default_factory=NormalNodeConfig)

    # 编辑时间（秒级时间戳）
    edited_time: NormalNodeConfig = field(default_factory=NormalNodeConfig)

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
# DETAIL 辅助字段配置（原始数据）
# ==========================================================


@dataclass(slots=True)
class DetailRawCommonConfig:
    """
    DETAIL_RAW_COMMON 配置对象

    对应配置文件中的 DETAIL_RAW_COMMON_* 字段。

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
