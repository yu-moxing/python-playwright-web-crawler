"""
浏览器(BROWSER) 配置对象

本模块仅定义配置文件中 BROWSER_ 前缀对应的数据结构。

职责：
    - 保存浏览器采集控制配置
    - 对应 ScriptConfig 中 BROWSER_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class BrowserItem:
    """
    BROWSER 配置对象

    对应配置文件：

        BROWSER_ENABLE_PLAYWRIGHT
        BROWSER_ENABLE_VISIBLE_ACCESS
        BROWSER_SHOW_WINDOWS
        BROWSER_SIMULATE_MOUSE_KEYBOARD
        BROWSER_COOKIES_DOMAIN
        BROWSER_COOKIES_INJECT_USER_LOGGEDIN
        BROWSER_COOKIES_INJECT_USER_GUEST
        BROWSER_DEFAULT_LOAD_DELAY_RANGE_MS
        BROWSER_CATE_LEVEL_LOAD_DELAY_RANGE_MS
        BROWSER_CATE_LIST_LOAD_DELAY_RANGE_MS
        BROWSER_DETAIL_LOAD_DELAY_RANGE_MS
        BROWSER_DEFAULT_SCROLL_DURATION_RANGE_MS
        BROWSER_CATE_LEVEL_SCROLL_DURATION_RANGE_MS
        BROWSER_CATE_LIST_SCROLL_DURATION_RANGE_MS
        BROWSER_DETAIL_SCROLL_DURATION_RANGE_MS
        BROWSER_CATE_LIST_NEED_UPDATE_CONTENT
        BROWSER_CATE_LIST_CRAWL_MAX_PER_USER_RANGE
        BROWSER_CATE_LIST_CRAWL_MAX_PAGE_NO_ON_CATE_LEVEL_LINK_RANGE
        BROWSER_CATE_LIST_CRAWL_MAX_PER_CATE_LEVEL_LINK_ON_USER_RANGE

    开关类字段取值 0/1（int）；
    cookies_domain 为纯字符串，不做格式校验；
    cookies_inject_user_* 保留原始字符串，由
    browser_loader.validate_browser_config 调用
    parse_cookies_inject_pairs 校验 key1::value1,key2::value2 格式；
    载入延迟 / 滚动持续 / 采集上限字段均保留原始字符串，由
    browser_loader.validate_browser_config 统一调用
    validate_3f_positive_range_or_disabled 校验三格式
    （-1 禁用 / 正整数 / 数字1-数字2 范围），运行期再解析为 (min, max)。
    """

    # ========== 浏览器控制 ==========
    enable_playwright: int = 1
    enable_visible_access: int = 0
    show_windows: int = 1
    simulate_mouse_keyboard: int = 0

    # ========== 浏览器 Cookies 注入 ==========
    # cookies 注入域名（如 .shopee.tw），纯字符串，不做格式校验
    cookies_domain: str = ""
    # cookies 注入键值列表（原始字符串）
    # 格式：key1::value1,key2::value2；可空；由 parse_cookies_inject_pairs 解析
    cookies_inject_user_loggedin: str = ""
    cookies_inject_user_guest: str = ""

    # ========== 载入延迟时间范围（原始字符串，单位：毫秒） ==========
    # 各层页面载入后的延迟；default 为回退值
    default_load_delay_range_ms: str = "-1"
    cate_level_load_delay_range_ms: str = "-1"
    cate_list_load_delay_range_ms: str = "-1"
    detail_load_delay_range_ms: str = "-1"

    # ========== 滚动持续时间范围（原始字符串，单位：毫秒） ==========
    # 各层页面滚动持续时长；default 为回退值
    default_scroll_duration_range_ms: str = "-1"
    cate_level_scroll_duration_range_ms: str = "-1"
    cate_list_scroll_duration_range_ms: str = "-1"
    detail_scroll_duration_range_ms: str = "-1"

    # ========== 已存在数据是否更新 ==========
    cate_list_need_update_content: int = 0

    # ========== 采集链接数、翻页数限制（原始字符串，三格式） ==========
    # -1 不限制；正整数固定值；数字1-数字2 随机范围
    cate_list_crawl_max_per_user_range: str = "-1"
    cate_list_crawl_max_page_no_on_cate_level_link_range: str = "-1"
    cate_list_crawl_max_per_cate_level_link_on_user_range: str = "-1"
