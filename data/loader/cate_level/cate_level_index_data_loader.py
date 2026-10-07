"""
Cate Level Index 数据加载模块

职责：

    - 读取 cate_level_index.txt
    - 按行解析分类索引数据
    - 将每一行转换为 CateLevelIndexDataItem

说明：

    本模块只负责：

        TXT
          ↓
        行字符串
          ↓
        CateLevelIndexDataItem

    文件底层读写由 fileio.txt_io 负责。

    本模块不负责：

        - TXT 文件底层读写
        - 数据写入
        - 数据回填
        - 分类索引匹配
        - 分类去重
"""

from constants.cate_const import (
    CATEGORY_FIELD_SEPARATOR,
    CATEGORY_INDEX_SEPARATOR,
)
from data.model.cate_level.cate_level_index_data_item import (
    CateLevelIndexDataItem,
)
from fileio.txt_io import read_lines


class CateLevelIndexDataLoader:
    """
    Cate Level Index 数据加载器。
    """

    # =========================================================
    # 文件级加载
    # =========================================================

    @classmethod
    def load(
        cls,
        *,
        file_path: str,
        encoding: str = "utf-8",
    ) -> list[CateLevelIndexDataItem]:
        """
        加载 cate_level_index.txt。

        Args:
            file_path:
                cate_level_index.txt 的完整文件路径。

            encoding:
                文件编码，默认 utf-8。

        Returns:
            分类索引数据项列表。
        """

        lines = read_lines(
            file_path,
            encoding=encoding,
        )

        items: list[CateLevelIndexDataItem] = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            item = cls._parse_line(line)
            items.append(item)

        return items

    # =========================================================
    # 单行解析
    # =========================================================

    @classmethod
    def _parse_line(
        cls,
        line: str,
    ) -> CateLevelIndexDataItem:
        """
        将 cate_level_index.txt 的一行解析为
        CateLevelIndexDataItem。

        示例：

            001#文艺------------002#青春文学------------004#校园/成长------------ ------------ ------------24

        解析为：

            cate_ids_path:
                [1, 2, 4]

            cate_names_path:
                ["文艺", "青春文学", "校园/成长"]

            cate_level_index:
                24
        """

        parts = line.split(CATEGORY_FIELD_SEPARATOR)

        if len(parts) != 6:
            raise ValueError(f"cate_level_index 数据格式错误：期望 6 个字段，实际 {len(parts)} 个字段：{line!r}")

        cate_ids_path: list[int] = []
        cate_names_path: list[str] = []

        # =====================================================
        # 解析 Level 0 ~ Level 4 分类字段
        # =====================================================

        for part in parts[:5]:
            part = part.strip()

            if not part:
                continue

            cate_id_text, cate_name = part.split(
                CATEGORY_INDEX_SEPARATOR,
                1,
            )

            cate_ids_path.append(int(cate_id_text))
            cate_names_path.append(cate_name)

        # =====================================================
        # 解析分类索引
        # =====================================================

        cate_level_index = int(parts[5].strip())

        # =====================================================
        # 构造数据模型
        # =====================================================

        return CateLevelIndexDataItem(
            cate_ids_path=cate_ids_path,
            cate_names_path=cate_names_path,
            cate_level_index=cate_level_index,
        )
