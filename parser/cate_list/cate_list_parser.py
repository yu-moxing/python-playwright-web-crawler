"""将分类列表页面解析为面向数据源的 CATE_LIST 数据项。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from config.context.node_var import (
    build_node_vars,
    node_var_for_node_name,
    replace_node_vars,
)
from constants.unit_const import UNIT_COUNT
from data.model.cate_list.cate_list_common_data_item import CateListCommonDataItem
from data.model.cate_list.cate_list_product_data_item import CateListProductDataItem
from parser.cate_list.cate_list_filter import filter_cate_list_items
from parser.field_extractor import FieldExtractor

logger = logging.getLogger(__name__)


@dataclass
class CateListParsedItem:
    """从一个配置的 CATE_LIST_UNIT 卡片中提取出的单条数据源记录。"""

    common: CateListCommonDataItem
    raw_id: str = ""
    # 独立去重 ID：从页面节点（CATE_LIST_COMMON_ID_*）提取，替代旧版 link_id 派生
    id: str = ""
    tags: str = ""
    product: Optional[CateListProductDataItem] = None


class CateListParser:
    """仅提取每个 CATE_LIST_UNIT 的 CHILD_NODE_LIST 所配置的字段。"""

    _COMMON_FIELDS = (
        "link",
        "main_title",
        "sub_title",
        "main_image",
        "sub_images",
        "view_count",
        "favorite_count",
        "comment_count",
        "main_owner_name",
        "main_owner_id",
        "main_owner_link",
        "sub_owner_name",
        "sub_owner_id",
        "sub_owner_link",
    )
    _PRODUCT_FIELDS = (
        "price",
        "price_currency",
        "price_text",
        "sales_count",
        "sales_text",
    )

    def __init__(self, *, script_config, field_extractor: FieldExtractor | None = None):
        self.script_config = script_config
        self.field_extractor = field_extractor or FieldExtractor()

    async def parse_cate_list_items(
        self,
        page,
        *,
        page_url: str,
        cate_list_unit_config,
    ) -> tuple[
        list[CateListParsedItem],
        list[CateListParsedItem],
    ]:
        """解析当前页面并返回数据项；每个定位到的 CATE_LIST_UNIT 元素产生一条数据项。"""
        cate_list_item = self.script_config.get_cate_list_item()

        valid_result: list[CateListParsedItem] = []
        invalid_result: list[CateListParsedItem] = []

        child_block_found = False

        # =========================================================
        # 遍历 CATE_LIST_UNIT_0 ~ CATE_LIST_UNIT_4
        # =========================================================
        for unit_index in range(UNIT_COUNT):
            # 获取当前 CATE_LIST_UNIT 配置
            unit_config = getattr(
                # self.script_config.cate_list_unit,
                cate_list_unit_config,
                f"unit{unit_index}",
            )

            # 当前 CATE_LIST_UNIT 未启用时，跳过
            if not unit_config.locator_enabled:
                continue

            # 当前 CATE_LIST_UNIT 没有配置任何 CHILD_NODE_LIST 时，跳过
            if not unit_config.enable_locator_child_node_list:
                continue

            # 当前 CATE_LIST_UNIT 不是:整块 配置时，跳过
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

            try:
                father_node_count = await father_nodes.count()

            except Exception:
                # 定位元素失败时记录异常，但不影响后续 CATE_LIST_UNIT 的处理
                logger.exception(
                    "Unable to locate CATE_LIST_UNIT_%d",
                    unit_index,
                )
                continue

            logger.info(
                "CATE_LIST_UNIT_%d 找到 %d 个父节点",
                unit_index,
                father_node_count,
            )

            # 遍历当前 CATE_LIST_UNIT 定位到的所有父级元素
            for father_node_index in range(father_node_count):
                child_items = await self._parse_cate_list_normal_nodes(
                    # 从当前 Locator 匹配到的多个元素中，
                    # 取出指定索引位置的那个父级元素
                    region=father_nodes.nth(father_node_index),
                    enable_locator_node_list=unit_config.enable_locator_child_node_list,
                    enable_combine_node_list=unit_config.enable_combine_child_node_list,
                    cate_list_item=cate_list_item,
                    page_url=page_url,
                    max_count=unit_config.child_max_count,
                )

                # 对当前父级元素解析出的数据进行过滤。
                #
                # 一个父级元素可能提取出多条 CateListParsedItem，
                # 分别接收有效数据和被过滤掉的数据。
                valid_child_items, invalid_child_items = filter_cate_list_items(
                    records=child_items,
                    cate_list_item=cate_list_item,
                )

                # 一个父级元素可能提取出多条 CateListParsedItem，
                # 因此使用 extend，而不是 append。
                # 有效数据进入最终结果。
                valid_result.extend(valid_child_items)

                # 被过滤掉的数据单独保留，后续统一统计。
                invalid_result.extend(invalid_child_items)

        # =========================================================
        # 5 个 UNIT 都没有启用 CHILD_BLOCK
        # 直接在整个 page 中提取 CATE_LIST 数据项。
        #
        # 此时没有父级块范围，因此：
        #     region = page
        #
        # node_names 使用 CATE_LIST 层面需要提取的节点名集合。
        # =========================================================
        if not child_block_found:
            logger.info("CATE_LIST 父级 UNIT_0 ~ UNIT_4 均未出现 child_block=1，使用整个 page 提取 CATE_LIST 数据项")

            child_items = await self._parse_cate_list_normal_nodes(
                region=page,
                enable_locator_node_list=cate_list_item.enable_locator_node_list,
                enable_combine_node_list=cate_list_item.enable_combine_node_list,
                cate_list_item=cate_list_item,
                page_url=page_url,
                # 注意：函数里调用：_extract_cate_list_node_values -> _extract_cate_list_many_node 之后
                # 会再判断是否使用这里的 max_count 值 或 node_config.child_max_count 值
                max_count=cate_list_item.max_count,
            )

            # 对整个 page 提取出的数据进行过滤。
            valid_child_items, invalid_child_items = filter_cate_list_items(
                records=child_items,
                cate_list_item=cate_list_item,
            )

            # 有效数据进入最终结果。
            valid_result.extend(valid_child_items)

            # 被过滤掉的数据保留，交给外层统一统计。
            invalid_result.extend(invalid_child_items)

        # return valid_result
        return valid_result, invalid_result

    async def _parse_cate_list_normal_nodes(
        self,
        *,
        region,
        # node_names: set[str],
        enable_locator_node_list: list[str],
        enable_combine_node_list: list[str],
        cate_list_item,
        page_url: str,
        max_count: int = -1,
    ) -> list[CateListParsedItem]:
        """
        解析一个 CATE_LIST UNIT 区域，并组装 0 至多条 CateListParsedItem。

        _extract_many_node() 返回的 list[str] 只是当前区域的中间提取结果。
        一个字段存在多个提取值时，这些值对应多个独立的 CateListParsedItem。

        本函数只负责：
            1. 提取 COMMON 字段的多值结果；
            2. 提取 RAW_COMMON 字段；
            3. 提取 PRODUCT 字段的多值结果；
            4. 收集当前区域的 NODE 变量；
            5. Phase-3：解析 _COMBINE；
            6. 将多值结果按记录展开为 list[CateListParsedItem]。

        本函数不负责：
            - 定位父级元素；
            - 定位最小节点列表；
            - 遍历多个最小节点；
            - 页面级去重；
            - Redis 去重。

        注意：
            CateListCommonDataItem / CateListProductDataItem 的字段仍然是单值。
            多值只存在于本函数内部的中间结果中，最终每一条
            CateListParsedItem 只保存一个字段值。
        """

        # ======================================================
        # 初始化
        # ======================================================

        # 每个字段的多值提取结果。
        #
        # 例如：
        #
        #     common_values["title"] = ["商品A", "商品B"]
        #     common_values["link"] = ["url-A", "url-B"]
        #
        # 最终再根据记录索引组装成：
        #
        #     CateListParsedItem(common.title="商品A", ...)
        #     CateListParsedItem(common.title="商品B", ...)

        # 当前 UNIT 区域内的 NODE 变量。
        #
        # NODE 变量本身就是多值，因此这里始终保存 list[str]。
        node_vars = build_node_vars()

        # NormalNodeConfig / UnitNodeConfig 可能被多个记录共享。
        # 每解析一个 UNIT 区域前，都需要重置 is_parsed。
        self._reset_item_is_parsed(cate_list_item)

        # ======================================================
        # Phase-1：提取 COMMON 字段
        # ======================================================

        common_values = await self._extract_cate_list_node_values(
            region=region,
            enable_locator_node_list=enable_locator_node_list,
            node_group=cate_list_item.common,
            field_names=self._COMMON_FIELDS,
            layer_prefix="CATE_LIST_COMMON",
            node_vars=node_vars,
            max_count=max_count,
        )

        # ======================================================
        # 提取 RAW_COMMON 字段
        # ======================================================

        raw_id: list[str] = []

        if "CATE_LIST_RAW_COMMON_ID" in enable_locator_node_list:
            raw_id = await self._extract_cate_list_many_node(
                region,
                cate_list_item.raw.id,
                max_count,
            )

        # ======================================================
        # 提取独立 ID
        # ======================================================
        #
        # CATE_LIST_COMMON_ID 不属于 _COMMON_FIELDS，
        # 因此单独提取。
        #
        # 同时把完整多值结果写入：
        #
        #     NODE_CATE_LIST_COMMON_ID
        #
        # 供后续 _COMBINE 使用。

        item_id: list[str] = []

        if "CATE_LIST_COMMON_ID" in enable_locator_node_list:
            id_node = cate_list_item.common.id

            item_id = await self._extract_cate_list_many_node(
                region,
                id_node,
                max_count,
            )

            node_var = node_var_for_node_name(
                id_node.node_name,
            )

            if node_var is not None:
                node_vars[node_var] = item_id

        # ======================================================
        # 提取 RAW TAGS
        # ======================================================

        tags: list[str] = []

        if "CATE_LIST_RAW_COMMON_TAGS" in enable_locator_node_list:
            tags = await self._extract_cate_list_many_node(
                region,
                cate_list_item.raw.tags,
                max_count,
            )

        # ======================================================
        # Phase-2：提取 PRODUCT 字段
        # ======================================================

        product_values: dict[str, list[str]] = {}

        if self.script_config.content_type == "product":
            product_values = await self._extract_cate_list_node_values(
                region=region,
                enable_locator_node_list=enable_locator_node_list,
                node_group=cate_list_item.product,
                field_names=self._PRODUCT_FIELDS,
                layer_prefix="CATE_LIST_PRODUCT",
                node_vars=node_vars,
                max_count=max_count,
            )

        # ======================================================
        # Phase-3：统一解析 _COMBINE
        # ======================================================
        #
        # 此时：
        #
        #     COMMON 多值已提取
        #     RAW_COMMON 已提取
        #     ID 多值已提取
        #     TAGS 已提取
        #     PRODUCT 多值已提取
        #     NODE 变量已准备完成
        #
        # replace_node_vars() 返回 list[str]。
        #
        # 因此 _COMBINE 结果也必须继续保留为多值，
        # 不能直接写入 DataItem。

        combine_values: dict[tuple[str, str], list[str]] = {}

        # common 因为是共用字段，不需要判断：content_type 的值
        combine_values.update(
            self._parse_cate_list_combine_values(
                enable_combine_node_list=enable_combine_node_list,
                node_group=cate_list_item.common,
                field_names=self._COMMON_FIELDS,
                layer_prefix="CATE_LIST_COMMON",
                node_vars=node_vars,
                holder_type="common",
            )
        )

        if self.script_config.content_type == "product":
            combine_values.update(
                self._parse_cate_list_combine_values(
                    enable_combine_node_list=enable_combine_node_list,
                    node_group=cate_list_item.product,
                    field_names=self._PRODUCT_FIELDS,
                    layer_prefix="CATE_LIST_PRODUCT",
                    node_vars=node_vars,
                    holder_type="product",
                )
            )

        # ======================================================
        # 计算最终记录数量
        # ======================================================
        #
        # 所有字段的多值结果统一参与记录数量计算。
        #
        # max_count == -1：
        #     取所有字段实际提取数量中的最大值。
        #
        # max_count > 0：
        #     严格生成 max_count 条记录。
        #
        # 最终组装记录时：
        #     某字段的值不足当前记录索引时，补 ""。

        # all_value_lists: list[list] = []
        all_value_lists: list[list[str]] = []

        all_value_lists.extend(
            common_values.values(),
        )

        all_value_lists.extend(
            product_values.values(),
        )

        all_value_lists.append(raw_id)
        all_value_lists.append(item_id)
        all_value_lists.append(tags)

        all_value_lists.extend(
            combine_values.values(),
        )

        # max_count = -1
        #     → 实际有几个值，就生成几条
        #     → 一个值都没有，就生成 0 条
        #
        # max_count = N
        #     → 明确要求生成 N 条
        #     → 不足的字段全部补 ""

        max_value_count = 0

        for values in all_value_lists:
            value_count = len(values)

            if value_count > max_value_count:
                max_value_count = value_count

        if max_count == -1:
            record_count = max_value_count
        else:
            record_count = max_count

        # ======================================================
        # 组装最终记录
        # ======================================================

        records: list[CateListParsedItem] = []

        for index in range(record_count):
            common = CateListCommonDataItem()

            product = CateListProductDataItem() if self.script_config.content_type == "product" else None

            # --------------------------------------------------
            # COMMON
            # --------------------------------------------------

            for name, values in common_values.items():
                value = values[index] if index < len(values) else ""

                if name == "link" and value:
                    value = urljoin(
                        page_url,
                        value,
                    )

                setattr(
                    common,
                    name,
                    value,
                )

            # --------------------------------------------------
            # PRODUCT
            # --------------------------------------------------

            if product is not None:
                for name, values in product_values.items():
                    value = values[index] if index < len(values) else ""

                    setattr(
                        product,
                        name,
                        value,
                    )

            # --------------------------------------------------
            # _COMBINE
            # --------------------------------------------------

            for (
                holder_type,
                attr_name,
            ), values in combine_values.items():
                value = values[index] if index < len(values) else ""

                if holder_type == "common":
                    if attr_name == "link" and value:
                        value = urljoin(
                            page_url,
                            value,
                        )

                    setattr(
                        common,
                        attr_name,
                        value,
                    )

                elif holder_type == "product":
                    if product is None:
                        continue

                    setattr(
                        product,
                        attr_name,
                        value,
                    )

            # --------------------------------------------------
            # RAW_COMMON / ID / TAGS
            # --------------------------------------------------

            raw_id_value = raw_id[index] if index < len(raw_id) else ""
            item_id_value = item_id[index] if index < len(item_id) else ""
            tags_value = tags[index] if index < len(tags) else ""

            # --------------------------------------------------
            # 当前记录
            # --------------------------------------------------

            record = CateListParsedItem(
                common=common,
                raw_id=raw_id_value,
                id=item_id_value,
                tags=tags_value,
                product=product,
            )

            records.append(record)

        return records

    async def _extract_cate_list_node_values(
        self,
        *,
        region,
        enable_locator_node_list: list[str],
        node_group,
        field_names: tuple[str, ...],
        layer_prefix: str,
        node_vars: dict[str, list[str]],
        max_count: int,
    ) -> dict[str, list[str]]:
        """
        提取一组 NormalNodeConfig 的多值结果。

        只处理 node_list 中启用的节点。

        同时：
            如果节点配置了 NODE 变量，
            将当前节点的多值结果写入 node_vars。
        """

        values_map: dict[str, list[str]] = {}

        for name in field_names:
            config_name = f"{layer_prefix}_{name.upper()}"

            if config_name not in enable_locator_node_list:
                continue

            node_config = getattr(node_group, name)

            values = await self._extract_cate_list_many_node(
                region,
                node_config,
                max_count,
            )

            values_map[name] = values

            node_var = node_var_for_node_name(
                node_config.node_name,
            )

            if node_var is not None:
                node_vars[node_var] = values

        return values_map

    def _parse_cate_list_combine_values(
        self,
        *,
        enable_combine_node_list: list[str],
        node_group,
        field_names: tuple[str, ...],
        layer_prefix: str,
        node_vars: dict[str, list[str]],
        holder_type: str,
    ) -> dict[tuple[str, str], list[str]]:
        """
        解析一组 _COMBINE 节点。

        返回：

            {
                ("common", "title"): [...],
                ("common", "link"): [...],
            }

        或：

            {
                ("product", "price"): [...],
            }
        """

        combine_values: dict[tuple[str, str], list[str]] = {}

        for name in field_names:
            config_name = f"{layer_prefix}_{name.upper()}"

            if config_name not in enable_combine_node_list:
                continue

            node_config = getattr(node_group, name)

            values = replace_node_vars(
                node_config.combine,
                node_vars,
                layer="CATE_LIST",
            )

            combine_values[(holder_type, name)] = values

        return combine_values

    @staticmethod
    def _reset_item_is_parsed(cate_list_item) -> None:
        """重置 item_detail 内所有 NormalNodeConfig 的 is_parsed 为 False。

        NormalNodeConfig 是 script_config 级共享单例，跨记录共用；
        提取后置 True，须在每条记录提取前重置，否则后续记录会被跳过。
        """
        groups = (
            cate_list_item.common,
            getattr(cate_list_item, "product", None),
            getattr(cate_list_item, "article", None),
            cate_list_item.raw,
        )
        for group in groups:
            if group is None:
                continue
            for field_name in getattr(type(group), "__dataclass_fields__", {}):
                node = getattr(group, field_name, None)
                if hasattr(node, "is_parsed"):
                    node.is_parsed = False

    async def _extract_cate_list_many_node(
        self,
        region,
        node_config,
        max_count: int = -1,
    ) -> list[str]:
        """
        提取单节点的多个字段值，并清理、截断提取结果。

        提取流程：

            1. 如果节点配置了 _COMBINE，则跳过自身原有字段提取，
               由 Phase-3 统一计算。

            2. 如果节点已经提取过，则跳过，避免重复提取和覆盖结果。

            3. 根据 father_css / father_xpath 确定当前节点的父级搜索区域：
               - father_css 优先；
               - father_xpath 次之；
               - 两者均为空时，使用传入的 region。

            4. 在确定的搜索区域中，根据当前节点的
               css / xpath / attr / regex 提取字段值。

            5. 清理提取结果，并根据 max_count 截断。

        Args:
            region:
                当前节点的上层搜索区域。
                通常由 CATE_LIST_UNIT 或其他上层流程传入。

            node_config:
                字段节点配置。

            max_count:
                最大提取数量。
                -1 表示不限制数量，返回全部符合条件的值。
                大于 0 的整数表示最多返回前 max_count 个值。
                当实际提取数量少于 max_count 时，返回全部实际提取值。

                本参数只负责限制当前节点的提取数量，
                不负责补齐缺失值。

                字段之间的数量对齐，以及不足数量时补 "",
                由上层 _parse_cate_list_normal_nodes() 负责。

        Returns:
            清理并按 max_count 截断后的字段值列表。

            不会为了满足 max_count 而补 ""。
        """

        # ------------------------------------------------------
        # 第一步：_COMBINE 节点跳过自身原提取
        # ------------------------------------------------------

        # _COMBINE 非空：跳过自身原提取，值由 Phase-3 统一计算
        if node_config.combine:
            return []

        # ------------------------------------------------------
        # 第二步：防止当前记录内重复提取
        # ------------------------------------------------------

        # 本记录内已提取过的节点不再提取，避免覆盖已有结果
        if node_config.is_parsed:
            return []

        # ------------------------------------------------------
        # 第三步：确定当前节点的实际搜索区域
        # ------------------------------------------------------
        # 存在父节点，并且这个父节点的 child_block == 0
        has_father_and_father_child_block_is_zero = False

        # father_css 有值时，优先使用 father_css
        if node_config.father_css:
            element_region = region.locator(node_config.father_css)
            has_father_and_father_child_block_is_zero = True

        # father_css 无值时，才使用 father_xpath
        elif node_config.father_xpath:
            element_region = region.locator(f"xpath={node_config.father_xpath}")
            has_father_and_father_child_block_is_zero = True

        # father_css / father_xpath 均为空时，
        # 直接使用上层传入的 region
        else:
            element_region = region

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

        # 节点完成提取，置位防止本记录内重复提取
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

        # max_count == -1：不限制数量，返回全部符合条件的值
        if max_count == -1:
            return cleaned_values

        # max_count > 0：最多返回前 max_count 个值
        # 注意：这里只截断，不补 ""
        return cleaned_values[:max_count]

    @staticmethod
    def _clean(value) -> str:
        """将字段值转换为字符串，并去除首尾空白字符。"""

        return "" if value is None else str(value).strip()
