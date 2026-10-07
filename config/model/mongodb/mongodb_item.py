"""
MongoDB(MONGODB) 配置对象

本模块仅定义配置文件中 MONGODB_ 前缀对应的数据结构。

职责：
    - 保存 MongoDB 相关配置（库名、集合键、CONTENT 集合分片）
    - 对应 ScriptConfig 中 MONGODB_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class MongodbItem:
    """
    MONGODB 配置对象

    对应配置文件：

        MONGODB_DATABASE_NAME
        MONGODB_CATE_LEVEL_LIST_COLLECTION_KEY
        MONGODB_CONTENT_COLLECTION_HASH_LENGTH
        MONGODB_CONTENT_COLLECTION_PREFIX

    content_collection_hash_length 只能取 2 或 3（其他值非法），
    由 mongodb_loader.validate_mongodb_config 校验。
    """

    # ========== 库名 ==========
    database_name: str = ""

    # ========== 数据库版本号 ==========
    database_version: str = ""

    # ========== 集合键 ==========
    cate_level_list_collection_key: str = ""

    # ========== CONTENT 集合分片 ==========
    # 分片位数，只能取 2 或 3（CONTENT 集合按 md5(raw_id) 末 N 位哈希分片）
    content_collection_hash_length: int = 2
    # 集合名前缀，如 CONTENT → CONTENT-00 ~ CONTENT-ff
    content_collection_prefix: str = ""
