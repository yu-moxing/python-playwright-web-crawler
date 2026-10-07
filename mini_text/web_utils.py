"""
URL 请求工具模块
提供多种方式获取网页内容
"""

import logging
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 配置日志
logger = logging.getLogger(__name__)


class WebRequestError(Exception):
    """网页请求异常"""

    pass


def _clean_url(url: str) -> str:
    """
    清理 URL，移除 >> 或 > 后面的内容

    Args:
        url: 原始 URL

    Returns:
        清理后的 URL

    Examples:
        >>> _clean_url("http://example.com>>extra")
        'http://example.com'
    """
    # 移除 >> 或 > 后面的内容
    for separator in [">>", ">"]:
        if separator in url:
            url = url.split(separator)[0]
    return url


def get_url_text(url: str, encoding: Optional[str] = None) -> str:
    """
    获取网页文本内容（简单请求）

    Args:
        url: 网页 URL
        encoding: 编码，默认自动检测或使用 GBK

    Returns:
        网页文本内容，请求失败返回空字符串

    Examples:
        >>> html = get_url_text("http://example.com", encoding="utf-8")
    """
    clean_url = _clean_url(url)
    use_encoding = encoding if encoding else "GBK"

    try:
        with urlopen(clean_url, timeout=30) as response:
            content = response.read()

            # 尝试解码
            try:
                return content.decode(use_encoding)
            except UnicodeDecodeError:
                # 如果指定编码失败，尝试 UTF-8
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    # 使用 response 的编码信息
                    charset = response.headers.get_content_charset() or "utf-8"
                    return content.decode(charset, errors="ignore")

    except HTTPError as e:
        logger.error(f"HTTP 错误: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        logger.error(f"URL 错误: {e.reason}")
        return ""
    except Exception as e:
        logger.error(f"请求失败: {e}")
        return ""


def get_url_text_with_user_agent(url: str, user_agent: Optional[str] = None, encoding: Optional[str] = None) -> str:
    """
    使用自定义 User-Agent 获取网页内容

    Args:
        url: 网页 URL
        user_agent: User-Agent 字符串，默认使用 IE
        encoding: 编码，默认自动检测

    Returns:
        网页文本内容，请求失败返回空字符串

    Examples:
        >>> html = get_url_text_with_user_agent(
        ...     "http://example.com",
        ...     user_agent="Mozilla/5.0 ..."
        ... )
    """
    clean_url = _clean_url(url)
    use_encoding = encoding if encoding else "utf-8"

    # 默认 User-Agent
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ua = user_agent if user_agent else default_ua

    try:
        request = Request(clean_url)
        request.add_header("User-Agent", ua)

        with urlopen(request, timeout=30) as response:
            content = response.read()

            # 智能解码
            charset = response.headers.get_content_charset()
            if charset:
                return content.decode(charset, errors="ignore")

            # 尝试常见编码
            for enc in [use_encoding, "utf-8", "gbk", "gb2312"]:
                try:
                    return content.decode(enc)
                except UnicodeDecodeError:
                    continue

            return content.decode("utf-8", errors="ignore")

    except HTTPError as e:
        logger.error(f"HTTP 错误: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        logger.error(f"URL 错误: {e.reason}")
        return ""
    except Exception as e:
        logger.error(f"请求失败: {e}")
        return ""


def get_url_text_with_referer(
    url: str,
    referer: Optional[str] = None,
    user_agent: Optional[str] = None,
    encoding: Optional[str] = None,
) -> str:
    """
    使用伪造的 Referer 获取网页内容

    Args:
        url: 网页 URL
        referer: Referer 字符串
        user_agent: User-Agent 字符串
        encoding: 编码

    Returns:
        网页文本内容

    Examples:
        >>> html = get_url_text_with_referer(
        ...     "http://example.com",
        ...     referer="http://referrer.com"
        ... )
    """
    clean_url = _clean_url(url)
    use_encoding = encoding if encoding else "utf-8"

    # 默认 User-Agent 和 Referer
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ua = user_agent if user_agent else default_ua

    try:
        request = Request(clean_url)
        request.add_header("User-Agent", ua)

        if referer:
            request.add_header("Referer", referer)

        with urlopen(request, timeout=30) as response:
            content = response.read()

            # 智能解码
            charset = response.headers.get_content_charset()
            if charset:
                return content.decode(charset, errors="ignore")

            for enc in [use_encoding, "utf-8", "gbk"]:
                try:
                    return content.decode(enc)
                except UnicodeDecodeError:
                    continue

            return content.decode("utf-8", errors="ignore")

    except HTTPError as e:
        logger.error(f"HTTP 错误: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        logger.error(f"URL 错误: {e.reason}")
        return ""
    except Exception as e:
        logger.error(f"请求失败: {e}")
        return ""


def get_url_text_with_js(
    url: str,
    timeout: int = 30,
    wait_time: int = 3,
    browser: str = "chrome",
    headless: bool = True,
) -> str:
    """
    获取执行 JavaScript 后的网页内容（使用 Playwright）

    需要安装: pip install playwright && playwright install

    Args:
        url: 网页 URL
        timeout: 超时时间（秒）
        wait_time: 等待 JS 执行的时间（秒）
        browser: 浏览器类型 ('chrome', 'firefox', 'webkit')
        headless: 是否使用无头模式

    Returns:
        执行 JS 后的网页 HTML 内容

    Raises:
        ImportError: 未安装 playwright
        Exception: 其他异常

    Examples:
        >>> html = get_url_text_with_js("http://example.com", wait_time=5)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("未安装 playwright，请运行: pip install playwright && playwright install")
        raise ImportError("需要安装 playwright: pip install playwright && playwright install")

    clean_url = _clean_url(url)

    try:
        with sync_playwright() as p:
            # 选择浏览器
            browser_launcher = {
                "chrome": p.chromium,
                "firefox": p.firefox,
                "webkit": p.webkit,
            }.get(browser, p.chromium)

            browser = browser_launcher.launch(headless=headless)
            page = browser.new_page()

            # 设置超时
            page.set_default_timeout(timeout * 1000)

            # 访问页面
            page.goto(clean_url)

            # 等待 JS 执行
            logger.info(f"等待 JS 执行 {wait_time} 秒...")
            time.sleep(wait_time)

            # 获取 HTML
            html_content = page.content()

            browser.close()

            return html_content

    except Exception as e:
        logger.error(f"获取 JS 渲染页面失败: {e}")
        return ""


def get_url_text_with_selenium(
    url: str,
    timeout: int = 30,
    wait_time: int = 3,
    browser: str = "chrome",
    headless: bool = True,
) -> str:
    """
    使用 Selenium 获取执行 JavaScript 后的网页内容

    需要安装: pip install selenium
    并下载对应浏览器驱动

    Args:
        url: 网页 URL
        timeout: 超时时间（秒）
        wait_time: 等待 JS 执行的时间（秒）
        browser: 浏览器类型 ('chrome', 'firefox')
        headless: 是否使用无头模式

    Returns:
        执行 JS 后的网页 HTML 内容

    Examples:
        >>> html = get_url_text_with_selenium("http://example.com")
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
    except ImportError:
        logger.error("未安装 selenium，请运行: pip install selenium")
        raise ImportError("需要安装 selenium: pip install selenium")

    clean_url = _clean_url(url)

    driver = None
    try:
        # 配置浏览器
        if browser == "chrome":
            options = ChromeOptions()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=options)
        else:  # firefox
            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)

        # 设置超时
        driver.set_page_load_timeout(timeout)

        # 访问页面
        driver.get(clean_url)

        # 等待 JS 执行
        logger.info(f"等待 JS 执行 {wait_time} 秒...")
        time.sleep(wait_time)

        # 获取 HTML
        html_content = driver.page_source

        return html_content

    except Exception as e:
        logger.error(f"Selenium 获取页面失败: {e}")
        return ""
    finally:
        if driver:
            driver.quit()
