"""
cate_list 内容采集执行入口

替代 Scrapy Spider 调度。

对外保持同步签名，
内部使用 asyncio 驱动异步采集流程
（Playwright 使用 async API）。

参数对齐 run_cate_level（keyword-only）。

link_items 为 main.cate_list 回填后的内存对象
（cate_ids_path / cate_links_path 由 backfill 填充，
 cate_level_link.txt 不保存这两个字段，不能从文件重载）。
"""

import asyncio
import logging
from resource.browser_session_factory import BrowserSessionFactory

from config.database.mongodb_config import MongoDBConfig

# ==================================================
# Database Configs
# ==================================================
from config.database.redis_config import RedisConfig
from database.mongodb.mongodb_client import MongoDBClient
from database.mongodb.mongodb_util import MongoDBUtil

# ==================================================
# Database Clients & Utils
# ==================================================
from database.redis.redis_client import RedisClient
from database.redis.redis_util import RedisUtil
from page.page_navigator import PageNavigator
from processor.cate_list.cate_list_processor import CateListProcessor

logger = logging.getLogger(__name__)


def run_cate_list(
    *,
    env: str,
    script_config,
    resource_context,
    cate_indexes,
    link_items,
    index_empty: bool,
    so=None,
    logger,
):
    """
    执行内容采集任务。

    Args:
        script_config:
            script.txt 解析后的配置对象。
        resource_context:
            浏览器 / IP / User 等资源上下文（无用户模式时 user=None）。
        cate_indexes:
            分类范围过滤参数（clii 解析得到的 {"parents","children"}）。
        link_items:
            回填后的分类链接列表（list[CateLevelLinkDataItem]）。
        index_empty:
            分类索引文件是否为空（为空时 clii 过滤失效）。
        so:
            排序参数（SoSpec 或 None），由 main.cli.sort_spec 解析得到。
    """
    logger.info("=" * 60)
    logger.info("开始内容采集")
    logger.info("=" * 60)

    try:
        asyncio.run(
            _run_async(
                env=env,
                script_config=script_config,
                resource_context=resource_context,
                cate_indexes=cate_indexes,
                link_items=link_items,
                index_empty=index_empty,
                so=so,
                logger=logger,
            )
        )

    except Exception:
        logger.exception("内容采集异常")
        raise

    finally:
        logger.info("内容采集结束")


async def _run_async(
    *,
    env: str,
    script_config,
    resource_context,
    cate_indexes,
    link_items,
    index_empty: bool,
    so,
    logger,
):
    """
    异步执行内容采集。
    """

    # ==================================================
    # Browser
    # ==================================================

    # 浏览器工厂由 Runner 持有。
    # Processor 只使用 PageNavigator，
    # 不负责 BrowserSessionFactory 生命周期。
    browser_factory = BrowserSessionFactory()

    # ==================================================
    # PageNavigator
    # ==================================================

    # PageNavigator 负责：
    #
    # - Browser Context 复用
    # - new_page
    # - goto
    # - 页面就绪检测
    # - 页面加载重试
    #
    sys_config = script_config.system

    page_navigator = PageNavigator(
        browser_factory=browser_factory,
        resource_context=resource_context,
        logger=logger,
        headless=not bool(script_config.browser.show_windows),
        max_retries=sys_config.page_load_max_retries,
        ready_check_enabled=sys_config.page_ready_check_enabled,
        page_goto_timeout=sys_config.page_goto_timeout,
        timeout=sys_config.page_ready_timeout,
        network_idle_enabled=sys_config.page_network_idle_enabled,
        network_idle_timeout=sys_config.page_network_idle_timeout,
        page_item=script_config.page,
    )

    # ==================================================
    # Redis
    # 根据本次运行传进来的 env，加载对应环境的 Redis 配置
    # 并创建这一轮采集任务使用的 Redis 连接基础设施
    # ==================================================

    redis_config = RedisConfig(env)

    redis_client = RedisClient(redis_config)

    redis_util = RedisUtil(redis_client.get_client())

    # ==================================================
    # MongoDB
    # 加载 MongoDB 配置
    # 并创建这一轮采集任务使用的 MongoDB 连接基础设施
    # ==================================================

    mongodb_config = MongoDBConfig(env)

    mongodb_client = MongoDBClient(mongodb_config)

    mongodb_util = MongoDBUtil(
        mongodb_client.get_client(),
        script_config.mongodb.database_name,
    )

    # ==================================================
    # CateListProcessor
    # ==================================================

    processor = CateListProcessor(
        script_config=script_config,
        resource_context=resource_context,
        cate_indexes=cate_indexes,
        link_items=link_items,
        index_empty=index_empty,
        so=so,
        page_navigator=page_navigator,
        redis_util=redis_util,
        mongodb_util=mongodb_util,
        logger=logger,
    )

    try:
        await processor.run()

    finally:
        # ==================================================
        # 关闭浏览器资源
        # ==================================================

        try:
            await browser_factory.close_all()

        except Exception:
            logger.exception("关闭 BrowserSessionFactory 异常")
