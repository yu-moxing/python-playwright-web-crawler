"""
脚本常量读取模块

作用：

    扫描脚本中的所有脚本常量，
    返回脚本常量字典，
    供后续配置解析阶段进行脚本常量替换使用。

脚本常量格式：

    @[SITE_NAME]=Amazon

说明：

    1. 只有等号左侧使用 "@[...]" 定义的项，
       才会被识别为脚本常量。

    2. 脚本常量的值必须为普通字符串，
       不允许引用其它脚本常量。

    3. 支持先引用，再定义。
       因为脚本加载时会先扫描整个脚本，
       再进行配置解析。
"""

import re

# 匹配：脚本常量定义
SCRIPT_CONSTANT_REGEX = re.compile(r"^@\[(?P<name>[A-Za-z_][A-Za-z0-9_]*)\]\s*=\s*(?P<value>.*)$")

# 匹配：脚本常量引用格式
SCRIPT_CONSTANT_REF_REGEX = re.compile(r"@\[(?P<name>[A-Za-z_][A-Za-z0-9_]*)\]")


def is_script_constant(line: str) -> bool:
    """
    判断是否为脚本常量定义。
    """
    return SCRIPT_CONSTANT_REGEX.match(line) is not None


def read_script_constants(lines: list[str]) -> dict[str, str]:
    """
    扫描脚本常量。

    Args:
        lines: 已移除注释后的脚本内容。

    Returns:
        dict[str, str]
    """

    constants: dict[str, str] = {}

    for line in lines:
        line = line.strip()

        if not line:
            continue

        match = SCRIPT_CONSTANT_REGEX.match(line)

        if match is None:
            continue

        name = match.group("name")
        value = match.group("value").strip()

        if "@[" in value:
            raise ValueError(f'脚本常量 "{name}" 的值不能引用其它脚本常量：{value}')

        if name in constants:
            raise ValueError(f"脚本常量重复定义：{name}")

        constants[name] = value

    return constants


def replace_script_constants(value: str, constants: dict[str, str]) -> str:
    """
    替换字符串中的脚本常量引用。

    示例：

        "./export/@[SITE_NAME]"
        ->
        "./export/Amazon"

    Args:
        value: 待替换字符串
        constants: 脚本常量字典

    Returns:
        替换后的字符串

    Raises:
        ValueError:
            当引用了未定义的脚本常量时。
    """

    def replace(match: re.Match) -> str:

        name = match.group("name")

        if name not in constants:
            raise ValueError(f"未定义脚本常量：{name}")

        return constants[name]

    return SCRIPT_CONSTANT_REF_REGEX.sub(replace, value)


if __name__ == "__main__":
    print("测试 read_script_constants()")

    test_cases = {
        "正常": [
            "@[SITE_NAME]=Amazon",
            "@[HOST_NAME]=AmazonCN",
            "",
            "LIST_URL=https://www.amazon.com",
            "OUTPUT_DIR=./export/@[SITE_NAME]",
        ],
        "重复定义": [
            "@[SITE_NAME]=Amazon",
            "@[SITE_NAME]=Taobao",
        ],
        "脚本常量引用脚本常量": [
            "@[SITE_NAME]=Amazon",
            "@[ROOT]=@[SITE_NAME]/export",
        ],
    }

    for name, lines in test_cases.items():
        print("=" * 60)
        print(name)
        print("=" * 60)

        try:
            result = read_script_constants(lines)
            print(result)

        except Exception as e:
            print(f"异常：{e}")

    print("\n测试 replace_script_constants()")

    test_lines = [
        "@[SITE_NAME]=Amazon",
        "@[HOST_NAME]=AmazonCN",
    ]

    constants = read_script_constants(test_lines)

    print(constants)

    print("-" * 60)

    tests = [
        "./export/@[SITE_NAME]",
        "@[HOST_NAME]/data",
        "@[HOST_NAME]-@[SITE_NAME]",
        "abc",
        "@[NOT_FOUND]",
    ]

    for item in tests:
        try:
            print(item)
            print("=>", replace_script_constants(item, constants))

        except Exception as e:
            print("异常：", e)
