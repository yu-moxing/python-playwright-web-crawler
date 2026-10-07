# 目标平均步长的 系数范围
MIN_SCROLL_STEP_FACTOR = 0.8
MAX_SCROLL_STEP_FACTOR = 0.95

# 空间上的“停止条件”
# 距离页面底部小于等于该值时，提前停止主动滚动。
# <= 0 表示禁用该功能。
SCROLL_BOTTOM_THRESHOLD = 800

# 最大滚动次数
MAX_SCROLL_TIMES = 16

# 当理论滚动次数超过 MAX_SCROLL_TIMES 时，
# 是否下一次直接滚动到底部。
SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED = True
