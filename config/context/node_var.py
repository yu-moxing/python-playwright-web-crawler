"""
节点变量（Node variables）

作用：

    识别、校验、管理、替换字符串中的节点变量引用。

节点变量格式：

    #{NODE_CATE_LIST_COMMON_ID}

说明：

    1. 节点变量必须以 NODE_ 开头。

    2. 节点变量不能在脚本中定义。

    3. 节点变量只能出现在 *_COMBINE 配置值中，即只能被
       具有 _COMBINE 属性的节点引用；不能出现在 _CSS / _XPATH /
       _ATTR / _REGEX 等其它配置值中。

    4. 节点变量的值不由本模块从页面提取，也不由 Python 程序
       预先固定提供。节点变量的值来自已有配置节点经过原有
       _CSS / _XPATH / _ATTR / _REGEX 提取流程后得到的运行时值。
       本模块只负责：

           - 节点变量定义与允许清单；
           - 引用识别（正则）；
           - 合法性检查（格式 / 清单 / 页面层级）；
           - 变量值管理与替换。

       实际页面元素提取复用现有 FieldExtractor / 节点解析流程，
       本模块不重新实现提取逻辑。

    5. 节点变量属于运行时变量，生命周期限定在当前页面层级、
       当前记录上下文内。每次开始处理新的对应记录时，都必须
       重新初始化相关节点变量，不允许使用上一次页面、上一个
       商品、上一个 UNIT 或上一个采集上下文的残留值。

    6. 节点变量值为空列表与节点变量不存在是两种不同情况：
       - 节点变量存在，但原始节点没有提取到值：允许，值为 []；
       - 节点变量名不在允许清单中：不允许，必须报错。

    7. 节点变量必须遵守所属页面层级：
       - NODE_CATE_LIST_* 只允许在 CATE_LIST 页面的 _COMBINE 中使用；
       - NODE_DETAIL_*  只允许在 DETAIL  页面的 _COMBINE 中使用；
       - CATE_LEVEL 当前没有定义可用的节点变量；
       - 不允许跨页面层级引用节点变量。

示例：

    映射（左侧节点变量名 -> 右侧已有配置节点名）：

        NODE_CATE_LIST_COMMON_ID            -> CATE_LIST_COMMON_ID
        NODE_CATE_LIST_COMMON_SUB_OWNER_ID  -> CATE_LIST_COMMON_SUB_OWNER_ID
        NODE_CATE_LIST_COMMON_MAIN_OWNER_ID -> CATE_LIST_COMMON_MAIN_OWNER_ID
        NODE_DETAIL_COMMON_MAIN_OWNER_ID    -> DETAIL_COMMON_MAIN_OWNER_ID
        NODE_DETAIL_COMMON_SUB_OWNER_ID     -> DETAIL_COMMON_SUB_OWNER_ID

    替换：

        node_vars = {
            "NODE_CATE_LIST_COMMON_ID": ["22713932092"],
            "NODE_CATE_LIST_COMMON_MAIN_OWNER_ID": ["925674003"],
        }

        replace_node_vars(
            "https://shopee.tw/product/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}/#{NODE_CATE_LIST_COMMON_ID}",
            node_vars,
            layer="CATE_LIST",
        )
        => ["https://shopee.tw/product/925674003/22713932092"]
"""

import re
from typing import Dict, Optional

# ==========================================================
# 节点变量映射与允许清单
# ==========================================================

# 左侧 = 节点变量名（NODE_ 前缀），右侧 = 已有配置节点名（NormalNodeConfig.node_name）。
# 右侧不是普通字符串值，而是一个已有配置节点：程序按该节点的
# _CSS / _XPATH / _ATTR / _REGEX 规则提取值，再赋值给左侧节点变量。
NODE_VARIABLE_NODE_MAP: Dict[str, str] = {
    "NODE_CATE_LIST_COMMON_ID": "CATE_LIST_COMMON_ID",
    "NODE_CATE_LIST_COMMON_SUB_OWNER_ID": "CATE_LIST_COMMON_SUB_OWNER_ID",
    "NODE_CATE_LIST_COMMON_MAIN_OWNER_ID": "CATE_LIST_COMMON_MAIN_OWNER_ID",
    "NODE_DETAIL_COMMON_MAIN_OWNER_ID": "DETAIL_COMMON_MAIN_OWNER_ID",
    "NODE_DETAIL_COMMON_SUB_OWNER_ID": "DETAIL_COMMON_SUB_OWNER_ID",
}

