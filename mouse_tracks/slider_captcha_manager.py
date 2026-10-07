import asyncio
import random

from constants.path_const import RISK_HUMAN_SLIDER_TRACKS_FILE
from mouse_tracks.unified_slider_dragger_v2 import UnifiedSliderDragger


class SliderCaptchaManager:
    """
    滑块验证码管理器。

    负责采集过程中的滑块验证码处理：
    1. 自动拟真拖拽处理
    2. 自动处理失败降级
    3. 连续触发风控保护
    4. 人工验证兜底恢复

    通过自动处理 + 人工介入机制，
    降低高频触发风控导致 IP / 账号风险。
    """

    def __init__(
        self,
        max_slider_trigger_count: int = 8,
        max_slider_auto_fail_count: int = 3,
        cooldown_range: tuple[float, float] = (10.0, 20.0),
    ):
        """
        Args:
            max_slider_trigger_count:
                用户采集过程中允许的最大滑块触发次数。
                达到阈值后停止当前用户采集。

            max_slider_auto_fail_count:
                自动滑块连续失败次数。
                达到阈值后进入人工验证。
        """

        self.max_slider_trigger_count = max_slider_trigger_count
        self.max_slider_auto_fail_count = max_slider_auto_fail_count

        self.cooldown_range = cooldown_range

        # 用户采集过程中，滑块验证码累计触发次数
        # 用于风控熔断
        self.slider_trigger_count = 0

        # 自动滑块处理连续失败次数
        # 达到阈值后进入人工验证
        self.slider_auto_fail_count = 0

        # 初始化滑块拟真拖拽器
        self.dragger = UnifiedSliderDragger(track_file=RISK_HUMAN_SLIDER_TRACKS_FILE)

    async def handle_slider(
        self,
        page,
        slider_selector: str,
        target_x_offset: float,
    ) -> bool:
        """
        处理滑块验证码。

        Returns:
            bool:
                True  表示处理完成
                False 表示处理失败
        """

        self.slider_trigger_count += 1

        if self.max_slider_trigger_count == -1:
            limit_text = "无限制"
        else:
            limit_text = str(self.max_slider_trigger_count)

        print(f"[!] 触发滑块验证码，累计次数: {self.slider_trigger_count}/{limit_text}")

        # ------------------------------------
        # 风控熔断判断
        # ------------------------------------
        if self.max_slider_trigger_count != -1 and self.slider_trigger_count >= self.max_slider_trigger_count:
            print("[!!!] 滑块触发次数达到阈值，停止当前用户采集")

            return False

        # ------------------------------------
        # 自动拟真拖拽处理
        # ------------------------------------
        try:
            print("[*] 尝试自动拟真拖拽处理...")

            success = await self.dragger.drag(
                page,
                slider_selector,
                target_x_offset,
            )

            if success:
                # 成功后：连续失败次数 清零
                self.slider_auto_fail_count = 0

                cooldown_seconds = random.uniform(*self.cooldown_range)

                print(f"[+] 自动处理成功，冷却 {cooldown_seconds:.1f} 秒")

                await asyncio.sleep(cooldown_seconds)

                return True

            else:
                raise Exception("滑块验证失败")

        except Exception as exc:
            print(f"[-] 自动处理失败: {exc}")

            # 自动失败次数累计
            self.slider_auto_fail_count += 1

            print(f"[!] 自动失败次数:{self.slider_auto_fail_count}/{self.max_slider_auto_fail_count}")

            # 达到自动失败阈值，进入人工验证
            if self.max_slider_auto_fail_count != -1 and self.slider_auto_fail_count >= self.max_slider_auto_fail_count:
                print("[!!!] 自动滑块连续失败达到阈值，进入人工验证")

                await self.wait_manual_verification()

                # 人工处理完成后，重置自动失败次数
                self.slider_auto_fail_count = 0

                # return True
                return await self._verify_manual_success(page)

            # 未达到人工阈值
            return False

    async def wait_manual_verification(self):
        """
        等待人工完成滑块验证。
        """

        print("[!!!] 自动滑块处理达到人工介入条件，进入人工验证模式")

        print("⚠️ 请切换浏览器窗口，手动完成滑块验证")

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, input, "✅ 完成验证后，请按回车继续采集...")

    async def _verify_manual_success(self, page):
        """
        验证人工滑块是否完成。
        """

        try:
            # 示例
            await page.wait_for_selector(".success", timeout=5000)

            return True

        except Exception:
            return False

    def reset(self):
        """
        重置当前用户采集状态。

        用于:
        1. 新用户开始采集
        2. 登录流程重新开始
        3. 任务重新启动
        """

        self.slider_trigger_count = 0

        self.slider_auto_fail_count = 0
