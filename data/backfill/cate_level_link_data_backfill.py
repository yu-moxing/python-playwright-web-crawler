"""
Cate Level Link 数据回填模块

职责：

    - 根据 CateLevelIndexDataItem 回填 CateLevelLinkDataItem.cate_ids_path
    - 根据分类名称路径回溯分类树
    - 回填 CateLevelLinkDataItem.cate_links_path

说明：

    本模块只负责：

        CateLevelLinkDataItem
                    +
        CateLevelIndexDataItem
                    ↓
        回填后的 CateLevelLinkDataItem

    本模块不负责：

        - TXT 文件读取
        - TXT 文件写入
        - 分类索引生成
        - 分类链接采集
        - 分类去重

回填规则：

    1. cate_ids_path

       根据 CateLevelLinkDataItem.cate_names_path，
       查找 CateLevelIndexDataItem.cate_names_path 对应的数据项，
       将对应的 cate_ids_path 回填。

       匹配为大小写/标点/空格不敏感：基于归一化键
       （只保留 Unicode 字母与数字并 casefold）匹配，
       原始 cate_names_path 字段保持不变。

    2. cate_links_path

       根据 cate_names_path 从 Level 0 开始逐级构造分类路径，
       查找对应的 CateLevelLinkDataItem，
       并按分类层级顺序保存对应 URL。

       cate_links_path 只保存 URL，
       不保存 level、limit_cate_level_0_id、
       cate_names_path 等其他数据。
"""

from data.model.cate_level.cate_level_index_data_item import CateLevelIndexDataItem
from data.model.cate_level.cate_level_link_data_item import CateLevelLinkDataItem


