"""
结构化数据批量写入模块

职责：

    - 缓存结构化数据（buffer）
    - 根据 batch_size 判断是否 flush
    - 将结构化数据批量写入对应 Writer
    - 读取已有数据（供去重器 seed）
    - 支持 dict 类型数据

支持的 output_type：

    - mongodb：MongoWriter
    - csv：CsvIO
    - json：JsonIO
    - jsonl：JsonlIO
    - excel：ExcelIO

说明：

    本模块只处理结构化数据。

    一条数据通常表示为：

        {
            "name": "小说",
            "url": "https://example.com",
            "category": "文学",
        }

    不负责普通字符串 / TXT 数据。

    TXT 数据应使用：

        TxtBatchWriter

设计原则：

    - 通用组件，不绑定 cate_level
    - product / article / cate_level 等 Processor 均可复用
    - 由调用方（Runner）构造后注入 Processor
    - Processor 不在内部 new Writer
    - batch_size=-1 表示采集完成后一次性写入
    - close() 负责刷写剩余数据

调用关系：

    Runner
        |
        v
    StructuredBatchWriter
        |
        v
    Processor
        |
        | add(dict)
        v
    buffer
        |
        | 达到 batch_size
        v
    flush()
        |
        +---- MongoDB
        +---- CSV
        +---- JSON
        +---- JSONL
        +---- Excel
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from database.mongodb.mongodb_writer import MongoWriter
from fileio.csv_io import CsvIO
from fileio.excel_io import ExcelIO
from fileio.json_io import JsonIO
from fileio.jsonl_io import JsonlIO

logger = logging.getLogger(__name__)


StructuredOutputType = Literal[
    "mongodb",
    "csv",
    "json",
    "jsonl",
    "excel",
]

Item = Dict[str, Any]


class StructuredBatchFile:
    """
    结构化数据批量写入器。

    输入：

        dict

    输出：

        MongoDB / CSV / JSON / JSONL / Excel

    Example:

        >>> structured_batch_file = StructuredBatchFile(
        ...     batch_size=100,
        ...     output_type="csv",
        ...     output_path="export/cate_level",
        ...     filename="cate_list.csv",
        ... )
        >>>
        >>> structured_batch_file.add({
        ...     "name": "小说",
        ...     "url": "https://example.com",
        ... })
        >>>
        >>> structured_batch_file.close()
    """

    def __init__(
        self,
        *,
        batch_size: int = -1,
        output_type: StructuredOutputType = "jsonl",
        output_path: str = ".",
        filename: Optional[str] = None,
        sheet_name: str = "Sheet1",
        mongo: Optional[dict] = None,
    ):
        """
        初始化结构化数据批量写入器。

        Args:
            batch_size:
                每累计多少条数据执行一次 flush。

                -1：
                    不自动 flush，
                    采集完成后由 close() 一次性写入。

            output_type:
                输出类型：

                    mongodb
                    csv
                    json
                    jsonl
                    excel

            output_path:
                文件输出目录。

                MongoDB 模式下不使用。

            filename:
                文件名。

                未指定时，根据 output_type
                使用默认文件名。

            sheet_name:
                Excel 工作表名称。

                仅 output_type="excel" 时使用。

            mongo:
                MongoDB 配置。

                仅 output_type="mongodb" 时使用。

                需要包含：

                    mongodb_client
                    database_name
                    collection_name

        Raises:
            ValueError:
                batch_size 不合法。

            ValueError:
                output_type 不支持。

            ValueError:
                MongoDB 模式缺少配置。
        """
        if batch_size == 0 or batch_size < -1:
            raise ValueError("batch_size 必须为 -1 或大于 0")

        self.batch_size = batch_size
        self.output_type = output_type
        self.buffer: List[Item] = []

        self._writer = self._build_writer(
            output_type=output_type,
            output_path=output_path,
            filename=filename,
            sheet_name=sheet_name,
            mongo=mongo,
        )

        logger.info(
            "StructuredBatchWriter 已初始化：output_type=%s, batch_size=%s",
            output_type,
            batch_size,
        )

    # ==========================
    # Writer 构建
    # ==========================

    @staticmethod
    def _build_writer(
        *,
        output_type: StructuredOutputType,
        output_path: str,
        filename: Optional[str],
        sheet_name: str,
        mongo: Optional[dict],
    ):
        """
        根据 output_type 构建底层 Writer。
        """

        if filename is None:
            default_filenames = {
                "csv": "data.csv",
                "json": "data.json",
                "jsonl": "data.jsonl",
                "excel": "data.xlsx",
            }

            filename = default_filenames.get(
                output_type,
                "data.out",
            )

        if output_type == "csv":
            return CsvIO(
                output_path=output_path,
                filename=filename,
            )

        if output_type == "json":
            return JsonIO(
                output_path=output_path,
                filename=filename,
            )

        if output_type == "jsonl":
            return JsonlIO(
                output_path=output_path,
                filename=filename,
            )

        if output_type == "excel":
            return ExcelIO(
                output_path=output_path,
                filename=filename,
                sheet_name=sheet_name,
            )

        if output_type == "mongodb":
            if not mongo:
                raise ValueError("output_type='mongodb' 需要提供 mongo 配置")

            return MongoWriter(**mongo)

        raise ValueError(f"不支持的结构化数据 output_type：{output_type}")

    # ==========================
    # 写入接口
    # ==========================

    def add(
        self,
        item: Item,
    ) -> None:
        """
        缓存一条结构化数据。

        达到 batch_size 时自动 flush。

        Args:
            item:
                结构化数据。

                当前要求为 dict。

        Raises:
            TypeError:
                item_detail 不是 dict。
        """
        if not isinstance(item, dict):
            raise TypeError(f"StructuredBatchWriter 只支持 dict 数据，当前类型：{type(item)}")

        self.buffer.append(item)

        if self.batch_size != -1 and len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        """
        刷写当前缓冲区数据。

        MongoDB：

            如果底层 Writer 支持 write_batch()，
            则一次批量写入。

        文件类：

            逐条调用 write()。

        Returns:
            本次成功提交的条数。
        """
        if not self.buffer:
            return 0

        count = len(self.buffer)

        try:
            # MongoDB 等批量 Writer
            if hasattr(
                self._writer,
                "write_batch",
            ):
                self._writer.write_batch(self.buffer)

            # JSON / JSONL / CSV / Excel
            else:
                for item in self.buffer:
                    self._writer.write(item)

        except Exception:
            logger.exception("结构化数据 flush 写入失败")
            raise

        self.buffer.clear()

        logger.info(
            "结构化数据 flush 写入 %d 条：%s",
            count,
            self.output_type,
        )

        return count

    def close(self) -> int:
        """
        关闭批量写入器。

        将 buffer 中剩余数据全部写入。

        Returns:
            最终写入的条数。
        """
        if not self.buffer:
            return 0

        return self.flush()

    # ==========================
    # 读取接口
    # ==========================

    def read_existing(self) -> List[Item]:
        """
        读取已有结构化数据。

        主要用于：

            去重器初始化 seen_keys

        文件不存在 / 文件损坏 / MongoDB
        不可读取时返回空列表。

        Returns:
            list[dict]
        """
        reader = getattr(
            self._writer,
            "read",
            None,
        )

        if reader is None:
            return []

        try:
            data = reader()

            if not isinstance(data, list):
                logger.warning("已有数据格式不是列表，将视为空数据")
                return []

            return data

        except Exception as e:
            logger.warning(
                "读取已有结构化数据失败，将视为无重复：%s",
                e,
            )
            return []
