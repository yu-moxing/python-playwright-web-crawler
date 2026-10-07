import asyncio
import json
import random


class CDPSliderDragger:
    def __init__(self, track_file="human_tracks_cdp.json"):
        with open(track_file, "r") as f:
            self.all_tracks = json.load(f)

    async def drag(self, page, slider_selector, target_x_offset):
        """
        使用 CDP 执行物理级拟真拖拽
        """
        # 1. 随机挑选一条真实轨迹
        track = random.choice(self.all_tracks)
        if not track:
            return

        # 2. 获取滑块当前在屏幕上的绝对位置
        slider_box = await page.locator(slider_selector).bounding_box()
        start_x = slider_box["x"] + slider_box["width"] / 2
        start_y = slider_box["y"] + slider_box["height"] / 2

        # 3. 计算轨迹的缩放与平移
        original_x_span = track[-1]["x"] - track[0]["x"]
        scale = target_x_offset / original_x_span if original_x_span != 0 else 1

        # 4. 获取 CDP Session
        cdp = await page.context.new_cdp_session(page)

        # 5. 模拟按下鼠标 (button: 1 表示左键)
        await cdp.send(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": start_x, "y": start_y, "button": "left", "clickCount": 1},
        )

        # 6. 按照真实时间戳回放轨迹
        for i in range(1, len(track)):
            move_x = start_x + (track[i]["x"] - track[0]["x"]) * scale
            move_y = start_y + (track[i]["y"] - track[0]["y"]) * scale
            time_delta = track[i]["ts"] - track[i - 1]["ts"]

            await cdp.send(
                "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": move_x, "y": move_y, "button": "left"}
            )
            # 真实时间间隔休眠
            await asyncio.sleep(time_delta / 1000.0)

        # 7. 模拟松开鼠标
        final_x = start_x + target_x_offset
        await cdp.send(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "x": final_x, "y": start_y, "button": "left", "clickCount": 1},
        )

        # 8. 清理 Session
        await cdp.detach()
