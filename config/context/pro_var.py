"""
项目变量（Project variables）

作用：

    判断字符串是否包含项目变量，
    并替换字符串中的项目变量。

项目变量格式：

    ${PRO_OUTPUT_DIR}

说明：

    1. 项目变量必须以 PRO_ 开头。

    2. 项目变量不能在脚本中定义。

    3. 项目变量只能出现在等号右侧，
       即只能被引用。

    4. 项目变量的值由 Python 程序提供。

示例：

    程序：

        program_vars = {
            "PRO_OUTPUT_DIR": "./export",
            "PRO_PROJECT_DIR": "/home/project",
        }

    脚本：

        OUTPUT_DIR=${PRO_OUTPUT_DIR}
"""

import re
from typing import Dict

# ==========================================================
# 延迟型项目变量（运行期替换）
# ==========================================================

# 这两个变量的值来自命令行 so 参数（或 so=ut 时 user_pool.xlsx 第 9 列），
# 在 load_configs → parse_script_config 之后才解析得到，无法在解析期注入
# 全局 program_vars 字典。故 parse_script_config 解析期遇到它们时原样保留
# ${PRO_...} 占位符，交由运行期在 redis head_key 消费点按 so_spec 二次替换。
DEFERRED_PROGRAM_VARS = frozenset(
    {
        "PRO_CATE_LEVEL_SORT_FIELD",
        "PRO_CATE_LEVEL_SORT_ORDER",
    }
)


def build_sort_program_vars(field, order) -> Dict[str, str]:
    """
    由 so 解析结果构造排序相关项目变量字典，供运行期对含
    ${PRO_CATE_LEVEL_SORT_FIELD} / ${PRO_CATE_LEVEL_SORT_ORDER} 占位符的
    值（如 redis head_key 前缀模板）做二次替换。

    Args:
        field: 排序字段（SoSpec.field，可为 None）
        order: 排序顺序（SoSpec.order，可为 None）

    Returns:
        {"PRO_CATE_LEVEL_SORT_FIELD": field or "", "PRO_CATE_LEVEL_SORT_ORDER": order or ""}
    """
    return {
        "PRO_CATE_LEVEL_SORT_FIELD": field or "",
        "PRO_CATE_LEVEL_SORT_ORDER": order or "",
    }


# ==========================================================
# 项目变量引用
# ==========================================================

PROGRAM_VAR_REF_REGEX = re.compile(r"\$\{(?P<name>PRO_[A-Za-z_][A-Za-z0-9_]*)\}")


def contains_program_var(value: str) -> bool:
    """
    判断字符串是否包含项目变量引用。

    Args:
        value: 待检查字符串

    Returns:
        True 表示包含项目变量，否则 False

    Examples:
        >>> contains_program_var("${PRO_OUTPUT_DIR}")
        True

        >>> contains_program_var("abc ${PRO_PROJECT_DIR}")
        True

        >>> contains_program_var("@{OUTPUT_DIR}")
        False

        >>> contains_program_var("abc")
        False
    """
    return PROGRAM_VAR_REF_REGEX.search(value) is not None


def replace_program_vars(value: str, program_vars: Dict[str, str]) -> str:
    """
    替换字符串中的项目变量。

    Args:
        value:
            待替换字符串
        program_vars:
            项目变量字典

    Returns:
        替换后的字符串

    Raises:
        ValueError:
            引用了未定义项目变量。

    Examples:

        >>> vars = {
        ...     "PRO_OUTPUT_DIR": "./export",
        ...     "PRO_PROJECT_DIR": "/root/project",
        ... }

        >>> replace_program_vars("${PRO_OUTPUT_DIR}", vars)
        './export'

        >>> replace_program_vars("${PRO_PROJECT_DIR}/logs", vars)
        '/root/project/logs'

        >>> replace_program_vars("abc", vars)
        'abc'
    """

    def replace(match: re.Match) -> str:
        name = match.group("name")

        # 延迟型变量未提供时原样保留占位符，交由运行期二次替换
        if name in DEFERRED_PROGRAM_VARS and name not in program_vars:
            return match.group(0)

        if name not in program_vars:
            raise ValueError(f"未定义项目变量：{name}")

        return program_vars[name]

    return PROGRAM_VAR_REF_REGEX.sub(replace, value)


if __name__ == "__main__":
    print("=" * 70)
    print("测试 pro_var.py")
    print("=" * 70)

    program_vars = {
        "PRO_OUTPUT_DIR": "./export",
        "PRO_PROJECT_DIR": "/home/project",
        "PRO_SITE": "Amazon",
    }

    # ------------------------------------------------------------
    # 测试 contains_program_var()
    # ------------------------------------------------------------

    print("\n测试 contains_program_var()")
    print("-" * 70)

    tests = [
        "${PRO_OUTPUT_DIR}",
        "abc ${PRO_PROJECT_DIR}",
        "${PRO_SITE}",
        "${OUTPUT_DIR}",
        "${SITE_NAME}",
        "abc",
        "",
    ]

    for item in tests:
        print(f"{item!r}")
        print(f"=> {contains_program_var(item)}")

    # ------------------------------------------------------------
    # 测试 replace_program_vars()
    # ------------------------------------------------------------

    print("\n测试 replace_program_vars()")
    print("-" * 70)

    tests = [
        "${PRO_OUTPUT_DIR}",
        "${PRO_PROJECT_DIR}/logs",
        "${PRO_SITE}",
        "abc",
        "${PRO_NOT_FOUND}",
    ]

    for item in tests:
        try:
            print(item)
            print("=>", replace_program_vars(item, program_vars))

        except Exception as e:
            print("异常：", e)
