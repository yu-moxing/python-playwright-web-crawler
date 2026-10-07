"""
分类树采集执行入口

替代 Scrapy Spider 调度。

对外保持同步签名，
内部使用 asyncio 驱动异步采集流程
（Playwright 使用 async API）。
"""

import asyncio
import logging
from pathlib import Path
from resource.browser_session_factory import BrowserSessionFactory

# from processor.common.structured_batch_writer import (
#     StructuredBatchWriter,
# )
from fileio.batch.txt_batch_file import TxtBatchFile
from page.page_navigator import PageNavigator
from processor.cate_level.cate_level_processor import CateLevelProcessor

logger = logging.getLogger(__name__)


def run_cate_level(
    *,
    script_config,
    resource_context,
    cate_indexes,
    cate_level_index_file_path,
    cate_level_link_file_path,
    logger,
):
    """
    执行分类层采集。

    Args:
        script_config:
            script.txt 解析后的配置对象。

        resource_context:
            浏览器 / IP / User 等资源上下文。

        cate_indexes:
            分类采集范围。

        cate_level_link_file_path:
            分类数据输出文件路径。
    """
    logger.info("=" * 60)
    logger.info("开始分类树采集")
    logger.info("=" * 60)

    try:
        asyncio.run(
            _run_async(
                script_config=script_config,
                resource_context=resource_context,
                cate_indexes=cate_indexes,
                cate_level_index_file_path=cate_level_index_file_path,
                cate_level_link_file_path=cate_level_link_file_path,
                logger=logger,
            )
        )

    except Exception:
        logger.exception("分类树采集异常")
        raise

    finally:
        logger.info("分类树采集结束")


async def _run_async(
    *,
    script_config,
    resource_context,
    cate_indexes,
    cate_level_index_file_path,
    cate_level_link_file_path,
    logger,
):
    """
    异步执行分类树采集。
    """
    cate_level_index_file_io = Path(cate_level_index_file_path)
    cate_level_link_file_io = Path(cate_level_link_file_path)

    # ==================================================
    # StructuredBatchWriter
    # ==================================================
    #
    # 分类树输出属于结构化数据：
    #
    # {
    #     "cate_level_0_type": "...",
    #     "cate_level_1_type": "...",
    #     "cate_level_2_type": "...",
    #     "url": "..."
    # }
    #
    # 因此使用 StructuredBatchWriter。
    #
    # 不再使用旧的 BatchWriter。
    # 不再使用 output_type="txt"。
    #
    # batch_writer = StructuredBatchWriter(
    #     batch_size=-1,
    #     output_type="csv",
    #     output_path=str(out.parent),
    #     filename=out.name,
    # )

    # ==================================================
    # 分类输出
    # ==================================================

    # 分类索引：
    #
    # 001#小说------------002#中国小说------------003#历史小说------------004#中国小说------------005#历史小说------------0

    cate_level_index_file = TxtBatchFile(
        batch_size=-1,
        # file_path=str(cate_level_index_file_io.parent / "cate_level_index.txt"),
        file_path=str(cate_level_index_file_path),
    )

    # 分类链接：
    #
    # 保存分类层采集得到的链接数据。
    #
    cate_level_link_file = TxtBatchFile(
        batch_size=-1,
        # file_path=str(cate_level_link_file_io.parent / "cate_level_link.txt"),
        file_path=str(cate_level_link_file_path),
    )

    # 判断是否存在旧的分类链接
    cate_level_link_list = cate_level_link_file.read_existing()

    if not cate_level_link_list:
        is_all_update = True
        first_all_update = True
    else:
        is_all_update = False
        first_all_update = False

    # ==================================================
    # Browser
    # ==================================================

    # 浏览器工厂由 Runner 持有。
    #
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
    # CateLevelProcessor
    # ==================================================

    processor = CateLevelProcessor(
        script_config=script_config,
        resource_context=resource_context,
        cate_indexes=cate_indexes,
        # batch_writer=batch_writer,
        cate_level_index_file=cate_level_index_file,
        cate_level_link_file=cate_level_link_file,
        cate_level_link_list=cate_level_link_list,
        page_navigator=page_navigator,
        is_all_update=is_all_update,
        first_all_update=first_all_update,
        logger=logger,
    )

    try:
        await processor.run()

    finally:
        # ==================================================
        # 写入剩余缓冲数据
        # ==================================================

        try:
            cate_level_index_file.close()

        except Exception:
            logger.exception("关闭 cate_level_index_file 异常")

        try:
            cate_level_link_file.close()

        except Exception:
            logger.exception("关闭 cate_level_link_file 异常")

        # ==================================================
        # 关闭浏览器资源
        # ==================================================

        try:
            await browser_factory.close_all()

        except Exception:
            logger.exception("关闭 BrowserSessionFactory 异常")
