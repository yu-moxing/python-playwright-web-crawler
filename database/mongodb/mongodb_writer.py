"""
MongoDB 写入器模块

职责：
    - 包装 MongoDBUtil，提供单条 / 批量写入与读取接口
    - 供 StructuredBatchWriter 以 output_type="mongodb" 调用

设计原则：
    - 不负责连接管理（连接由 MongoDBClient 负责）
    - 复用 database/mongodb/mongodb_util.py 的 CRUD 能力

调用关系：
    StructuredBatchWriter(output_type="mongodb")
            |
            v
        MongoWriter
            |
            v
        MongoDBUtil -> MongoDB
"""

import logging

from database.mongodb.mongodb_util import MongoDBUtil

logger = logging.getLogger(__name__)


class MongoWriter:
    """
    MongoDB 写入器

    Example:
        >>> writer = MongoWriter(
        ...     mongodb_client=client,
        ...     database_name="project_a",
        ...     collection_name="CATE-00",
        ... )
        >>> writer.write({"level_0": "女装##1", ...})
        >>> writer.write_batch([{"level_0": "男装##2", ...}, ...])
    """

    def __init__(self, *, mongodb_client, database_name, collection_name):
        """
        初始化 MongoDB 写入器

        Args:
            mongodb_client: MongoClient 对象（由 MongoDBClient.get_client() 提供）
            database_name: 数据库名（按项目隔离）
            collection_name: 集合名
        """
        self.util = MongoDBUtil(mongodb_client, database_name)
        self.collection_name = collection_name

    def write(self, doc):
        """写入单条文档"""
        self.util.insert_one(self.collection_name, doc)

    def write_batch(self, docs):
        """
        批量写入文档

        Args:
            docs: 文档列表
        """
        if not docs:
            return
        self.util.insert_many(self.collection_name, docs)

    def read(self):
        """
        读取全部文档

        Returns:
            list[dict]
        """
        cursor = self.util.find(self.collection_name)
        return list(cursor)
