"""
CateList Redis 管理器

负责记录 CATE_LIST 分页 URL 的采集状态。

Redis Key 结构：

    无：sort_order 时
    CATE_LIST_LINK-${PRO_PROJECT_DIR_NAME}:${sort_field}:${page_url}

    有：sort_order 时
    CATE_LIST_LINK-${PRO_PROJECT_DIR_NAME}:${sort_field}-${sort_order}:${page_url}

例如：

    CATE_LIST_LINK-1051-001-shopee_tw-product-zh_tw:price-https://shopee.tw/xxx?page=5

状态语义：

    Key 不存在
        → 未采集

    Key 存在
        → 已采集

Value 本身没有业务含义，只用于表示 Key 已存在。

TTL：

    根据 sort_field 从 sort_fields_ttl 中获取。

例如：

    pop   → 604800
    ctime → 172800
    sales → 604800
    price → 604800
"""

from __future__ import annotations

from database.redis.redis_ttl_util import get_sort_field_ttl


class CateListRedis:
    """CATE_LIST 分页 URL Redis 管理器。"""

    def __init__(
        self,
        *,
        redis_util,
        # project_dir_name: str,
        sort_field: str,
        sort_order: str,
        head_key_template: str,
        sort_fields_ttl: dict[str, int],
    ):
        self.redis_util = redis_util
        self.sort_field = sort_field
        self.sort_order = sort_order
        self.head_key_template = head_key_template
        self.sort_fields_ttl = sort_fields_ttl

        self.head_key = self._build_head_key()

    # =========================================================
    # ① 构造 Redis Head Key
    #
    # head_key_template 已完成 ${PRO_*} 项目变量替换。
    # 追加 sort_field；sort_order 有值时同时追加排序方向。
    #
    # sort_order 有值：
    #   CATE_LIST_LINK-xxx:price-asc
    #
    # sort_order 无值：
    #   CATE_LIST_LINK-xxx:price
    # =========================================================

    def _build_head_key(self) -> str:
        """构造当前排序字段对应的 Redis head key。"""

        if self.sort_order:
            return f"{self.head_key_template}:{self.sort_field}-{self.sort_order}"

        return f"{self.head_key_template}:{self.sort_field}"

    # =========================================================
    # ② 判断分页 URL 是否已经采集
    #
    # CATE_LIST 的 Redis Key 由 Head Key 和分页 URL组成。
    #
    # Head Key：
    #     CATE_LIST_LINK-xxx:price-asc
    #
    # 最终 Key：
    #     CATE_LIST_LINK-xxx:price-asc:https://shopee.tw/xxx?page=5
    # =========================================================

    def exists(self, page_url: str) -> bool:
        return bool(
            self.redis_util.get(
                self.head_key,
                page_url,
                # separator="-",
                separator=":",
            )
        )

    # =========================================================
    # ③ 标记分页 URL 已采集
    #
    # 每采集完成一个分页 URL，就写入 Redis。
    #
    # Value 本身没有业务含义，只用于表示 Key 存在。
    #
    # 同时按照当前 sort_field 设置 TTL。
    # =========================================================

    def set_crawled(self, page_url: str) -> None:

        ttl = get_sort_field_ttl(
            self.sort_field,
            self.sort_fields_ttl,
        )

        self.redis_util.set(
            self.head_key,
            page_url,
            "1",
            ttl=ttl,
            # separator="-",
            separator=":",
        )
