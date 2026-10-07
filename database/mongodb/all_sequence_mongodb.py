from pymongo import ReturnDocument


class AllSequenceMongoDB:
    """
    MongoDB批量自增ID管理

    支持：
        指定数据库
        指定sequence集合
        指定主键字段
    """

    def __init__(self, mongodb_util, collection_name, field_key, field_value):
        """
        初始化

        参数:
            mongodb_util:
                MongoDBUtil 对象（内部已绑定当前项目的 database）

            collection_name:
                自增序列 Collection 名称，例如:
                    CONTENT_SEQUENCE

            field_key:
                Sequence 文档的字段名称，例如:
                    _id

            field_value:
                Sequence 文档的字段值，例如:
                    CONTENT_IID
        """

        # self.collection = database[collection_name]
        # 直接复用 mongodb_util 内部已经绑定好数据库的 database 对象
        self.collection = mongodb_util.database[collection_name]

        self.field_key = field_key

        self.field_value = field_value

        # 确保指定的 Sequence 已经存在
        self.collection.update_one(
            {self.field_key: self.field_value},
            {"$setOnInsert": {"value": 0}},
            upsert=True,
        )

    def allocate_id_range(self, count):
        """
        原子分配一段连续 ID。

        根据初始化时指定的 field_key 和 field_value，
        从 MongoDB Sequence 中递增指定数量的 ID，
        返回本次分配的连续 ID 范围。

        Args:
            count:
                本次需要分配的 ID 数量。

        Returns:
            tuple[int, int]:
                本次分配的起始 ID 和结束 ID。
        """

        result = self.collection.find_one_and_update(
            {self.field_key: self.field_value},
            {"$inc": {"value": count}},
            return_document=ReturnDocument.AFTER,
        )

        if result is None:
            raise Exception(f"Sequence 不存在: {self.field_key}={self.field_value}")

        end = result["value"]

        start = end - count + 1

        return start, end
