import re


def extract_regex_key(
    value: str,
    regex: str,
) -> str:
    """
    根据正则表达式从字符串中提取业务 Key。

    规则：
        1. 无正则 -> 返回空字符串
        2. 正则匹配失败 -> 返回空字符串
        3. 有捕获组 -> 返回第一个捕获组
        4. 无捕获组 -> 返回完整匹配
    """

    value = value.strip()
    regex = regex.strip()

    if not value or not regex:
        return ""

    try:
        match = re.search(
            regex,
            value,
            flags=re.IGNORECASE,
        )
    except re.error:
        return ""

    if match is None:
        return ""

    if match.lastindex:
        return match.group(1)

    return match.group(0)
