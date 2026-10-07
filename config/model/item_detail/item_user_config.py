"""
item_detail 用户池数据模型

与 cate_list 的 UserConfig 区别：

    cate_list user_pool.xlsx 列结构（index 0-8）：
        index / username / password / browser_type / browser_index /
        ip_spec / clli / clii / so

    item_detail user_pool.xlsx 列结构（index 0-6）：
        index / username / password / browser_type / browser_index /
        ip_spec / id_i

    即 item_detail 用 id_i 替换了 cate_list 的 clli 位置（row[6]），
    且不再有 clii / so 两列。故不能直接复用 resource.UserConfig。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ItemUserConfig:
    """
    item_detail 用户池单行配置。

    属性：
        index:          用户索引（Excel 第 1 列，row[0]）
        username:       用户名（row[1]）
        password:       密码（row[2]）
        browser_type:   浏览器类型（row[3]）
        browser_index:  浏览器索引（row[4]）
        ip_spec:        IP 池索引规格（row[5]，必填）
        id_i:           item_list_link 索引范围原始字符串（row[6]），
                        取值为 -1 / 非负整数 / N-M / ut（ut 仅作占位标记，
                        由 CLI 预备层解析为最终 ItemIndexSpec）。
    """

    index: int
    username: str
    password: str
    browser_type: int
    browser_index: int
    ip_spec: str
    id_i: str = "-1"
