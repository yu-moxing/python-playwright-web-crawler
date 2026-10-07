from .login_slider import drag_slider


async def handle_slider(page):

    distance = 154

    result = await drag_slider(page, distance)

    return result
