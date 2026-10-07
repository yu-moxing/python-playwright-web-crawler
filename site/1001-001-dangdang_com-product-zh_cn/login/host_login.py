async def login(page, user):

    username = page.locator("#login_username")

    if await username.count() == 0:
        return False

    await username.fill(user.username)

    await page.locator("#login_password").fill(user.password)

    await page.locator(".login-btn").click()

    return True
