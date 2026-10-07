"""
分类相关公共常量。
"""

CATEGORY_FIELD_SEPARATOR = "------------"
CATEGORY_INDEX_SEPARATOR = "#"

CATEGORY_LEVEL_SEPARATOR = "--"
CATEGORY_DATA_SEPARATOR = ">>>"
CATEGORY_LIMIT_SEPARATOR = ">"


# 分类层级
CATE_LEVEL_COUNT = 5
MAX_CATE_LEVEL_INDEX = CATE_LEVEL_COUNT - 1
MIN_CATE_LEVEL_INDEX = 0

# 特殊分类 ID
OTHER_CATE_ID = 999

# 分类 ID 固定长度
CATE_ID_LENGTH = 3

# =========================================================
# Redis Value
# =========================================================

# 分类链接已经采集完成
# 已经到达分类分页末尾/确定没有下一页
STATUS_COMPLETED_END = "COMPLETED_END"

# 连续页面采集到相同的 items
# 发现后续页面反复返回 Redis / MongoDB 中已经存在的数据，因此停止继续翻页
STATUS_SAME_ITEMS_END = "SAME_ITEMS_END"
