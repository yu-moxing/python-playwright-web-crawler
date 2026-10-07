"""
JSONL 文件读写模块

职责：
    - 将采集结果写入 JSONL 文件（JSON Lines / NDJSON，每行一个对象）
    - 从 JSONL 文件读取全部数据
    - 支持 dict / dataclass 对象
    - 自动创建输出目录
    - 支持追加写入

调用关系：
    FileIoManager / BatchWriter
            |
            v
        JsonlIO
            |
            v
        JSONL文件
"""

import json
import logging
from dataclasses import asdict

from fileio.base_file import ensure_dir, exists, to_path

logger = logging.getLogger(__name__)


class JsonlIO:
    """
    JSONL 读写器（JSON Lines / NDJSON，每行一个 JSON 对象）
    """

    def __init__(self, *, output_path, filename="data.jsonl"):
        """
        初始化 JSONL 读写器

        参数：
            output_path: 输出目录
            filename: jsonl 文件名
        """
        self.output_path = to_path(output_path)
        self.filename = filename
        self.file_path = self.output_path / self.filename

        ensure_dir(self.output_path)

    def write(self, data):
        """
        写入一条数据（追加一行 JSON）

        支持：
            dict
            dataclass 对象
        """
        item = self._convert_data(data)
        if not item:
            logger.warning("jsonl 写入数据为空")
            return

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.debug("jsonl 写入成功: %s", self.file_path)

    def read(self):
        """
        读取全部数据

        返回：
            list[dict]：每行解析为一个 dict

        文件不存在或为空时返回空列表
        """
        if not exists(self.file_path):
            logger.warning("jsonl 文件不存在: %s", self.file_path)
            return []

        result = []
        with open(self.file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("jsonl 行损坏，跳过: %s", line)

        return result

    def _convert_data(self, data):
        """转换数据格式"""
        if hasattr(data, "__dataclass_fields__"):
            return asdict(data)

        if isinstance(data, dict):
            return data

        raise TypeError(f"jsonl 不支持的数据类型: {type(data)}")
