"""
TXT 批量写入模块

职责：

    - 缓存 TXT 字符串数据
    - 根据 batch_size 自动 flush
    - 批量追加写入 TXT 文件
    - 读取已有 TXT 数据
    - 仅处理 str 类型数据

说明：

    本模块专门用于：

        str
            ↓
        TXT
            ↓
        一行一条数据

    例如：

        "https://example.com/1"
        "https://example.com/2"
        "https://example.com/3"

    每条字符串数据对应 TXT 文件中的一行。

    本模块不负责：

        - JSON
        - JSONL
        - CSV
        - Excel
        - MongoDB
        - dict / dataclass 等结构化数据

    结构化数据应使用 StructuredBatchWriter。

调用关系：

    Runner
        |
        v
    Processor
        |
        | add(str)
        v
    TxtBatchWriter
        |
        | flush()
        v
    TxtIO
        |
        v
    TXT 文件
"""

import logging
from typing import List

from fileio.txt_io import append_lines, read_lines

logger = logging.getLogger(__name__)


class TxtBatchFile:
    """
    TXT 批量写入器。

    数据类型：

        str

    一条字符串对应 TXT 文件中的一行。

    Example:

        >>> txt_batch_file = TxtBatchFile(
        ...     batch_size=100,
        ...     file_path="export/url/url.txt",
        ... )
        >>> txt_batch_file.add("https://example.com/1")
        >>> txt_batch_file.add("https://example.com/2")
        >>> txt_batch_file.close()
    """

    def __init__(
        self,
        *,
        batch_size: int = -1,
        file_path: str,
        encoding: str = "utf-8",
    ):
        """
        初始化 TXT 批量写入器。

        Args:
            batch_size:
                每累计多少条数据执行一次 flush。

                -1：
                    不自动 flush，
                    由 close() 最后统一写入。

            file_path:
                TXT 文件路径。

            encoding:
                文件编码，默认 utf-8。

        Raises:
            ValueError:
                batch_size 为 0 或小于 -1。
        """
        if batch_size == 0 or batch_size < -1:
            raise ValueError("batch_size 必须为 -1 或大于 0")

        self.batch_size = batch_size
        self.file_path = file_path
        self.encoding = encoding

        self.buffer: List[str] = []

        logger.info(
            "TxtBatchWriter 已初始化：file_path=%s, batch_size=%s",
            file_path,
            batch_size,
        )

    def add(
        self,
        item: str,
    ) -> None:
        """
        缓存一条 TXT 数据。

        一条数据对应 TXT 文件中的一行。

        达到 batch_size 时自动 flush。

        Args:
            item:
                要写入的字符串。

        Raises:
            TypeError:
                item_detail 不是 str。
        """
        if not isinstance(item, str):
            raise TypeError(f"TxtBatchWriter 只支持 str 数据，当前类型: {type(item)}")

        self.buffer.append(item)

        if self.batch_size != -1 and len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        """
        将当前缓冲区数据追加写入 TXT 文件。

        使用 TxtIO.append_lines() 批量写入。

        Returns:
            本次写入的条数。
        """
        if not self.buffer:
            return 0

        count = len(self.buffer)

        success = append_lines(
            self.buffer,
            self.file_path,
            encoding=self.encoding,
        )

        if not success:
            logger.error(
                "TXT flush 写入失败：%s",
                self.file_path,
            )
            return 0

        self.buffer.clear()

        logger.info(
            "TXT flush 写入 %d 条数据：%s",
            count,
            self.file_path,
        )

        return count

    def close(self) -> int:
        """
        关闭写入器。

        将缓冲区中的剩余数据全部写入 TXT 文件。

        Returns:
            最终写入的条数。
        """
        if not self.buffer:
            return 0

        return self.flush()

    def read_existing(self) -> List[str]:
        """
        读取已有 TXT 数据。

        用于去重器初始化已有数据。

        Returns:
            List[str]

            文件不存在或读取失败时返回空列表。
        """
        return read_lines(
            self.file_path,
            encoding=self.encoding,
        )
