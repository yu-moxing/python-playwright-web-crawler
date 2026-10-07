class RedisUtil:
    def __init__(self, redis_client):
        self.redis = redis_client

    def make_key(self, head_key, key, separator=":"):
        return f"{head_key}{separator}{key}"

    def set(self, head_key, key, value, ttl=None, separator=":"):
        redis_key = self.make_key(
            head_key,
            key,
            separator=separator,
        )

        if ttl:
            self.redis.set(redis_key, value, ex=ttl)
        else:
            self.redis.set(redis_key, value)

    def get(self, head_key, key, separator=":"):
        redis_key = self.make_key(
            head_key,
            key,
            separator=separator,
        )

        return self.redis.get(redis_key)

    def set_batch(self, head_key, items, ttl=None, separator=":"):
        """
        批量写入 Redis。

        Args:
            head_key: Redis Key 公共前缀。
            items: 待写入数据，例如：
                   [
                       ("001", "value1"),
                       ("002", "value2"),
                       ("003", "value3"),
                   ]
            ttl: 所有 Key 统一使用的过期时间，单位：秒。
                 None 表示不过期。

        注意：如果没有公共的前缀，需要传入：head_key、separator都为空字符串；而：keys得是组装后的完整key
        """
        pipe = self.redis.pipeline()

        for key, value in items:
            redis_key = self.make_key(
                head_key,
                key,
                separator=separator,
            )

            if ttl:
                pipe.set(redis_key, value, ex=ttl)
            else:
                pipe.set(redis_key, value)

        pipe.execute()

    def get_batch(self, head_key, keys, separator=":"):
        """
        批量读取 Redis。

        Args:
            head_key: Redis Key 公共前缀。
            keys: Redis Key 后缀列表，例如：
                  ["001", "002", "003"]

        注意：如果没有公共的前缀，需要传入：head_key、separator都为空字符串；而：keys得是组装后的完整key

        Returns:
            按 keys 原顺序返回对应的 Value。
        """
        redis_keys = [
            self.make_key(
                head_key,
                key,
                separator=separator,
            )
            for key in keys
        ]

        return self.redis.mget(redis_keys)
