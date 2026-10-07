"""
项目路径常量

所有项目目录、资源文件路径统一定义。
"""

from pathlib import Path

# ==========================
# 项目根目录
# ==========================

PROJECT_DIR_PATH = Path(__file__).resolve().parent.parent

# ==========================
# 目录名称常量（仅名称，不含路径）
# 用于动态构建项目子目录路径
# ==========================

# 主项目 的：一级目录名
# POOL_DIR_NAME = "../pool"
POOL_DIR_NAME = "pool"
# LOGS_DIR_NAME = "../logs"
LOGS_DIR_NAME = "logs"
# SITE_DIR_NAME = "../site"  # 网站采集目录名称
SITE_DIR_NAME = "site"  # 网站采集目录名称

# 采集项目 的：一级目录名
SCRIPT_DIR_NAME = "script"
# TASKS_LOGS_DIR_NAME = "task_logs"
BACKUP_DIR_NAME = "backup"
INPUT_DIR_NAME = "input"
OUTPUT_DIR_NAME = "output"
LOGIN_DIR_NAME = "login"
USER_DIR_NAME = "user"

# 采集项目 的：二级目录名
BRAND_DICT_DIR_NAME = "brand_dict"
CATE_LEVEL_LINK_DIR_NAME = "cate_level_link"
CATE_LEVEL_INDEX_DIR_NAME = "cate_level_index"
LINK_DIR_NAME = "link"

# ==========================
# 文件名称常量
# ==========================

SCRIPT_FILE_NAME = "script.txt"
SCRIPT_INFO_FILE_NAME = "script_info.txt"
USER_POOL_FILE_NAME = "user_pool.xlsx"
IP_POOL_FILE_NAME = "ip_pool.xlsx"

# ==========================
# 保存文件的类型
# ==========================

CATE_LEVEL_INDEX_FILE_TYPE = "txt"
CATE_LEVEL_LINK_FILE_TYPE = "txt"

# 完整文件名=文件名+"."+文件类型
CATE_LEVEL_INDEX_FILE_NAME = "cate_level_index"
CATE_LEVEL_LINK_FILE_NAME = "cate_level_link"


# ==========================
# 基础目录
# ==========================

# SCRIPT_DIR = PROJECT_DIR / "script"
# LOG_DIR = PROJECT_DIR / "logs"


# ==========================
# 输入目录
# ==========================
# INPUT_DIR_PATH = PROJECT_DIR_PATH / INPUT_DIR_NAME

# 注：input 目录为预留目录，用于存放输入文件
# 用户池文件已移至 user 目录下


# ==========================
# 用户目录
# ==========================
# USER_DIR_PATH = PROJECT_DIR_PATH / USER_DIR_NAME
# 用户池文件
# USER_POOL_FILE_PATH = USER_DIR_PATH / USER_POOL_FILE_NAME


# ==========================
# 输出目录
# ==========================
# OUTPUT_DIR_PATH = PROJECT_DIR_PATH / OUTPUT_DIR_NAME
# 品牌词典
# BRAND_DICT_DIR_PATH = OUTPUT_DIR_PATH / BRAND_DICT_DIR_NAME
# 快速链接
# SPEED_LINK_DIR_PATH = OUTPUT_DIR_PATH / CATE_LEVEL_LINK_DIR_NAME
# 分类树
# CATE_LEVEL_DIR_PATH = OUTPUT_DIR_PATH / CATE_LEVEL_INDEX_DIR_NAME
# 链接
# LINK_DIR_PATH = OUTPUT_DIR_PATH / LINK_DIR_NAME


# ==========================
# 资源池目录
# ==========================

POOL_DIR_PATH = PROJECT_DIR_PATH / POOL_DIR_NAME

# 浏览器池
BROWSER_POOL_FILE_PATH = POOL_DIR_PATH / "browser_pool_0_chromium.xlsx"

# 指纹池
BROWSER_FINGERPRINT_FILE_PATH = POOL_DIR_PATH / "browser_fingerprint_0_chromium.xlsx"

# IP池
IP_POOL_FILE_PATH = POOL_DIR_PATH / IP_POOL_FILE_NAME


# ==========================
# 网站采集目录
# ==========================

# 各网站采集项目目录的根，形如 <项目根>/site/1001-001-dangdang_com-PRODUCT-zh_CN
SITE_DIR_PATH = PROJECT_DIR_PATH / SITE_DIR_NAME


# ==========================
# 登录脚本 Python 文件名称常量
# ==========================

# 登录首页（用户名密码登录入口）
LOGIN_HOME_PY_FILE_NAME = "login_home.py"

# 用户名密码登录页
LOGIN_USER_PASSWORD_PY_FILE_NAME = "login_user_password.py"

# 二维码登录页
LOGIN_QR_CODE_PY_FILE_NAME = "login_qr_code.py"

# 短信验证码登录页
LOGIN_SMS_CODE_PY_FILE_NAME = "login_sms_code.py"

# 鼠标--人类滑块轨迹数据文件名
LOGIN_HUMAN_SLIDER_TRACKS_FILE = "login_human_slider_tracks.json"

# 鼠标--风控/频率限制人类滑块轨迹数据文件名
RISK_HUMAN_SLIDER_TRACKS_FILE = "risk_human_slider_tracks.json"


# ==========================
# 用户存储子目录名称常量
# ==========================

COOKIE_DIR_NAME = "cookie"
LOCAL_STORAGE_DIR_NAME = "local-storage"
SESSION_STORAGE_DIR_NAME = "session-storage"


# ==========================
# 浏览器类型映射
# ==========================

# 浏览器类型ID -> 浏览器类型名
# 用于拼接浏览器池/指纹池文件名：browser_pool_{type}_{name}.xlsx
BROWSER_TYPE_NAMES = {
    0: "chromium",
    1: "chrome",
}


# ==========================
# 浏览器池文件名模板
# ==========================

# 格式: browser_pool_{type}_{name}.xlsx
# 例如: browser_pool_0_chromium.xlsx
BROWSER_POOL_FILE_TEMPLATE = "browser_pool_{type}_{name}.xlsx"
BROWSER_FINGERPRINT_FILE_TEMPLATE = "browser_fingerprint_{type}_{name}.xlsx"
