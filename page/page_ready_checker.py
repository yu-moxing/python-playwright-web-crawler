class PageReadyChecker:
    @staticmethod
    async def wait(
        page,
        # ready_selector: str,
        ready_selector: str | None = None,
        timeout: int = 15000,
        network_idle_enabled: bool = False,
        network_idle_timeout: int = 30000,
    ):

        # 1. 必须：DOM加载完成
        # await page.wait_for_load_state(
        #     "domcontentloaded"
        # )

        # 2. 可选：等待网络空闲
        if network_idle_enabled:
            try:
                await page.wait_for_load_state("networkidle", timeout=network_idle_timeout)
            except Exception:
                pass

        # 3. 必须：业务关键元素出现--(没指定:ready_selector 就跳过元素等待)
        if ready_selector:
            await page.wait_for_selector(ready_selector, timeout=timeout)

        return True
