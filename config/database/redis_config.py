"""
Redis配置

负责：
    从 app_config 获取 Redis 配置

不负责：
    Redis连接
    Redis操作
"""

from config.application.app_config import get_app_config


class RedisConfig:
    def __init__(self, env=None):

        app_config = get_app_config(env)

        self.config = app_config.get("redis", {})

    @property
    def host(self):

        return self.config.get("host")

    @property
    def port(self):

        return self.config.get("port")

    @property
    def password(self):

        return self.config.get("password")

    @property
    def db(self):

        return self.config.get("db", 0)

    @property
    def protocol(self):

        return self.config.get("protocol", 2)

    @property
    def max_connections(self):

        return self.config.get("max_connections", 20)

    @property
    def socket_timeout(self):

        return self.config.get("socket_timeout")

    @property
    def socket_connect_timeout(self):

        return self.config.get("socket_connect_timeout")
