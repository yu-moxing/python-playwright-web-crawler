class MongoDBUtil:
    """
    MongoDB操作工具类

    负责：
        1. 获取数据库集合
        2. 封装常用CRUD操作

    MongoDB项目隔离方式：
        database_name -> 区分项目

    例如：
        project_a
            |
            └── CONTENT-00

        project_b
            |
            └── CONTENT-00
    """

    def __init__(self, mongodb_client, database_name):
        """
        初始化MongoDB工具类

        参数:
            mongodb_client:
                MongoClient对象

            database_name:
                当前项目数据库名称
        """

        # MongoDB客户端
        self.client = mongodb_client

        # 当前项目数据库
        self.database = self.client[database_name]

    # =====================================================
    # 获取集合
    # =====================================================

    def get_collection(self, collection_name):
        """
        获取MongoDB集合

        参数:
            collection_name:
                集合名称

        返回:
            Collection对象
        """

        return self.database[collection_name]

    # =====================================================
    # 插入一条数据
    # =====================================================

    def insert_one(self, collection_name, data):
        """
        插入单条文档数据
        """

        collection = self.get_collection(collection_name)

        return collection.insert_one(data)

    # =====================================================
    # 插入多条数据
    # =====================================================

    def insert_many(self, collection_name, data_list, *, ordered=True):
        """
        批量插入文档数据。

        参数:
            collection_name:
                集合名称

            data_list:
                文档列表

            ordered:
                是否按照文档顺序执行插入。
                False 表示某条文档插入失败后，继续处理后续文档。

        返回:
            InsertManyResult
        """

        collection = self.get_collection(collection_name)

        return collection.insert_many(
            data_list,
            ordered=ordered,
        )

    # =====================================================
    # 查询一条数据
    # =====================================================

    def find_one(self, collection_name, query):
        """
        查询单条文档数据
        """

        collection = self.get_collection(collection_name)

        return collection.find_one(query)

    # =====================================================
    # 查询多条数据
    # =====================================================

    def find(self, collection_name, query=None):
        """
        查询多条文档数据

        返回:
            MongoDB Cursor
        """

        collection = self.get_collection(collection_name)

        return collection.find(query or {})

    # =====================================================
    # 更新数据
    # =====================================================

    def update_one(self, collection_name, query, update_data):
        """
        更新单条文档数据
        """

        collection = self.get_collection(collection_name)

        return collection.update_one(query, {"$set": update_data})

    # =====================================================
    # 删除数据
    # =====================================================

    def delete_one(self, collection_name, query):
        """
        删除单条文档数据
        """

        collection = self.get_collection(collection_name)

        return collection.delete_one(query)
