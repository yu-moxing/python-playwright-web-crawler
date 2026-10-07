"""
内容采集启动入口（cate_list）

镜像 cate_level.py 的四种命令行格式与资源调度流程，但分类参数为 clii
（cate level index id），语义不同于 cate_level 的 clli（cate level link index）：

    - clli（cate_level）：分类链接索引，clli=ut 读 user_pool.xlsx 第 7 列 cate link index。
    - clii（cate_list）：分类索引 id，对应 cate_level_index.txt；
      clii=ut 读 user_pool.xlsx 第 8 列 clii(cate level index id)。
      clii 的父级>子级匹配 cate_level_index.txt 每行 strs[0] 的 level0 id 与
      strs[1] 的 level1 id（具体过滤交由执行层，本入口仅解析透传）。

四种命令格式：

    格式1: python -m main.cate_list --dev p 1001-001 u -1 clii "-1>-1"
    格式2: python -m main.cate_list        p 1001-001 u -1 clii "-1>-1"   # 默认 dev
    格式3: python -m main.cate_list                                       # 默认 dev + 预设
    格式4: python -m main.cate_list --pro p 1001-001 u -1 clii "-1>-1"

执行层说明:

    本入口的 CLI 解析、资源调度、clii 解析均已完成；执行步骤调用
    processor.cate_list.cate_list_runner.run_cate_list，目前为占位
    （NotImplementedError），浏览器采集流程待后续实现。
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
from constants.path_const import LOGS_DIR_NAME, USER_POOL_FILE_NAME
from data.backfill.cate_level_link_data_backfill import CateLevelLinkDataBackfill
from data.loader.cate_level.cate_level_index_data_loader import CateLevelIndexDataLoader
from data.loader.cate_level.cate_level_link_data_loader import CateLevelLinkDataLoader
from main.cli.args_parser import parse_cli_args
from main.cli.args_utils import parse_cate_indexes
from main.cli.runner_base import create_logger, load_configs, setup_directories
from main.cli.sort_spec import SoValidationError, parse_and_validate_so
from processor.cate_list.cate_list_runner import run_cate_list

# ================= Business Logic =================


def execute_cate_list(
    resource_context: ResourceContext,
    env: str,
    script_config,
    project_config,
    logger: logging.Logger,
    link_items,
    index_empty: bool,
    cate_indexes: dict = None,
    so=None,
):
    """
    执行内容采集任务

    负责:
        - 接收资源上下文
        - 调用内容采集 runner
        - 管理单次内容采集流程

    参数:
        resource_context: 当前用户的完整资源上下文（无用户模式时 user=None）
        script_config: 脚本配置对象
        project_config: 项目配置对象
        logger: 日志记录器实例
        link_items: 回填后的分类链接列表（list[CateLevelLinkDataItem]，对所有用户共享）
        index_empty: 分类索引文件是否为空（为空时 clii 过滤失效）
        cate_indexes: 分类范围过滤参数（clii 解析得到的 {"parents","children"}，透传给 runner）
        so: 排序参数（SoSpec 或 None，透传给 runner）
    """
    logger.info("=" * 60)
    logger.info("开始内容采集（Starting content collection）")
    logger.info(f"完整项目ID（Full project ID）: {project_config.full_id}")
    logger.info("=" * 60)

    logger.info("使用资源调度系统--Using resource scheduling system (USE_RESOURCE_SCHEDULER=True)")

    username = resource_context.user.username if resource_context.user else "no_user"

    logger.info(
        f"分配资源（Allocate resource）: user {resource_context.user.index if resource_context.user else 'no_user'}"
    )
    logger.info(f"  Username: {username}")
    logger.info(f"  Browser index: {resource_context.browser.index}")
    logger.info(f"  Browser profile: {resource_context.browser.user_data_dir}")
    logger.info(f"  Proxy: {resource_context.get_proxy_string() or 'None'}")

    logger.info(f"开始内容采集 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run content collection
    try:
        run_cate_list(
            env=env,
            script_config=script_config,
            resource_context=resource_context,
            cate_indexes=cate_indexes,
            link_items=link_items,
            index_empty=index_empty,
            so=so,
            logger=logger,
        )

    except Exception:
        logger.exception("内容采集失败")
        raise

    logger.info(f"内容采集流程结束 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ================= Main Entry =================


def main():
    """Main function - Content collection"""

    # ============================================================
    # 1. 解析命令行参数
    # ============================================================
    run_args = parse_cli_args(
        cate_keyword="clii",
        cate_label="cate level index id",
        sort_keyword="so",
    )

    full_project_id = run_args.project_id

    # ============================================================
    # 2. 创建总项目 Logger
    # ============================================================
    main_logger = create_logger(
        name="cate_list",
        log_dir=os.path.join(BASE_DIR, "logs"),
        project_id=full_project_id,
    )

    # ============================================================
    # 3. Log startup info
    # ============================================================
    main_logger.info("=" * 60)
    main_logger.info("Python-PlayWright-Web - Content collection mode (cate_list)")
    main_logger.info("=" * 60)

    main_logger.info(f"环境--Environment: {run_args.env}")
    main_logger.info(f"预设--Preset: {run_args.preset}")
    main_logger.info(f"项目ID--Project ID: {full_project_id}")
    main_logger.info(f"用户索引--User indexes: {run_args.user_indexes}")

    if run_args.cli_is_ut:
        main_logger.info("分类参数--clii: ut（按用户取 user_pool.xlsx 第8列 clii(cate level index id) 的值）")
    else:
        main_logger.info(f"分类索引--Cate indexes: {run_args.cate_indexes}")

    if run_args.so_is_ut:
        main_logger.info("排序参数--so: ut（按用户取 user_pool.xlsx 第9列 so(sort and order) 的值）")
    else:
        main_logger.info(f"排序参数--so: {run_args.so_arg_raw}")

    main_logger.info(f"--- 开始执行项目（Start executing project）: {full_project_id} (env={run_args.env}) ---")

    # ============================================================
    # 4. 创建项目配置加载器
    # ============================================================
    project_loader = ProjectConfigLoader(full_project_id)

    try:
        # ========================================================
        # 5. 加载项目配置、脚本配置、资源池
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
        # 7.5 分类索引/链接数据载入与回填
        #
        # 步骤 2：载入 cate_level_index.txt（分类索引）
        #   文件为空（<1 行）→ 警告，继续执行；
        #   clii 分类限制将失效（无 index id 可匹配）。
        #
        # 步骤 3：载入 cate_level_link.txt（分类链接）
        #   文件为空（<1 行）→ 报错并退出；无分类链接可采集。
        #
        # 步骤 4：对 link_items 用 index_items 回填
        #   索引为空时跳过回填（clii 限制已失效）。
        # ========================================================

        # 步骤 2：载入分类索引
        index_items = CateLevelIndexDataLoader.load(
            file_path=str(project_config.cate_level_index_file_path),
        )

        index_empty = len(index_items) < 1
        if index_empty:
            project_logger.warning(
                "cate_level_index.txt 分类索引文件为空。"
                '会导致：clii ( cate level index id ) 的值为非"-1>-1"时，'
                '">"号左侧的：cate level 0级 index id 分类索引，'
                '和">"号右侧的：cate level 1级 index id 分类索引限制失效。'
                "虽然程序可以继续执行。但是：clii 参数的分类限制，会失效。"
            )
        else:
            project_logger.info(f"载入分类索引（cate_level_index）：{len(index_items)} 条")

        # 步骤 3：载入分类链接
        link_items = CateLevelLinkDataLoader.load(
            file_path=str(project_config.cate_level_link_file_path),
        )

        if len(link_items) < 1:
            project_logger.error("cate_level_link.txt 分类链接文件为空。无分类链接可采集，程序无法执行，退出。")
            return

        project_logger.info(f"载入分类链接（cate_level_link）：{len(link_items)} 条")

        # 步骤 4：回填（索引为空时跳过）
        if not index_empty:
            CateLevelLinkDataBackfill.backfill(
                link_items=link_items,
                index_items=index_items,
            )
            project_logger.info(f"分类链接数据回填完成：{len(link_items)} 条")
        else:
            project_logger.info("分类索引为空，跳过回填；clii 参数的分类限制将失效。")

        # ========================================================
        # 7.6 so（sort and order）参数校验（非 ut 时一次性校验）
        #
        # so=ut 时在第 9 列逐用户读取后校验（见下方用户校验块）。
        # 成员校验需 script_config.cate_list 三个列表，故在 load_configs 之后。
        # ========================================================
        so_spec = None
        if run_args.so_arg_raw and not run_args.so_is_ut:
            try:
                so_spec = parse_and_validate_so(
                    run_args.so_arg_raw,
                    sort_fields=script_config.cate_list.sort_fields,
                    sort_order_supported_fields=script_config.cate_list.sort_order_supported_fields,
                    sort_order_values=script_config.cate_list.sort_order_values,
                    allow_ut=True,
                )
            except SoValidationError as e:
                project_logger.error(f"so 参数错误：{e}")
                return

        # ========================================================
        # ============ 用户索引校验 ============
        #
        # 校验规则：
        #   1. u -1（无有效用户索引）且 LOGIN_NEED_LOGIN=1 → 冲突，报错退出
        #   2. u 给了具体索引，但用户表中一个都没匹配 → 报错退出
        #   3. 部分匹配 → 未命中者记 warning，继续采集命中的用户
        #   4. 对命中的用户新增两项硬性校验：浏览器池、IP 池
        #   5. clii=ut 时读取用户表第8列 clii(cate level index id) 并校验格式
        #   6. so=ut 时读取用户表第9列 so(sort and order) 并校验格式
        #      （第9列值不能再是 ut）
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

            execute_cate_list(
                resource_context=resource_context,
                env=run_args.env,
                script_config=script_config,
                project_config=project_config,
                logger=project_logger,
                link_items=link_items,
                index_empty=index_empty,
                cate_indexes=run_args.cate_indexes,
                so=so_spec,
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

            # clii=ut 时：
            # user_index -> 解析后的分类范围
            user_cate_indexes = {}

            # so=ut 时：
            # user_index -> 解析后的排序规格
            user_so_specs = {}

            for user_index in selected:
                user = pool_data.users[user_index]

                # ------------------------------------------------
                # 检查一：浏览器池文件存在 / ≥2行 / 含该用户 browser_index
                # ------------------------------------------------
                try:
                    pool_loader.validate_user_browser(user)
                except (
                    PoolLoadError,
                    ResourceNotFoundError,
                ) as e:
                    check_errors.append(str(e))

                # ------------------------------------------------
                # 检查二：用户 IP 池索引规格全部存在
                # ------------------------------------------------
                ip_err = ResourceMapper.validate_user_ip(
                    user,
                    pool_data,
                )

                if ip_err:
                    check_errors.append(ip_err)

                # ------------------------------------------------
                # 检查三：clii=ut 时读取用户表第8列
                # clii(cate level index id)
                # ------------------------------------------------
                if run_args.cli_is_ut:
                    raw_clii = user.cate_level_index

                    try:
                        user_cate_indexes[user_index] = parse_cate_indexes(raw_clii)
                    except argparse.ArgumentTypeError as e:
                        check_errors.append(
                            f"用户 {user_index}({user.username}) 的 cate level index 值 '{raw_clii}' 格式错误：{e}"
                        )

                # ------------------------------------------------
                # 检查四：so=ut 时读取用户表第9列 so(sort and order)
                # 第9列的值需重新按格式 1/2/4/5 校验，且不能再是 ut
                # ------------------------------------------------
                if run_args.so_is_ut:
                    raw_so = user.sort_and_order

                    try:
                        user_so_specs[user_index] = parse_and_validate_so(
                            raw_so,
                            sort_fields=script_config.cate_list.sort_fields,
                            sort_order_supported_fields=script_config.cate_list.sort_order_supported_fields,
                            sort_order_values=script_config.cate_list.sort_order_values,
                            allow_ut=False,
                        )
                    except SoValidationError as e:
                        check_errors.append(f"用户 {user_index}({user.username}) 的 so 值 '{raw_so}' 错误：{e}")

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
            # 13. 逐个用户执行内容采集
            # ====================================================
            for user_index in selected:
                resource_context = resource_allocator.allocate(user_index)

                # clii=ut：
                # 使用用户第8列解析出的分类范围
                #
                # 否则：
                # 使用命令行 clii 分类范围
                if run_args.cli_is_ut:
                    cate_idx = user_cate_indexes.get(user_index)
                else:
                    cate_idx = run_args.cate_indexes

                # so=ut：
                # 使用用户第9列解析出的排序规格
                #
                # 否则：
                # 使用命令行 so 排序规格
                if run_args.so_is_ut:
                    so_idx = user_so_specs.get(user_index)
                else:
                    so_idx = so_spec

                execute_cate_list(
                    resource_context=resource_context,
                    env=run_args.env,
                    script_config=script_config,
                    project_config=project_config,
                    logger=project_logger,
                    link_items=link_items,
                    index_empty=index_empty,
                    cate_indexes=cate_idx,
                    so=so_idx,
                )

        # ========================================================
        # 14. 内容采集完成
        # ========================================================
        project_logger.info("=" * 60)
        project_logger.info(f"内容采集已经完成（Content collection completed） - Project {full_project_id}")
        project_logger.info("=" * 60)

        # 总项目 Logger 也记录完成状态
        main_logger.info(f"内容采集完成（Content collection completed） - Project {full_project_id}")

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
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    main()
