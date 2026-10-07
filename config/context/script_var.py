"""
脚本变量读取模块

作用：

    扫描脚本中的所有脚本变量，
    返回脚本变量字典，
    供后续配置解析阶段进行脚本变量替换使用。

脚本变量格式：

    @{OUTPUT_DIR}=./export/@[SITE_NAME]

说明：

    1. 只有等号左侧使用 "@{...}" 定义的项，
       才会被识别为脚本变量。

    2. 脚本变量的值可以是：
       - 普通字符串
       - 引用脚本常量 @[常量名]

    3. 脚本变量不允许引用其它脚本变量。

    4. 支持先引用，再定义。
       因为脚本加载时会先扫描整个脚本，
       再进行配置解析。

加载顺序：

    1. 先遍历一次脚本常量（Script Constant）
    2. 再遍历一次脚本变量（Script variables）
"""

import re
from typing import Dict

# 匹配：脚本变量定义
SCRIPT_VAR_REGEX = re.compile(r"^@\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}\s*=\s*(?P<value>.*)$")

# 匹配：脚本变量引用格式
SCRIPT_VAR_REF_REGEX = re.compile(r"@\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}")


def is_script_var(line: str) -> bool:
    """
    判断是否为脚本变量定义。

    Args:
        line: 配置行

    Returns:
        True 如果是脚本变量定义，否则 False

    Examples:
        >>> is_script_var("@{OUTPUT_DIR}=./export")
        True
        >>> is_script_var("OUTPUT_DIR=./export")
        False
        >>> is_script_var("@[SITE_NAME]=Amazon")
        False
    """
    return SCRIPT_VAR_REGEX.match(line) is not None


def read_script_vars(lines: list[str], constants: Dict[str, str]) -> Dict[str, str]:
    """
    扫描脚本变量。

    Args:
        lines: 已移除注释后的脚本内容
        constants: 脚本常量字典（用于替换变量值中的常量引用）

    Returns:
        dict[str, str]: 脚本变量字典

    Raises:
        ValueError:
            - 脚本变量值中引用了其它脚本变量
            - 脚本变量重复定义
            - 引用了未定义的脚本常量

    Examples:
        >>> constants = {"SITE_NAME": "Amazon", "BASE_URL": "https://www.amazon.com"}
        >>> lines = [
        ...     "@{OUTPUT_DIR}=./export/@[SITE_NAME]",
        ...     "@{LIST_URL}=@[BASE_URL]/products",
        ... ]
        >>> vars = read_script_vars(lines, constants)
        >>> vars
        {'OUTPUT_DIR': './export/Amazon', 'LIST_URL': 'https://www.amazon.com/products'}
    """
    variables: Dict[str, str] = {}

    # 导入脚本常量替换函数（延迟导入避免循环依赖）
    from config.context.script_constant import replace_script_constants

    for line in lines:
        line = line.strip()

        if not line:
            continue

        match = SCRIPT_VAR_REGEX.match(line)

        if match is None:
            continue

        name = match.group("name")
        value = match.group("value").strip()

        # 检查值中是否有脚本常量引用 @[...]
        if "@[" in value and "]" in value:
            # 替换脚本常量引用
            value = replace_script_constants(value, constants)

        # 检查值中是否有脚本变量引用 @{...}（禁止）
        if "@{" in value and "}" in value:
            var_ref_match = SCRIPT_VAR_REF_REGEX.search(value)
            if var_ref_match:
                ref_name = var_ref_match.group("name")
                raise ValueError(f'脚本变量 "{name}" 的值不能引用其它脚本变量：@{{{ref_name}}}')

        # 检查重复定义
        if name in variables:
            raise ValueError(f"脚本变量重复定义：{name}")

        variables[name] = value

    return variables


def replace_script_vars(value: str, variables: Dict[str, str]) -> str:
    """
    替换字符串中的脚本变量引用。

    示例：

        "./export/@{OUTPUT_DIR}"
        ->
        "./export/Amazon"

    Args:
        value: 待替换字符串
        variables: 脚本变量字典

    Returns:
        替换后的字符串

    Raises:
        ValueError:
            当引用了未定义的脚本变量时。

    Examples:
        >>> variables = {"OUTPUT_DIR": "./export/Amazon", "LIST_URL": "https://www.amazon.com/products"}
        >>> replace_script_vars("./data/@{OUTPUT_DIR}", variables)
        './data/./export/Amazon'
        >>> replace_script_vars("@{LIST_URL}/page1", variables)
        'https://www.amazon.com/products/page1'
    """

    def replace(match: re.Match) -> str:
        name = match.group("name")

        if name not in variables:
            raise ValueError(f"未定义脚本变量：{name}")

        return variables[name]

    return SCRIPT_VAR_REF_REGEX.sub(replace, value)


if __name__ == "__main__":
    print("=" * 70)
    print("测试 script_var.py")
    print("=" * 70)

    # 模拟脚本常量
    constants = {"SITE_NAME": "Amazon", "BASE_URL": "https://www.amazon.com"}

    # 测试 read_script_vars()
    print("\n测试 read_script_vars()")

    test_cases = {
        "正常": [
            "@{OUTPUT_DIR}=./export/@[SITE_NAME]",
            "@{LIST_URL}=@[BASE_URL]/products",
            "",
            "SAVE_PATH=@{OUTPUT_DIR}/data",
        ],
        "重复定义": [
            "@{OUTPUT_DIR}=./export",
            "@{OUTPUT_DIR}=./data",
        ],
        "脚本变量引用脚本变量": [
            "@{OUTPUT_DIR}=./export",
            "@{DATA_DIR}=@{OUTPUT_DIR}/data",
        ],
        "引用未定义常量": [
            "@{OUTPUT_DIR}=./export/@[NOT_FOUND]",
        ],
    }

    for name, lines in test_cases.items():
        print("=" * 60)
        print(name)
        print("=" * 60)

        try:
            result = read_script_vars(lines, constants)
            print(result)

        except Exception as e:
            print(f"异常：{e}")

    # 测试 replace_script_vars()
    print("\n" + "=" * 70)
    print("测试 replace_script_vars()")
    print("=" * 70)

    test_vars = {
        "OUTPUT_DIR": "./export/Amazon",
        "LIST_URL": "https://www.amazon.com/products",
    }

    print(f"变量字典：{test_vars}")
    print("-" * 60)

    tests = [
        "./data/@{OUTPUT_DIR}",
        "@{LIST_URL}/page1",
        "@{LIST_URL}-@{OUTPUT_DIR}",
        "abc",
        "@{NOT_FOUND}",
    ]

    for item in tests:
        try:
            print(f"{item}")
            print(f"=> {replace_script_vars(item, test_vars)}")

        except Exception as e:
            print(f"异常：{e}")
