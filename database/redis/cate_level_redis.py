"""
分类链接采集状态 Redis 管理器

负责：
    - 根据项目目录名和排序字段构造分类链接 Redis head key。
    - 根据分类 index 管理对应的 Redis key。
    - 管理分类链接采集断点。
    - 管理已完成分类链接的 TTL。

状态：
    1
        Redis key 不存在时，由程序解释为未采集。

    2
        Redis key 存在，并且 value 为上次采集的翻页 URL。
        由程序解释为需要继续采集。

    3
        Redis key 存在，并且 value 为 END。
        由程序解释为已经采集完成。

注意：
    Redis 中不直接存储 1 / 2 / 3 状态值。

    Redis 实际存储：

        不存在
            → 未采集

        {page_url}
            → 需要继续采集

        END
            → 已经采集完成
"""

from __future__ import annotations

from constants.cate_const import STATUS_COMPLETED_END
from database.redis.redis_ttl_util import get_sort_field_ttl


class CateLevelRedis:
    """分类链接采集状态 Redis 管理器。"""

    # =========================================================
    # 初始化
    # =========================================================

    def __init__(
        self,
        *,
        redis_util,
        # mongodb_util,
        sort_field: str,
        sort_order: str,
        head_key_template: str,
        sort_fields_ttl: dict[str, int],
    ):
        """
        初始化分类链接 Redis 管理器。

        Args:
            redis_util:
                RedisUtil，负责底层 Redis 操作。

            sort_field:
                当前排序字段，例如：
                    pop
                    ctime
                    sales
                    price

            head_key_template:
                分类链接 Redis head key。
                ${PRO_*} 项目变量已在配置解析阶段完成替换。

                例如：
                    CATE_LEVEL_LINK-1051-001-shopee_tw-product-zh_tw

            sort_fields_ttl:
                各排序字段对应的 Redis TTL，例如：
                    {
                        "pop": 604800,
                        "ctime": 172800,
                        "sales": 604800,
                        "price": 604800,
                    }
        """

        self.redis_util = redis_util
        # self.mongodb_util = mongodb_util
        self.sort_field = sort_field
        self.sort_order = sort_order

        self.head_key_template = head_key_template
        self.sort_fields_ttl = sort_fields_ttl

        # =====================================================
        # 构造 head key
        #
        # head_key_template 已完成 ${PRO_*} 项目变量替换。
        # 追加 sort_field；sort_order 有值时同时追加排序方向。
        # =====================================================

        self.head_key = self._build_head_key()

    # =========================================================
    # Key 构造
    #
    # head_key_template 已完成 ${PRO_*} 项目变量替换。
    # 追加 sort_field；sort_order 有值时同时追加排序方向。
    #
    # sort_order 有值：
    #   CATE_LEVEL_LINK-xxx:price-asc
    #
    # sort_order 无值：
    #   CATE_LEVEL_LINK-xxx:price
    # =========================================================

    def _build_head_key(self) -> str:
        """构造当前排序字段对应的 Redis head key。"""

        if self.sort_order:
            return f"{self.head_key_template}:{self.sort_field}-{self.sort_order}"

        return f"{self.head_key_template}:{self.sort_field}"

    # =========================================================
    # 状态读取
    # =========================================================

    def get(self, index: int) -> str | None:
        """
        获取指定分类链接的采集状态。

        Redis Key 不存在时：
            返回 None，表示未采集。

        Redis Key 存在时：
            直接返回 Redis 中保存的 value。

        Redis 实际 value：

            None
                表示 Redis Key 不存在，未采集。

            {page_url}
                表示需要继续采集。

            END
                表示已经采集完成。

        Returns:
            None
                Redis Key 不存在，未采集。

            {page_url}
                Redis Key 存在，需要继续采集。

            "END"
                Redis Key 存在，已经采集完成。
        """

        value = self.redis_util.get(
            self.head_key,
            str(index),
        )

        if value is None:
            return None

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return value

    # =========================================================
    # 状态写入：更新最新分页 URL
    # =========================================================

    def update_page_url(
        self,
        index: int,
        page_url: str,
    ) -> None:
        """
        更新分类链接最新采集到的分页 URL。

        每采集到一条新的分页链接后调用一次。

        Redis Value：
            直接保存最新的分页 URL。

        TTL：
            每次更新时重新设置当前 sort_field 对应的 TTL。

        例如：

            Key：
                CATE_LEVEL_LINK-1051-001-shopee_tw-product-zh_tw:price:7

            Value：
                https://shopee.tw/xxx?page=5

            TTL：
                price -> 604800 秒

        当继续采集到下一条分页链接时：

            Value：
                https://shopee.tw/xxx?page=6

            TTL：
                重新设置为 604800 秒

        Args:
            index:
                cate_level_link.txt 中的分类链接 index。

            page_url:
                最新采集到的分页 URL。
        """

        ttl = get_sort_field_ttl(
            self.sort_field,
            self.sort_fields_ttl,
        )

        self.redis_util.set(
            self.head_key,
            str(index),
            page_url,
            ttl=ttl,
        )

    # =========================================================
    # 状态写入：已完成
    # =========================================================

    def set_completed(self, index: int) -> None:
        """
        设置分类链接为已完成状态。

        Redis Value：
            END

        TTL：
            从当前 sort_field 对应的 sort_fields_ttl 获取。

        采集完成后：
            将最新采集进度更新为 END，
            并重新设置 TTL。

        TTL 到期后：
            Redis 自动删除该 key。

        下一次采集时：
            key 不存在
                ↓
            get(index) 返回 None
                ↓
            从分类第一页重新开始采集。
        """

        ttl = get_sort_field_ttl(
            self.sort_field,
            self.sort_fields_ttl,
        )

        self.redis_util.set(
            self.head_key,
            str(index),
            STATUS_COMPLETED_END,
            ttl=ttl,
        )
