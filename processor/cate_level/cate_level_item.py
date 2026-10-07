"""
分类项数据处理模块

职责：
    - 构造分类层 Item（dict）
    - 对分类项列表按字段去重

设计原则：
    - 本模块只做纯数据处理，不读写文件、不依赖 fileio
    - 文件 I/O 由调用方 CateLevelItemHandler.flush() 用 TxtBatchFile 完成
    - Item 为扁平 dict，键为 level_0/level_1/level_2/level_3/link，
      值约定为 "标题##ID" 或占位 "00"
    - create_item() 当前未被 cate_level 运行链路调用（预留工具方法）
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def create_item(
    level_0: str = "00",
    level_1: str = "00",
    level_2: str = "00",
    level_3: str = "00",
    level_4: str = "00",
    link: Optional[str] = None,
) -> Dict[str, str]:
    """
    创建分类数据项

    Args:
        level_0: 主分类（0级）
        level_1: 1级分类
        level_2: 2级分类
        level_3: 3级分类
        level_4: 4级分类
        link: 分类链接（可选）

    Returns:
        数据字典

    Example:
        >>> item_detail = create_item('女装##123', '连衣裙##456', '长袖##789','圆领##1012', '00')
    """
    item = {
        "level_0": level_0 if level_0 else "00",
        "level_1": level_1 if level_1 else "00",
        "level_2": level_2 if level_2 else "00",
        "level_3": level_3 if level_3 else "00",
        "level_4": level_4 if level_4 else "00",
    }

    if link:
        item["link"] = link

    return item
