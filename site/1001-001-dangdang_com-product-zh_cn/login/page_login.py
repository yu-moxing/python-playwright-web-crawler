"""
当当登录页面处理

负责:
    - 输入账号
    - 输入密码
    - 勾选用户协议
    - 点击登录
"""

import random


async def random_delay(page, min_ms=2000, max_ms=5000):
    """
    随机等待

    模拟人工操作间隔
    """
    await page.wait_for_timeout(random.randint(min_ms, max_ms))


async def login(page, user):
    """
    当当登录

    Args:
        page:
            Playwright Page对象

        user:
            用户登录对象
            需要:
                user.username
                user.password

    Returns:
        bool:
            True  登录流程执行完成
            False 登录页面异常
    """

    # 用户名输入框
    username = page.locator("div.inputs").filter(has_text="手机号/昵称/邮箱").locator("input")

    if await username.count() == 0:
        return False

    # 输入用户名
    await random_delay(page)
    await username.fill(user.username)

    # 输入密码
    await random_delay(page)
    await page.locator("input[type=password]").fill(user.password)

    # 勾选用户协议
    await random_delay(page)

    agreement = page.locator("div.agreement")

    if await agreement.count() > 0:
        await agreement.click()

    # 点击登录
    await random_delay(page)
    await page.locator("a.btn").click()

    return True
