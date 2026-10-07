"""
item_detail Runner

同步门面，驱动 async Playwright 流程。

职责：
    - 按用户循环：每个用户独立 BrowserSessionFactory + ResourceContext + 一轮 item_urls 采集
    - no-user（item_users 为空）：单次采集，用 DEFAULT_BROWSER_INDEX
    - finally 释放 BrowserSessionFactory

script_config 由 main 预备层加载后传入；item_users 由 main 预备层从 user_pool 解析后传入。
ResourceContext 由 item_resource_loader.build_item_resource_context 按 user_pool + 资源池构建。
"""

from __future__ import annotations

import asyncio
import logging
import os
from resource import BrowserSessionFactory, PoolLoader
from typing import List, Optional

from config.loader.item_detail.item_project_loader import ItemProjectConfig
from config.loader.item_detail.item_resource_loader import build_item_resource_context
from config.model.item_detail.item_detail_item import ItemDetailScriptConfig
from config.model.item_detail.item_user_config import ItemUserConfig
from constants.item_detail.path_const import POOL_DIR_NAME
from page.page_navigator import PageNavigator
from processor.item_detail.item_detail_processor import ItemDetailProcessor


def run_item_detail(
    *,
    env: str,
    project_config: ItemProjectConfig,
    script_config: ItemDetailScriptConfig,
    item_users: List[ItemUserConfig],
    item_urls: List[str],
    logger: logging.Logger,
) -> None:
    """
    item_detail 同步入口（由 main/item_detail/item_detail.py 调用）。

    item_users 为空（id_u=-1）→ no-user 单次采集；
    非空 → 按用户循环，每用户独立资源 + 独立一轮 item_urls。
    cookies 路径按用户解析（<项目>/cookies/<user-index>_cookies.txt）。
    """
    logger.info("=" * 60)
    logger.info("item_detail Runner 启动：env=%s, 用户数=%d", env, len(item_users))
    logger.info("=" * 60)

    try:
        asyncio.run(
            _run_async(
                env=env,
                project_config=project_config,
                script_config=script_config,
                item_users=item_users,
                item_urls=item_urls,
                logger=logger,
            )
        )
    except Exception:
        logger.exception("item_detail Runner 执行异常")
        raise
    finally:
        logger.info("item_detail Runner 结束")


async def _run_async(
    *,
    env: str,
    project_config: ItemProjectConfig,
    script_config: ItemDetailScriptConfig,
    item_users: List[ItemUserConfig],
    item_urls: List[str],
    logger: logging.Logger,
) -> None:
    # 项目根：processor/item_detail/item_detail_runner.py 向上三级
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pool_dir = os.path.join(base_dir, POOL_DIR_NAME)

    if not item_users:
        # no-user 模式：单次采集（user_index=-1 → -1_cookies.txt）
        logger.info("no-user 模式（id_u=-1）：单次采集")
        await _run_one_pass(
            item_user=None,
            pool_dir=pool_dir,
            project_config=project_config,
            script_config=script_config,
            item_urls=item_urls,
            logger=logger,
        )
        return

    # 按用户循环
    total = len(item_users)
    for i, item_user in enumerate(item_users, start=1):
        logger.info("=" * 40)
        logger.info("按用户采集 [%d/%d]：user_index=%s, username=%s", i, total, item_user.index, item_user.username)
        logger.info("=" * 40)
        await _run_one_pass(
            item_user=item_user,
            pool_dir=pool_dir,
            project_config=project_config,
            script_config=script_config,
            item_urls=item_urls,
            logger=logger,
        )


async def _run_one_pass(
    *,
    item_user: Optional[ItemUserConfig],
    pool_dir: str,
    project_config: ItemProjectConfig,
    script_config: ItemDetailScriptConfig,
    item_urls: List[str],
    logger: logging.Logger,
) -> None:
    """单次采集：构建该用户的资源 → 跑一轮 item_urls → 关闭浏览器。"""
    # 每用户独立 BrowserSessionFactory（Runner 管生命周期）
    browser_factory = BrowserSessionFactory()

    pool_loader = PoolLoader(pool_dir=pool_dir)
    resource_context = build_item_resource_context(item_user, pool_loader, project_config, logger)

    # cookies 按用户解析：<项目>/cookies/<user-index>_cookies.txt
    user_index = item_user.index if item_user is not None else -1
    cookies_file_path = str(project_config.cookies_file_path(user_index))
    if not os.path.exists(cookies_file_path):
        logger.info("cookies 文件不存在，将跳过注入：%s", cookies_file_path)
    else:
        logger.info("cookies 文件：%s", cookies_file_path)

    page_navigator = PageNavigator(
        browser_factory=browser_factory,
        resource_context=resource_context,
        logger=logger,
        headless=bool(script_config.headless),
    )

    processor = ItemDetailProcessor(
        project_config=project_config,
        script_config=script_config,
        item_urls=item_urls,
        cookies_file_path=cookies_file_path,
        page_navigator=page_navigator,
        logger=logger,
    )

    try:
        await processor.run()
    finally:
        try:
            await browser_factory.close_all()
        except Exception:
            logger.exception("关闭 BrowserSessionFactory 异常")
