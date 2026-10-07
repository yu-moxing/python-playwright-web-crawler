"""
文件基础工具模块

职责：
    - Path 路径处理
    - 输出目录自动创建
    - 文件存在检查
    - 文件编码管理（默认编码常量）

说明：
    本模块只提供文件层面的基础工具函数。
    不包含 JSON / JSONL / TXT 的格式处理，
    不包含 read/write 业务逻辑，不包含序列化逻辑。
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 文件编码管理：统一默认编码常量
DEFAULT_ENCODING = "utf-8"


def to_path(file_path) -> Path:
    """
    Path 路径处理：把 str / Path 归一为 Path。
    """
    return Path(file_path)


def ensure_dir(directory) -> Path:
    """
    输出目录自动创建：把 directory 当作目录，
    执行 mkdir(parents=True, exist_ok=True)。

    parents=True：
        会自动创建所有中间缺失的父目录（多级目录一次性创建）

    exist_ok=True：
        目录已存在时不会报错
    """
    path = to_path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent_dir(file_path) -> Path:
    """
    输出目录自动创建：为 file_path 创建其父目录。
    """
    path = to_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def exists(file_path) -> bool:
    """
    文件存在检查。
    """
    return to_path(file_path).exists()
