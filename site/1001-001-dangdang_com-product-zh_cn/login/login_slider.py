"""
当当滑块验证码处理

负责:
    - 获取滑块按钮
    - 模拟鼠标拖动
    - 等待验证结果
"""

import asyncio
import random


async def random_delay(min_ms=500, max_ms=1500):
    """
    随机等待
    """
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def drag_slider(page, distance):
    """
    拖动滑块

    Args:
        page:
            Playwright Page对象

        distance:
            需要移动的距离(px)

    Returns:
        bool:
            True  拖动完成
            False 滑块不存在
    """

    slider = page.locator("#sliderBtn")

    if await slider.count() == 0:
        return False

    box = await slider.bounding_box()

    if not box:
        return False

    # 滑块中心点
    start_x = box["x"] + box["width"] / 2

    start_y = box["y"] + box["height"] / 2

    # 移动到滑块
    await page.mouse.move(start_x, start_y)

    await random_delay()

    # 按下鼠标
    await page.mouse.down()

    await random_delay(200, 500)

    # 模拟人工移动轨迹
    steps = [
        0.15,
        0.30,
        0.45,
        0.60,
        0.75,
        0.90,
        1.00,
    ]

    for step in steps:
        move_x = start_x + distance * step

        move_y = start_y + random.randint(-2, 2)

        await page.mouse.move(move_x, move_y, steps=random.randint(3, 8))

        await random_delay(50, 200)

    # 松开鼠标
    await page.mouse.up()

    return True
