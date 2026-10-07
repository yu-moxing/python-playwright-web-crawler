import json
import random


class HumanSliderDragger:
    def __init__(self, track_file="human_tracks.json"):
        with open(track_file, "r") as f:
            self.all_tracks = json.load(f)

    async def drag(self, page, slider_selector, target_x_offset):
        """
        在 Playwright 中执行拟真拖拽
        :param page: Playwright Page 对象
        :param slider_selector: 滑块的 CSS 选择器
        :param target_x_offset: 需要拖动的 X 轴像素距离
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
        # 真实轨迹的总跨度
        original_x_span = track[-1]["x"] - track[0]["x"]
        # 计算缩放比例，使轨迹长度适配实际需要滑动的距离
        scale = target_x_offset / original_x_span if original_x_span != 0 else 1

        # 4. 注入并执行拖拽动作 (Playwright 原生 JS 注入)
        await page.evaluate(
            """(args) => {
            const { startX, startY, track, scale, targetOffset } = args;

            // 模拟按下鼠标
            const mousedownEvent = new MouseEvent('mousedown', {
                bubbles: true, cancelable: true, clientX: startX, clientY: startY
            });
            document.elementFromPoint(startX, startY).dispatchEvent(mousedownEvent);

            // 按照真实时间戳回放轨迹
            track.forEach((point, index) => {
                setTimeout(() => {
                    const moveX = startX + (point.x - track[0].x) * scale;
                    const moveY = startY + (point.y - track[0].y) * scale;

                    const mousemoveEvent = new MouseEvent('mousemove', {
                        bubbles: true, cancelable: true, clientX: moveX, clientY: moveY
                    });
                    document.elementFromPoint(moveX, moveY).dispatchEvent(mousemoveEvent);
                }, point.ts - track[0].ts);
            });

            // 模拟松开鼠标
            setTimeout(() => {
                const finalX = startX + targetOffset;
                const mouseupEvent = new MouseEvent('mouseup', {
                    bubbles: true, cancelable: true, clientX: finalX, clientY: startY
                });
                document.elementFromPoint(finalX, startY).dispatchEvent(mouseupEvent);
            }, track[track.length - 1].ts - track[0].ts + 50);

        }""",
            {"startX": start_x, "startY": start_y, "track": track, "scale": scale, "targetOffset": target_x_offset},
        )
