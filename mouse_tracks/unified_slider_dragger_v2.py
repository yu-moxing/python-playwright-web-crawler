"""
模块名称: unified_slider_dragger_v2.py
描述: 统一滑块拖拽器 (Unified Slider Dragger) - 自动维护版
      基于 Playwright 的自动化滑块验证码处理模块。在 V1 版本的基础上，
      引入了轨迹池自动维护机制，确保高并发爬虫场景下的稳定性与高性能。

核心特性:
    1. 双引擎拟真拖拽：默认使用轻量级 JS 注入（魔法攻击），
       失败时自动降级为 CDP 物理模拟（物理攻击），实现无缝容错。

    2. 轨迹池自动维护：基于内存池（MAX_TRACKS）进行 LRU 淘汰，
       结合 aiofiles 异步写入，确保每次成功拖拽后自动追加高质量轨迹，
       防止文件无限膨胀，同时绝不阻塞爬虫主协程。

设计哲学:
    摒弃传统的纯数学公式生成轨迹，采用“真实人类轨迹回放 + 动态等比缩放”策略。
    通过保留人类操作时的“高频微颤”和“非均匀时间间隔”，从底层规避风控检测。

依赖说明:
    - playwright: 浏览器自动化核心
    - aiofiles: 异步文件 IO，保证高并发下的写入性能
"""

import asyncio
import json
import os
import random

import aiofiles
from playwright.async_api import Page


