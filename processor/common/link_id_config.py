"""
分类链接 ID 配置工具

职责：

- 根据分类层级获取对应的 LINK_ID 提取正则
- 根据分类层级配置从 URL 中提取 LINK_ID
- 统一封装 script_config.cate_level 的层级配置访问

本模块不负责：

- 正则表达式底层执行
- URL 解析
- 分类链接去重
- 分类链接业务规则
- Writer / Collector / Handler 业务处理

数据流：

    script_config
          ↓
    get_level_link_id_regex()
          ↓
    LINK_ID regex
          ↓
    mini_text.regex_utils.extract_regex_key()
          ↓
    Link ID
"""

from __future__ import annotations

from mini_text.regex_utils import extract_regex_key


def get_level_link_id_regex(
    script_config,
    level: int,
) -> str:
    """
    获取指定分类层级的 LINK_ID 提取正则。

    分类层级与配置对应关系：

        level == 0
            → cate_level.level0_link_regex

        level >= 1
            → cate_level.level{level}.link_id_regex

    Args:
        script_config:
            ScriptConfig 配置对象。

        level:
            分类层级。

            例如：

                0
                1
                2
                3
                4

    Returns:
        str:
            当前分类层级对应的 LINK_ID 提取正则。

            如果配置不存在或正则为空，
            返回空字符串。
    """

    if script_config is None:
        return ""

    if level < 0:
        return ""

    cate_level = getattr(
        script_config,
        "cate_level",
        None,
    )

    if cate_level is None:
        return ""

    # =====================================================
    # Level 0
    # =====================================================

    if level == 0:
        return str(
            getattr(
                cate_level,
                "level0_link_regex",
                "",
            )
            or ""
        ).strip()

    # =====================================================
    # Level 1 ~ Level N
    # =====================================================

    level_config = getattr(
        cate_level,
        f"level{level}",
        None,
    )

    if level_config is None:
        return ""

    return str(
        getattr(
            level_config,
            "link_id_regex",
            "",
        )
        or ""
    ).strip()


def extract_link_id(
    *,
    script_config,
    url: str,
    level: int,
) -> str:
    """
    根据分类层级配置的 LINK_ID 正则，
    从 URL 中提取 LINK_ID。

    规则：

        1. 当前层级没有配置正则 → ""
        2. 正则匹配失败 → ""
        3. 匹配成功 → 返回 LINK_ID
    """

    if not url:
        return ""

    regex = get_level_link_id_regex(
        script_config,
        level,
    )

    if not regex:
        return ""

    return extract_regex_key(
        url,
        regex,
    )
