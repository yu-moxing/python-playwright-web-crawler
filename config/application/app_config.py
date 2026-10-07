"""
应用配置加载器

负责：
    加载 env/dev.yaml
    加载 env/pro.yaml

提供：
    get_app_config()
    配置对象按环境缓存
"""

import os
from pathlib import Path

import yaml

# 项目根目录
#
# 当前:
# config/application/app_config.py
#
# parents[0] -> application
# parents[1] -> config
# parents[2] -> 项目根目录

PROJECT_DIR = Path(__file__).resolve().parents[2]


# env目录
ENV_DIR = PROJECT_DIR / "env"


# 默认环境
DEFAULT_ENV = "dev"
# DEFAULT_ENV = "pro"


class AppConfig:
    def __init__(self, env=None):

        self.env = env or os.getenv("APP_ENV") or DEFAULT_ENV

        self.config = self._load_config()

    # ========================================================
    # 加载yaml
    # ========================================================

    def _load_config(self):

        config_file = ENV_DIR / f"{self.env}.yaml"

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在:{config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ========================================================
    # 获取配置节点
    # ========================================================

    def get(self, key, default=None):

        return self.config.get(key, default)


# ============================================================
# 全局配置缓存
#
# 按环境缓存:
#
# dev
#   |
#   AppConfig(dev)
#
# pro
#   |
#   AppConfig(pro)
#
# 避免 dev/pro 配置互相覆盖
# ============================================================

_app_config_cache = {}


def get_app_config(env=None):
    """
    参数:
        env:
            指定的运行环境（如 'dev', 'pro'）。
            若为 None，则降级读取系统环境变量 APP_ENV；
            若环境变量也不存在，则使用默认环境 DEFAULT_ENV。
    """
    current_env = env or os.getenv("APP_ENV") or DEFAULT_ENV

    if current_env not in _app_config_cache:
        _app_config_cache[current_env] = AppConfig(current_env)

    return _app_config_cache[current_env]
