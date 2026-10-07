"""
风控(RISK) 配置对象

本模块仅定义配置文件中 RISK_ 前缀对应的数据结构。

职责：
    - 保存采集过程中风控滑块相关配置（滑块开关、类型、人类轨迹库、阈值）
    - 对应 ScriptConfig 中 RISK_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class RiskItem:
    """
    RISK 配置对象

    对应配置文件：

        RISK_SLIDER_CHECK_DIALOG
        RISK_SLIDER_CHECK_MODE
        RISK_SLIDER_VERIFY_URL_KEYWORDS
        RISK_SLIDER_SHOW_NEXT_ACTION
        RISK_SLIDER_TYPE
        RISK_HUMAN_SLIDER_TRACK_ENABLED
        RISK_MAX_SLIDER_TRIGGER_COUNT
        RISK_MAX_SLIDER_AUTO_FAIL_COUNT

    开关类字段取值 0/1（int）；
    RISK_SLIDER_TYPE 取值 IMAGE_SLIDER_GAP，
    由 risk_loader.validate_risk_config 校验（仅当 RISK_SLIDER_CHECK_DIALOG=1 时生效）。
    阈值类字段保留原始字符串，由 parse_threshold_range 校验格式。
    """

    # ========== 风控滑块检测 ==========
    # 是否检测滑块验证窗口（0：不检测；1：检测）
    slider_check_dialog: int = 0
    # 滑块检测方式：DOM / URL / 空（仅当 slider_check_dialog=1 时生效）
    slider_check_mode: str = ""
    # URL 检测关键字（逗号分隔；slider_check_mode=URL 时不能为空）
    slider_verify_url_keywords: str = ""
    # 检测到验证窗口后的下一步操作：PAUSE / AUTO / EXIT / 空
    slider_show_next_action: str = ""

    # ========== 风控滑块类型 ==========
    slider_type: str = ""

    # ========== 人类轨迹库 ==========
    human_slider_track_enabled: int = 0

    # ========== 阈值（原始字符串，validate 阶段校验格式）==========
    max_slider_trigger_count: str = "-1"
    max_slider_auto_fail_count: str = "-1"
