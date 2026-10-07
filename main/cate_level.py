"""
分类采集启动入口

本脚本用于采集网站分类列表（多级分类）。

使用方法：
    python cate_level.py <项目编号>

    # 示例
    python cate_level.py 1001-001        # 加载 1001-001-xxx 目录下的配置

项目目录结构（新格式）：
    K:/scrapy_test/Python-PlayWright-Web/site\
    ├── 1001-001-dangdang_com-product-zh_cn\
    │   ├── script/                    # 脚本文件目录
    │   │      └── script.txt
    │   ├── logs/                      # 项目日志 (+)
    │   ├── input/                     # 输入文件 (+)
    │   ├── user/                      # 用户目录 (+)
    │   │      ├── 0/                  # 用户索引号0 (+)
    │   │      │      ├── cookie/      # 浏览器cookie (+)
    │   │      │      ├── local-storage/    # (+)
    │   │      │      └── session-storage/  # (+)
    │   │      └── user_pool.xlsx
    │   ├── output/brand_dict/         # 品牌名词典 (+)
    │   ├── output/cate_level_link/    # 分类链接 (+)
    │   ├── output/cate_level_index/   # 分类索引 (+)
    │   └── output/link/               # 链接 (+)
    ├── pool/                          # 资源池目录
    │   ├── browser_pool_0_chromium.xlsx       # 浏览器池
    │   ├── browser_fingerprint_0_chromium.xlsx # 指纹池
    │   └── ip_pool.xlsx                      # IP 池
    ├── resource/                      # 资源调度模块
    └── cate_level.py

    (注：带 (+) 的目录在项目初始化时自动创建)

资源调度流程：
    PoolLoader.load_all(project_id, project_dir) → ResourceAllocator.allocate(user_index) → ResourceContext
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, BASE_DIR)

# 导入资源调度模块
from resource import (
    PoolLoader,
    PoolLoadError,
    ResourceAllocator,
    ResourceContext,
    ResourceMapper,
    ResourceNotFoundError,
    ResourceValidationError,
)

from config.loader.project_loader import (
    ProjectConfigLoader,
    ProjectNotFoundError,
)
from config.loader.script_config import (
    ScriptConfig,
    parse_script_config,
    print_config_summary,
)
from constants.path_const import LOGS_DIR_NAME, SCRIPT_INFO_FILE_NAME, USER_POOL_FILE_NAME

from fileio.file_backup import backup
from main.cli.args_parser import parse_cli_args
from main.cli.args_utils import parse_cate_indexes
from main.cli.runner_base import create_logger
from processor.cate_level.cate_level_runner import run_cate_level

# ================= Logging Configuration =================
# create_logger 统一由 main.cli.runner_base 提供（含 root 路由），本入口直接复用。


# ================= Business Logic =================


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
    # 项目目录下的目录（已在 project_loader.py 中创建）
    # 这里可以创建其他必要的目录（如备份目录等）
    dirs = [
        "backup",
    ]

    for dir_name in dirs:
        dir_path = os.path.join(project_dir, dir_name)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")


def load_configs(project_loader: ProjectConfigLoader, logger: logging.Logger) -> tuple:
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

    # 动态计算文件路径
    # script_file = os.path.join(project_config.project_dir_path, "script", "script.txt")
    script_file = project_config.script_file_path
    # user_file = os.path.join(project_config.project_dir_path, "user", "user_pool.xlsx")
    user_file = project_config.user_pool_file_path

    full_id = project_config.full_id  # Use full_id for export/logging
    main_id = project_config.main_id  # Use main_id for resource pool
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


def execute_cate_level(
    resource_context: ResourceContext,
    script_config: ScriptConfig,
    project_config,
    logger: logging.Logger,
    cate_indexes: dict = None,
):
    """
    执行分类树采集任务

    负责:
        - 接收资源上下文
        - 调用分类处理器
        - 管理单次分类采集流程

    参数:
        resource_context: 当前用户的完整资源上下文（无用户模式时 user=None）
        script_config: 脚本配置对象
        project_config: 项目配置对象
        logger: 日志记录器实例
        cate_indexes: 分类范围过滤参数（透传给 Playwright 采集 runner run_cate_level）
    """
    logger.info("=" * 60)
    logger.info("开始分类树采集（Starting category level collection）")
    logger.info(f"完整项目ID（Full project ID）: {project_config.full_id}")
    logger.info("=" * 60)

    logger.info("使用资源调度系统--Using resource scheduling system (PoolLoader + ResourceAllocator)")

    username = resource_context.user.username if resource_context.user else "no_user"

    # 是否备份现由 SYSTEM_NEED_BACKUP 配置驱动（script_config.system.need_backup）
    if script_config.system.need_backup == 1 and os.path.exists(project_config.cate_level_link_file_path):
        backup_path = backup(
            project_config.cate_level_link_file_path,
            project_config.backup_cate_level_link_dir_path,
        )
        logger.info(f"备份现有数据（Backup existing data）: {backup_path}")

    logger.info(
        f"分配资源（Allocate resource）: user {resource_context.user.index if resource_context.user else 'no_user'}"
    )
    logger.info(f"  Username: {username}")
    logger.info(f"  Browser index: {resource_context.browser.index}")
    logger.info(f"  Browser profile: {resource_context.browser.user_data_dir}")
    logger.info(f"  Proxy: {resource_context.get_proxy_string() or 'None'}")

    logger.info(f"开始采集分类树 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run category level collector
    try:
        run_cate_level(
            script_config=script_config,
            resource_context=resource_context,
            cate_indexes=cate_indexes,
            cate_level_index_file_path=project_config.cate_level_index_file_path,
            cate_level_link_file_path=project_config.cate_level_link_file_path,
            logger=logger,
        )

    except Exception:
        logger.exception("分类树采集失败")
        raise

    logger.info(f"分类树采集完成 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ================= Main Entry =================


def main():
    """Main function - Category collection"""

    # ============================================================
    # 1. 解析命令行参数
    # ============================================================
    run_args = parse_cli_args()

    full_project_id = run_args.project_id

    # ============================================================
    # 2. 创建总项目 Logger
    #
    # 日志目录：
    # K:\scrapy_test\Python-PlayWright-Web\logs
    #
    # 用于记录整个 Python-PlayWright-Web 项目的启动及运行信息。
    # ============================================================
    main_logger = create_logger(
        name="cate_level",
        log_dir=os.path.join(BASE_DIR, "logs"),
        project_id=full_project_id,
    )

    # ============================================================
    # 3. Log startup info
    # ============================================================
    main_logger.info("=" * 60)
    main_logger.info("Python-PlayWright-Web - Category Level collection mode")
    main_logger.info("=" * 60)

    main_logger.info(f"环境--Environment: {run_args.env}")
    main_logger.info(f"预设--Preset: {run_args.preset}")
    main_logger.info(f"项目ID--Project ID: {full_project_id}")
    main_logger.info(f"用户索引--User indexes: {run_args.user_indexes}")

    if run_args.cli_is_ut:
        main_logger.info("分类参数--clli: ut（按用户取 user_pool.xlsx 第7列 cate link index 的值）")
    else:
        main_logger.info(f"目录索引--Cate indexes: {run_args.cate_indexes}")

    main_logger.info(f"--- 开始执行项目（Start executing project）: {full_project_id} (env={run_args.env}) ---")

    # ============================================================
    # 4. 创建项目配置加载器
    # ============================================================
    project_loader = ProjectConfigLoader(full_project_id)

    try:
        # ========================================================
        # 5. 加载项目配置、脚本配置、资源池
        #
        # 这里会得到 project_config.project_dir_path
        # ========================================================
        (
            script_config,
            project_config,
            pool_data,
            pool_loader,
        ) = load_configs(
            project_loader,
            main_logger,
        )

        # ========================================================
        # 6. 创建当前采集项目 Logger
        #
        # 日志目录：
        # K:\scrapy_test\Python-PlayWright-Web\site\
        #   1001-001-dangdang_com-product-zh_cn\logs
        #
        # 这里必须使用 project_config.project_dir_path，
        # 因为项目目录名称包含 site_name / content_type 等信息。
        # ========================================================
        project_logger = create_logger(
            name=f"project_{full_project_id}",
            log_dir=os.path.join(
                project_config.project_dir_path,
                LOGS_DIR_NAME,
            ),
            project_id=full_project_id,
        )

        project_logger.info("=" * 60)
        project_logger.info(f"开始执行项目（Start executing project）: {full_project_id}")
        project_logger.info(f"环境--Environment: {run_args.env}")
        project_logger.info(f"预设--Preset: {run_args.preset}")
        project_logger.info(f"项目目录--Project directory: {project_config.project_dir_path}")
        project_logger.info("=" * 60)

        # ========================================================
        # 7. 创建项目所需目录
        # ========================================================
        setup_directories(
            project_config.project_dir_path,
            project_logger,
        )

        # ========================================================
        # ============ 用户索引校验 ============
        #
        # 校验规则：
        #   1. u -1（无有效用户索引）且 LOGIN_NEED_LOGIN=1
        #      → 冲突，报错退出
        #
        #   2. u 给了具体索引，但用户表中一个都没匹配
        #      → 报错退出
        #
        #   3. 部分匹配
        #      → 未命中者记 warning
        #      → 继续采集命中的用户
        #
        #   4. 对命中的用户新增两项硬性校验
        #      → 浏览器池
        #      → IP 池
        # ========================================================

        need_login = script_config.login.need_login
        requested = run_args.user_indexes
        user_raw = run_args.user_arg_raw
        available = set(pool_data.users.keys())
        pool_name = USER_POOL_FILE_NAME

        # ========================================================
        # 8. 无用户模式：u -1
        # ========================================================
        if not requested:
            # LOGIN_NEED_LOGIN=1 时必须指定用户
            if need_login == 1:
                project_logger.error(
                    "命令行参数：u -1 没有指定用户索引，而配置文件：LOGIN_NEED_LOGIN 值为 1。要求登录后才能采集。"
                )
                return

            # LOGIN_NEED_LOGIN=0：无用户模式
            project_logger.info(
                "未选择用户，在无用户模式下运行 "
                "（No user selected, running in no-user mode）"
                "（浏览器索引0，无代理--browser index 0, no proxy）"
            )

            try:
                resource_allocator = ResourceAllocator(
                    pool_data,
                    project_config.main_id,
                    project_config.project_dir_path,
                )
            except ResourceValidationError:
                project_logger.exception("资源验证失败（Resource validation failed）")
                return

            resource_context = resource_allocator.allocate_no_user()

            execute_cate_level(
                resource_context=resource_context,
                script_config=script_config,
                project_config=project_config,
                logger=project_logger,
                cate_indexes=run_args.cate_indexes,
            )

        # ========================================================
        # 9. 指定用户模式
        # ========================================================
        else:
            # 与可用用户取交集
            selected = [i for i in requested if i in available]

            skipped = [i for i in requested if i not in available]

            # ----------------------------------------------------
            # 记录不存在的用户索引
            # ----------------------------------------------------
            for idx in skipped:
                project_logger.warning(f"用户索引 {idx} 在用户表 {pool_name} 中不存在，已跳过")

            # ----------------------------------------------------
            # 一个用户都没有匹配上
            # ----------------------------------------------------
            if not selected:
                if len(requested) > 1:
                    project_logger.error(
                        f"在用户表：{pool_name} 中，没有找到任意一个与启动参数 u {user_raw} 匹配的用户索引。"
                    )
                else:
                    project_logger.error(f"在用户表：{pool_name} 中，没有找到与启动参数 u {user_raw} 匹配的用户索引。")

                return

            # ====================================================
            # 10. 命中用户的硬性校验
            # ====================================================
            check_errors = []

            # cli=ut 时：
            # user_index -> 解析后的分类范围
            user_cate_indexes = {}

            for user_index in selected:
                user = pool_data.users[user_index]

                # ------------------------------------------------
                # 检查一：
                # 浏览器池文件存在 / ≥2行 /
                # 含该用户 browser_index
                # ------------------------------------------------
                try:
                    pool_loader.validate_user_browser(user)
                except (
                    PoolLoadError,
                    ResourceNotFoundError,
                ) as e:
                    check_errors.append(str(e))

                # ------------------------------------------------
                # 检查二：
                # 用户 IP 池索引规格全部存在
                # ------------------------------------------------
                ip_err = ResourceMapper.validate_user_ip(
                    user,
                    pool_data,
                )

                if ip_err:
                    check_errors.append(ip_err)

                # ------------------------------------------------
                # 检查三：
                # cli=ut 时读取用户表第7列
                # cate link index
                # ------------------------------------------------
                if run_args.cli_is_ut:
                    raw_cli = user.cate_link_index

                    try:
                        user_cate_indexes[user_index] = parse_cate_indexes(raw_cli)
                    except argparse.ArgumentTypeError as e:
                        check_errors.append(
                            f"用户 {user_index}({user.username}) 的 cate link index 值 '{raw_cli}' 格式错误：{e}"
                        )

            # ====================================================
            # 11. 用户资源校验失败
            # ====================================================
            if check_errors:
                project_logger.error(
                    "选定用户的资源校验失败（Selected users resource validation failed），已终止采集："
                )

                for err in check_errors:
                    project_logger.error(f"  - {err}")

                return

            # ====================================================
            # 12. 全量资源校验
            # ====================================================
            try:
                resource_allocator = ResourceAllocator(
                    pool_data,
                    project_config.main_id,
                    project_config.project_dir_path,
                )
            except ResourceValidationError:
                project_logger.exception("资源验证失败（Resource validation failed）")
                return

            # ====================================================
            # 13. 逐个用户执行分类采集
            # ====================================================
            for user_index in selected:
                resource_context = resource_allocator.allocate(user_index)

                # cli=ut：
                # 使用用户第7列解析出的分类范围
                #
                # 否则：
                # 使用命令行 clli 分类范围
                if run_args.cli_is_ut:
                    cate_idx = user_cate_indexes.get(user_index)
                else:
                    cate_idx = run_args.cate_indexes

                execute_cate_level(
                    resource_context=resource_context,
                    script_config=script_config,
                    project_config=project_config,
                    logger=project_logger,
                    cate_indexes=cate_idx,
                )

        # ========================================================
        # 14. 分类采集完成
        # ========================================================
        project_logger.info("=" * 60)
        project_logger.info(f"分类树已经采集完成（Category Level collection completed） - Project {full_project_id}")
        project_logger.info("=" * 60)

        # 总项目 Logger 也记录完成状态
        main_logger.info(f"分类树采集完成（Category Level collection completed） - Project {full_project_id}")

    # ============================================================
    # 15. 项目配置不存在
    # ============================================================
    except ProjectNotFoundError as e:
        main_logger.error(f"项目配置错误（Project configuration error）: {e}")

        main_logger.info("请检查项目ID是否正确（Please check if project ID is correct）")

        return

    # ============================================================
    # 16. 其他未处理异常
    # ============================================================
    except Exception:
        main_logger.exception("执行失败（Execution failed）")


if __name__ == "__main__":
    # main() 为同步函数
    # allocate/load_configs/execute_cate_level 均为同步调用
    main()
