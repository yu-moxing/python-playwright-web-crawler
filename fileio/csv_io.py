"""
CSV 文件读写模块

职责：

    - 将采集结果写入 CSV 文件
    - 从 CSV 文件读取全部数据
    - 支持 dict / dataclass对象
    - 自动创建输出目录
    - 提供 backup / get_stats 等按路径调用的模块级工具函数


调用关系：

    FileIoManager
            |
            v
        CsvIO
            |
            v
        CSV文件

    main / processor 等调用方
            |
            v
        read / write / backup / get_stats（模块级函数）
"""

import csv
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CsvIO:
    """
    CSV 读写器
    """

    def __init__(
        self,
        *,
        output_path,
        filename="data.csv",
    ):
        """
        初始化CSV读写器


        参数：

            output_path:

                输出目录


            filename:

                CSV文件名
        """

        self.output_path = Path(output_path)

        self.filename = filename

        self.file_path = self.output_path / self.filename

        self._header_written = False

        self._create_output_dir()

    def _create_output_dir(self):
        """
        创建输出目录
        """

        self.output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def write(
        self,
        data,
    ):
        """
        写入一条数据


        支持：

            dict

            dataclass对象
        """

        row = self._convert_data(data)

        if not row:
            logger.warning("CSV写入数据为空")

            return

        self._write_row(row)

    def read(
        self,
    ):
        """
        读取全部数据


        返回：

            list[dict]

                每行一个 dict，键为表头


        文件不存在或为空时返回空列表
        """

        if not self.file_path.exists():
            logger.warning(
                "CSV文件不存在: %s",
                self.file_path,
            )

            return []

        with open(
            self.file_path,
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            reader = csv.DictReader(file)

            return [dict(row) for row in reader if row]

    def _convert_data(
        self,
        data,
    ):
        """
        转换数据格式
        """

        # dataclass

        if hasattr(
            data,
            "__dataclass_fields__",
        ):
            return asdict(data)

        # dict

        if isinstance(
            data,
            dict,
        ):
            return data

        raise TypeError(f"CSV不支持的数据类型: {type(data)}")

    def _write_row(
        self,
        row,
    ):
        """
        写入CSV
        """

        file_exists = self.file_path.exists() and self.file_path.stat().st_size > 0

        with open(
            self.file_path,
            "a",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=row.keys(),
            )

            # 第一次写入表头

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        logger.debug(
            "CSV写入成功: %s",
            self.file_path,
        )


# ==========================
# 模块级工具函数（按路径调用）
# ==========================


def read(file_path: str) -> List[Dict[str, str]]:
    """
    读取 CSV 文件

    Args:
        file_path: CSV 文件路径

    Returns:
        数据列表，每个元素为字典

    Raises:
        FileNotFoundError: 文件不存在

    Example:
        >>> data = read('export/cate_level/cate_list.csv')
        >>> print(len(data))
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV 文件不存在：{file_path}")

    data = []

    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 清理字段值（去除首尾空格，空值补 "00"）
                cleaned_row = {k: v.strip() if v else "00" for k, v in row.items()}
                data.append(cleaned_row)

        logger.info(f"读取 CSV 文件：{file_path}，共 {len(data)} 条数据")
        return data

    except Exception as e:
        logger.error(f"读取 CSV 文件失败：{file_path} - {e}")
        raise


def write(
    data: List[Dict[str, str]],
    file_path: str,
    fieldnames: Optional[List[str]] = None,
    mode: str = "a",
) -> int:
    """
    写入 CSV 文件

    Args:
        data: 数据列表
        file_path: CSV 文件路径
        fieldnames: 字段名列表（可选，默认为 ['level_0', 'level_1', 'level_2', 'level_3']）
        mode: 写入模式（'a' 追加，'w' 覆盖）

    Returns:
        写入的数据条数

    Example:
        >>> data = [{'level_0': '女装##123', 'level_1': '连衣裙##456', 'level_2': '00', 'level_3': '00'}]
        >>> write(data, 'export/cate_level/cate_list.csv')
    """
    if not data:
        logger.warning("数据为空，跳过写入")
        return 0

    # 默认字段名
    if not fieldnames:
        fieldnames = ["level_0", "level_1", "level_2", "level_3"]

    # 确保目录存在
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"创建目录：{dir_path}")

    # 检查文件是否存在，决定是否写入表头
    file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0

    try:
        with open(file_path, mode, encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # 文件不存在或为空时写入表头
            if not file_exists or mode == "w":
                writer.writeheader()

            # 写入数据
            writer.writerows(data)

        logger.info(f"写入 CSV 文件：{file_path}，共 {len(data)} 条数据")
        return len(data)

    except Exception as e:
        logger.error(f"写入 CSV 文件失败：{file_path} - {e}")
        raise


def get_stats(file_path: str) -> Dict[str, int]:
    """
    获取 CSV 文件统计信息

    Args:
        file_path: CSV 文件路径

    Returns:
        统计信息字典

    Example:
        >>> stats = get_stats('export/cate_level/cate_list.csv')
        >>> print(stats)
    """
    if not os.path.exists(file_path):
        return {"total": 0, "unique": 0, "duplicates": 0}

    try:
        data = read(file_path)

        # 统计唯一数据
        seen: Set[str] = set()
        for item in data:
            key = "|".join([item.get(f, "00") for f in ["level_0", "level_1", "level_2", "level_3"]])
            seen.add(key)

        return {
            "total": len(data),
            "unique": len(seen),
            "duplicates": len(data) - len(seen),
            "file_size": os.path.getsize(file_path),
        }

    except Exception as e:
        logger.error(f"获取统计信息失败：{e}")
        return {"total": 0, "unique": 0, "duplicates": 0, "error": str(e)}
