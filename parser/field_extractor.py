"""
字段提取器（流程层）

统一处理 _CSS / _XPATH / _ATTR / _REGEX 四后缀的元素提取流程：

    第一步 定位（Selector）：
        优先 _CSS，为空则 _XPATH；两者皆空表示不提取该元素，返回 []。
    第二步 取值（Extractor）：
        _ATTR 非空 → 取该属性；_ATTR 为空 → 取元素文本。
    第三步 正则（Regex）：
        _REGEX 非空 → 对每个取值做 re.search 二次处理；
        有捕获组取 group(1)，无捕获组取 group(0)，不匹配保留原值。

底层 DOM 操作委托给 parser.selector_parser.SelectorParser。
"""

import logging
import re
from typing import List, Optional

from parser.selector_parser import SelectorParser

logger = logging.getLogger(__name__)


class FieldExtractor:
    """四后缀字段提取流程"""

    def __init__(self):
        self.selector_parser = SelectorParser()

    def _apply_if_regex_not_empty(
        self,
        values: List[str],
        regex: str,
    ) -> List[str]:
        if not regex:
            return values

        pattern = self._strip_regex_prefix(regex)

        if not pattern:
            return values

        return [self._apply_regex(value, pattern) for value in values]

    async def extract(
        self,
        element_region,
        css: str = "",
        xpath: str = "",
        attr: str = "",
        regex: str = "",
    ) -> List[str]:
        """
        在指定元素区域内提取字段值。

        根据 CSS / XPATH 在指定的元素区域内定位元素，
        并提取属性值或元素文本，最后进行正则二次处理。

        Args:
            element_region:
                元素搜索区域。
                可以是 Playwright Page 或 Locator 对象。

                - Page：在整个页面范围内搜索。
                - Locator：在指定元素范围内搜索。

            css:
                CSS 选择器（纯选择器，不含 ::attr / ::text）。

            xpath:
                XPath 表达式（纯表达式，不含 /@attr）。

            attr:
                要提取的属性名；为空表示提取元素文本。

            regex:
                后处理正则；为空表示不进行二次处理。

        Returns:
            提取结果列表。
        """

        # 第一步：定位选择器
        # 优先 CSS，其次 XPATH；两者都为空则不提取。
        selector = self._pick_selector(css, xpath)

        if not selector:
            return []

        # 第二步：在指定的 element_region 范围内定位元素并取值
        # 根据 attr 决定提取属性值还是元素文本。
        values = await self.selector_parser.extract_values(
            element_region,
            selector,
            attr,
        )

        # 第三步：对提取结果进行正则二次处理
        return self._apply_if_regex_not_empty(values, regex)

    def extract_regex(
        self,
        values: List[str],
        regex: str,
    ) -> List[str]:
        """
        对字段值列表执行正则提取。

        Args:
            values: 字段值列表。
            regex: 正则表达式。

        Returns:
            正则提取后的字段值列表。
        """
        return self._apply_if_regex_not_empty(values, regex)

    def _pick_selector(self, css: str, xpath: str) -> Optional[str]:
        """
        选择定位选择器：优先 CSS，为空则 XPATH（带 xpath= 前缀），皆空返回 None
        """
        if css:
            return css
        if xpath:
            return f"xpath={xpath}"
        return None

    def _strip_regex_prefix(self, regex: str) -> str:
        """
        剥离 'regex:' 前缀（兼容历史配置值，如 'regex:list-([A-Z]+)-'）
        """
        if regex.startswith("regex:"):
            return regex[len("regex:") :]
        return regex

    def _apply_regex(self, text: str, pattern: str) -> str:
        """
        对单个取值做正则二次处理

        有捕获组取 group(1)，无捕获组取 group(0)，不匹配保留原值。
        """
        match = re.search(pattern, text)
        if not match:
            return text
        if match.groups():
            return match.group(1)
        return match.group(0)
