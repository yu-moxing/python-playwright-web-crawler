"""
CONTENT Redis 管理器

负责：
    1. 生成 CONTENT Redis Key。
    2. 批量查询和写入 CONTENT Redis。

Redis Key：
    CONTENT-${PRO_PROJECT_DIR_NAME}:${HASH_SUFFIX}:${MD5}

其中：
    HASH_SUFFIX：MD5(source.id) 最后 N 位。
    MD5：ContentDataRecord._id。

TTL：
    使用 RedisItem.content_default_ttl，默认 604800 秒（7 天）。

注意：
    CONTENT Redis 仅作为缓存，不是数据源。
    Redis 不存在时，仍需继续进行 MongoDB 去重。
"""

from __future__ import annotations


class ContentRedis:
    """CONTENT Redis 缓存管理器。"""

    def __init__(
        self,
        *,
        redis_util,
        head_key_template: str,
        content_hash_length: int,
        content_ttl: int,
    ):
        """
        初始化 CONTENT Redis 管理器。

        Args:
            redis_util: RedisUtil，负责底层 Redis 操作。
            content_head_key: CONTENT Redis Head Key。
            content_hash_length: MD5 尾部用于 Key 的长度。
            content_ttl: CONTENT Redis 缓存 TTL。
        """

        self.redis_util = redis_util
        self.head_key_template = head_key_template
        self.content_hash_length = content_hash_length
        self.content_ttl = content_ttl

    # =========================================================
    # 构造 CONTENT Redis Head Key
    # =========================================================

    def _build_head_key(self, md5_hash_id: str) -> str:
        """根据 CONTENT _id 构造 Redis Head Key。"""

        hash_suffix = md5_hash_id[-self.content_hash_length :]

        return f"{self.head_key_template}:{hash_suffix}"

    # =========================================================
    # 批量查询
    # =========================================================

    def get_batch(self, md5_hash_ids: list[str]) -> list:
        """
        批量查询 CONTENT Redis。

        返回结果与 md5_hash_ids 顺序一致，不存在时返回 None。
        """
        if not md5_hash_ids:
            return []

        # 1. 初始化一个空列表，用于存放完整的 Redis Key
        redis_keys = []

        # 2. 遍历每一个 md5_hash_id
        for md5_hash_id in md5_hash_ids:
            # 3. 获取前缀，并手动拼接完整的 Key
            # 假设分隔符是 ":"，请根据你实际的 _build_head_key 逻辑调整
            head_key = self._build_head_key(md5_hash_id)
            full_key = f"{head_key}:{md5_hash_id}"

            # 4. 将构建好的完整 Key 追加到列表中
            redis_keys.append(full_key)

        # 5. 传入完整的 redis_keys，通过空字符串绕过底层的前缀拼接逻辑
        return self.redis_util.get_batch(head_key="", keys=redis_keys, separator="")

    # =========================================================
    # 批量写入
    # =========================================================

    def set_batch(self, md5_hash_ids: list[str]) -> None:
        """
        批量写入 CONTENT Redis，并使用 content_ttl 设置 TTL。
        """
        if not md5_hash_ids:
            return

        # 1. 初始化一个空列表，用于存放 (完整Key, Value) 的元组
        items = []

        # 2. 遍历每一个 md5_hash_id
        for md5_hash_id in md5_hash_ids:
            # 3. 获取前缀，并手动拼接完整的 Key（与 get_batch 保持绝对一致）
            head_key = self._build_head_key(md5_hash_id)
            full_key = f"{head_key}:{md5_hash_id}"

            # 4. 将完整 Key 和默认值 "1" 打包
            items.append((full_key, "1"))

        # 5. 调用底层的批量写入方法，通过空字符串绕过前缀拼接逻辑
        # 这样既利用了 Pipeline 的高性能，又保证了 Key 的绝对正确
        self.redis_util.set_batch(head_key="", items=items, ttl=self.content_ttl, separator="")
