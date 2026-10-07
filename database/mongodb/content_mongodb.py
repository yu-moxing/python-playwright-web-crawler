"""
CONTENT MongoDB 管理器

负责：
    1. 根据 CONTENT 哈希规则，动态路由到对应的 MongoDB Collection。
    2. 批量查询和写入 CONTENT MongoDB 数据。

Collection 命名规则：
    {CONTENT_COLLECTION_PREFIX}-{HASH_SUFFIX}

    例如：
        CONTENT-00
        CONTENT-FF

设计原则：
    1. 与 ContentRedis 对应，MongoDB 是 CONTENT 的持久化数据源。
    2. 不直接持有 MongoClient，而是复用底层的 MongoDBUtil。
    3. 通过 content_hash_length 计算后缀，将 CONTENT 数据分散存储到多个 Collection。
"""

from __future__ import annotations

from collections import defaultdict

from pymongo.errors import BulkWriteError


class ContentMongoDB:
    """CONTENT MongoDB 业务管理器。"""

    def __init__(
        self,
        *,
        mongodb_util,
        content_collection_prefix: str,
        content_hash_length: int,
    ):
        """
        初始化 CONTENT MongoDB 管理器。

        Args:
            mongodb_util: MongoDBUtil 对象，负责底层 MongoDB CRUD 操作。
            content_collection_prefix: CONTENT 集合前缀（如 "CONTENT"）。
            content_hash_length: MD5 尾部用于集合路由的哈希长度。
        """
        self.mongodb_util = mongodb_util
        self.content_collection_prefix = content_collection_prefix
        self.content_hash_length = content_hash_length

    # =========================================================
    # 构造 CONTENT Collection Name
    # =========================================================

    def _build_collection_name(self, md5_hash_id: str) -> str:
        """
        根据 CONTENT _id 构造 MongoDB Collection 名称。

        Args:
            md5_hash_id: 内容的 MD5 哈希值。

        Returns:
            str: 完整的集合名称，例如 "CONTENT-A1"。
        """
        # 取 MD5 的最后 N 位作为后缀
        hash_suffix = md5_hash_id[-self.content_hash_length :].upper()

        return f"{self.content_collection_prefix}-{hash_suffix}"

    # =========================================================
    # 批量查询
    # 只能知道这批 ID 里有哪些已经存在了,查出存在的就行
    # 不会按：md5_hash_ids 列表的顺序，返回。
    # 返回的是：打乱后，能查询到的数据记录
    # =========================================================

    def get_batch(self, md5_hash_ids: list[str]) -> list[dict]:
        """
        批量查询 CONTENT MongoDB。

        由于 MongoDB 不支持跨集合的批量查询，
        这里按集合分组后分别查询，最后合并返回。

        Args:
            md5_hash_ids: 内容的 MD5 哈希值列表。

        Returns:
            list[dict]: 查询到的文档列表。
        """
        if not md5_hash_ids:
            return []

        # 1. 按集合名称对 ID 进行分组（使用 defaultdict 简化代码）
        collection_map = defaultdict(list)
        for md5_hash_id in md5_hash_ids:
            col_name = self._build_collection_name(md5_hash_id)
            collection_map[col_name].append(md5_hash_id)

        # 2. 遍历分组，分别查询并合并结果
        results = []
        for col_name, ids in collection_map.items():
            query = {"_id": {"$in": ids}}
            cursor = self.mongodb_util.find(col_name, query)
            # 优化：直接 extend cursor 迭代器，避免 list(cursor) 一次性加载到内存
            results.extend(cursor)

        return results

    # =========================================================
    # 批量写入
    # =========================================================

    def set_batch(self, docs: list[dict]) -> list[dict]:
        """
        批量写入 CONTENT MongoDB。

        自动根据文档中的 _id (md5_hash_id) 路由到对应的 Collection。

        ordered=False 时，即使部分文档写入失败，
        MongoDB 仍会继续处理后续文档。

        Args:
            docs:
                待写入的文档列表，每个文档必须包含 '_id' 字段。

        Returns:
            list[dict]:
                实际成功写入 MongoDB 的文档列表。
        """
        if not docs:
            return []

        # 1. 按集合名称对文档进行分组
        collection_map = defaultdict(list)

        for doc in docs:
            md5_hash_id = doc.get("_id")

            if not md5_hash_id:
                continue

            col_name = self._build_collection_name(md5_hash_id)
            collection_map[col_name].append(doc)

        # 2. 遍历分组，分别执行批量插入
        successful_docs = []

        for col_name, col_docs in collection_map.items():
            try:
                self.mongodb_util.insert_many(
                    col_name,
                    col_docs,
                    ordered=False,
                )

                # 整个批次全部写入成功
                successful_docs.extend(col_docs)

            except BulkWriteError as error:
                # 获取本次批量写入失败的文档下标
                failed_indexes = {write_error["index"] for write_error in error.details.get("writeErrors", [])}

                # 排除失败记录，保留实际成功写入的记录
                for record_index, doc in enumerate(col_docs):
                    if record_index not in failed_indexes:
                        successful_docs.append(doc)

        return successful_docs
