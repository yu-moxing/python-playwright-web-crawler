"""
Unit 处理过滤器。

职责：
    - 对 UnitNodeConfig 进行运行时判断
    - 判断是否存在 CSS/XPath 选择器
    - 判断 CSS/XPath 的使用优先级
    - 判断 Unit 是否真正启用

说明：
    UnitFilter 不保存 Unit 配置数据。
    Unit 配置统一由 UnitNodeConfig 表示。
"""

from config.model.node.unit_node_config import UnitNodeConfig


class UnitFilter:
    """
    单元过滤器。

    CSS 优先，XPath 次之。
    只有 child_filter 不为空时，
    后续提取阶段才真正启用。
    """

    def __init__(self, config: UnitNodeConfig):
        self.config = config

    def has_selector(self) -> bool:
        """是否存在 CSS/XPath 选择器。"""
        return bool(self.config.css or self.config.xpath)

    def use_css(self) -> bool:
        """优先CSS"""
        return bool(self.config.css)

    def use_xpath(self) -> bool:
        """是否使用 XPath。"""
        return not self.config.css and bool(self.config.xpath)

    def is_enable(self) -> bool:
        """
        是否真正启用。

        必须满足：

        ① CSS/XPath 至少有一个
        ② child_filter 非空
        """
        return self.has_selector() and bool(self.config.all_child_node_list)
