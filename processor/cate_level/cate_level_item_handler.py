"""
分类层数据接收处理器

职责：

- 接收 CateLevelCollector 产生的分类索引
- 接收 CateLevelCollector 产生的分类链接
- 对分类链接执行最终输出去重
- 将分类索引交给 cate_level_index_writer
- 将分类链接交给 cate_level_link_writer
- 采集结束后刷写两个 Writer

本模块不负责：

- 分类页面导航
- 分类页面解析
- 分类 URL 标准化
- 分类 URL 业务规则
- 分类范围过滤
- 分类索引具体构造
- 分类链接具体构造
- 数据统计
- Browser / Context / Page 生命周期管理

分类链接去重规则：

    Link ID
        ↓
    如果存在
        ↓
    id:<link_id>

    如果不存在
        ↓
    url:<url>

历史数据：

    cate_level_link_list
            ↓
    提取 URL / flag
            ↓
    根据 level 提取 Link ID
            ↓
    构造 dedup key
            ↓
    DuplicateChecker.seed()

本次采集：

    Collector
        ↓
    accept_link()
        ↓
    构造 dedup key
        ↓
    DuplicateChecker
        ↓
    新数据 → Writer
    重复数据 → 丢弃
"""

from __future__ import annotations

import logging

from processor.common.duplicate_checker import DuplicateChecker
from processor.common.link_id_config import extract_link_id

logger = logging.getLogger(__name__)


