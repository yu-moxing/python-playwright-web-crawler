"""
Detail 页面 Common 数据项

职责：

    - 保存 Detail（详情）页面采集得到的商品、文章共有字段
    - 对应 DETAIL_COMMON_* 配置
    - 作为 Detail Parser / Processor 阶段的数据结构
    - 不负责数据库持久化

说明：

    DetailCommonDataItem 表示从 Detail（详情）页面采集得到的
    商品、文章等内容共有数据。

    本数据项只对应：

        DETAIL_COMMON_*

    与分类列表页面对应的：

        CATE_LIST_COMMON_*

    属于不同的采集来源，因此分别定义 DataItem。

    虽然 CATE_LIST_COMMON_* 与 DETAIL_COMMON_* 最终可能写入同一个
    ContentDataRecord.common，但两者在采集阶段职责不同。
"""

from dataclasses import dataclass


@dataclass
class DetailCommonDataItem:
    """
    Detail（详情）页面 Common 数据项。

    对应配置：

        DETAIL_COMMON_SUMMARY
        DETAIL_COMMON_DESCRIPTION
        DETAIL_COMMON_PUBLISH_TIME
        DETAIL_COMMON_EDITED_TIME

        DETAIL_COMMON_MAIN_OWNER_*
        DETAIL_COMMON_SUB_OWNER_*

    数据最终可以与 CateListCommonDataItem 合并，
    形成 ContentDataRecord.common。
    """

    # =========================================================
    # 内容
    # =========================================================

    summary: str = ""
    description: str = ""

    # =========================================================
    # 时间
    # =========================================================

    # 发布时间：秒级 Unix 时间戳
    publish_time: int = 0

    # 编辑时间：秒级 Unix 时间戳
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
