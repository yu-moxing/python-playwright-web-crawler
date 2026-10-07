# normal_node_config.py

from dataclasses import dataclass


@dataclass(slots=True)
class NormalNodeConfig:
    node_name: str = ""
    node_type: str = ""

    # 当父节点的 _CHILD_BLOCK 值为 0 时，才设置 father_css 、 father_xpath 、father_child_max_count  的值
    # 当前节点的父级搜索范围
    father_css: str = ""
    father_xpath: str = ""
    father_child_max_count: int = -1

    # 当前节点本身怎么找
    css: str = ""
    xpath: str = ""
    attr: str = ""
    regex: str = ""

    # 分类 ID 提取规则（_ID_REGEX 后缀，CATE_LEVEL 的 LINK 节点使用）
    id_regex: str = ""

    # 链接拼接模板（_COMBINE 后缀）
    # 非空时，该字段的值由此模板与其它已提取字段拼接生成，而非从页面节点提取。
    # 运行期消费（替换 ${PRO_COMMON_*} 等占位符）由 parser/processor 负责。
    combine: str = ""

    # 是否已解析。默认：False 。解释过后，此值才是：True。此字段防止重复解析（）
    # 当父节点的 _CHILD_BLOCK 值为 1，是在父节点提取后的列表里提取。而不是自己单独提取
    is_parsed: bool = False
    # 是否激活：定位器。默认：False，只有：css 或 xpath 至少有一项取值不为空时，并且：combine 值为空 或无 combine属性 ，此值才是：True
    locator_enabled: bool = False
    # 是否激活：组合属性。默认：False，只有：存在combine属性且combine不为空时，并且：css 或 xpath 均为空，此值才是：True
    combine_enabled: bool = False