class UnifiedSliderDragger:
    """
    统一滑块拖拽器 (带自动维护机制)

    自动在 JS 注入与 CDP 物理模拟之间切换，并在每次成功拖拽后自动维护轨迹池。
    """

    # 内存中保留的最大轨迹数量，超出此上限将自动清理最旧的数据 (LRU策略)
    MAX_TRACKS = 100

    def __init__(self, track_file="slider_tracks.json"):
        """
        初始化拖拽器并加载轨迹数据。

        :param track_file: str, 真实人类轨迹 JSON 文件路径，默认为 "slider_tracks.json"
        """
        self.track_file = track_file
        self.track_pool = []
        self._load_tracks()

    def _load_tracks(self):
        """
        同步加载轨迹文件。
        若文件不存在则自动创建空文件；若文件损坏则重置为空文件。
        """
        if not os.path.exists(self.track_file):
            print(f"[*] 轨迹文件不存在，正在自动创建: {self.track_file}")
            self._save_tracks_sync([])
            return

        try:
            with open(self.track_file, "r", encoding="utf-8") as f:
                self.track_pool = json.load(f)
            print(f"[+] 成功加载 {len(self.track_pool)} 条轨迹数据。")
        except (json.JSONDecodeError, ValueError):
            print("[!] 轨迹文件损坏，已重置为空文件。")
            self.track_pool = []
            self._save_tracks_sync([])

    async def _append_track(self, track):
        """
        【自动维护核心】追加新轨迹并清理旧数据。
        每次成功拖拽后调用，将当前轨迹追加到内存池，并异步持久化到磁盘。

        :param track: list[dict], 本次成功拖拽使用的轨迹数据
        """
        # 1. 追加到内存池
        self.track_pool.append(track)

        # 2. 超过上限时，丢弃最旧的轨迹，保持内存池大小恒定
        if len(self.track_pool) > self.MAX_TRACKS:
            self.track_pool = self.track_pool[-self.MAX_TRACKS :]

        # 3. 使用 aiofiles 异步写入文件，避免阻塞爬虫主线程
        try:
            async with aiofiles.open(self.track_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.track_pool, indent=2))
        except Exception as e:
            print(f"[-] 轨迹文件异步写入失败: {e}")

    def _save_tracks_sync(self, data):
        """
        同步保存轨迹数据（仅用于初始化或重置时的兜底操作）。

        :param data: list, 需要写入的轨迹列表
        """
        with open(self.track_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    async def drag(self, page: Page, slider_selector: str, target_x_offset: float, max_retries: int = 2):
        """
        执行拟真拖拽操作。

        流程:
            1. JS 注入拖拽
            2. 失败降级 CDP 模拟
            3. 验证验证码结果
            4. 成功后保存有效轨迹

        :return:
            bool
        """

        if not self.track_pool:
            raise Exception("轨迹池为空，请先手动采集至少一条轨迹。")

        for attempt in range(max_retries):
            try:
                # 保存本次使用的轨迹
                used_track = None

                if attempt == 0:
                    print("[*] 正在使用 JS 注入模式拖拽...")

                    used_track = await self._drag_with_js(page, slider_selector, target_x_offset)

                else:
                    print("[!] JS 模式失败，降级为 CDP 物理模拟模式...")

                    used_track = await self._drag_with_cdp(page, slider_selector, target_x_offset)

                # 等待验证码状态更新
                await asyncio.sleep(1)

                # ⭐关键：判断是否真的成功
                success = await self._verify_success(page)

                if success:
                    print("[+] 滑块验证成功")

                    # 只有真正成功才保存轨迹
                    if used_track:
                        await self._append_track(used_track)

                    return True

                else:
                    print("[!] 拖拽完成，但是验证码失败")

            except Exception as e:
                print(f"[-] 拖拽失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        raise Exception("滑块拖拽最终失败，请检查验证码状态或轨迹数据。")

    async def _drag_with_js(self, page: Page, slider_selector: str, target_x_offset: float):
        """
        方案 A: JS 注入模式。

        通过 page.evaluate 在浏览器上下文中派发鼠标事件，
        按真实轨迹时间间隔回放。

        注意:
            本方法只负责执行拖拽动作，
            不负责判断验证码成功，
            不负责保存轨迹。

        :return:
            本次使用的轨迹数据
        """

        # 随机选择一条历史轨迹
        track = random.choice(self.track_pool)

        # 获取滑块位置
        slider_box = await page.locator(slider_selector).bounding_box()

        if not slider_box:
            raise Exception(f"未找到滑块元素: {slider_selector}")

        start_x = slider_box["x"] + slider_box["width"] / 2

        start_y = slider_box["y"] + slider_box["height"] / 2

        # 原始轨迹跨度
        original_x_span = track[-1]["x"] - track[0]["x"]

        # 缩放比例
        scale = target_x_offset / original_x_span if original_x_span != 0 else 1

        await page.evaluate(
            """
            (args) => {

                return new Promise((resolve) => {

                    const {
                        startX,
                        startY,
                        track,
                        scale,
                        targetOffset
                    } = args;


                    const firstPoint = track[0];


                    const lastPoint =
                        track[track.length - 1];


                    /*
                     * 鼠标按下
                     */
                    const startElement =
                        document.elementFromPoint(
                            startX,
                            startY
                        );


                    startElement.dispatchEvent(
                        new MouseEvent(
                            "mousedown",
                            {
                                bubbles: true,
                                cancelable: true,
                                clientX: startX,
                                clientY: startY,
                                button: 0
                            }
                        )
                    );


                    /*
                     * 按真实轨迹移动
                     */
                    track.forEach((point)=>{


                        setTimeout(()=>{


                                const moveX =
                                    startX
                                    +
                                    (
                                        point.x
                                        -
                                        firstPoint.x
                                    )
                                    *
                                    scale;


                                const moveY =
                                    startY
                                    +
                                    (
                                        point.y
                                        -
                                        firstPoint.y
                                    );


                                const element =
                                    document.elementFromPoint(
                                        moveX,
                                        moveY
                                    );


                                if(element){

                                    element.dispatchEvent(
                                        new MouseEvent(
                                            "mousemove",
                                            {
                                                bubbles:true,
                                                cancelable:true,
                                                clientX:moveX,
                                                clientY:moveY,
                                                button:0
                                            }
                                        )
                                    );

                                }


                            },
                            point.ts - firstPoint.ts);


                    });



                    /*
                     * 鼠标释放
                     */
                    const duration =
                        lastPoint.ts
                        -
                        firstPoint.ts;


                    setTimeout(()=>{


                            const finalX =
                                startX
                                +
                                targetOffset;


                            const element =
                                document.elementFromPoint(
                                    finalX,
                                    startY
                                );


                            if(element){

                                element.dispatchEvent(
                                    new MouseEvent(
                                        "mouseup",
                                        {
                                            bubbles:true,
                                            cancelable:true,
                                            clientX:finalX,
                                            clientY:startY,
                                            button:0
                                        }
                                    )
                                );

                            }


                            // 通知 Python 拖拽完成
                            resolve(true);


                        },
                        duration + 50);


                });

            }
            """,
            {
                "startX": start_x,
                "startY": start_y,
                "track": track,
                "scale": scale,
                "targetOffset": target_x_offset,
            },
        )

        return track

    async def _drag_with_cdp(self, page: Page, slider_selector: str, target_x_offset: float):
        """
        方案 B: CDP 物理模拟模式 (物理攻击)
        通过 Chrome DevTools Protocol (CDP) 直接发送底层输入事件，绕过前端 JS 监听，防检测能力极强。
        成功后会自动触发轨迹池维护。
        """
        track = random.choice(self.track_pool)
        slider_box = await page.locator(slider_selector).bounding_box()
        start_x = slider_box["x"] + slider_box["width"] / 2
        start_y = slider_box["y"] + slider_box["height"] / 2
        original_x_span = track[-1]["x"] - track[0]["x"]
        scale = target_x_offset / original_x_span if original_x_span != 0 else 1

        cdp = await page.context.new_cdp_session(page)
        try:
            # 1. 模拟鼠标按下
            await cdp.send(
                "Input.dispatchMouseEvent",
                {"type": "mousePressed", "x": start_x, "y": start_y, "button": "left", "clickCount": 1},
            )
            # 2. 按照真实轨迹的时间差和坐标进行移动
            for i in range(1, len(track)):
                move_x = start_x + (track[i]["x"] - track[0]["x"]) * scale
                move_y = start_y + (track[i]["y"] - track[0]["y"]) * scale
                time_delta = track[i]["ts"] - track[i - 1]["ts"]
                await cdp.send(
                    "Input.dispatchMouseEvent", {"type": "mouseMoved", "x": move_x, "y": move_y, "button": "left"}
                )
                await asyncio.sleep(time_delta / 1000.0)

            # 3. 模拟鼠标释放
            final_x = start_x + target_x_offset
            await cdp.send(
                "Input.dispatchMouseEvent",
                {"type": "mouseReleased", "x": final_x, "y": start_y, "button": "left", "clickCount": 1},
            )
        finally:
            # 确保 CDP 会话被正确释放，防止内存泄漏
            await cdp.detach()

        # 拖拽成功后，自动将当前轨迹追加到池中并持久化
        # await self._append_track(track)
        return track

    async def _verify_success(self, page: Page):
        """
        判断验证码是否真正通过。

        不同网站需要不同实现。
        """

        try:
            # 示例:
            # 等待成功元素出现

            await page.wait_for_selector(".success", timeout=3000)

            return True

        except Exception:
            return False
