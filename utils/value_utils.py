import random


def resolve_value_or_range(value: str) -> int:
    """
    将配置值解析为最终整数值。

    支持：
        -1          → -1
        正整数 N    → N
        N-M         → 随机返回 [N, M] 内的整数

    Raises:
        ValueError: 配置格式非法。
    """
    raw = value.strip()

    if raw == "-1":
        return -1

    # 单个正整数
    if raw.lstrip("+").isdigit():
        number = int(raw)

        if number <= 0:
            raise ValueError(f"配置值非法：{value}（单独数字必须大于 0）")

        return number

    # 数字1-数字2
    if "-" in raw and not raw.startswith("-"):
        left_str, right_str = (part.strip() for part in raw.split("-", 1))

        if not left_str.isdigit() or not right_str.isdigit():
            raise ValueError(f"配置值非法：{value}（范围格式应为：数字1-数字2）")

        left = int(left_str)
        right = int(right_str)

        if left <= 0 or right <= 0:
            raise ValueError(f"配置值非法：{value}（范围值必须大于 0）")

        if right <= left:
            raise ValueError(f"配置值非法：{value}（右值必须大于左值）")

        return random.randint(left, right)

    raise ValueError(f"配置值非法：{value}（合法格式：-1、大于 0 的整数、或 数字1-数字2）")