class CateLevelLinkDataBackfill:
    """
    Cate Level Link 数据回填器。
    """

    # =========================================================
    # 对外入口
    # =========================================================

    @classmethod
    def backfill(
        cls,
        *,
        link_items: list[CateLevelLinkDataItem],
        index_items: list[CateLevelIndexDataItem],
    ) -> list[CateLevelLinkDataItem]:
        """
        对 CateLevelLinkDataItem 执行全部回填。

        回填内容：

            1. cate_ids_path
            2. cate_links_path

        Args:
            link_items:
                已经由 CateLevelLinkDataLoader
                加载得到的分类链接数据。

            index_items:
                已经由 CateLevelIndexDataLoader
                加载得到的分类索引数据。

        Returns:
            回填后的 CateLevelLinkDataItem 列表。
        """

        # =====================================================
        # 第一阶段：
        # 根据分类名称路径建立索引
        # =====================================================

        index_map = cls._build_index_map(index_items)

        link_map = cls._build_link_map(link_items)

        # =====================================================
        # 第二阶段：
        # 回填每一个 LinkDataItem
        # =====================================================

        for link_item in link_items:
            # -------------------------------------------------
            # 回填 cate_ids_path
            # -------------------------------------------------

            cls._backfill_cate_ids_path(
                link_item=link_item,
                index_map=index_map,
            )

            # -------------------------------------------------
            # 回填 cate_links_path
            # -------------------------------------------------

            cls._backfill_cate_links_path(
                link_item=link_item,
                link_map=link_map,
            )

        return link_items

    # =========================================================
    # 归一化匹配键
    # =========================================================

    @staticmethod
    def _normalize_key(cate_names_path) -> tuple[str, ...]:
        """
        归一化分类名称路径为匹配键。

        每段名称：剔除所有特殊符号（含中英文标点、半角/全角符号，
        如 / 、 & - 空格 等），只保留 Unicode 字母（含中文繁体及各国文字）
        与数字，再 casefold 统一小写。

        用于 index_map / link_map 的建键与查询，使匹配对大小写、
        标点、空格不敏感。原始 cate_names_path 字段不变，仅匹配键归一化。
        """

        def _norm(name: str) -> str:
            return "".join(c for c in name if c.isalnum()).casefold()

        return tuple(_norm(name) for name in cate_names_path)

    # =========================================================
    # 建立 Index Map
    # =========================================================

    @classmethod
    def _build_index_map(
        cls,
        index_items: list[CateLevelIndexDataItem],
    ) -> dict[tuple[str, ...], list[int]]:
        """
        建立：

            cate_names_path -> cate_ids_path

        例如：

            (
                "经管/励志",
                "成功/励志",
                "情商/心灵感悟",
            )
            ->
            [1, 2, 5]
        """

        index_map: dict[tuple[str, ...], list[int]] = {}

        for item in index_items:
            key = cls._normalize_key(item.cate_names_path)

            if key in index_map:
                raise ValueError(f"发现重复的分类名称路径，无法唯一确定 cate_ids_path：{key!r}")

            index_map[key] = item.cate_ids_path

        return index_map

    # =========================================================
    # 建立 Link Map
    # =========================================================

    @classmethod
    def _build_link_map(
        cls,
        link_items: list[CateLevelLinkDataItem],
    ) -> dict[tuple[str, ...], str]:
        """
        建立：

            cate_names_path -> url

        例如：

            ("经管/励志",)
            ->
            "https://e.dangdang.com/list-JG-dd_sale-0-1.html"

            ("经管/励志", "成功/励志")
            ->
            "https://e.dangdang.com/list-CGLZ-dd_sale-0-1.html"
        """

        link_map: dict[tuple[str, ...], str] = {}

        for item in link_items:
            key = cls._normalize_key(item.cate_names_path)

            if key in link_map:
                raise ValueError(f"发现重复的分类名称路径，无法唯一确定分类 URL：{key!r}")

            link_map[key] = item.url

        return link_map

    # =========================================================
    # 回填 cate_ids_path
    # =========================================================

    @classmethod
    def _backfill_cate_ids_path(
        cls,
        *,
        link_item: CateLevelLinkDataItem,
        index_map: dict[tuple[str, ...], list[int]],
    ) -> None:
        """
        根据 cate_names_path 回填 cate_ids_path。

        匹配为大小写/标点/空格不敏感：基于 _normalize_key 归一化键
        （只保留 Unicode 字母与数字并 casefold）查询 index_map。
        """

        key = cls._normalize_key(link_item.cate_names_path)

        cate_ids_path = index_map.get(key)

        if cate_ids_path is None:
            raise ValueError(f"找不到对应的分类索引数据：cate_names_path={link_item.cate_names_path!r}")

        # 使用 list 副本，避免两个 DataItem 共享同一个 list 对象。
        link_item.cate_ids_path = list(cate_ids_path)

    # =========================================================
    # 回填 cate_links_path
    # =========================================================

    @classmethod
    def _backfill_cate_links_path(
        cls,
        *,
        link_item: CateLevelLinkDataItem,
        link_map: dict[tuple[str, ...], str],
    ) -> None:
        """
        根据 cate_names_path 逐级向上回溯分类树链接。

        例如：

            cate_names_path：

                [
                    "经管/励志",
                    "成功/励志",
                    "情商/心灵感悟",
                ]

        得到：

            [
                "https://e.dangdang.com/list-JG-dd_sale-0-1.html",
                "https://e.dangdang.com/list-CGLZ-dd_sale-0-1.html",
                "https://e.dangdang.com/list-QSQXGL-dd_sale-0-1.html",
            ]

        注意：

            cate_links_path 只保存 URL。
        """

        cate_names_path = link_item.cate_names_path

        cate_links_path: list[str] = []

        # =====================================================
        # 从 Level 0 开始，逐级构造分类路径
        # =====================================================

        for level in range(1, len(cate_names_path) + 1):
            path_key = cls._normalize_key(cate_names_path[:level])

            url = link_map.get(path_key)

            if url is None:
                raise ValueError(
                    f"找不到分类层级对应的 URL：cate_names_path={cate_names_path!r}, level={level}, path={path_key!r}"
                )

            cate_links_path.append(url)

        # =====================================================
        # 回填
        # =====================================================

        link_item.cate_links_path = cate_links_path
