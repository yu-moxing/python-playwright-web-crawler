"""
cate_list 分类范围过滤模块

职责：

    - 规范化 clii 分类范围配置
    - 判断当前分类链接是否允许采集

与 processor.cate_level.cate_level_filter.CateLevelFilter 的区别：

    CateLevelFilter 按"枚举位置 index"过滤（level0_list / level1 链接列表的下标）。

    CliiFilter 按 cate_ids_path 中的"实际 index id 值"过滤：
        - cate_ids_path[0]：cate level 0 级 index id
        - cate_ids_path[1]：cate level 1 级 index id

clii 语义：

    clii "a-b>c-d"
        > 左侧 a-b：限定 level 0 级 id 范围
        > 右侧 c-d：限定 level 1 级 id 范围
        -1 侧：不限制

    > 右侧非 -1，但分类链接只有 level0、没有 level1 id
    （cate_ids_path 长度为 1，如 --0>>>-1>文艺 这种 0 级入口链接）：
        跳过。

本模块不负责：

    - 页面导航
    - DOM 提取
    - URL 标准化
    - 数据去重
    - 数据写入
"""

from __future__ import annotations

from data.model.cate_level.cate_level_link_data_item import (
    CateLevelLinkDataItem,
)


class CliiFilter:
    """
    cate_list 分类范围过滤器。

    根据 clii 解析出的 cate_indexes 判断：

        link_item.cate_ids_path[0]  （level 0 级 index id）
        link_item.cate_ids_path[1]  （level 1 级 index id）

    是否在当前采集范围内。

    cate_indexes 为 None、或索引文件为空（index_empty）时不过滤。
    """

    def __init__(
        self,
        cate_indexes: dict | None,
        index_empty: bool,
    ):
        """
        初始化分类范围过滤器。

        Args:
            cate_indexes:
                clii 解析结果，形如：

                    None

                    {"parents": "all", "children": "all"}

                    {"parents": [0, 2], "children": [1, 3]}

            index_empty:
                分类索引文件是否为空。
                为空时 cate_ids_path 无值可匹配，整体不过滤。
        """

        self._index_empty = index_empty
        self._filter = self._normalize(cate_indexes)

    # =====================================================
    # 配置规范化
    # =====================================================

    @staticmethod
    def _normalize(
        cate_indexes: dict | None,
    ) -> dict | None:
        """
        规范化 clii 过滤参数。

        None 表示不过滤。

        返回：

            {
                "all_parents": bool,
                "parents": set | None,
                "all_children": bool,
                "children": set | None,
            }

        parents == "all"  → all_parents = True, parents = None
        children == "all" → all_children = True, children = None

        全部父级 + 全部子级 → 等价于不过滤，返回 None。
        """

        if not cate_indexes:
            return None

        parents = cate_indexes.get("parents")
        children = cate_indexes.get("children")

        all_parents = parents == "all"
        all_children = children == "all"

        if all_parents and all_children:
            return None

        return {
            "all_parents": all_parents,
            "parents": (None if all_parents else set(parents or [])),
            "all_children": all_children,
            "children": (None if all_children else set(children or [])),
        }

    # =====================================================
    # 匹配
    # =====================================================

    def match(
        self,
        link_item: CateLevelLinkDataItem,
    ) -> bool:
        """
        判断当前分类链接是否在采集范围内。

        Args:
            link_item: 回填后的分类链接数据项。

        Returns:
            True: 允许采集。
            False: 不允许采集。
        """

        # -------------------------------------------------
        # 索引为空 / 未配置过滤 → 不过滤
        # -------------------------------------------------

        if self._index_empty or self._filter is None:
            return True

        ids = link_item.cate_ids_path

        # -------------------------------------------------
        # Level 0 级 index id
        # -------------------------------------------------

        if not self._filter["all_parents"]:
            if not ids or ids[0] not in (self._filter["parents"] or set()):
                return False

        # -------------------------------------------------
        # Level 1 级 index id
        # -------------------------------------------------

        if self._filter["all_children"]:
            return True

        # children 指定了具体范围：
        # 分类链接没有 level1 id（只有 level0）→ 跳过
        if len(ids) < 2:
            return False

        return ids[1] in (self._filter["children"] or set())
