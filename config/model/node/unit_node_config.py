# unit_node_config.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class UnitNodeConfig:
    node_name: str = ""
    node_type: str = ""

    css: str = ""
    xpath: str = ""

    child_block: int = 1
    child_max_count: int = -1

    all_child_node_list: list[str] = field(default_factory=list)
    enable_locator_child_node_list: list[str] = field(default_factory=list)
    enable_combine_child_node_list: list[str] = field(default_factory=list)

    # 是否激活：定位器。默认：False，只有：css 或 xpath 至少有一项取值不为空时，此值才是：True
    locator_enabled: bool = False
