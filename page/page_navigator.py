"""
页面导航器模块（PageNavigator）

职责：
    - 持有 BrowserSessionFactory 引用，负责 create_context / new_page / goto / PageReadyChecker / 页面加载重试
    - 按 ResourceContext/User 复用 BrowserContext（保持 cookie / session / localStorage）
    - 不持有 Page 对象（page 为一次采集任务的临时资源，由 load() 返回给调用方持有与关闭）

设计原则：
    - PageNavigator 实例为 per-run / per-user，不跨用户共享
    - 严禁 self.page 单例字段：page 由 load() 返回给调用方持有，避免多 Processor / 多用户采集互相污染
    - BrowserSessionFactory 生命周期由 Runner 管理（创建 + close_all）；PageNavigator 只持有引用、不创建/不关闭

调用方：
    CateLevelProcessor（注入 PageNavigator，调 load(url) / load(url, page=self.page)）
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Optional

from playwright.async_api import BrowserContext, Page
from playwright.async_api import Error as PlaywrightError

from config.model.page.page_item import PageItem
from constants.browser_const import (
    MAX_SCROLL_STEP_FACTOR,
    MAX_SCROLL_TIMES,
    MIN_SCROLL_STEP_FACTOR,
    SCROLL_BOTTOM_THRESHOLD,
    SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED,
)
from page.page_ready_checker import PageReadyChecker

logger = logging.getLogger(__name__)


# 页面类型 → PageItem 就绪选择器属性名
_PAGE_TYPE_ATTR = {
    "HOME": "home_ready_selector",
    "LOGIN": "login_ready_selector",
    "RISK": "risk_ready_selector",
    "CATE_LEVEL": "cate_level_ready_selector",
    "CATE_LIST": "cate_list_ready_selector",
    "DETAIL": "detail_ready_selector",
}


class PageNavigator:
    """
    页面加载会话

    Example:
        >>> loader = PageNavigator(browser_factory=factory, resource_context=ctx, headless=False)
        >>> page = await loader.load(home_url)          # 首次：懒建 context+page 并导航
        >>> await loader.load(url, page=page)           # 后续：复用 page 导航
        >>> # 调用方负责 page.close()；context 由 factory.close_all() 关闭
    """

    def __init__(
        self,
        *,
        browser_factory,
        resource_context,
        logger,
        headless: bool = False,
        max_retries: int = 3,
        ready_check_enabled: int = 1,
        page_goto_timeout: int = 30000,
        timeout: int = 15000,
        network_idle_enabled: int = 0,
        network_idle_timeout: int = 30000,
        page_item: Optional[PageItem] = None,
    ):
        """
        初始化页面加载会话

        Args:
            browser_factory: BrowserSessionFactory（由 Runner 创建/关闭，此处仅持有引用）
            resource_context: 资源上下文（携带 user_data_dir / proxy / fingerprint 等）
            headless: 是否无头
            max_retries: 页面加载最大重试次数
            ready_check_enabled: 是否启用就绪检测
            page_goto_timeout: page.goto() 打开 URL 超时（毫秒）
            timeout: 就绪检测超时（毫秒）
            network_idle_enabled: 是否启用 networkidle 等待
            network_idle_timeout: networkidle 超时（毫秒）
            page_item: 各页面类型就绪选择器配置（PAGE_*_READY_SELECTOR），用于按 page_type 解析 ready_selector
        """
        self.browser_factory = browser_factory
        self.resource_context = resource_context
        self.logger = logger
        self.headless = headless

        self._ready_kwargs = dict(
            max_retries=max_retries,
            ready_check_enabled=ready_check_enabled,
            page_goto_timeout=page_goto_timeout,
            timeout=timeout,
            network_idle_enabled=network_idle_enabled,
            network_idle_timeout=network_idle_timeout,
        )

        # 各页面类型就绪选择器配置（可选）
        self._page_item = page_item

        # 懒持有本次 run 的 context（factory 按 user_data_dir 缓存，此处仅存引用复用 cookie/session）
        self._context: Optional[BrowserContext] = None
        # 严禁：不得有 self.page 单例字段（page 由 load() 返回给调用方，避免多用户污染）

    async def load(
        self,
        url: str,
        page: Optional[Page] = None,
        page_type: Optional[str] = None,
        ready_selector: Optional[str] = None,
        delay_ms: int = -1,
    ) -> Page:
        """
        加载页面

        首次调用（page=None）：懒创建 BrowserContext（factory 按 user 复用）+ new_page，
        导航后返回 page。
        后续调用（传入 page）：复用已有 page 与登录状态导航，返回同一 page。

        Args:
            url: 目标 URL
            page: 已有 page（复用）；None 则新建
            page_type: 当前页面类型（HOME/LOGIN/RISK/CATE_LEVEL/CATE_LIST/DETAIL），
                       用于从 PageItem 解析 ready_selector；未设置则不启用元素等待
            ready_selector: 显式就绪选择器（优先于 page_type 解析结果）

        Returns:
            导航后的 page 对象（由调用方持有与关闭）
        """
        if self._context is None:
            self._context = await self.browser_factory.create_context(self.resource_context, headless=self.headless)
        if page is None:
            page = await self._context.new_page()

        # ready_selector 解析优先级：显式覆盖 > page_type 查找 > 空
        if ready_selector is None and page_type and self._page_item is not None:
            attr = _PAGE_TYPE_ATTR.get(page_type)
            if attr:
                ready_selector = getattr(self._page_item, attr, "") or ""

        await self._navigate(page, url, ready_selector)

        # 页面基础就绪后的额外等待时间，用于等待动态内容进一步渲染
        if delay_ms > 0:
            await page.wait_for_timeout(delay_ms)

        return page

    async def _navigate(self, page: Page, url: str, ready_selector: Optional[str]) -> None:
        """goto + PageReadyChecker + PlaywrightError 重试循环"""
        max_retries = self._ready_kwargs["max_retries"]
        max_attempts = max_retries + 1

        for attempt in range(max_attempts):
            try:
                # await page.goto(url)
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self._ready_kwargs["page_goto_timeout"],
                )

                if self._ready_kwargs["ready_check_enabled"]:
                    await PageReadyChecker.wait(
                        page,
                        ready_selector=ready_selector,
                        timeout=self._ready_kwargs["timeout"],
                        network_idle_enabled=bool(self._ready_kwargs["network_idle_enabled"]),
                        network_idle_timeout=self._ready_kwargs["network_idle_timeout"],
                    )

                return

            except PlaywrightError as e:
                print("=" * 60)
                print("页面加载异常参数信息")
                print(f"url                     = {url}")
                print(f"retry                   = {attempt}")
                print(f"max_retries             = {max_retries}")
                print(f"ready_check_enabled     = {self._ready_kwargs['ready_check_enabled']}")
                print(f"ready_selector          = {ready_selector}")
                print(f"page_goto_timeout       = {self._ready_kwargs['page_goto_timeout']}")
                print(f"timeout                 = {self._ready_kwargs['timeout']}")
                print(f"network_idle_enabled    = {self._ready_kwargs['network_idle_enabled']}")
                print(f"network_idle_timeout    = {self._ready_kwargs['network_idle_timeout']}")
                print(f"exception               = {e}")
                print("=" * 60)

                # # 是否超过最大次数？
                # if attempt >= max_retries:
                #     # 是 ---> raise（放弃，报错）
                #     raise

                # 最后一次尝试仍失败
                if attempt == max_attempts - 1:
                    raise

                logger.warning(f"页面加载失败，第 {attempt + 1} 次重试: {e}")

                # 否 ---> continue（重新尝试）
                continue

    async def scroll_to_load_more(
        self,
        page: Page,
        *,
        duration_ms: int = -1,
        stable_rounds: int = 2,
    ) -> None:
        """
        滚动页面，触发懒加载内容。

        duration_ms 表示整个滚动过程的最大持续时间，而不是单次等待时间。

        每次主动滚动前重新获取当前页面的：
            1. 可视区域高度；
            2. 完整页面高度；
            3. 当前滚动位置。

        根据当前页面状态判断是否允许继续滚动：

            剩余滚动距离
            ÷
            可视区域高度
            =
            理论剩余滚动次数

        如果理论剩余滚动次数超过 MAX_SCROLL_TIMES：

            SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED = True：
                本次直接滚动到页面底部。

            SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED = False：
                停止继续滚动。

        实际每次正常滚动距离以可视区域高度为基础，
        使用 MIN_SCROLL_STEP_FACTOR ~ MAX_SCROLL_STEP_FACTOR
        对目标滚动步长进行随机调整。

        当距离页面底部小于等于 SCROLL_BOTTOM_THRESHOLD，
        且 SCROLL_BOTTOM_THRESHOLD > 0 时，
        不再继续主动滚动。

        到达页面底部后，不再增加主动滚动次数，
        而是等待页面懒加载，并检查页面高度是否继续增加。

        滚动后的等待时间根据剩余 duration 和剩余滚动次数动态分配，
        不使用固定等待时间。

        当出现以下任一情况时停止：

            1. duration_ms == -1；
            2. 页面已经到底，并且页面高度连续 stable_rounds 轮没有增加；
            3. SCROLL_BOTTOM_THRESHOLD > 0，
               且距离页面底部小于等于 SCROLL_BOTTOM_THRESHOLD；
            4. 理论剩余滚动次数超过 MAX_SCROLL_TIMES，
               且 SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED = False；
            5. 超过 duration_ms 指定的最大持续时间。

        Args:
            page:
                当前页面。

            duration_ms:
                整个滚动过程的最大持续时间，单位毫秒。
                -1 表示不执行任何滚动操作。

            stable_rounds:
                页面已经到底后，页面高度连续多少轮不增加后停止。
        """
        if duration_ms == -1:
            return

        if duration_ms <= 0:
            raise ValueError(f"duration_ms 配置非法：{duration_ms}（必须为 -1 或大于 0）")

        if stable_rounds <= 0:
            raise ValueError(f"stable_rounds 配置非法：{stable_rounds}（必须大于 0）")

        start_time = time.monotonic()

        # 时间上的“停止条件”：
        # 最多允许滚动多长时间。
        deadline = start_time + duration_ms / 1000

        # 实际主动滚动次数。
        # 到底后的 stable 检查不计入此次数。
        scroll_times = 0

        # 页面到底后的连续稳定次数。
        stable_count = 0

        while True:
            # ==================================================
            # 第一步：检查 duration 是否已经耗尽
            # ==================================================

            if time.monotonic() >= deadline:
                break

            # ==================================================
            # 第二步：每一轮重新获取页面状态
            # ==================================================

            viewport_height = await page.evaluate("() => window.innerHeight")

            scroll_height = await page.evaluate("() => document.documentElement.scrollHeight")

            current_scroll_y = await page.evaluate("() => window.scrollY")

            max_scroll_y = max(
                scroll_height - viewport_height,
                0,
            )

            # ==================================================
            # 第三步：判断当前是否已经到底
            # ==================================================

            if current_scroll_y >= max_scroll_y:
                remaining_time_ms = int(
                    max(
                        (deadline - time.monotonic()) * 1000,
                        0,
                    )
                )

                if remaining_time_ms <= 0:
                    break

                # 到底后不再增加 scroll_times。
                #
                # 此时等待的目的不是继续滚动，
                # 而是给页面懒加载一个继续增加页面高度的机会。
                #
                # 按照剩余 stable_rounds 动态分配等待时间。
                remaining_stable_rounds = max(
                    stable_rounds - stable_count,
                    1,
                )

                wait_ms = max(
                    remaining_time_ms // remaining_stable_rounds,
                    1,
                )

                await page.wait_for_timeout(wait_ms)

                # ==================================================
                # 重新检查页面高度和滚动位置
                # ==================================================

                new_viewport_height = await page.evaluate("() => window.innerHeight")

                new_scroll_height = await page.evaluate("() => document.documentElement.scrollHeight")

                new_scroll_y = await page.evaluate("() => window.scrollY")

                new_max_scroll_y = max(
                    new_scroll_height - new_viewport_height,
                    0,
                )

                # 页面高度增加，说明懒加载产生了新内容。
                if new_scroll_height > scroll_height:
                    stable_count = 0

                # 页面高度没有增加，并且当前仍然位于页面底部，
                # 才算一次稳定检查。
                elif new_scroll_y >= new_max_scroll_y:
                    stable_count += 1

                else:
                    # 页面位置发生变化，但没有新的页面高度增加。
                    stable_count = 0

                self.logger.debug(
                    "页面懒加载滚动：round=%d，已到底，scroll_y=%.0f -> %.0f，height=%d -> %d，stable=%d",
                    scroll_times + 1,
                    current_scroll_y,
                    new_scroll_y,
                    scroll_height,
                    new_scroll_height,
                    stable_count,
                )

                if stable_count >= stable_rounds:
                    break

                continue

            # ==================================================
            # 第四步：计算当前距离页面底部的剩余距离
            # ==================================================

            remaining_scroll_y = max(
                max_scroll_y - current_scroll_y,
                0,
            )

            # ==================================================
            # 第五步：判断是否已经接近页面底部
            # ==================================================

            # SCROLL_BOTTOM_THRESHOLD <= 0：
            #     禁用“接近底部提前停止”功能。
            #
            # SCROLL_BOTTOM_THRESHOLD > 0：
            #     距离页面底部小于等于该值时停止主动滚动。
            if SCROLL_BOTTOM_THRESHOLD > 0 and remaining_scroll_y <= SCROLL_BOTTOM_THRESHOLD:
                break

            # ==================================================
            # 第六步：计算理论剩余滚动次数
            # ==================================================

            remaining_scroll_times = math.ceil(remaining_scroll_y / viewport_height)

            # ==================================================
            # 第七步：根据理论剩余滚动次数决定本次滚动方式
            # ==================================================

            scroll_to_bottom = False

            if remaining_scroll_times > MAX_SCROLL_TIMES:
                if SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED:
                    # 页面理论滚动次数超过最大允许次数，
                    # 但配置允许在本次直接滚动到底部。
                    scroll_to_bottom = True

                    self.logger.debug(
                        "页面懒加载滚动：理论剩余滚动次数超过上限，"
                        "本次直接滚动到底部，"
                        "remaining_scroll_y=%.0f，viewport_height=%d，"
                        "remaining_scroll_times=%d，max_scroll_times=%d",
                        remaining_scroll_y,
                        viewport_height,
                        remaining_scroll_times,
                        MAX_SCROLL_TIMES,
                    )

                else:
                    # 页面理论滚动次数超过最大允许次数，
                    # 且配置不允许直接滚动到底部。
                    self.logger.debug(
                        "页面懒加载滚动：页面过长，停止滚动，"
                        "remaining_scroll_y=%.0f，viewport_height=%d，"
                        "remaining_scroll_times=%d，max_scroll_times=%d",
                        remaining_scroll_y,
                        viewport_height,
                        remaining_scroll_times,
                        MAX_SCROLL_TIMES,
                    )
                    break

            # ==================================================
            # 第八步：计算本次滚动距离
            # ==================================================

            if scroll_to_bottom:
                # 理论剩余滚动次数超过 MAX_SCROLL_TIMES，
                # 并且配置要求下一次直接滚动到底部。
                scroll_distance = remaining_scroll_y

            else:
                # 正常滚动：
                # 以可视区域高度为基础，
                # 使用随机系数调整实际滚动距离。
                scroll_step_factor = random.uniform(
                    MIN_SCROLL_STEP_FACTOR,
                    MAX_SCROLL_STEP_FACTOR,
                )

                scroll_distance = viewport_height * scroll_step_factor

                # 防止本次滚动超过剩余距离。
                scroll_distance = min(
                    scroll_distance,
                    remaining_scroll_y,
                )

            next_scroll_y = current_scroll_y + scroll_distance

            # ==================================================
            # 第九步：执行滚动前再次检查 duration
            # ==================================================

            if time.monotonic() >= deadline:
                break

            await page.evaluate(
                """
                (scroll_y) => {
                    window.scrollTo(0, scroll_y);
                }
                """,
                next_scroll_y,
            )

            scroll_times += 1

            # 主动滚动后，本轮不属于“到底后的稳定检查”。
            stable_count = 0

            # ==================================================
            # 第十步：根据剩余 duration 动态分配等待时间
            # ==================================================

            remaining_time_ms = int(
                max(
                    (deadline - time.monotonic()) * 1000,
                    0,
                )
            )

            if remaining_time_ms <= 0:
                break

            # 这里的 remaining_scroll_times 是“理论剩余次数”。
            #
            # 当前已经完成一次主动滚动，
            # 因此下一轮实际还需要的次数至少减少 1。
            remaining_wait_rounds = max(
                remaining_scroll_times - 1,
                1,
            )

            wait_ms = max(
                remaining_time_ms // remaining_wait_rounds,
                1,
            )

            await page.wait_for_timeout(wait_ms)

            # ==================================================
            # 第十一步：检查本次滚动后的页面状态
            # ==================================================

            new_viewport_height = await page.evaluate("() => window.innerHeight")

            new_scroll_height = await page.evaluate("() => document.documentElement.scrollHeight")

            new_scroll_y = await page.evaluate("() => window.scrollY")

            new_max_scroll_y = max(
                new_scroll_height - new_viewport_height,
                0,
            )

            self.logger.debug(
                "页面懒加载滚动：round=%d，"
                "scroll_y=%.0f -> %.0f，height=%d -> %d，"
                "remaining_scroll_times=%d，scroll_to_bottom=%s",
                scroll_times,
                current_scroll_y,
                new_scroll_y,
                scroll_height,
                new_scroll_height,
                remaining_scroll_times,
                scroll_to_bottom,
            )

            # ==================================================
            # 第十二步：检查 duration
            # ==================================================

            if time.monotonic() >= deadline:
                break

            # ==================================================
            # 第十三步：
            # 如果已经到底，不在这里增加 stable_count。
            #
            # 下一轮循环重新进入“到底后的稳定检查”。
            #
            # 如果没有到底，则下一轮重新获取：
            #
            #     viewport_height
            #     scroll_height
            #     scroll_y
            #
            # 然后重新计算：
            #
            #     remaining_scroll_y
            #     remaining_scroll_times
            #     scroll_distance
            #
            # 因此页面高度发生变化后，
            # 下一轮也会自动重新计算滚动距离。
            # ==================================================

            if new_scroll_y >= new_max_scroll_y:
                stable_count = 0
