"""
文件IO管理模块

职责：

    - 根据 SYSTEM 配置初始化IO处理器
    - 管理 CSV / JSON / TXT / Excel 等IO处理器
    - 提供统一 write / read 接口

说明：

    本模块不负责具体文件格式处理。

    具体格式由对应 IO 处理器负责。


调用关系：

    Processor
        |
        v
    FileIoManager
        |
        +---- CsvIO
        |
        +---- JsonIO
        |
        +---- JsonlIO
        |
        +---- ExcelIO
"""

import logging

from fileio.csv_io import CsvIO

# from fileio.jsonl_io import JsonlIO
from fileio.json_io import JsonIO

logger = logging.getLogger(__name__)


class FileIoManager:
    """
    文件IO管理器

    根据 SystemItem 配置决定：

        - 是否输出 CSV
        - 是否输出 JSON
        - 是否输出 TXT
        - 是否输出 Excel
    """

    def __init__(
        self,
        *,
        system_config,
        output_path,
    ):
        """
        初始化文件IO管理器


        参数：

            system_config:

                SystemItem对象


            output_path:

                文件输出目录
        """

        self.system_config = system_config

        self.output_path = output_path

        # IO处理器列表
        self.handlers = []

        self._load_handlers()

    def _load_handlers(self):
        """
        根据 SYSTEM 配置加载IO处理器
        """

        # ===============================
        # 全字段 CSV
        # ===============================

        if self.system_config.all_fields_save_csv:
            self.handlers.append(CsvIO(output_path=self.output_path))

        # ===============================
        # 全字段 JSON
        # ===============================

        if self.system_config.all_fields_save_json:
            self.handlers.append(JsonIO(output_path=self.output_path))

        # ===============================
        # 全字段 TXT
        # ===============================

        # if self.system_config.all_fields_save_txt:
        #
        #     self.handlers.append(
        #         JsonlIO(
        #             output_path=self.output_path
        #         )
        #     )

        # ===============================
        # Excel
        #
        # 后续 SystemItem 增加：
        #
        # all_fields_save_excel
        #
        # 后启用
        # ===============================

        if not self.handlers:
            logger.warning("未启用任何输出格式")

        logger.info("初始化IO处理器数量: %s", len(self.handlers))

    def write(
        self,
        data,
    ):
        """
        执行数据写入


        参数：

            data:

                Model对象

                或 dict
        """

        for handler in self.handlers:
            try:
                handler.write(data)

            except Exception:
                logger.exception(
                    "写入失败: %s",
                    handler.__class__.__name__,
                )

                raise

    def read(
        self,
    ):
        """
        读取所有IO处理器的数据


        返回：

            dict: {处理器类名: list[dict]}

                每个启用的处理器读取一份


        文件不存在或为空时对应值为空列表
        """

        result = {}

        for handler in self.handlers:
            try:
                result[handler.__class__.__name__] = handler.read()

            except Exception:
                logger.exception(
                    "读取失败: %s",
                    handler.__class__.__name__,
                )

                raise

        return result

    def close(self):
        """
        关闭IO资源

        预留：

            Excel 处理器
            文件句柄
            缓存写入

        """

        for handler in self.handlers:
            close_method = getattr(
                handler,
                "close",
                None,
            )

            if close_method:
                close_method()
