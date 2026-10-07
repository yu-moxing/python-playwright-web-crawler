"""
Cate Level Link 数据加载模块

职责：

    - 读取 cate_level_link.txt
    - 按行解析分类链接数据
    - 将每一行转换为 CateLevelLinkDataItem

说明：

    本模块只负责：

        TXT
          ↓
        行字符串
          ↓
        CateLevelLinkDataItem

    文件底层读写由 fileio.txt_io 负责。

    本模块不负责：

        - TXT 文件底层读写
        - cate_ids_path 回填
        - cate_links_path 回填
        - 分类索引匹配
        - 分类树路径构建
        - 分类去重

    cate_ids_path 和 cate_links_path
    在 Loader 阶段为空列表，
    后续由 data/backfill 负责填充。
"""

from constants.cate_const import (
    CATEGORY_DATA_SEPARATOR,
    CATEGORY_LEVEL_SEPARATOR,
    CATEGORY_LIMIT_SEPARATOR,
)
from data.model.cate_level.cate_level_link_data_item import (
    CateLevelLinkDataItem,
)
from fileio.txt_io import read_lines


class CateLevelLinkDataLoader:
    """
    Cate Level Link 数据加载器。
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
    ) -> list[CateLevelLinkDataItem]:
        """
        加载 cate_level_link.txt。

        Args:
            file_path:
                cate_level_link.txt 的完整文件路径。

            encoding:
                文件编码，默认 utf-8。

        Returns:
            CateLevelLinkDataItem 列表。
        """

        lines = read_lines(
            file_path,
            encoding=encoding,
        )

        items: list[CateLevelLinkDataItem] = []

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
    ) -> CateLevelLinkDataItem:
        """
        将 cate_level_link.txt 的一行解析为
        CateLevelLinkDataItem。

        原始格式：

            {url}{CATEGORY_LEVEL_SEPARATOR}{level}
            {CATEGORY_DATA_SEPARATOR}
            {limit_cate_level_0_id}{CATEGORY_LIMIT_SEPARATOR}
            {cate_names_path}

        示例：

            https://e.dangdang.com/list-XHJS-dd_sale-0-1.html--2>>>-1>文艺||青春文学||玄幻/惊悚

        解析结果：

            url:
                https://e.dangdang.com/list-XHJS-dd_sale-0-1.html

            level:
                2

            limit_cate_level_0_id:
                -1

            cate_name:
                玄幻/惊悚

            cate_names_path:
                ["文艺", "青春文学", "玄幻/惊悚"]

            cate_ids_path:
                []

            cate_links_path:
                []
        """

        # =====================================================
        # 第一层：
        #
        # {url}--{level}
        # >>>
        # {limit_cate_level_0_id}>{cate_names_path}
        # =====================================================

        url_level, cate_data = line.split(
            CATEGORY_DATA_SEPARATOR,
            1,
        )

        # =====================================================
        # 第二层：
        #
        # {url}--{level}
        # =====================================================

        url, level_text = url_level.rsplit(
            CATEGORY_LEVEL_SEPARATOR,
            1,
        )

        level = int(level_text)

        # =====================================================
        # 第三层：
        #
        # {limit_cate_level_0_id}>{cate_names_path}
        # =====================================================

        limit_id_text, cate_names_path_text = cate_data.split(
            CATEGORY_LIMIT_SEPARATOR,
            1,
        )

        limit_cate_level_0_id = int(limit_id_text)

        # =====================================================
        # 第四层：
        #
        # 文艺||青春文学||玄幻/惊悚
        # =====================================================

        cate_names_path = [name.strip() for name in cate_names_path_text.split("||") if name.strip()]

        # =====================================================
        # 当前分类名称
        #
        # 取 cate_names_path 最后一个非空值
        # =====================================================

        cate_name = cate_names_path[-1] if cate_names_path else ""

        # =====================================================
        # 构造 DataItem
        #
        # cate_ids_path：
        #     后续由 data/backfill 回填
        #
        # cate_links_path：
        #     后续由 data/backfill 回填
        # =====================================================

        return CateLevelLinkDataItem(
            url=url,
            level=level,
            limit_cate_level_0_id=limit_cate_level_0_id,
            cate_name=cate_name,
            cate_names_path=cate_names_path,
            cate_ids_path=[],
            cate_links_path=[],
        )
