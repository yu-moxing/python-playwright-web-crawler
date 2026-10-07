"""MongoDB 配置

负责：
    从 app_config 获取 MongoDB 连接配置

不负责：
    MongoDB 数据库名称
    MongoDB Collection 配置
    MongoDB 连接
    MongoDB CRUD
"""

from config.application.app_config import get_app_config


class MongoDBConfig:
    def __init__(self, env=None):
        app_config = get_app_config(env)
        self.config = app_config.get("mongodb", {})

    @property
    def host(self):
        return self.config.get("host")

    @property
    def port(self):
        return self.config.get("port")

    @property
    def username(self):
        return self.config.get("username")

    @property
    def password(self):
        return self.config.get("password")

    @property
    def auth_source(self):
        return self.config.get("auth_source", "admin")

    @property
    def max_pool_size(self):
        return self.config.get("max_pool_size", 50)

    @property
    def server_selection_timeout(self):
        return self.config.get("server_selection_timeout", 5)

    @property
    def connect_timeout(self):
        return self.config.get("connect_timeout", 5)