# 允许的节点变量名清单。不在该清单中的 NODE_ 名称一律视为非法。
SUPPORTED_NODE_VARIABLES = frozenset(NODE_VARIABLE_NODE_MAP)

# 反向映射：已有配置节点名 -> 节点变量名。
# 供提取阶段把原始节点提取结果同步赋值给对应节点变量使用。
NODE_TO_NODE_VAR: Dict[str, str] = {v: k for k, v in NODE_VARIABLE_NODE_MAP.items()}

# 节点变量所属页面层级。用于阻止跨页面层级引用。
NODE_VAR_LAYER: Dict[str, str] = {
    "NODE_CATE_LIST_COMMON_ID": "CATE_LIST",
    "NODE_CATE_LIST_COMMON_SUB_OWNER_ID": "CATE_LIST",
    "NODE_CATE_LIST_COMMON_MAIN_OWNER_ID": "CATE_LIST",
    "NODE_DETAIL_COMMON_MAIN_OWNER_ID": "DETAIL",
    "NODE_DETAIL_COMMON_SUB_OWNER_ID": "DETAIL",
}


# ==========================================================
# 节点变量引用正则
# ==========================================================

# 注意：正则只能识别格式正确的节点变量引用，不能代替允许清单检查。
# 例如 #{NODE_UNKNOWN_ID} 虽然符合正则格式，但不属于允许清单，
# 仍必须报错。
NODE_VAR_REF_REGEX = re.compile(r"#\{(?P<name>NODE_[A-Za-z_][A-Za-z0-9_]*)\}")


# ==========================================================
# 节点变量字典构造
# ==========================================================
def build_node_vars() -> dict[str, list[str]]:
    """
    创建节点变量字典。

    所有允许使用的 NODE 变量都会初始化为空列表。
    空列表表示变量存在，但当前没有提取到值。

    Returns:
        {节点变量名: []}，覆盖全部允许变量。
    """
    return {name: [] for name in SUPPORTED_NODE_VARIABLES}


# ==========================================================
# 识别
# ==========================================================


def contains_node_var(value: str) -> bool:
    """
    判断字符串是否包含节点变量引用。

    Args:
        value: 待检查字符串

    Returns:
        True 表示包含节点变量，否则 False

    Examples:
        >>> contains_node_var("#{NODE_CATE_LIST_COMMON_ID}")
        True

        >>> contains_node_var(
        ...     "https://shopee.tw/product/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}/#{NODE_CATE_LIST_COMMON_ID}"
        ... )
        True

        >>> contains_node_var("https://shopee.tw/home")
        False
    """
    return NODE_VAR_REF_REGEX.search(value) is not None


def node_var_for_node_name(node_name: str) -> Optional[str]:
    """
    由已有配置节点名反查对应的节点变量名。

    供提取阶段判断某个 NormalNodeConfig 是否是节点变量的源节点：
    若返回非 None，则该节点提取结果应同步写入对应的 NODE_ 变量。

    Args:
        node_name: 已有配置节点名（NormalNodeConfig.node_name），
                   例如 "CATE_LIST_COMMON_ID"

    Returns:
        对应的节点变量名（例如 "NODE_CATE_LIST_COMMON_ID"），
        不在映射中时返回 None。
    """
    return NODE_TO_NODE_VAR.get(node_name)


# ==========================================================
# 合法性检查与替换
# ==========================================================


def _check_node_var(name: str, layer: str) -> None:
    """
    校验单个节点变量引用的合法性（清单 + 页面层级）。

    Args:
        name: 节点变量名（正则捕获组）
        layer: 当前页面层级，"CATE_LIST" / "DETAIL"

    Raises:
        ValueError:
            引用了未定义的节点变量（不在允许清单），
            或引用了其它页面层级的节点变量。
    """
    if name not in SUPPORTED_NODE_VARIABLES:
        raise ValueError(f"未定义节点变量：{name}")

    var_layer = NODE_VAR_LAYER[name]
    if var_layer != layer:
        raise ValueError(f"节点变量 {name} 属于 {var_layer} 页面层级，不允许在 {layer} 页面层级的 _COMBINE 中使用")


