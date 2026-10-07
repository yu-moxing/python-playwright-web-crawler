"""
登录状态检测模块

功能:
    检测当前浏览器页面是否已经登录。

判断规则:
    当当顶部欢迎区域:
        存在 登录 a 标签 -> 未登录
        不存在 登录 a 标签 -> 已登录
"""

from playwright.async_api import Page


class LoginChecker:
    """
    登录状态检测器。
    """

    LOGIN_SELECTOR = ".ddnewhead_welcome a.login_link"

    @classmethod
    async def is_logged_in(cls, page: Page) -> bool:
        """
        判断是否已经登录。

        Returns:
            True  : 已登录
            False : 未登录
        """

        login_link = await page.locator(cls.LOGIN_SELECTOR).count()

        # 存在登录链接
        if login_link > 0:
            return False

        # 不存在登录链接
        return True
