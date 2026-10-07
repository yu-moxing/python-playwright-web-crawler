"""
Selector Parser（Playwright 原语层）

只负责低层 DOM 操作：定位元素 + 取值（文本 / 属性）。
不负责 _CSS/_XPATH 优先级、_ATTR 空值判定、_REGEX 二次处理等流程逻辑
（由 field_extractor.FieldExtractor 负责）。

选择器约定（Playwright 原生）：
    - CSS：直接传，如 '.third_level a'
    - XPath：带 'xpath=' 前缀，如 'xpath=//a[@class="x"]'

取值约定：
    - attr 非空：取该属性（如 'href'）
    - attr 为空：取元素文本（all_inner_texts）
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class SelectorParser:
    """Playwright 选择器原语"""

    async def extract_values(
        self,
        page,
        selector: str,
        attr: str = "",
    ) -> List[str]:
        """
        根据选择器定位元素并取值

        Args:
            page: Playwright Page 对象（async API）
            selector: Playwright 原生选择器。CSS 直传；XPath 传 'xpath=...'
            attr: 属性名。非空则取该属性，为空则取元素文本

        Returns:
            取值列表；定位/取值异常时返回空列表
        """
        if not selector:
            return []

        try:
            locator = page.locator(selector)
            if attr:
                return await self._get_attributes(locator, attr)
            return await locator.all_inner_texts()
        except Exception:
            logger.exception("选择器取值失败：selector=%s, attr=%s", selector, attr)
            return []

    async def _get_attributes_old(self, locator, attr: str) -> List[str]:
        """
        对所有匹配元素取指定属性

        通过 evaluate_all 注入 JS 调用 getAttribute。
        """
        js = f'els => els.map(e => e.getAttribute("{attr}"))'
        return await locator.evaluate_all(js)

    async def _get_attributes(self, locator, attr: str) -> List[str]:
        """
        对所有匹配元素取指定属性。

        通过 evaluate_all 注入 JS 调用 getAttribute。
        属性不存在时使用空字符串，保持与元素顺序一致。
        此版函数：null → ""，绝不删除元素
        """
        js = f'els => els.map(e => e.getAttribute("{attr}") ?? "")'
        return await locator.evaluate_all(js)
