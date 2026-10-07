"""
Page 配置对象

本模块定义配置文件中 PAGE_ 前缀对应的数据结构。

职责：
    - 保存各页面类型（HOME/LOGIN/RISK/CATE_LEVEL/CATE_LIST/DETAIL）的就绪检测选择器
    - 对应 ScriptConfig 中 PAGE_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
    各选择器均可为空（空表示该页面类型不启用就绪元素等待）。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class PageItem:
    """
    PAGE 配置对象

    对应配置文件：

        PAGE_HOME_READY_SELECTOR
        PAGE_LOGIN_READY_SELECTOR
        PAGE_RISK_READY_SELECTOR
        PAGE_CATE_LEVEL_READY_SELECTOR
        PAGE_CATE_LIST_READY_SELECTOR
        PAGE_DETAIL_READY_SELECTOR

    各字段为 CSS 选择器字符串，未配置时为空串；
    PageReadyChecker.wait 内通过 `if ready_selector:` 判断是否启用元素等待。
    """

    home_ready_selector: str = ""
    login_ready_selector: str = ""
    risk_ready_selector: str = ""
    cate_level_ready_selector: str = ""
    cate_list_ready_selector: str = ""
    detail_ready_selector: str = ""
