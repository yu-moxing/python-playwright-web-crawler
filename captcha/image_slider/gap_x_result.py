from dataclasses import dataclass


@dataclass
class GapXResult:
    """
    图片滑块验证码缺口检测结果。
    """

    # 缺口X坐标
    gap_x: int

    # 滑块当前X坐标
    slider_x: int = 0

    # 需要移动距离
    distance: int = 0

    # 匹配可信度
    confidence: float = 0.0

    # 检测算法
    method: str = "contour"
