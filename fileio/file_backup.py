"""
文件备份模块

职责：

    - 通用文件备份
    - 为备份文件添加时间戳
    - 自动创建备份目录
    - 保留原文件元数据
    - 不关心具体文件格式

支持：

    - CSV
    - JSON
    - JSONL
    - TXT
    - Excel
    - HTML
    - XML
    - 其他普通文件

备份文件名格式：

    YYYYMMDD_HHMMSS_原文件名

例如：

    原文件：
        export/cate_level/cate_list.csv

    备份文件：
        backup/20260814_205000_cate_list.csv

说明：

    本模块只负责“文件复制备份”，
    不负责具体文件格式的读写。

调用关系：

    CSV / JSON / TXT / Excel 等模块
                |
                v
          file_backup.py
                |
                v
             backup()
                |
                v
             备份文件
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from fileio.base_file import ensure_dir, exists, to_path

logger = logging.getLogger(__name__)


def backup(
    file_path: str,
    backup_dir: str = "backup",
) -> str:
    """
    备份文件，并在备份文件名前添加时间戳。

    备份文件名格式：

        YYYYMMDD_HHMMSS_原文件名

    Args:
        file_path:
            待备份文件路径。

        backup_dir:
            备份文件存放目录。
            默认为当前工作目录下的 backup。

    Returns:
        成功：
            返回备份文件路径。

        文件不存在或备份失败：
            返回空字符串。

    Example:

        >>> backup_path = backup(
        ...     "export/cate_level/cate_list.csv"
        ... )
        >>> print(backup_path)

        backup/20260814_205000_cate_list.csv
    """

    path = to_path(file_path)

    # =========================================================
    # 检查源文件
    # =========================================================

    if not exists(path):
        logger.warning(
            "文件不存在，无法备份：%s",
            path,
        )
        return ""

    # =========================================================
    # 创建备份目录
    # =========================================================

    backup_path = to_path(backup_dir)

    try:
        ensure_dir(backup_path)

    except OSError as e:
        logger.error(
            "创建备份目录失败：%s，错误：%s",
            backup_path,
            e,
        )
        return ""

    # =========================================================
    # 生成备份文件名
    # =========================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_filename = (
        f"{timestamp}_{path.name}"
    )

    target_path = (
        backup_path / backup_filename
    )

    # =========================================================
    # 执行文件复制
    # =========================================================

    try:
        shutil.copy2(
            path,
            target_path,
        )

        logger.info(
            "文件备份成功：%s -> %s",
            path,
            target_path,
        )

        return str(target_path)

    except OSError as e:
        logger.error(
            "文件备份失败：%s -> %s，错误：%s",
            path,
            target_path,
            e,
        )
        return ""