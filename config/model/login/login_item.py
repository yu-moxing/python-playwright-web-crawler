"""
登录(LOGIN) 配置对象

本模块仅定义配置文件中 LOGIN_ 前缀对应的数据结构。

职责：
    - 保存登录流程相关配置（登录开关、滑块验证、人类轨迹库、阈值、各登录入口）
    - 对应 ScriptConfig 中 LOGIN_* 配置
    - 不参与数据库存储

说明：
    本对象属于"Crawler 配置层"，
    仅表示脚本配置，不表示采集结果。
"""

from dataclasses import dataclass


@dataclass(slots=True)
class LoginItem:
    """
    LOGIN 配置对象

    对应配置文件：

        LOGIN_HIDE_URL_PREFIX
        LOGIN_NEED_LOGIN
        LOGIN_SLIDER_ENABLED
        LOGIN_SLIDER_TYPE
        LOGIN_SLIDER_SHOW_MODE
        LOGIN_HUMAN_SLIDER_TRACK_ENABLED
        LOGIN_MAX_SLIDER_TRIGGER_COUNT
        LOGIN_MAX_SLIDER_AUTO_FAIL_COUNT
        LOGIN_HOME_ENABLE
        LOGIN_HOME_URL
        LOGIN_USER_PASSWORD_ENABLE
        LOGIN_USER_PASSWORD_URL
        LOGIN_QR_CODE_ENABLE
        LOGIN_QR_CODE_URL
        LOGIN_SMS_CODE_ENABLE
        LOGIN_SMS_CODE_URL

    开关类字段取值 0/1（int）；
    LOGIN_SLIDER_TYPE 取值 IMAGE_SLIDER_GAP，
    LOGIN_SLIDER_SHOW_MODE 取值 PRESS_LONGI_BTN_BEFORE / PRESS_LONGI_BTN_AFTER，
    由 login_loader.validate_login_config 校验。
    阈值类字段保留原始字符串，由 parse_threshold_range 校验格式。
    """

    # ========== URL 前缀隐藏 ==========
    hide_url_prefix: str = ""

    # ========== 登录总开关 ==========
    need_login: int = 1

    # ========== 登录滑块 ==========
    slider_enabled: int = 0
    slider_type: str = ""
    slider_show_mode: str = ""

    # ========== 人类轨迹库 ==========
    human_slider_track_enabled: int = 0

    # ========== 阈值（原始字符串，validate 阶段校验格式）==========
    max_slider_trigger_count: str = "-1"
    max_slider_auto_fail_count: str = "-1"

    # ========== 首页：用户名密码登录 ==========
    home_enable: int = 0
    home_url: str = ""

    # ========== 用户名密码独立登录页 ==========
    user_password_enable: int = 0
    user_password_url: str = ""

    # ========== 二维码登录页 ==========
    qr_code_enable: int = 0
    qr_code_url: str = ""

    # ========== 短信验证码登录页 ==========
    sms_code_enable: int = 0
    sms_code_url: str = ""
