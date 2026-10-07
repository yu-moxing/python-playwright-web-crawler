"""
item_detail 详情采集入口

职责（仅启动预备 + 调用 Runner）：
    - CLI 参数解析
    - dev / pro 环境判断
    - id_p / id_u / id_i 参数定位
    - item 项目目录定位
    - user_pool.xlsx 定位（仅 id_i=ut 时读取）
    - item_list_link.txt 校验与索引选择
    - cookies.txt 可选检查
    - 启动 Runner

业务流程（浏览器资源、cookie 注入、page 访问）在 processor/item_detail。

本阶段不实现 script.txt 的加载/解析（后续阶段）。

启动示例：
    python -m main.item_detail.item_detail
    python -m main.item_detail.item_detail --dev
    python -m main.item_detail.item_detail --dev id_p 1051-001 id_u 0 id_i -1
    python -m main.item_detail.item_detail --pro id_p 1051-001 id_u -1 id_i 0-9
"""

from __future__ import annotations

import asyncio
import os
import sys

# 项目根 bootstrap（与 main/cate_list.py 一致）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.loader.item_detail.item_detail_loader import (  # noqa: E402
    parse_item_detail_script_config,
)
from config.loader.item_detail.item_project_loader import (  # noqa: E402
    ItemProjectConfig,
    ItemProjectConfigLoader,
)
from config.loader.item_detail.item_user_pool_loader import (  # noqa: E402
    ItemUserPoolLoader,
)
from config.loader.project_loader import ProjectNotFoundError  # noqa: E402
from constants.item_detail.path_const import (  # noqa: E402
    ITEM_LIST_LINK_FILE_NAME,
    LOGS_DIR_NAME,
)
from main.cli.item_detail.item_args import ItemRunArgs, parse_item_cli_args  # noqa: E402
from main.cli.item_detail.item_index_spec import (  # noqa: E402
    ItemIndexSpec,
    parse_item_index_spec,
)
from main.cli.runner_base import BASE_DIR as RUNNER_BASE_DIR  # noqa: E402
from main.cli.runner_base import create_logger  # noqa: E402
from processor.item_detail.item_detail_runner import run_item_detail  # noqa: E402

# ============================================================
# 预备层
# ============================================================


def _select_item_urls(urls, item_spec: ItemIndexSpec) -> list:
    """
    按 ItemIndexSpec 从全量 urls 中选出本次要采集的子集。
    """
    if item_spec.all:
        return list(urls)

    selected = []
    total = len(urls)
    for i in item_spec.indexes:
        if 0 <= i < total:
            selected.append(urls[i])
        else:
            # 越界索引跳过并提示
            print(f"警告：id_i 索引 {i} 越界（共 {total} 条），已跳过", file=sys.stderr)

    return selected


def _resolve_item_users(
    args: ItemRunArgs,
    users,
    project_config: ItemProjectConfig,
    logger,
) -> list:
    """
    由 id_u 解析出 ItemUserConfig 列表（供 Runner 按用户循环）。

    id_u=-1（args.user_indexes 为空）→ 空列表（no-user 模式）。
    否则逐个 user_index 在 user_pool 中查找，缺失报错。
    """
    if not args.user_indexes:
        # id_u=-1：no-user
        return []

    if not users:
        print(
            f"错误：id_u 指定了用户，但 user_pool.xlsx 无数据或不存在：{project_config.user_pool_file_path}",
            file=sys.stderr,
        )
        sys.exit(2)

    item_users = []
    for user_index in args.user_indexes:
        if user_index not in users:
            print(
                f"错误：user_pool.xlsx 中不存在用户索引 {user_index}。可用索引：{sorted(users.keys())}",
                file=sys.stderr,
            )
            sys.exit(2)
        item_users.append(users[user_index])

    logger.info("id_u 解析：用户索引 %s → %d 个用户", args.user_arg_raw, len(item_users))
    return item_users


