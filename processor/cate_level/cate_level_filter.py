"""
分类范围过滤模块

职责：

- 规范化分类范围配置
- 判断 Level 0 父级分类是否允许采集
- 判断 Level 1 子级分类是否允许采集

支持的配置：

    None
        不过滤。

    {
        "parents": "all",
        "children": "all",
    }
        全部父级 + 全部子级。
        等价于不过滤。

    {
        "parents": [0, 2],
        "children": [1, 3],
    }
        只采集指定的父级 / 子级索引。

本模块不负责：

- 页面导航
- DOM 提取
- URL 标准化
- URL 业务规则
- Item 构造
- 数据校验
- 数据去重
- 数据统计
- 数据写入

说明：

CateLevelFilter 只负责“分类范围判断”。

它不知道：

    分类页面是什么
    分类 URL 是什么
    Item 怎么构造

它只回答：

    这个 Level 0 是否允许？
    这个 Level 1 是否允许？
"""

from __future__ import annotations


class CateLevelFilter:
    """
    分类范围过滤器。

    负责根据 cate_indexes 判断：

        Level 0 parent
        Level 1 child

    是否在当前采集范围内。

    None 表示不过滤。
    """

    def __init__(
        self,
        cate_indexes: dict | None = None,
    ):
        """
        初始化分类范围过滤器。

        Args:
            cate_indexes:
                分类范围配置。

                例如：

                    None

                或：

                    {
                        "parents": "all",
                        "children": "all",
                    }

                或：

                    {
                        "parents": [0, 2],
                        "children": [1, 3],
                    }
        """

        self._filter = self._normalize(cate_indexes)

    # =====================================================
    # 配置规范化
    # =====================================================

    @staticmethod
    def _normalize(
        cate_indexes: dict | None,
    ) -> dict | None:
        """
        规范化分类过滤参数。

        None 表示不过滤。

        返回：

            {
                "all_parents": bool,
                "parents": set | None,
                "all_children": bool,
                "children": set | None,
            }

        说明：

        如果：

            parents == "all"

        则：

            all_parents = True
            parents = None

        children 同理。
        """

        # -------------------------------------------------
        # 未配置过滤
        # -------------------------------------------------

        if not cate_indexes:
            return None

        parents = cate_indexes.get("parents")

        children = cate_indexes.get("children")

        # -------------------------------------------------
        # 是否全部父级
        # -------------------------------------------------

        all_parents = parents == "all"

        # -------------------------------------------------
        # 是否全部子级
        # -------------------------------------------------

        all_children = children == "all"

        # -------------------------------------------------
        # 全部父级 + 全部子级
        #
        # 等价于不过滤。
        # -------------------------------------------------

        if all_parents and all_children:
            return None

        return {
            "all_parents": all_parents,
            "parents": (None if all_parents else set(parents or [])),
            "all_children": all_children,
            "children": (None if all_children else set(children or [])),
        }

    # =====================================================
    # Level 0 Parent
    # =====================================================

    def allow_parent(
        self,
        index: int,
    ) -> bool:
        """
        判断 Level 0 父级分类
        是否在采集范围内。

        Args:
            index:
                Level 0 分类索引。

        Returns:
            True:
                允许采集。

            False:
                不允许采集。
        """

        # -------------------------------------------------
        # 未配置过滤
        # -------------------------------------------------

        if self._filter is None:
            return True

        # -------------------------------------------------
        # 全部父级
        # -------------------------------------------------

        if self._filter["all_parents"]:
            return True

        # -------------------------------------------------
        # 指定父级
        # -------------------------------------------------

        return index in (self._filter["parents"] or set())

    # =====================================================
    # Level 1 Child
    # =====================================================

    def allow_child(
        self,
        index: int,
    ) -> bool:
        """
        判断 Level 1 子级分类
        是否在采集范围内。

        Args:
            index:
                Level 1 分类索引。

        Returns:
            True:
                允许采集。

            False:
                不允许采集。
        """

        # -------------------------------------------------
        # 未配置过滤
        # -------------------------------------------------

        if self._filter is None:
            return True

        # -------------------------------------------------
        # 全部子级
        # -------------------------------------------------

        if self._filter["all_children"]:
            return True

        # -------------------------------------------------
        # 指定子级
        # -------------------------------------------------

        return index in (self._filter["children"] or set())
