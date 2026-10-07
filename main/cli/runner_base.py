"""
采集入口公共脚手架

从 cate_level.py 抽出的、与采集类型无关的通用入口件，供 cate_list 等入口复用，
避免各入口复制整段脚手架代码。

包含:

    - create_logger(name, log_dir, project_id, level)
    - setup_directories(project_dir, logger)
    - load_configs(project_loader, logger) -> (script_config, project_config, pool_data, pool_loader)

说明:

    create_logger 为全项目唯一实现（cate_level / cate_list 等入口统一 import），
    内含 root 路由：leaf 模块日志靠传播到 root 输出，并按当前阶段（全局 logs/
    或站点 site/<id>/logs/）落盘。
"""

from __future__ import annotations

import logging
import os
from resource import PoolLoader, PoolLoadError

from config.loader.script_config import (
    parse_script_config,
    print_config_summary,
)
from constants.path_const import LOGS_DIR_NAME, SCRIPT_INFO_FILE_NAME

# root logger 上由本模块管理的 handler 的识别标签，用于幂等添加 / 阶段切换。
_PPW_CONSOLE_TAG = "_ppw_console"
_PPW_FILE_TAG = "_ppw_file"


def _setup_root(formatter, level, file_handler=None):
    """
    配置根 logger：保证控制台 handler 幂等存在，并按当前阶段切换文件 handler。

    - 控制台 handler：仅添加一次（打 _PPW_CONSOLE_TAG），接收所有传播到 root 的日志。
    - 文件 handler：用 file_handler 切换。传入时移除 root 上旧的同标签文件 handler，
      把当前 file_handler 打标签后挂到 root（复用 named logger 已建的那个实例），
      使 leaf 模块日志按当前阶段（全局 logs/ 或站点 site/<id>/logs/）落盘。
      传 None 时仅保证控制台基线，不动文件 handler。
    """
    root = logging.getLogger()
    root.setLevel(level)

    # 控制台 handler 幂等添加
    if not any(getattr(h, _PPW_CONSOLE_TAG, False) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        setattr(console, _PPW_CONSOLE_TAG, True)
        root.addHandler(console)

    if file_handler is None:
        return

    # 切换文件 handler：移除旧的，挂上新的
    for h in list(root.handlers):
        if getattr(h, _PPW_FILE_TAG, False):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass

    file_handler.setFormatter(formatter)
    setattr(file_handler, _PPW_FILE_TAG, True)
    root.addHandler(file_handler)


# 项目根目录：main/cli/runner_base.py 向上三级
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_logger(name, log_dir, project_id, level=logging.INFO):
    """
    创建独立的日志记录器。

    日志文件按“日期 + 项目 ID + Logger 名称”命名：

        YYYYMMDD_PROJECT_ID_NAME.log

    例如：

        20260815_1001-001_main.log

    同一天、同一个项目、同一个 Logger 会继续追加到同一个日志文件。

    Args:
        name: 日志记录器名称。
        log_dir: 日志文件目录。
        project_id: 项目 ID，例如 "1001-001"。
        level: 日志级别。

    Returns:
        logging.Logger: 已配置的日志记录器实例。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 禁止日志向上传播到根 Logger，避免重复输出。
    logger.propagate = False

    # 日志格式（无论是否新建 handler，root 基线都需用到）
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 若 handler 已存在，直接返回，避免重复添加。仍保证 root 控制台基线。
    if logger.handlers:
        _setup_root(formatter, level, None)
        return logger

    # 当前日期，例如：20260815
    date_str = _today_str()

    # 日志文件名：20260815_1001-001_main.log
    log_filename = f"{date_str}_{project_id}_{name}.log"
    log_file = os.path.join(log_dir, log_filename)

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 文件处理器（named logger 与 root 复用同一实例：named logger 直接写、
    # leaf 模块日志传播到 root 经此 handler 落盘当前阶段文件）
    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # root 基线 + 阶段文件路由（leaf 模块日志靠传播到 root 输出）
    _setup_root(formatter, level, file_handler)

    return logger


def setup_directories(project_dir: str, logger: logging.Logger):
    """
    创建必要的目录

    说明:
        大部分目录已在 ProjectConfigLoader.load_configs() 中创建。
        此函数用于创建项目额外目录。

    参数:
        project_dir: 项目目录路径
        logger: 日志记录器实例
    """
    dirs = [
        "backup",
    ]

    for dir_name in dirs:
        dir_path = os.path.join(project_dir, dir_name)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")


def load_configs(project_loader, logger: logging.Logger) -> tuple:
    """
    加载配置文件

    参数:
        project_loader: 项目配置加载器
        logger: 日志记录器实例

    返回:
        (脚本配置, 项目配置, 资源池数据, 资源池加载器)
        注意：此处不再创建 ResourceAllocator，交由 main() 在完成选定用户校验后创建，
        以便选定用户的 scoped 校验（浏览器池/IP 池）先于全量校验作为权威闸门。
    """
    project_config = project_loader.load_configs()

    script_file = project_config.script_file_path
    user_file = project_config.user_pool_file_path

    full_id = project_config.full_id
    main_id = project_config.main_id
    sub_id = project_config.sub_id

    site_name = project_config.site_name
    content_type = project_config.content_type

    logger.info("=" * 60)
    logger.info("Loading configuration - Category collection")
    logger.info(f"Full project ID: {full_id}")
    logger.info(f"Main ID: {main_id}")
    logger.info(f"Sub ID: {sub_id}")

    logger.info(f"Site Name: {site_name}")
    logger.info(f"Content Type: {content_type}")
    logger.info(f"Script file: {script_file}")
    logger.info(f"User pool: {user_file}")
    logger.info("=" * 60)

    # Load resource pool (using main_id, shared across sub-projects)
    logger.info("Loading resource pool...")

    pool_dir = os.path.join(BASE_DIR, "pool")
    pool_loader = PoolLoader(pool_dir=pool_dir)
    try:
        pool_data = pool_loader.load_all(
            project_id=main_id, project_dir=project_config.project_dir_path, browser_type=0
        )
    except PoolLoadError:
        logger.exception("Resource pool load failed")
        raise

    logger.info("已成功加载资源池数据（Resource pool loaded successfully）")
    logger.info(f"  可用用户数量（Available users）: {len(pool_data.users)}")
    logger.info(f"  用户索引（User indices）: {sorted(pool_data.users.keys())}")

    # 生成项目变量字典
    program_vars = project_loader.get_program_vars()
    logger.info(f"项目变量（Project variables）: {program_vars}")

    script_config = parse_script_config(script_file, program_vars)
    summary_file = os.path.join(project_config.project_dir_path, LOGS_DIR_NAME, SCRIPT_INFO_FILE_NAME)
    print_config_summary(script_config, output_file=summary_file)
    logger.info(f"配置摘要已写入（Config summary written to）: {summary_file}")

    return script_config, project_config, pool_data, pool_loader


def _today_str() -> str:
    """返回今日 YYYYMMDD（封装以便测试时替换，且避免在模块顶层调用 datetime）。"""
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d")
