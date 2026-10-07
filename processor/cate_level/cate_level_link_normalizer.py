"""
分类层级链接 URL 标准化模块

职责：

- 将原始 href 转换为绝对 URL
- 过滤明显不是页面导航的 href
- 对 URL 做基础标准化

本模块不负责：

- 页面 DOM 元素提取
- CSS / XPath 定位
- URL 去重
- 正则匹配
- 产品链接业务过滤
- 分类链接业务过滤
- 分类层级判断
- floor 规则
- 分类名称提取
- CateLevelItem 构建
- 页面导航

说明：

本模块只处理“原始 href → 标准化 URL”。

页面中的 href 如何获取，由 CateLevelParser 根据
CATE_LEVEL_X_LINK_CSS / XPATH / ATTR 配置负责。

Java 原版 readAllLink() 中的通用 URL 处理逻辑，
在 Python 版中集中放在这里。

Java 原版中的业务逻辑，例如：

- needLowerCase
- needFilterProductLink
- needFilterSubStringLink
- needFilterTypeLink
- needProductLinkAddStr
- needTypeLinkAddStr
- strRegex_1

不在本模块处理。

其中：

- 分类链接业务规则由 CateLevelLinkBuilder 负责。
- URL 去重由 DuplicateChecker 负责。
"""

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse


@dataclass(frozen=True)
class NormalizedLink:
    """
    标准化后的分类链接。

    Attributes:
        url:
            标准化后的绝对 URL。
    """

    url: str


class CateLevelLinkNormalizer:
    """
    分类层级链接 URL 标准化器。

    负责：

        原始 href
            ↓
        过滤明显无效 href
            ↓
        相对 URL → 绝对 URL
            ↓
        检查 HTTP / HTTPS
            ↓
        去除 fragment
            ↓
        NormalizedLink

    本类不负责：

        - DOM 元素提取
        - CSS / XPath 定位
        - 链接文本提取
        - URL 去重
        - 分类业务规则
    """

    @staticmethod
    def normalize(
        href: str,
        base_url: str,
    ) -> NormalizedLink | None:
        """
        标准化单个 href。

        Args:
            href:
                从页面指定元素中提取出的原始 href。

            base_url:
                当前页面 URL。
                用于将相对 URL 转换为绝对 URL。

        Returns:
            NormalizedLink:
                标准化成功。

            None:
                href 不属于有效页面链接。
        """

        if not href:
            return None

        href = href.strip()

        if not href:
            return None

        # 过滤明显不是页面导航的 href。
        if CateLevelLinkNormalizer._is_non_navigation_href(href):
            return None

        # 相对 URL → 绝对 URL。
        url = urljoin(base_url, href)

        # URL 基础标准化。
        url = CateLevelLinkNormalizer._normalize_url(url)

        if not url:
            return None

        return NormalizedLink(url=url)

    @staticmethod
    def _is_non_navigation_href(href: str) -> bool:
        """
        判断 href 是否明显不是普通页面导航链接。

        当前排除：

        - #xxx
        - javascript:
        - mailto:
        - tel:
        - data:

        注意：

        这里属于“明显无效链接类型”过滤，
        不属于分类业务过滤。
        """

        value = href.strip().lower()

        if not value:
            return True

        # 页面内部锚点。
        if value.startswith("#"):
            return True

        # JavaScript 伪链接。
        if value.startswith("javascript:"):
            return True

        # 邮件链接。
        if value.startswith("mailto:"):
            return True

        # 电话链接。
        if value.startswith("tel:"):
            return True

        # Data URL。
        if value.startswith("data:"):
            return True

        return False

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        对 URL 做基础标准化。

        当前处理：

        - 去除 URL 前后的空白
        - 必须具有 scheme
        - 必须具有 netloc
        - 只允许 HTTP / HTTPS
        - URL path 中的非 ASCII 字符进行 UTF-8 percent-encoding
        - 保留已经存在的 percent-encoding，避免二次编码
        - 去除 fragment（#xxx）

        不处理：

        - query 参数删除
        - query 参数排序
        - URL 参数业务过滤
        - URL 大小写转换
        - URL 去重
        - 产品 / 分类 URL 业务规则
        """

        url = url.strip()

        if not url:
            return ""

        parsed = urlparse(url)

        # 必须具有协议和主机。
        if not parsed.scheme or not parsed.netloc:
            return ""

        scheme = parsed.scheme.lower()

        # 只接受 HTTP / HTTPS。
        if scheme not in {"http", "https"}:
            return ""

        # ---------------------------------------------------------
        # URL path 编码
        #
        # 例如：
        #
        # /襯衫-cat.11040766.11042303
        #
        # →
        #
        # /%E8%A5%AF%E8%A1%AB-cat.11040766.11042303
        #
        # safe="/"：
        #   保留 path 中的 /
        #
        # safe="%/"：
        #   保留已经存在的 %XX 编码，避免二次编码。
        # ---------------------------------------------------------

        from urllib.parse import quote

        encoded_path = quote(
            parsed.path,
            safe="/%",
            encoding="utf-8",
            errors="strict",
        )

        # Fragment 不参与页面 URL 判断。
        parsed = parsed._replace(
            path=encoded_path,
            fragment="",
        )

        return urlunparse(parsed)

    # _normalize_url_old 没考虑url中，带有：中文的情况。
    @staticmethod
    def _normalize_url_old(url: str) -> str:
        """
        对 URL 做基础标准化。

        当前处理：

        - 去除 URL 前后的空白
        - 必须具有 scheme
        - 必须具有 netloc
        - 只允许 HTTP / HTTPS
        - 去除 fragment（#xxx）

        不处理：

        - query 参数删除
        - query 参数排序
        - URL 参数业务过滤
        - URL 大小写转换
        - URL 去重
        - 产品 / 分类 URL 业务规则
        """

        url = url.strip()

        if not url:
            return ""

        parsed = urlparse(url)

        # 必须具有协议和主机。
        if not parsed.scheme or not parsed.netloc:
            return ""

        scheme = parsed.scheme.lower()

        # 只接受 HTTP / HTTPS。
        if scheme not in {"http", "https"}:
            return ""

        # Fragment 不参与页面 URL 判断。
        parsed = parsed._replace(fragment="")

        return urlunparse(parsed)
