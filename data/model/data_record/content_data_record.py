"""
CONTENT 数据记录模型

职责：

    - 定义 CONTENT 最终数据库记录的数据结构
    - 保存记录身份信息
    - 保存数据结构版本
    - 保存 5 个客户的导出次数
    - 保存商品、文章及未来其他内容类型共有的 Common 数据
    - 保存动态业务扩展 Content JSON 数据

说明：

    ContentDataRecord 是最终面向数据库的数据记录模型。

    本模型不负责：

    - 页面数据采集
    - CSS / XPATH 配置
    - 数据清洗
    - MongoDB 集合路由
    - MongoDB 分片
    - 数据库读写

    Common 字段来自：

        CATE_LIST_COMMON_*
        DETAIL_COMMON_*

    CL（分类列表）页面和 D（详情）页面虽然是不同的采集来源，
    但针对的是同一个商品、文章或其他内容实体，因此最终统一
    汇聚到 common。

    content 为动态 JSON 结构，用于保存具体业务类型的扩展数据。
    当前可以是 Product、Article，未来也可以增加其他内容类型，
    ContentDataRecord 本身无需因此修改。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContentCommonData:
    """
    CONTENT 公共数据。

    字段来源：

        CATE_LIST_COMMON_*
        DETAIL_COMMON_*

    这些字段属于商品、文章以及未来其他内容类型共同拥有的
    内容属性。
    """

    # =========================================================
    # 链接
    # =========================================================

    link: str = ""
    # 独立去重 ID（来自 CATE_LIST_COMMON_ID_* 提取）
    id: str = ""

    # =========================================================
    # 标题
    # =========================================================

    main_title: str = ""
    sub_title: str = ""

    # =========================================================
    # 图片
    # =========================================================

    main_image: str = ""
    sub_images: List[str] = field(default_factory=list)

    # =========================================================
    # 统计数据
    # =========================================================

    view_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0

    # =========================================================
    # 内容
    # =========================================================

    summary: str = ""
    description: str = ""

    # =========================================================
    # 时间
    # =========================================================

    publish_time: int = 0
    edited_time: int = 0

    # =========================================================
    # 主所有者
    # =========================================================

    main_owner_name: str = ""
    main_owner_id: str = ""
    main_owner_link: str = ""

    # =========================================================
    # 副所有者
    # =========================================================

    sub_owner_name: str = ""
    sub_owner_id: str = ""
    sub_owner_link: str = ""


@dataclass
class ContentDataRecord:
    """
    CONTENT 最终数据库数据记录。

    一条 ContentDataRecord 对应数据库中的一条 CONTENT 数据。

    结构：

        ├── _id
        ├── iid
        ├── version
        │
        ├── raw_id
        ├── raw_url
        ├── crawl_url
        ├── update_url
        ├── crawl_time
        ├── update_time
        │
        ├── export_customer_0_times
        ├── export_customer_1_times
        ├── export_customer_2_times
        ├── export_customer_3_times
        ├── export_customer_4_times
        │
        ├── common
        └── content

    其中：

        _id
            CONTENT 数据库记录的唯一主键。

        iid
            系统自定义的自增业务索引。

        version
            ContentDataRecord 数据结构版本。

        raw_id
            第三方数据的唯一原始 ID。

        raw_url
            第三方数据的唯一原始 URL。

        crawl_url
            本次采集使用的 URL。

        update_url
            后续更新数据使用的 URL。

        crawl_time
            数据最近一次采集时间。

        update_time
            数据最近一次更新时间。

        export_customer_*_times
            5 个不同客户对应的导出次数。

        common
            所有内容类型共有的固定字段。

        content
            动态 JSON 业务扩展字段。
            不区分 Product、Article 或未来新增的其他内容类型。
    """

    # =========================================================
    # Record Identity
    # =========================================================
    # _id 是根据：md5(内容id)
    _id: str = ""
    iid: int = 0

    # =========================================================
    # 用户及登录相关
    # =========================================================
    # 用户索引、用户名
    user_index: int = -1
    user_name: str = ""

    # 用户是否登录
    is_logged_in: int = 1

    # =========================================================
    # Data Structure Version
    # =========================================================

    system_version: str = "0.1"
    mongodb_database_version: str = "0.0.1"

    # =========================================================
    # Raw / Crawl / Update Metadata
    # =========================================================

    raw_id: str = ""
    raw_url: str = ""

    crawl_url: str = ""
    crawl_time: int = 0

    update_url: str = ""
    update_time: int = 0

    # =========================================================
    # Export Statistics
    # =========================================================
    # ects是：export custom times 的缩写
    ects_0: int = 0
    ects_1: int = 0
    ects_2: int = 0
    ects_3: int = 0
    ects_4: int = 0

    # =========================================================
    # Common Data
    # =========================================================

    common: ContentCommonData = field(default_factory=ContentCommonData)

    # =========================================================
    # Dynamic Business Content
    # =========================================================

    content: Dict[str, Any] = field(default_factory=dict)
