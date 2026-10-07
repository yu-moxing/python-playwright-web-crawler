"""
配置文件注释处理模块

作用：

    删除配置文件中的所有注释，
    返回仅包含有效配置内容的文本列表，
    供后续脚本常量扫描与配置解析使用。

支持注释：

    1. //      单行注释（仅行首有效）
    2. /* */   注释块（支持跨行）

支持格式：

    // 单行注释

    KEY=VALUE /* 行尾注释 */

    /*
    多行注释
    */

    KEY=VALUE /*
    多行注释
    */

    NEXT=123

输入：
    list[str]（原始配置文件文本）

输出：
    list[str]（已移除所有注释后的有效配置文本）

说明：
    本模块仅负责移除注释，不负责：

    - 配置项解析
    - 脚本常量扫描
    - 脚本常量替换
    - 配置合法性校验
"""

import logging

logger = logging.getLogger(__name__)


def remove_inline_comment(line: str) -> str:
    """
    去除单行内的 /* */ 注释

    示例：
    KEY=VALUE /* 注释 */
    -> KEY=VALUE
    """

    start = line.find("/*")

    if start == -1:
        return line.strip()

    end = line.find("*/", start + 2)

    if end == -1:
        return line[:start].strip()

    return (line[:start] + line[end + 2 :]).strip()


def is_comment_line(line: str) -> bool:
    """
    判断是否为整行注释
    """

    line = line.strip()

    if not line:
        return False

    if line.startswith("//"):
        return True

    return False


def clean_line(line: str) -> str:
    """
    处理单行配置文本。

    功能：
    - 去除首尾空白
    - 过滤 // 单行注释
    - 去除单行 /* */ 注释
    """

    line = line.strip()

    if not line:
        return ""

    if is_comment_line(line):
        return ""

    line = remove_inline_comment(line)

    return line.strip()


def clean_lines(lines: list[str]) -> list[str]:
    """
    处理整个配置文件。

    输入：
        list[str]（原始配置文件文本）

    输出：
        list[str]（移除所有注释后的有效配置文本）
    """

    result = []

    in_comment_block = False

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")

        # =====================================
        # 当前位于跨行注释块内部
        # =====================================
        if in_comment_block:
            end_pos = line.find("*/")

            if end_pos == -1:
                continue

            in_comment_block = False

            remain = line[end_pos + 2 :].strip()

            if remain:
                processed = clean_line(remain)

                if processed:
                    result.append(processed)

            continue

        # =====================================
        # 查找注释块开始
        # =====================================
        start_pos = line.find("/*")

        if start_pos != -1:
            end_pos = line.find("*/", start_pos + 2)

            # -------------------------
            # 单行注释块
            # -------------------------
            if end_pos != -1:
                processed = clean_line(line)

                if processed:
                    result.append(processed)

                continue

            # -------------------------
            # 跨行注释块开始
            # -------------------------
            before = line[:start_pos].strip()

            if before:
                processed = clean_line(before)

                if processed:
                    result.append(processed)

            in_comment_block = True

            continue

        # =====================================
        # 普通配置行
        # =====================================
        processed = clean_line(line)

        if processed:
            result.append(processed)

    return result


if __name__ == "__main__":
    test_lines = [
        "// 单行注释",
        "",
        "NAME=test",
        "/*",
        "这是第一行注释",
        "这是第二行注释",
        "*/",
        "AGE=18",
        "CITY=Tokyo /* 行尾注释 */",
        "URL=http://example.com",
        "KEY=VALUE /*",
        "跨行说明1",
        "跨行说明2",
        "*/",
        "NEXT=123",
        "AAA=111 /* abc */ BBB=222",
    ]

    print("=" * 60)
    print("测试结果")
    print("=" * 60)

    result = clean_lines(test_lines)

    for item in result:
        print(item)
