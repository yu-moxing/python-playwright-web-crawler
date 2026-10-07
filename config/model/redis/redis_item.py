"""
Redis(REDIS) 配置对象

本模块仅定义配置文件中 REDIS_ 前缀对应的数据结构。

职责：
    - 保存 Redis 相关配置（TTL、Key 前缀模板）
    - 对应 ScriptConfig 中 REDIS_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。

    Key 前缀模板中可能含运行时占位符 ${排序字段}，
    由 pro_var.py 的正则（仅匹配 ${PRO_...}）原样保留，
    交由运行期再替换。
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(slots=True)
class RedisItem:
    """
    REDIS 配置对象

    对应配置文件：

        REDIS_CONTENT_DEFAULT_TTL_S
        REDIS_CATE_LEVEL_SORT_HIDE_FIELD_TTL_S
        REDIS_CATE_LEVEL_SORT_FIELDS_TTL_S
        REDIS_CATE_LEVEL_DEFAULT_TTL_S
        REDIS_CATE_LIST_DEFAULT_TTL_S
        REDIS_USER_LOGGEDIN_TTL_S
        REDIS_USER_GUEST_TTL_S
        REDIS_PROXY_IP_LOGGEDIN_TTL_S
        REDIS_PROXY_IP_GUEST_TTL_S
        REDIS_CATE_LEVEL_LINK_ENABLE
        REDIS_CATE_LIST_LINK_ENABLE
        REDIS_CONTENT_ENABLE
        REDIS_CONTENT_HEAD_KEY
        REDIS_CATE_LEVEL_LINK_HEAD_KEY
        REDIS_CATE_LIST_LINK_HEAD_KEY
        REDIS_USER_HEAD_KEY
        REDIS_PROXY_IP_HEAD_KEY

    TTL 字段单位为秒；
    content/cate_level/cate_list 系列 TTL 为正整数；
    user/proxy_ip 系列 TTL 可取 -1（不启用缓存）或正整数；
    cate_level_sort_fields 为字段→TTL 映射，按配置书写顺序保序；
    *_enable 为缓存开关（1 启用 / 0 禁用）；
    head_key 为 Key 前缀模板，${排序字段} 占位符原样保留待运行期替换。
    """

    # ========== TTL（单位：秒） ==========
    # 内容默认缓存 TTL
    content_default_ttl: int = 604800
    # 隐藏排序字段的缓存 TTL
    cate_level_sort_hide_field_ttl: int = 604800
    # 各指定排序字段的缓存 TTL（字段→TTL 映射，按配置书写顺序保序，Python dict 3.7+ 保序）
    cate_level_sort_fields: Dict[str, int] = field(default_factory=dict)
    # 分类层默认缓存 TTL
    cate_level_default_ttl: int = 864000
    # 分类列表层默认缓存 TTL
    cate_list_default_ttl: int = 864000

    # 用户名缓存 TTL（Key: 用户索引+用户名；-1 不启用缓存）
    user_loggedin_ttl: int = -1
    user_guest_ttl: int = -1
    # 用户代理 IP 缓存 TTL（Key: 用户索引+用户名；-1 不启用缓存）
    proxy_ip_loggedin_ttl: int = -1
    proxy_ip_guest_ttl: int = -1

    # ========== 缓存开关（1 启用 / 0 禁用） ==========
    # 分类层链接缓存开关
    cate_level_link_enable: int = 1
    # 分类列表层链接缓存开关
    cate_list_link_enable: int = 1
    # 内容缓存开关
    content_enable: int = 1

    # ========== Key 前缀模板 ==========
    # CONTENT / CATE_LEVEL_LINK 含运行时占位符 ${排序字段}，原样保留待运行期替换
    content_head_key: str = ""
    cate_level_link_head_key: str = ""
    cate_list_link_head_key: str = ""
    # 用户名 / 代理IP 的 Key 前缀模板
    user_head_key: str = ""
    proxy_ip_head_key: str = ""
