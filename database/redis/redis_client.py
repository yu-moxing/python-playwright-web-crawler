from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from config.database.redis_config import RedisConfig


class RedisClient:
    """
    Redis连接客户端

    负责：
        1. 创建Redis连接池
        2. 创建Redis客户端

    Redis通过key前缀区分不同项目。
    """

    def __init__(self, config: "RedisConfig"):
        """
        初始化Redis客户端

        参数:
            config:
                RedisConfig对象
        """

        # ====================================================
        # 创建Redis连接池
        #
        # redis-py通过ConnectionPool管理连接。
        # ====================================================

        self.pool = redis.ConnectionPool(
            # Redis地址
            host=config.host,
            # Redis端口
            port=config.port,
            # Redis密码
            password=config.password,
            # Redis数据库编号
            db=config.db,
            # Redis协议版本--Redis 5.0 不支持 HELLO/RESP3，因此使用 RESP2
            protocol=config.protocol,
            # 最大连接数
            max_connections=config.max_connections,
            # socket读取超时时间
            socket_timeout=config.socket_timeout,
            # socket连接超时时间
            socket_connect_timeout=config.socket_connect_timeout,
        )

        # ====================================================
        # 创建Redis客户端
        # ====================================================

        self.client = redis.Redis(connection_pool=self.pool)

    def get_client(self):
        """
        获取Redis客户端

        返回:
            redis.Redis对象
        """

        return self.client