def validate_node_var_refs(value: str, *, layer: str) -> None:
    """
    检查字符串中的节点变量引用是否合法（格式已由正则保证）。

    仅做清单与页面层级校验，不替换。可供解析期或运行期前置预检。

    Args:
        value: 待检查字符串
        layer: 当前页面层级，"CATE_LIST" / "DETAIL"

    Raises:
        ValueError:
            引用了未定义节点变量，或引用了其它页面层级的节点变量。
    """
    for match in NODE_VAR_REF_REGEX.finditer(value):
        _check_node_var(match.group("name"), layer)


def replace_node_vars(
    value: str,
    node_vars: dict[str, list[str]],
    *,
    layer: str,
) -> list[str]:
    """
    替换字符串中的 NODE 变量。

    节点变量的值统一为 list[str]。

    Args:
        value: 待替换字符串。
        node_vars: 节点变量字典。
            值统一为 list[str]。
        layer: 当前页面层级，"CATE_LIST" / "DETAIL"。

    Returns:
        替换后的字符串列表。

        没有 NODE 变量引用时：
            "https://shopee.tw/home"
            -> ["https://shopee.tw/home"]

        一个 NODE 变量有多个值时：
            "/shop/#{NODE_A}"
            NODE_A = ["100", "200"]
            -> ["/shop/100", "/shop/200"]

        多个 NODE 变量有多个值时，进行组合展开：

            "/shop/#{NODE_A}/#{NODE_B}"

            NODE_A = ["100", "200"]
            NODE_B = ["aaa", "bbb"]

            -> [
                "/shop/100/aaa",
                "/shop/100/bbb",
                "/shop/200/aaa",
                "/shop/200/bbb",
            ]

        任意一个被引用的 NODE 变量值为空列表时：
            -> []

    Raises:
        ValueError:
            引用了未定义节点变量，
            或引用了其它页面层级的节点变量。
    """
    matches = list(NODE_VAR_REF_REGEX.finditer(value))

    # 没有 NODE 变量引用。
    # 为了保证返回类型始终是 list[str]，直接返回单元素列表。
    if not matches:
        return [value]

    # 保存每个 NODE 变量前后的固定文本。
    #
    # 例如：
    #
    #   "/shop/#{NODE_A}/item_detail/#{NODE_B}"
    #
    # 最终得到：
    #
    #   fragments[0] = "/shop/"
    #   fragments[1] = "/item_detail/"
    #   fragments[2] = ""
    fragments: list[str] = []

    # 保存每个 NODE 变量对应的值列表。
    variable_values: list[list[str]] = []

    last_end = 0

    for match in matches:
        # 当前 NODE 变量之前的固定文本。
        fragments.append(value[last_end : match.start()])

        name = match.group("name")

        # 校验：
        # 1. 是否是允许的 NODE 变量；
        # 2. 是否属于当前页面层级。
        _check_node_var(name, layer)

        values = node_vars[name]

        # 节点变量存在，但没有提取到值。
        # 不生成任何组合结果。
        if not values:
            return []

        variable_values.append(values)

        last_end = match.end()

    # 最后一个 NODE 变量之后的固定文本。
    fragments.append(value[last_end:])

    # 初始结果从第一个固定文本开始。
    results: list[str] = [fragments[0]]

    # 逐个 NODE 变量展开。
    #
    # 每展开一个变量，就把当前已有结果与该变量的所有值进行组合。
    # 因此多个多值变量会自然形成笛卡尔积。
    for index, values in enumerate(variable_values):
        next_results: list[str] = []

        for result in results:
            for variable_value in values:
                next_results.append(result + variable_value + fragments[index + 1])

        results = next_results

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("测试 node_var.py")
    print("=" * 70)

    node_vars = build_node_vars()
    # node_vars["NODE_CATE_LIST_COMMON_ID"] = "22713932092"
    # node_vars["NODE_CATE_LIST_COMMON_MAIN_OWNER_ID"] = "925674003"
    node_vars["NODE_CATE_LIST_COMMON_ID"] = ["22713932092"]
    node_vars["NODE_CATE_LIST_COMMON_MAIN_OWNER_ID"] = ["925674003"]

    # ------------------------------------------------------------
    # 测试 build_node_vars()
    # ------------------------------------------------------------
    print("\n测试 build_node_vars()")
    print("-" * 70)
    fresh = build_node_vars()
    print("键数:", len(fresh))
    # print("全部为空:", all(v == "" for v in fresh.values()))
    print("全部为空:", all(v == [] for v in fresh.values()))
    print("键集合:", sorted(fresh.keys()))

    # ------------------------------------------------------------
    # 测试 contains_node_var()
    # ------------------------------------------------------------
    print("\n测试 contains_node_var()")
    print("-" * 70)
    for item in [
        "#{NODE_CATE_LIST_COMMON_ID}",
        "https://shopee.tw/product/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}/#{NODE_CATE_LIST_COMMON_ID}",
        "https://shopee.tw/home",
        "",
        "#{AREA_CATE_LIST_COMMON_ID}",
    ]:
        print(f"{item!r} => {contains_node_var(item)}")

    # ------------------------------------------------------------
    # 测试 replace_node_vars() 多值展开
    # ------------------------------------------------------------
    print("\n测试 replace_node_vars() 多值展开")
    print("-" * 70)

    multi_node_vars = build_node_vars()
    multi_node_vars["NODE_CATE_LIST_COMMON_ID"] = [
        "100",
        "200",
    ]
    multi_node_vars["NODE_CATE_LIST_COMMON_MAIN_OWNER_ID"] = [
        "900",
        "901",
    ]

    print(
        replace_node_vars(
            "https://shopee.tw/product/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}/#{NODE_CATE_LIST_COMMON_ID}",
            multi_node_vars,
            layer="CATE_LIST",
        )
    )

    # ------------------------------------------------------------
    # 测试 replace_node_vars()
    # ------------------------------------------------------------
    print("\n测试 replace_node_vars()")
    print("-" * 70)
    cases = [
        "https://shopee.tw/product/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}/#{NODE_CATE_LIST_COMMON_ID}",
        "https://shopee.tw/shop/#{NODE_CATE_LIST_COMMON_MAIN_OWNER_ID}",
        "https://shopee.tw/home",
        "#{NODE_CATE_LIST_COMMON_ID}",  # 值非空
        "#{NODE_CATE_LIST_COMMON_SUB_OWNER_ID}",  # 值为空列表，应返回 []
        "https://shopee.tw/product/#{NODE_UNKNOWN_ID}/#{NODE_CATE_LIST_COMMON_ID}",  # 未知变量
        "https://shopee.tw/product/#{NODE_PRODUCT_TITLE}",  # 不允许的 NODE_
        "https://shopee.tw/product/#{NODE_DETAIL_COMMON_MAIN_OWNER_ID}",  # 跨页面层级
    ]
    for item in cases:
        try:
            print(item)
            print("=>", replace_node_vars(item, node_vars, layer="CATE_LIST"))
        except Exception as e:
            print("异常：", e)

    # ------------------------------------------------------------
    # 测试 node_var_for_node_name()
    # ------------------------------------------------------------
    print("\n测试 node_var_for_node_name()")
    print("-" * 70)
    for nm in [
        "CATE_LIST_COMMON_ID",
        "CATE_LIST_COMMON_MAIN_OWNER_ID",
        "CATE_LIST_COMMON_SUB_OWNER_ID",
        "DETAIL_COMMON_MAIN_OWNER_ID",
        "DETAIL_COMMON_SUB_OWNER_ID",
        "CATE_LIST_COMMON_LINK",
        "NODE_CATE_LIST_COMMON_ID",
    ]:
        print(f"{nm} => {node_var_for_node_name(nm)}")

    # ------------------------------------------------------------
    # 测试 DETAIL 层（跨层反向）
    # ------------------------------------------------------------
    print("\n测试 DETAIL 层 replace_node_vars()")
    print("-" * 70)
    detail_vars = build_node_vars()
    # detail_vars["NODE_DETAIL_COMMON_MAIN_OWNER_ID"] = "123456"
    detail_vars["NODE_DETAIL_COMMON_MAIN_OWNER_ID"] = ["123456"]
    try:
        print(
            replace_node_vars(
                "https://shopee.tw/shop/#{NODE_DETAIL_COMMON_MAIN_OWNER_ID}",
                detail_vars,
                layer="DETAIL",
            )
        )
        # DETAIL 层引用 CATE_LIST 变量应报错
        replace_node_vars(
            "https://shopee.tw/#{NODE_CATE_LIST_COMMON_ID}",
            detail_vars,
            layer="DETAIL",
        )
    except Exception as e:
        print("跨层异常：", e)
