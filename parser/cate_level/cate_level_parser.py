"""
分类层解析器

负责在已渲染的 Playwright Page 上，按 CateLevelConfig 规则
提取单层分类的 link / name / id。

设计原则：
- 只负责"提取"，不负责导航（导航由 processor 控制 page.goto）
- 只负责"解析规则"，不负责业务决策（过滤、落盘由 processor 处理）
- 全异步：底层 Playwright Page 为 async API

提取流程委托给 parser.field_extractor.FieldExtractor
（_CSS / _XPATH 定位 → _ATTR 取属性或文本 → _REGEX 二次处理）。
其中分类 ID 由 link_id_regex 从已提取的链接中派生（独立产出，不替换链接）。
"""

import logging
import re
from typing import List, Tuple

from constants.unit_const import UNIT_COUNT
from parser.field_extractor import FieldExtractor

logger = logging.getLogger(__name__)


class CateLevelParser:
    def __init__(
        self,
        script_config,
    ):

        self.script_config = script_config

        self.field_extractor = FieldExtractor()

    def _deduplicate(
        self,
        links: List[str],
        names: List[str],
        ids: List[str],
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        对单层分类结果进行去重。

        去重规则：
            1. links 和 names 长度必须一致。
               不一致时打印警告，并原样返回。
            2. ids 不为空时：
               以 ids 中的分类 ID 作为去重依据。
               相同 ID 只保留第一次出现的分类。
            3. ids 为空时：
               以 links 中的链接作为去重依据。
               相同链接只保留第一次出现的分类。
               此时 ids 返回空列表。

        Args:
            links: 分类链接列表。
            names: 分类名称列表。
            ids: 分类 ID 列表。

        Returns:
            去重后的 (links, names, ids)。
        """

        # links / names 必须一一对应
        if len(links) != len(names):
            print(f"警告：分类链接和分类名称数量不一致：links={len(links)}, names={len(names)}")
            return links, names, ids

        # =========================================================
        # 有 ID：根据 ids 去重
        # =========================================================
        # if link_id_regex:
        if len(ids) > 0:
            if len(ids) != len(links):
                print(f"警告：分类 ID 与分类链接数量不一致：ids={len(ids)}, links={len(links)}")
                return links, names, ids

            new_links = []
            new_names = []
            new_ids = []

            ids_set = set()

            for link, name, id in zip(links, names, ids):
                if id in ids_set:
                    continue

                ids_set.add(id)
                new_links.append(link)
                new_names.append(name)
                new_ids.append(id)

            return new_links, new_names, new_ids

        # =========================================================
        # 无 ID：根据 links 去重
        # =========================================================
        new_links = []
        new_names = []

        links_set = set()

        for link, name in zip(links, names):
            if link in links_set:
                continue

            links_set.add(link)
            new_links.append(link)
            new_names.append(name)

        return new_links, new_names, []

    async def parse_cate_level_items(
        self,
        *,
        page,
        cate_level_config,
        cate_level_unit_config,
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        提取单层分类。

        根据 level_config（CateLevelConfig）从当前页面提取：
            - links：分类链接
            - names：分类名称
            - ids：从 links 中按 ID 正则派生的分类 ID

        每个普通节点均可配置自己的父级搜索范围：

            father_css
            father_xpath

        父级定位规则：
            1. father_css 不为空时，优先使用 CSS。
            2. father_css 为空时，使用 father_xpath。
            3. father_css / father_xpath 均为空时，
               直接使用当前 page 作为搜索区域。

        Returns:
            (links, names, ids) 三个列表。
        """

        if not cate_level_config.link.locator_enabled:
            return [], [], []

        all_links = []
        all_names = []
        all_ids = []

        child_block_found = False

        # =========================================================
        # 遍历 CATE_LEVEL_UNIT_0 ~ CATE_LEVEL_UNIT_4
        # =========================================================
        for unit_index in range(UNIT_COUNT):
            unit_config = getattr(
                cate_level_unit_config,
                f"unit{unit_index}",
            )

            # 当前 CATE_LEVEL_UNIT 未启用时，跳过
            if not unit_config.locator_enabled:
                continue

            # 当前 CATE_LEVEL_UNIT 没有配置任何 CHILD_NODE_LIST 时，跳过
            if not unit_config.enable_locator_child_node_list:
                continue

            if unit_config.child_block != 1:
                continue

            child_block_found = True

            # -----------------------------------------------------
            # 提取父节点
            # CSS 有值时优先使用 CSS
            # CSS 无值时才使用 XPath
            # -----------------------------------------------------
            if unit_config.css:
                father_nodes = page.locator(unit_config.css)

            elif unit_config.xpath:
                father_nodes = page.locator(f"xpath={unit_config.xpath}")

            else:
                # CSS/XPath 均未配置，当前 UNIT 无法定位，直接跳过
                continue

            logger.info(
                "CATE_LEVEL 父级 UNIT_%d 找到 child_block=1，"
                "先提取符合父节点的元素列表，再遍历父节点元素，"
                "从每个父节点元素中提取普通分类节点",
                unit_index,
            )

            # -----------------------------------------------------
            # 遍历父节点
            # -----------------------------------------------------
            father_node_count = await father_nodes.count()

            for father_node_index in range(father_node_count):
                father_node = father_nodes.nth(father_node_index)

                links, names, ids = await self._parse_cate_level_normal_nodes(
                    page=father_node,
                    level_config=cate_level_config,
                    max_count=unit_config.child_max_count,
                )

                all_links.extend(links)
                all_names.extend(names)
                all_ids.extend(ids)

        # =========================================================
        # 5 个 UNIT 都没有启用 CHILD_BLOCK
        # 直接在整个 page 中提取
        # =========================================================

        if not child_block_found:
            logger.info("CATE_LEVEL 父级 UNIT_0 ~ UNIT_4 均未出现 child_block=1，使用整个 page 提取普通分类节点")
            return await self._parse_cate_level_normal_nodes(
                page=page,
                level_config=cate_level_config,
                # 注意：函数里调用：_extract_cate_level_many_node 之后
                # 会再判断是否使用这里的 max_count 值 或 node_config.child_max_count 值
                max_count=cate_level_config.max_count,
            )

        return all_links, all_names, all_ids

    async def _parse_cate_level_normal_nodes(
        self,
        *,
        page,
        level_config,
        max_count: int = -1,
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        提取普通分类节点。

        根据 level_config（CateLevelConfig）从当前页面或父级搜索区域提取：
            - links：分类链接
            - names：分类名称
            - ids：从 links 中按 ID 正则派生的分类 ID

        max_count 的来源：

            1. CHILD_BLOCK=1：
                上层按父节点逐块提取时，
                由当前 CATE_LEVEL UNIT 的 child_max_count
                作为 max_count 传入。

                此时 page 通常是当前父节点的 Locator，
                普通子节点直接在该父节点范围内提取。

            2. 未发现 CHILD_BLOCK=1：
                此时可能存在两种情况：

                a. 没有父节点：
                    普通节点的 father_css / father_xpath 均为空，
                    使用整个 page 提取。
                    调用方传入 max_count=-1，表示不限数量。

                b. 存在父节点，但父节点 CHILD_BLOCK=0：
                    普通节点的 father_css / father_xpath
                    已由配置回填逻辑写入。
                    此时虽然调用方传入 max_count=-1，
                    但 _extract_cate_level_many_node()
                    会根据当前普通节点的父级配置，
                    使用 father_child_max_count 重新确定实际 max_count，
                    并通过 father_css / father_xpath 定位父级搜索区域。

        max_count == -1：
            表示调用方本身不限制普通节点的提取数量。

            对于没有父节点的普通节点：
                根据 links、names、ids 三个字段实际提取数量中的最大值
                生成最终结果。

            对于存在父节点且父节点 CHILD_BLOCK=0 的普通节点：
                实际节点提取数量由其 father_child_max_count 控制。

        max_count > 0：
            最终严格生成 max_count 条结果。
            links、names、ids 不足 max_count 时使用空字符串补齐；
            超过 max_count 时截断。

        如果 links、names、ids 三项长度不一致：
            - 取三项中的最大长度作为实际提取数量；
            - 长度不足的列表使用空字符串 "" 补齐；
            - 最终再根据 max_count 确定结果数量；
            - 保证最终返回的三个列表长度始终一致，
              避免函数外按索引处理时发生数据错位。

        注意：
            本函数负责组织 links、names、ids 三个字段的提取、
            派生、去重以及最终长度对齐。

            普通节点自身是否存在父级搜索范围，以及
            CHILD_BLOCK=0 时实际使用的 father_child_max_count，
            由 _extract_cate_level_many_node() 根据 node_config 判断。

        Returns:
            (links, names, ids) 三个列表。
            三个列表最终长度始终一致。
        """

        # ------------------------------------------------------
        # 初始化
        # ------------------------------------------------------

        # 每页/每层提取前重置 is_parsed。
        # NormalNodeConfig 是共享单例，
        # 不重置则上一页置位会导致本页提取被跳过。
        level_config.link.is_parsed = False
        level_config.name.is_parsed = False

        # ------------------------------------------------------
        # Phase-1：提取分类链接
        # ------------------------------------------------------

        links = await self._extract_cate_level_many_node(
            page=page,
            node_config=level_config.link,
            max_count=max_count,
        )

        # ------------------------------------------------------
        # Phase-2：提取分类名称
        # ------------------------------------------------------

        names = await self._extract_cate_level_many_node(
            page=page,
            node_config=level_config.name,
            max_count=max_count,
        )

        # ------------------------------------------------------
        # Phase-3：从链接派生分类 ID
        # ------------------------------------------------------
        # _derive_ids 函数，不能有：max_count 参数的原因，写在函数头注释里
        ids = self._derive_ids(
            links=links,
            link_id_regex=level_config.link_id_regex,
        )

        # ------------------------------------------------------
        # 第 1 道去重：单页面内部去重
        # ------------------------------------------------------

        # 保证当前页面提取出来的 links / names / ids
        # 尽可能保持一一对应，并消除当前页面内部的重复。
        links, names, ids = self._deduplicate(
            links,
            names,
            ids,
        )

        # ------------------------------------------------------
        # 计算当前实际结果数量
        # ------------------------------------------------------

        # 所有字段的实际提取结果统一参与数量计算。
        #
        # max_count == -1：
        #     取 links / names / ids 实际数量中的最大值。
        #
        # max_count > 0：
        #     严格生成 max_count 条。
        #
        # 注意：
        #     此处只决定最终结果数量，
        #     不改变各字段已经提取到的实际值。

        actual_count = max(
            len(links),
            len(names),
            len(ids),
        )

        if max_count == -1:
            record_count = actual_count
        else:
            record_count = max_count

        # ------------------------------------------------------
        # 对齐三项长度
        # ------------------------------------------------------

        links_len = len(links)
        names_len = len(names)
        ids_len = len(ids)

        if links_len == names_len == ids_len:
            logger.info(f"提取分类三项长度均为：{links_len}")

        else:
            logger.warning(f"提取分类三项，长度不等：links={links_len}, names={names_len}, ids={ids_len}")

        # ------------------------------------------------------
        # 按最终 record_count 对三个列表统一截断 / 补齐
        # ------------------------------------------------------

        # max_count == -1：
        #     record_count = 实际最大长度。
        #
        # max_count > 0：
        #     record_count = max_count。
        #
        # 因此这里统一处理：
        #     - 超过 record_count → 截断
        #     - 少于 record_count → 补 ""
        #
        # 最终三个列表长度始终完全一致。

        links = links[:record_count]
        names = names[:record_count]
        ids = ids[:record_count]

        links.extend([""] * (record_count - links_len))
        names.extend([""] * (record_count - names_len))
        ids.extend([""] * (record_count - ids_len))

        logger.info(f"提取分类最终记录数量为：{record_count}")

        # ------------------------------------------------------
        # 第 2 道去重：
        # 在 cate_level_collector.check_and_add() 中执行。
        # ------------------------------------------------------

        return links, names, ids

    async def _extract_cate_level_many_node(
        self,
        page,
        node_config,
        max_count: int = -1,
    ) -> list[str]:
        """
        提取普通分类节点的多个字段值，并清理、截断提取结果。

        提取流程：

            1. 如果节点配置了 _COMBINE，则跳过自身原有字段提取，
               由上层统一计算。

            2. 如果节点已经提取过，则跳过，避免重复提取和覆盖结果。

            3. 根据 father_css / father_xpath 确定当前节点的父级搜索区域：
               - father_css 优先；
               - father_xpath 次之；
               - 两者均为空时，使用传入的 page。

            4. 在确定的搜索区域中，根据当前节点的
               css / xpath / attr / regex 提取字段值。

            5. 清理提取结果。

            6. 根据 max_count 截断提取结果。

        Args:
            page:
                当前搜索区域。

                CHILD_BLOCK=1 时：
                    通常是上层传入的单个父节点 Locator。
                    此时回填逻辑不会为当前节点填充
                    father_css / father_xpath，因此直接使用 page
                    作为当前搜索区域。

                CHILD_BLOCK=0 时：
                    通常是整个 Playwright Page。
                    此时通过 father_css / father_xpath
                    定位当前节点的父级搜索区域。

            node_config:
                普通节点配置，通常为 NormalNodeConfig。

            max_count:
                最大提取数量。

                -1 表示不限制数量，返回全部符合条件的值；
                大于 0 的整数表示最多返回前 max_count 个值。

                本参数只负责限制当前节点的提取数量，
                不负责补齐缺失值。

                字段之间的数量对齐，以及不足数量时补 "",
                由上层 _parse_cate_level_normal_nodes() 负责。

        Returns:
            清理并按 max_count 截断后的字段值列表。

            不会为了满足 max_count 而补 ""。
        """

        # ------------------------------------------------------
        # 第一步：_COMBINE 节点跳过自身原提取
        # ------------------------------------------------------

        # _COMBINE 非空时，跳过自身原有 CSS/XPath 等字段提取。
        # 该节点的值由上层统一计算。
        if node_config.combine:
            return []

        # ------------------------------------------------------
        # 第二步：防止当前流程内重复提取
        # ------------------------------------------------------

        # 当前节点已经提取过，则不再重复提取，
        # 避免覆盖已有结果。
        if node_config.is_parsed:
            return []

        # ------------------------------------------------------
        # 第三步：确定当前节点的实际搜索区域
        # ------------------------------------------------------
        # 存在父节点，并且这个父节点的 child_block == 0
        has_father_and_father_child_block_is_zero = False

        # father_css 有值时，优先使用 father_css。
        if node_config.father_css:
            element_region = page.locator(node_config.father_css)
            has_father_and_father_child_block_is_zero = True

        # father_css 无值时，才使用 father_xpath。
        elif node_config.father_xpath:
            element_region = page.locator(f"xpath={node_config.father_xpath}")
            has_father_and_father_child_block_is_zero = True

        # father_css / father_xpath 均为空时，
        # 直接使用上层传入的 page。
        else:
            element_region = page

        # ------------------------------------------------------
        # 第四步：提取当前节点字段值
        # ------------------------------------------------------

        values = await self.field_extractor.extract(
            element_region,
            css=node_config.css,
            xpath=node_config.xpath,
            attr=node_config.attr,
            regex=node_config.regex,
        )

        # 节点完成提取，置位防止当前流程内重复提取。
        node_config.is_parsed = True

        # ------------------------------------------------------
        # 第五步：清理提取结果
        # ------------------------------------------------------

        cleaned_values: list[str] = []

        for value in values:
            cleaned_value = self._clean(value)
            cleaned_values.append(cleaned_value)

        # ------------------------------------------------------
        # 第六步：根据 max_count 截断
        # ------------------------------------------------------

        # has_father_and_father_child_block_is_zero 的作用：
        # 当普通节点是由 CHILD_BLOCK=0 的 UNIT 回填出来的子节点时，
        # 真正控制该子节点最多提取多少个值的，不应该使用函数传入的 max_count，
        # 而应该使用父 UNIT 回填的 father_child_max_count
        if has_father_and_father_child_block_is_zero:
            max_count = node_config.father_child_max_count

        # max_count == -1：不限制数量，返回全部符合条件的值。
        if max_count == -1:
            return cleaned_values

        # max_count > 0：最多返回前 max_count 个值。
        # 注意：这里只截断，不补 ""。
        return cleaned_values[:max_count]

    def _derive_ids(
        self,
        links: list[str],
        link_id_regex: str,
    ) -> list[str]:
        """
        从分类链接中按正则表达式派生分类 ID。

        Args:
            links:
                已经完成数量控制的分类链接列表。

                links 在进入本函数之前，
                已由 _extract_cate_level_many_node() 根据当前节点配置
                以及父级 CHILD_BLOCK / father_child_max_count 等规则，
                确定最终的提取数量。

                因此，本函数不能再次使用 max_count 限制数量。
                如果在 _derive_ids 再次引入 max_count 参数，
                可能导致原本已经正确的数组大小，被改为不正确。

            link_id_regex:
                从分类链接中提取分类 ID 的正则表达式。
                可带 ``regex:`` 前缀。

        Returns:
            按 links 顺序派生的分类 ID 列表。

            未配置 id_regex 时返回空列表。
            正则不匹配的链接对应位置返回空字符串。

            配置了 id_regex 时，
            返回的 ID 数量与 links 保持一致。
        """

        # 未配置 ID 正则，不派生 ID。
        if not link_id_regex:
            return []

        pattern = self._strip_regex_prefix(link_id_regex)

        # 去掉 regex: 前缀后没有实际正则内容。
        if not pattern:
            return [""] * len(links)

        ids: list[str] = []

        for link in links:
            if not link:
                ids.append("")
                continue

            match = re.search(
                pattern,
                link,
            )

            if not match:
                ids.append("")
            elif match.groups():
                ids.append(match.group(1))
            else:
                ids.append(match.group(0))

        return ids

    def _strip_regex_prefix(
        self,
        value: str,
    ) -> str:
        """
        剥离 regex 规则的 "regex:" 前缀

        cate_level_loader 将配置值原样存入 link_id_regex，
        即仍带 "regex:" 前缀（如 "regex:list-([A-Z]+)-"），
        直接用于 re.search 会匹配字面量导致永远失败，此处剥离。
        """

        if value.startswith("regex:"):
            return value[len("regex:") :]

        return value
