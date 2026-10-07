"""
分类列表（CL）页面 Common 数据项

职责：

    - 保存分类列表（CL）页面采集得到的商品、文章共有字段
    - 对应 CATE_LIST_COMMON_* 配置
    - 作为 CL Parser / Processor 阶段的数据结构
    - 不负责数据库持久化

说明：

    CateListCommonDataItem 表示从分类列表（CL）页面采集得到的
    商品、文章以及未来其他内容类型共有的数据。

    本数据项只对应：

        CATE_LIST_COMMON_*

    Detail（详情）页面对应的：

        DETAIL_COMMON_*

    属于不同的采集来源，因此分别定义 DataItem。

    虽然 CATE_LIST_COMMON_* 与 DETAIL_COMMON_* 最终可能对应同一个内容实体，
    并最终汇聚到 ContentDataRecord.common，
    但采集阶段的数据结构保持来源独立。
"""

from dataclasses import dataclass


@dataclass
class CateListCommonDataItem:
    """
    分类列表（CL）页面 Common 数据项。

    对应配置：

        CATE_LIST_COMMON_LINK_*

        CATE_LIST_COMMON_ID_*（独立去重 ID，由 parser 提取到 CateListParsedItem.id）

        CATE_LIST_COMMON_MAIN_TITLE_*
        CATE_LIST_COMMON_SUB_TITLE_*

        CATE_LIST_COMMON_MAIN_IMAGE_*
        CATE_LIST_COMMON_SUB_IMAGES_*

        CATE_LIST_COMMON_VIEW_COUNT_*
        CATE_LIST_COMMON_FAVORITE_COUNT_*
        CATE_LIST_COMMON_COMMENT_COUNT_*

        CATE_LIST_COMMON_MAIN_OWNER_*
        CATE_LIST_COMMON_SUB_OWNER_*
    """

    # =========================================================
    # 链接
    # =========================================================

    link: str = ""

    # =========================================================
    # 标题
    # =========================================================

    main_title: str = ""
    sub_title: str = ""

    # =========================================================
    # 图片
    # =========================================================

    # 主图 URL
    main_image: str = ""

    # 副图列表
    #
    # 当前 CL 配置定义为：
    #     最多 5 张，JSON 字符串
    #
    # 因此这里保持 str 类型。
    sub_images: str = ""

    # =========================================================
    # 统计数据
    # =========================================================

    # 浏览数
    view_count: int = 0

    # 收藏数
    favorite_count: int = 0

    # 评价数 / 评论数
    comment_count: int = 0

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
