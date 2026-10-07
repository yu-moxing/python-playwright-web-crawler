from pymongo import MongoClient

from config.database.mongodb_config import MongoDBConfig


class MongoDBClient:
    """
    MongoDB连接客户端

    负责：
        1. 创建MongoDB连接
        2. 管理MongoDB连接池

    MongoDB通过database名称区分不同项目，
    不像Redis通过head_key前缀区分项目。
    """

    def __init__(self, config: MongoDBConfig):
        """
        初始化MongoDB客户端

        参数:
            config:
                MongoDBConfig对象
        """

        # 创建MongoDB客户端
        #
        # MongoClient内部自带连接池机制，
        # 不需要像Redis一样手动创建ConnectionPool。

        self.client = MongoClient(
            # MongoDB地址
            host=config.host,
            # MongoDB端口
            port=config.port,
            # MongoDB认证用户
            username=config.username,
            # MongoDB认证密码
            password=config.password,
            # 用户认证数据库
            # 通常为admin
            authSource=config.auth_source,
            # 最大连接池数量
            maxPoolSize=config.max_pool_size,
            # 服务选择超时时间（秒转换毫秒）
            serverSelectionTimeoutMS=config.server_selection_timeout * 1000,
            # TCP连接超时时间（秒转换毫秒）
            connectTimeoutMS=config.connect_timeout * 1000,
        )

    def get_client(self):
        """
        获取MongoDB客户端

        返回:
            MongoClient对象
        """

        return self.client
