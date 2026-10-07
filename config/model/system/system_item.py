"""
系统(SYSTEM) 配置对象

本模块仅定义配置文件中 SYSTEM_ 前缀对应的数据结构。

职责：
    - 保存系统级采集配置（页面编码、采集方案、文件输出格式、自定义输出字段）
    - 对应 ScriptConfig 中 SYSTEM_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
"""

from dataclasses import dataclass, field
from typing import List

from constants.custom import CUSTOM_COUNT


@dataclass(slots=True)
class SystemItem:
    """
    SYSTEM 配置对象

    对应配置文件：

        SYSTEM_NEED_BACKUP
        SYSTEM_PAGE_ENCODE
        SYSTEM_CRAWL_PLAN
        SYSTEM_PAGE_LOAD_MAX_RETRIES
        SYSTEM_PAGE_READY_CHECK_ENABLED
        SYSTEM_PAGE_GOTO_TIMEOUT
        SYSTEM_PAGE_READY_TIMEOUT
        SYSTEM_PAGE_NETWORK_IDLE_ENABLED
        SYSTEM_PAGE_NETWORK_IDLE_TIMEOUT
        SYSTEM_ALL_FIELDS_SAVE_CSV
        SYSTEM_ALL_FIELDS_SAVE_JSON
        SYSTEM_ALL_FIELDS_SAVE_TXT
        SYSTEM_CUSTOM_0_FIELDS_LIST ~ SYSTEM_CUSTOM_4_FIELDS_LIST
        SYSTEM_CUSTOM_FIELDS_0_SAVE ~ SYSTEM_CUSTOM_FIELDS_4_SAVE

    开关类字段取值 0/1（int）；
    SYSTEM_CRAWL_PLAN 取值 ONLY_STATIC / ONLY_JSON / ONLY_BROWSER / BROWSER_JSON，
    由 system_loader.validate_system_config 校验。
    SYSTEM_CUSTOM_FIELDS_{i}_SAVE 取值 空 / CSV / EXCEL / JSON / JSONL / TXT 之一，
    自定义字段组数与保存项数均由 constants.custom.CUSTOM_COUNT 决定。
    """

    # ========== 系统版本号 ==========
    version: str = ""

    # ========== 页面编码 ==========
    page_encode: str = "UTF-8"

    # ========== 采集方案 ==========
    crawl_plan: str = "ONLY_BROWSER"

    # ========== 是否备份 ==========
    # 采集前是否备份现有数据（1=备份，0=不备份）
    need_backup: int = 1

    # ========== 页面准备检测 ==========
    # 页面加载失败最大重试次数
    page_load_max_retries: int = 3
    # 是否启用页面准备检测（1=开启，0=不检测）
    page_ready_check_enabled: int = 1
    # page.goto() 打开 URL 的最大等待超时（毫秒）
    page_goto_timeout: int = 30000
    # 页面关键元素等待超时时间（毫秒）
    page_ready_timeout: int = 15000
    # 是否启用网络空闲检测（1=开启，0=不检测）
    page_network_idle_enabled: int = 0
    # 网络空闲检测等待超时（毫秒），仅当 page_network_idle_enabled=1 时生效
    page_network_idle_timeout: int = 30000

    # ========== 全部字段输出格式 ==========
    all_fields_save_csv: int = 0
    all_fields_save_json: int = 1
    all_fields_save_txt: int = 1

    # ========== 自定义输出字段 ==========
    # 索引 0..CUSTOM_COUNT-1，对应 SYSTEM_CUSTOM_{i}_FIELDS_LIST
    custom_fields_lists: List[List[str]] = field(default_factory=lambda: [[] for _ in range(CUSTOM_COUNT)])
    # 索引 0..CUSTOM_COUNT-1，对应 SYSTEM_CUSTOM_FIELDS_{i}_SAVE
    # 每项为 list[str]，逗号分隔的导出格式（空 / CSV / EXCEL / JSON / JSONL / TXT 之一）
    custom_fields_saves: List[List[str]] = field(default_factory=lambda: [[] for _ in range(CUSTOM_COUNT)])
