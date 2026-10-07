"""
item_detail Processor

职责（流程编排层）：
    - create_context → 注入 cookie → new_page → login → crawl_item → 关闭

不负责：
    - CLI 参数解析 / 项目定位 / user_pool 读取 / id_i 解析（在 main 预备层）
    - item_list_link.txt 读取与索引选择（在 main 预备层，Processor 只接收已选 item_urls）
    - ResourceContext 构建（在 config/loader/item_detail/item_resource_loader.py）
    - script.txt 解析（已由 ItemDetailScriptConfig 传入）

cookie_domain / home_url / access_home_page / headless 来自 script_config。
ResourceContext 由 Runner 经 PageNavigator 传入。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, Page

from config.loader.item_detail.item_project_loader import ItemProjectConfig
from config.model.item_detail.item_detail_item import ItemDetailScriptConfig
from page.page_navigator import PageNavigator
from utils.value_utils import resolve_value_or_range

# ============================================================
# 延迟 / 滚动随机范围
# ============================================================
# cookie_domain / home_url / access_home_page / headless 已由 script.txt 提供。
# 浏览器 EXE / 用户目录 / 指纹 / 代理 / browser_type 已由 user_pool + 资源池提供
# （config/loader/item_detail/item_resource_loader.py）。
# 下面 4 个 range 常量后续按用户等级从 script_config.user_level_ranges 选取
# （§十四未列入删除清单，本阶段保留为扁平默认值）。

# HOME 延迟 / 滚动随机范围（后续按用户等级从 script_config 选取）
ITEM_HOME_LOAD_DELAY_RANGE_MS = "15000-42000"
ITEM_HOME_SCROLL_DURATION_RANGE_MS = "15000-42000"

# ITEM 延迟 / 滚动随机范围（后续按用户等级从 script_config 选取）
ITEM_LOAD_DELAY_RANGE_MS = "15000-42000"
ITEM_SCROLL_DURATION_RANGE_MS = "15000-42000"


# ============================================================
# Processor
# ============================================================


class ItemDetailProcessor:
    """
    item_detail 流程编排器。

    生命周期（run）：
        create_context → 注入 cookie → new_page → login → crawl_item → 关闭
    """

    def __init__(
        self,
        *,
        project_config: ItemProjectConfig,
        script_config: ItemDetailScriptConfig,
        item_urls: List[str],
        cookies_file_path: str,
        page_navigator: PageNavigator,
        logger: logging.Logger,
    ):
        self.project_config = project_config
        self.script_config = script_config
        self.item_urls = item_urls
        self.cookies_file_path = cookies_file_path
        self.page_navigator = page_navigator
        self.logger = logger

        self.browser_factory = page_navigator.browser_factory
        self.resource_context = page_navigator.resource_context

        self.page: Optional[Page] = None
        self._context: Optional[BrowserContext] = None

    async def run(self) -> None:
        """
        主流程：创建 context → 注入 cookie → 创建 page → login → crawl_item。
        finally 释放 page（browser_factory 由 Runner 释放）。
        """
        try:
            # 1. 创建 BrowserContext（内部完成 Playwright 启动、指纹 add_init_script）
            #    headless 取自 script_config
            self._context = await self.browser_factory.create_context(
                self.resource_context,
                headless=bool(self.script_config.headless),
            )

            # 2. 注入 Cookie（在 new_page 之前）
            await self._inject_cookies()

            # 3. 创建 Page
            self.page = await self._context.new_page()

            # 4. 访问首页（按 access_home_page）
            await self.login()

            # 5. 顺序访问 ITEM URL 列表
            await self.crawl_item()

        finally:
            # Processor 只负责关闭工作 Page；
            # BrowserSessionFactory 由 Runner 统一释放。
            if self.page is not None:
                try:
                    await self.page.close()
                except Exception:
                    self.logger.exception("关闭 Page 异常")
                self.page = None

            self._context = None

    # ------------------------------------------------------------------
    # Cookie 注入
    # ------------------------------------------------------------------

    async def _inject_cookies(self) -> None:
        """
        读取并解析 cookies.txt，在 new_page 之前注入。

        cookies.txt 可选（任务§24）：
            - 不存在 → 跳过注入
            - 为空 → 跳过注入
            - 有内容 → 解析并注入；解析完全失败 → 终止
        """
        cookie_domain = self.script_config.cookie_domain
        if not cookie_domain or not self.cookies_file_path:
            self.logger.info("未配置 Cookie，跳过注入")
            return

        if not os.path.exists(self.cookies_file_path):
            self.logger.info("Cookie 文件不存在，跳过注入：%s", self.cookies_file_path)
            return

        cookies = self._load_cookie_file()
        if not cookies:
            self.logger.warning("Cookie 解析结果为空，未注入：%s", self.cookies_file_path)
            return

        await self._context.add_cookies(cookies)
        self.logger.info(
            "Cookie 注入完成：数量=%d, domain=%s, file=%s",
            len(cookies),
            cookie_domain,
            self.cookies_file_path,
        )

    def _load_cookie_file(self) -> List[Dict[str, Any]]:
        """
        读取并解析 Cookie 文件，返回 Playwright add_cookies 所需的 dict 列表。

        支持两种格式：
          - 格式 A（JSON）：JSON 数组，或常见的 JSON 包装结构。
          - 格式 B（name=value;name=value）：单行分号分隔，domain 取 ITEM_COOKIE_DOMAIN。

        文件为空 → 返回空列表；非空但解析完全失败 → 终止。
        禁止将 cookie value 写入日志。
        """
        with open(self.cookies_file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            return []

        # 先尝试 JSON（含常见包装结构）
        cookies = self._try_parse_json_cookies(content)
        cookie_format = "JSON"

        # JSON 失败则兜底 name=value;name=value
        if cookies is None:
            cookies = self._parse_name_value_cookies(content)
            cookie_format = "name=value;"

        if not cookies:
            self.logger.error(
                "Cookie 解析完全失败（JSON 与 name=value; 均无法解析）：file=%s",
                self.cookies_file_path,
            )
            raise ValueError(f"Cookie 解析完全失败：{self.cookies_file_path}")

        self.logger.info(
            "Cookie 解析成功：格式=%s, 数量=%d, domain=%s",
            cookie_format,
            len(cookies),
            self.script_config.cookie_domain,
        )
        return cookies

    def _try_parse_json_cookies(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """
        尝试按 JSON 解析 Cookie。成功返回 list（可能为空），非 JSON 返回 None。
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None

        # dict 包装：尝试提取内含列表，或当作单条 cookie
        if isinstance(data, dict):
            extracted = None
            for key in ("cookies", "data", "list"):
                value = data.get(key)
                if isinstance(value, list):
                    extracted = value
                    break
            if extracted is None:
                if "name" in data and "value" in data:
                    extracted = [data]
                else:
                    return []
            data = extracted

        if not isinstance(data, list):
            return []

        result: List[Dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            value = str(item.get("value", "")).strip()
            if not name or not value:
                continue
            domain = str(item.get("domain", "")).strip() or self.script_config.cookie_domain
            path = str(item.get("path", "")).strip() or "/"
            result.append({"name": name, "value": value, "domain": domain, "path": path})

        return result

    def _parse_name_value_cookies(self, content: str) -> List[Dict[str, Any]]:
        """
        按 name=value;name=value 解析。统一使用 script_config.cookie_domain，path 默认 "/"。
        """
        cookie_domain = self.script_config.cookie_domain
        result: List[Dict[str, Any]] = []
        for segment in content.split(";"):
            seg = segment.strip()
            if not seg or "=" not in seg:
                continue
            name, _, value = seg.partition("=")
            name = name.strip()
            value = value.strip()
            if not name or not value:
                continue
            result.append(
                {
                    "name": name,
                    "value": value,
                    "domain": cookie_domain,
                    "path": "/",
                }
            )
        return result

    # ------------------------------------------------------------------
    # login：可选首页访问 + 滚动
    # ------------------------------------------------------------------

    async def login(self) -> None:
        """
        按 script_config.access_home_page 决定是否访问首页并滚动。
        登录态来自 cookie，无用户名/密码登录。
        """
        access_home_page = bool(self.script_config.access_home_page)
        home_url = self.script_config.home_url

        if not access_home_page:
            self.logger.info("access_home_page=0，跳过首页访问")
            return

        delay_ms = resolve_value_or_range(ITEM_HOME_LOAD_DELAY_RANGE_MS)
        self.logger.info("HOME 页面加载：url=%s", home_url)

        self.page = await self.page_navigator.load(
            home_url,
            page=self.page,
            page_type="HOME",
            delay_ms=delay_ms,
        )

        duration_ms = resolve_value_or_range(ITEM_HOME_SCROLL_DURATION_RANGE_MS)
        await self.page_navigator.scroll_to_load_more(
            self.page,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # crawl_item：顺序访问 ITEM URL
    # ------------------------------------------------------------------

    async def crawl_item(self) -> None:
        """
        顺序遍历 item_urls，逐条 load(ITEM_DETAIL) + scroll_to_load_more()。
        每个 URL 独立计算 load delay 与 scroll duration；单条失败记录后继续。
        """
        if not self.item_urls:
            self.logger.warning("ITEM URL 列表为空，跳过 crawl_item")
            return

        total = len(self.item_urls)
        self.logger.info("ITEM 总数量=%d", total)

        for idx, item_url in enumerate(self.item_urls, start=1):
            try:
                delay_ms = resolve_value_or_range(ITEM_LOAD_DELAY_RANGE_MS)
                self.logger.info("ITEM[%d/%d] 开始处理：url=%s", idx, total, item_url)

                self.page = await self.page_navigator.load(
                    item_url,
                    page=self.page,
                    page_type="ITEM_DETAIL",
                    delay_ms=delay_ms,
                )

                duration_ms = resolve_value_or_range(ITEM_SCROLL_DURATION_RANGE_MS)
                await self.page_navigator.scroll_to_load_more(
                    self.page,
                    duration_ms=duration_ms,
                )

                self.logger.info("ITEM[%d/%d] 处理完成", idx, total)

            except Exception:
                # 单个 ITEM 失败不中断整体流程，遵循 PageNavigator 既有重试语义
                self.logger.exception(
                    "ITEM[%d/%d] 页面处理失败：url=%s",
                    idx,
                    total,
                    item_url,
                )