class CateLevelItemHandler:
    """
    分类层数据接收处理器。

    当前负责两类数据：

        1. 分类索引
        2. 分类链接

    Collector 不直接操作 Writer。

    Collector：

        accept_index(index)
        accept_link(link)

    Handler：

        index → cate_level_index_writer
        link  → cate_level_link_writer

    分类链接去重：

        历史 cate_level_link.txt
                +
        本次采集新数据
                ↓
        DuplicateChecker

    去重优先级：

        Link ID
            ↓
        URL
    """

    def __init__(
        self,
        *,
        script_config,
        cate_level_index_file,
        cate_level_link_file,
        cate_level_link_list,
    ):
        """
        初始化分类层数据接收处理器。

        Args:
            cate_level_index_file:
                分类索引 Writer。

            cate_level_link_file:
                分类链接 Writer。

            cate_level_link_list:
                已有 cate_level_link.txt 中的历史分类链接。

            script_config:
                当前站点脚本配置。

                用于根据分类层级提取 LINK_ID。
        """

        # =====================================================
        # 配置
        # =====================================================

        self.script_config = script_config

        # =====================================================
        # Writer
        # =====================================================

        self.cate_level_index_file = cate_level_index_file

        self.cate_level_link_file = cate_level_link_file

        # =====================================================
        # 分类链接最终输出去重
        # =====================================================

        self.link_duplicate_checker = DuplicateChecker()

        # =====================================================
        # 预填历史分类链接
        # =====================================================

        self._seed_existing_links(
            cate_level_link_list,
        )

    # =========================================================
    # 分类链接去重 Key
    # =========================================================

    @staticmethod
    def _parse_link_line(
        link: str,
    ) -> tuple[str, int] | None:
        """
        从分类链接业务字符串中提取：

            URL
            flag

        当前业务格式：

            URL--flag>>>cate_names_path

        例如：

            https://e.dangdang.com/list-XGSCX-dd_sale-0-1.html--1>>>-1>心理学||性格色彩学

        返回：

            (
                "https://e.dangdang.com/list-XGSCX-dd_sale-0-1.html",
                1,
            )

        Args:
            link:
                分类链接业务字符串。

        Returns:
            (url, level)
                解析成功。

            None
                解析失败。
        """

        if not link:
            return None

        link = str(link).strip()

        if not link:
            return None

        # -----------------------------------------------------
        # 先定位 >>>
        #
        # URL / flag 在 >>> 前面
        # -----------------------------------------------------

        value_split_index = link.find(">>>")

        if value_split_index == -1:
            return None

        head = link[:value_split_index]

        # -----------------------------------------------------
        # URL--flag
        #
        # 使用最后一个 "--"，
        # 避免 URL 本身未来出现 "--" 时误切。
        # -----------------------------------------------------

        flag_split_index = head.rfind("--")

        if flag_split_index == -1:
            return None

        url = head[:flag_split_index].strip()
        flag_str = head[flag_split_index + 2 :].strip()

        if not url:
            return None

        try:
            level = int(flag_str)

        except ValueError:
            return None

        return url, level

    def _build_link_dedup_key(
        self,
        *,
        link: str,
    ) -> str | None:
        """
        根据分类链接业务字符串构造最终去重 Key。

        优先级：

            Link ID
                ↓
            URL

        例如：

            id:XS2

        或：

            url:https://example.com/list-xxx.html
        """

        parsed = self._parse_link_line(link)

        if parsed is None:
            return None

        url, level = parsed

        # -----------------------------------------------------
        # Link ID 优先
        # -----------------------------------------------------

        link_id = extract_link_id(
            script_config=self.script_config,
            url=url,
            level=level,
        )

        link_id = link_id.strip()

        if link_id:
            return f"id:{link_id}"

        # -----------------------------------------------------
        # 没有 Link ID
        # → URL 去重
        # -----------------------------------------------------

        return f"url:{url}"

    # =========================================================
    # 历史数据预填
    # =========================================================

    def _seed_existing_links(
        self,
        cate_level_link_list,
    ) -> None:
        """
        将已有 cate_level_link.txt 数据
        转换成 DuplicateChecker Key。

        注意：

            cate_level_link_list 保存的是完整业务字符串，
            不能直接 seed 原字符串。

        必须先：

            link
              ↓
            URL + flag
              ↓
            Link ID / URL
              ↓
            dedup key
              ↓
            seed()
        """

        if not cate_level_link_list:
            logger.info("没有已有 cate_level_link 数据，分类链接去重器从空集合开始")
            return

        keys = []

        invalid_count = 0

        for link in cate_level_link_list:
            key = self._build_link_dedup_key(
                link=link,
            )

            if key is None:
                invalid_count += 1
                logger.warning(
                    "已有分类链接无法构造去重 Key，跳过：%s",
                    link,
                )
                continue

            keys.append(key)

        self.link_duplicate_checker.seed(keys)

        logger.info(
            "已有分类链接预填完成：历史数据=%d，唯一 Key=%d，无效=%d",
            len(cate_level_link_list),
            len(keys),
            invalid_count,
        )

    # =========================================================
    # 分类索引
    # =========================================================

    def accept_index(
        self,
        index: str,
    ) -> bool:
        """
        接收一条分类索引数据。

        当前只负责将索引交给
        cate_level_index_writer。

        分类索引最终去重规则
        等 index 格式完全确定后再处理。
        """

        if not index:
            return False

        index = str(index).strip()

        if not index:
            return False

        self.cate_level_index_file.add(index)

        return True

    # =========================================================
    # 分类链接
    # =========================================================

    def accept_link(
        self,
        link: str,
    ) -> bool:
        """
        接收一条分类链接数据。

        去重规则：

            Link ID 优先；
            没有 Link ID 时使用 URL。

        DuplicateChecker 同时包含：

            1. 历史 cate_level_link.txt
            2. 本次运行已经接受的分类链接
        """

        if not link:
            return False

        link = str(link).strip()

        if not link:
            return False

        # -----------------------------------------------------
        # 构造业务唯一 Key
        # -----------------------------------------------------

        dedup_key = self._build_link_dedup_key(
            link=link,
        )

        if dedup_key is None:
            logger.warning(
                "分类链接无法构造去重 Key，跳过：%s",
                link,
            )
            return False

        # -----------------------------------------------------
        # 最终输出去重
        # -----------------------------------------------------

        if self.link_duplicate_checker.is_duplicate_key(
            dedup_key,
        ):
            logger.info(
                "分类链接重复，跳过输出：key=%s, link=%s",
                dedup_key,
                link,
            )
            return False

        # -----------------------------------------------------
        # 登记本次已经接受的数据
        # -----------------------------------------------------

        self.link_duplicate_checker.add_key(
            dedup_key,
        )

        # -----------------------------------------------------
        # 写入 Writer
        # -----------------------------------------------------

        self.cate_level_link_file.add(
            link,
        )

        return True

    # =========================================================
    # 数据落盘
    # =========================================================

    def flush(self) -> None:
        """
        刷写分类索引和分类链接。
        """

        index_file = self.cate_level_index_file.close()

        link_file = self.cate_level_link_file.close()

        logger.info(
            "分类层输出完成：index=%d 条，link=%d 条",
            index_file,
            link_file,
        )
