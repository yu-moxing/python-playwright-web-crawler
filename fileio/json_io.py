"""
JSON 文件读写模块


职责：

    - 将采集结果写入 JSON 文件
    - 从 JSON 文件读取全部数据
    - 支持 dict / dataclass对象
    - 自动创建输出目录
    - 支持追加写入


调用关系：

    FileIoManager
            |
            v
        JsonIO
            |
            v
        JSON文件
"""

import json
import logging
from dataclasses import asdict

from fileio.base_file import ensure_dir, exists, to_path

logger = logging.getLogger(__name__)


class JsonIO:
    """
    JSON 读写器
    """

    def __init__(
        self,
        *,
        output_path,
        filename="data.json",
    ):
        """
        初始化 JSON 读写器


        参数：

            output_path:

                输出目录


            filename:

                JSON文件名
        """

        self.output_path = to_path(output_path)

        self.filename = filename

        self.file_path = self.output_path / self.filename

        ensure_dir(self.output_path)

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

        item = self._convert_data(data)

        if not item:
            logger.warning("JSON写入数据为空")

            return

        self._append_json(item)

    def read(
        self,
    ):
        """
        读取全部数据


        返回：

            list[dict]

                顶层 JSON 数组的每个元素


        文件不存在或损坏时返回空列表
        """

        if not exists(self.file_path):
            logger.warning(
                "JSON文件不存在: %s",
                self.file_path,
            )

            return []

        try:
            with open(
                self.file_path,
                "r",
                encoding="utf-8",
            ) as file:
                content = json.load(file)

                if isinstance(
                    content,
                    list,
                ):
                    return content

                logger.warning(
                    "JSON文件格式不是列表: %s",
                    self.file_path,
                )

                return []

        except json.JSONDecodeError:
            logger.warning(
                "JSON文件损坏: %s",
                self.file_path,
            )

            return []

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

        raise TypeError(f"JSON不支持的数据类型: {type(data)}")

    def _append_json(
        self,
        item,
    ):
        """
        追加JSON数据
        """

        data_list = []

        # 文件存在，读取旧数据

        if exists(self.file_path):
            try:
                with open(
                    self.file_path,
                    "r",
                    encoding="utf-8",
                ) as file:
                    content = json.load(file)

                    if isinstance(
                        content,
                        list,
                    ):
                        data_list = content

                    else:
                        logger.warning("JSON文件格式不是列表，将重新创建")

            except json.JSONDecodeError:
                logger.warning("JSON文件损坏，将重新创建")

        # 添加新数据

        data_list.append(item)

        # 写回文件

        with open(
            self.file_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data_list,
                file,
                ensure_ascii=False,
                indent=4,
            )

        logger.debug(
            "JSON写入成功: %s",
            self.file_path,
        )