def _resolve_item_index_spec(
    args: ItemRunArgs,
    item_users: list,
    project_config: ItemProjectConfig,
    logger,
) -> ItemIndexSpec:
    """
    解析最终的 ItemIndexSpec。

    非 ut：直接用 CLI 已解析的 spec。
    ut：读 item_users[0]（要求 id_u 为单个用户）的 id_i 列，禁止嵌套 ut，再解析。
    """
    if not args.item_is_ut:
        # CLI 已解析（preset 或普通值）
        return args.item_index_spec

    # id_i=ut：要求 id_u 为单个用户索引
    if len(item_users) != 1:
        print(
            f"错误：id_i=ut 时 id_u 必须为单个用户索引，当前 id_u={args.user_arg_raw}",
            file=sys.stderr,
        )
        sys.exit(2)

    user = item_users[0]
    id_i_raw = user.id_i

    logger.info("id_i=ut 解析：user_index=%s, user_pool id_i 原值=%s", user.index, id_i_raw)

    # 禁止死亡嵌套
    if id_i_raw.strip().lower() == "ut":
        print(
            "错误：id_i=ut，但 user_pool.xlsx 中对应用户的 id_i 仍为 ut，不允许形成嵌套。",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        spec = parse_item_index_spec(id_i_raw)
    except Exception as exc:  # argparse.ArgumentTypeError
        print(
            f"错误：user_pool.xlsx 中 id_i 列值非法：{id_i_raw}。\n{exc}",
            file=sys.stderr,
        )
        sys.exit(2)

    return spec


def _read_and_select_item_urls(
    project_config: ItemProjectConfig,
    item_spec: ItemIndexSpec,
    logger,
) -> list:
    """
    校验 item_list_link.txt（存在 + 非空）并按 id_i 选出子集。
    """
    file_path = project_config.item_list_link_file_path

    if not os.path.exists(file_path):
        print(f"错误：{ITEM_LIST_LINK_FILE_NAME} 不存在：{file_path}", file=sys.stderr)
        sys.exit(2)

    with open(file_path, "r", encoding="utf-8") as f:
        all_urls = [line.strip() for line in f if line.strip()]

    if not all_urls:
        print(f"错误：{ITEM_LIST_LINK_FILE_NAME} 内容为空：{file_path}", file=sys.stderr)
        sys.exit(2)

    logger.info("读取 %s：file=%s, count=%d", ITEM_LIST_LINK_FILE_NAME, file_path, len(all_urls))

    selected = _select_item_urls(all_urls, item_spec)

    if not selected:
        print(
            f"错误：按 id_i 选出的链接为空（item_list_link 共 {len(all_urls)} 条，id_i 索引无命中）。",
            file=sys.stderr,
        )
        sys.exit(2)

    logger.info("本次采集链接数=%d", len(selected))
    return selected


# ============================================================
# 入口
# ============================================================


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 1. CLI 参数解析（内部完成组合校验与冲突校验）
    args = parse_item_cli_args()

    # 2. 定位 item 项目目录
    try:
        project_loader = ItemProjectConfigLoader(args.project_id)
        project_config = project_loader.load_configs()
    except ProjectNotFoundError as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(2)
    except (ValueError, RuntimeError) as e:
        print(f"错误：项目定位失败：{e}", file=sys.stderr)
        sys.exit(2)

    # 3. 主 logger（全局 logs/）
    main_logger = create_logger(
        name="item_detail",
        log_dir=os.path.join(RUNNER_BASE_DIR, LOGS_DIR_NAME),
        project_id=args.project_id,
    )

    main_logger.info("=" * 60)
    main_logger.info("Python-PlayWright-Web item_detail 入口")
    main_logger.info("=" * 60)
    main_logger.info("env=%s, preset=%s", args.env, args.preset)
    main_logger.info("id_p=%s, id_u=%s, id_i=%s", args.project_id, args.user_arg_raw, args.item_arg_raw)

    # 4. 加载 user_pool.xlsx 一次（供 id_u 解析 + id_i=ut 读取 + Runner 资源构建）
    user_pool_loader = ItemUserPoolLoader(project_config.project_dir_path)
    users = user_pool_loader.load()

    # 5. 解析 id_u → item_users 列表（空=no-user 模式）
    item_users = _resolve_item_users(args, users, project_config, main_logger)

    # 6. 解析 id_i（普通值或 ut；ut 读 item_users[0].id_i）
    item_spec = _resolve_item_index_spec(args, item_users, project_config, main_logger)
    main_logger.info("最终 id_i 规格：all=%s, indexes=%s", item_spec.all, item_spec.indexes)

    # 7. 校验并读取 item_list_link.txt，按 id_i 选子集
    item_urls = _read_and_select_item_urls(project_config, item_spec, main_logger)

    # 8. cookies 路径按用户解析（<项目>/cookies/<user-index>_cookies.txt），
    #    由 Runner 在按用户循环时逐用户解析并检查，此处不再统一检查。

    # 9. 加载 script.txt（项目变量 + 四类变量上下文由 loader 内部复用现有机制处理）
    try:
        program_vars = project_loader.get_program_vars()
        script_config = parse_item_detail_script_config(str(project_config.script_file_path), program_vars)
    except Exception as e:
        main_logger.exception("script.txt 加载失败：%s", str(project_config.script_file_path))
        print(f"错误：script.txt 加载失败：{e}", file=sys.stderr)
        sys.exit(2)

    # 10. 项目 logger（项目目录下 logs/）
    project_logger = create_logger(
        name=f"item_{project_config.full_id}",
        log_dir=str(project_config.logs_dir_path),
        project_id=project_config.full_id,
    )

    # 11. 启动 Runner（浏览器资源在此之后才初始化；按用户循环；cookies 按用户解析）
    run_item_detail(
        env=args.env,
        project_config=project_config,
        script_config=script_config,
        item_users=item_users,
        item_urls=item_urls,
        logger=project_logger,
    )


if __name__ == "__main__":
    main()
