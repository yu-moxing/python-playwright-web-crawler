"""
分类层级链接业务构建模块

职责：

- 根据 NormalizedLink 构建分类层级业务链接
- 执行链接业务正则处理
- 执行分类 URL 业务规则
- 处理 Start Enter 入口规则
- 处理分类链接文本
- 处理 inter_link_type
- 设置分类链接 flag
- 设置分类链接 index
- 构建最终业务链接字符串

本模块不负责：

- 页面导航
- Playwright DOM 操作
- <a> 元素提取
- 相对 URL 转绝对 URL
- 基础 URL 标准化
- URL 去重
- 数据校验
- 数据落盘
- 产品链接处理
- 分类相似度匹配
- 分类 ID 匹配
- 分类删除
- 快速链接更新

模块关系：

    CateLevelParser
        │
        ├── href
        ├── name
        └── id
             │
             ▼
    CateLevelLinkNormalizer
             │
             │ NormalizedLink
             ▼
    CateLevelCollector
             │
             ▼
    CateLevelLinkBuilder
             │
             ▼
         BuiltLink
             │
             ▼
    CateLevelItemHandler
             │
             ├── accept_index()
             └── accept_link()

设计说明：

Java 原版 readAllLink() 将以下职责全部混合在一个方法中：

- 页面读取
- HTML 解析
- <a> 提取
- URL 标准化
- 正则过滤
- URL 去重
- 产品链接处理
- 分类链接处理
- 分类文本处理
- floor 规则
- 分类相似度匹配
- 分类 ID 匹配
- 快速链接更新
- 原始分类保存
- 文件落盘

Python 版本将这些职责拆开。

本模块只承接：

    NormalizedLink
        +
    分类名称 name
        +
    flag
        +
    index
        ↓
    分类业务 URL / 文本处理
        ↓
    BuiltLink

其中：

    flag
        当前分类链接的业务 flag。

    index
        当前层分类链接索引。

分类相似度匹配，例如旧 Java：

    MyText.getMaxLikeType(...)

不属于本 Builder。

分类匹配应该在后续分类处理阶段完成。

URL 去重由：

    processor.common.duplicate_checker.DuplicateChecker

统一负责。


说明：

本 Builder 当前只负责分类层级链接。

产品链接不属于本模块职责，因此：

- 不判断 is_product
- 不保存 is_product 状态
- 不处理产品 URL
- 不保留产品 URL 配置
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mini_text.keyword_utils import (
    get_code_to_chinese,
    get_code_to_string,
    get_normal_category_str,
)
from mini_text.regex_utils import extract_regex_key
from processor.cate_level.cate_level_link_normalizer import NormalizedLink


@dataclass(frozen=True)
class BuiltLink:
    """
    构建后的分类层级业务链接。

    Attributes:
        url:
            最终业务 URL。

        cate_name:
            分类路径文本。

            例如：

                小说
                小说||言情小说
                小说||言情小说||古代言情

            注意：

            这里是“分类文本”，
            不是最终分类索引。

        value:
            当前阶段构建出的业务链接字符串。

            例如：

                URL--1>>>-1>小说
                URL--0>>>15>小说||言情小说

        flag:
            当前分类链接业务 flag。

        curr_cate_level_link_index:
            当前层链接在 links 中的位置索引。

            注意：

            这个 index 不是最终分类索引。

        limit_cate_level_0_id:
            限制当前采集链路只能归入哪个 Level 0 分类。

            -1：
                不限制。

            > 0：
                限制在指定 Level 0 分类 ID 下。
    """

    url: str

    # 当前分类名称
    cate_name: str = ""

    # 最终业务字符串
    value: str = ""

    # 当前业务层级
    flag: int = 0

    # 当前层链接位置
    curr_cate_level_link_index: int = -1

    # Level 0 限定 ID
    limit_cate_level_0_id: int = -1


@dataclass
class CateLevelLinkBuildConfig:
    """
    分类层级链接业务构建配置。

    该配置用于承接 Java readAllLink() 中与分类链接
    业务处理相关的配置。

    注意：

    页面读取、DOM 提取、URL 相对路径处理等参数
    不属于本配置。

    本配置只服务于分类层级链接业务构建。
    """

    # =========================================================
    # URL 业务正则
    # =========================================================

    regex: str = ""

    # =========================================================
    # 链接文本
    # =========================================================

    # need_get_link_text: bool = False
    need_get_link_text: bool = True

    # =========================================================
    # URL 处理
    # =========================================================

    need_lower_case: bool = False

    # =========================================================
    # 分类链接
    # =========================================================

    need_filter_cate_link: bool = False

    cate_filter_regex: str = ""

    cate_filter_head: str = ""

    need_cate_link_add_str: bool = False

    cate_link_add_str: str = ""

    # =========================================================
    # Start Enter
    # =========================================================

    is_start_enter: bool = False

    min_start_id: int = 0

    max_start_id: int = 0

    delete_start_ids: set[str] | None = None

    # =========================================================
    # 分类文本
    # =========================================================

    # 保留 inter_link_type。
    #
    # 该字段属于旧系统业务配置字段，
    # 当前不因为 cate 的分类语义而进行重命名。
    inter_link_cate: str = ""

    default_link_cate_text: str = "其他"

    # =========================================================
    # 输出格式
    # =========================================================

    link_separator: str = ">>>"

    # 保留该字段，是为了兼容旧配置中的 smallSplit。
    #
    # 当前 Builder 不直接使用它。
    small_split: str = "||"


class CateLevelLinkBuilder:
    """
    分类层级链接业务构建器。

    输入：

        NormalizedLink
            +
        name
            +
        flag
            +
        index

    输出：

        BuiltLink

    本类只负责分类链接的业务构建。

    不负责：

        - 产品链接处理
        - URL 去重
        - 页面操作
        - DOM 提取
        - URL 基础标准化
        - 相似度匹配
        - 分类 ID 匹配
        - 分类删除
        - 快速链接更新
        - 数据落盘

    URL 去重统一交给：

        processor.common.duplicate_checker.DuplicateChecker
    """

    def __init__(
        self,
        config: CateLevelLinkBuildConfig,
    ) -> None:
        self.config = config

    # =========================================================
    # 对外接口
    # =========================================================

    def build(
        self,
        normal_link: NormalizedLink,
        *,
        cate_name: str = "",
        cate_names_path: list[str] | None = None,
        curr_cate_level_link_index: int = -1,
        flag: int = 0,
        limit_cate_level_0_id: int = -1,
    ) -> BuiltLink | None:
        """
        构建单个分类业务链接。

        Args:
            normal_link:
                URL 标准化后的 NormalizedLink。

            cate_name:
                CateLevelParser 提取出的原始分类名称。

            curr_cate_level_link_index:
                当前层分类链接索引。

            flag:
                当前分类链接业务 flag。

            limit_cate_level_0_id:
                限制当前分类链路只能归入指定的 Level 0 分类 ID。

                -1 表示不限制。

        Returns:
            BuiltLink:
                构建成功。

            None:
                当前链接不符合业务规则。
        """

        url = normal_link.url.strip()

        if not url:
            return None

        # -----------------------------------------------------
        # 1. URL 大小写处理
        # -----------------------------------------------------

        if self.config.need_lower_case:
            url = url.lower()

        # -----------------------------------------------------
        # 2. URL 业务正则
        # -----------------------------------------------------

        if not self._match_regex(url):
            return None

        # -----------------------------------------------------
        # 3. Start Enter 入口过滤
        # -----------------------------------------------------

        if self.config.is_start_enter:
            if not self._pass_start_enter_filter(url):
                return None

        # -----------------------------------------------------
        # 4. 分类 URL 业务处理
        # -----------------------------------------------------

        url = self._build_cate_url(url)

        if not url:
            return None

        # -----------------------------------------------------
        # 5. 分类文本处理
        # -----------------------------------------------------

        cate_name_normal_text = ""

        if self.config.need_get_link_text == True:
            cate_name_normal_text = self._normalize_link_cate_text(cate_name)

            if cate_name_normal_text is None:
                return None

        # -----------------------------------------------------
        # 6. 构建最终业务值
        # -----------------------------------------------------

        cate_level_link_line = self._build_value(
            url=url,
            flag=flag,
            # index 当前 links 中的位置
            # index=index,
            limit_cate_level_0_id=limit_cate_level_0_id,
            cate_name=cate_name_normal_text,
            cate_names_path=cate_names_path,
        )

        return BuiltLink(
            url=url,
            cate_name=cate_name_normal_text,
            value=cate_level_link_line,
            flag=flag,
            curr_cate_level_link_index=curr_cate_level_link_index,
            limit_cate_level_0_id=limit_cate_level_0_id,
        )

    def build_all(
        self,
        links: list[NormalizedLink],
        names: list[str] | None = None,
        *,
        flag: int = 0,
    ) -> list[BuiltLink]:
        """
        批量构建分类业务链接。

        Args:
            links:
                URL 标准化后的链接列表。

            names:
                与 links 按索引对应的分类名称列表。

                如果未提供，则所有链接使用空字符串。

            flag:
                当前批次分类链接使用的业务 flag。

        Returns:
            构建成功后的 BuiltLink 列表。

        注意：

        本方法不负责 URL 去重。

        即使输入中存在相同 URL，
        这里也不会删除重复项。

        index 使用当前 links 列表中的实际索引，
        对应旧 Java 中：

            for (int i = 0; i < floorLength; i++)
        """

        results: list[BuiltLink] = []

        for curr_cate_level_link_index, link in enumerate(links):
            name = ""

            if names is not None and curr_cate_level_link_index < len(names):
                name = names[curr_cate_level_link_index]

            built = self.build(
                normal_link=link,
                cate_name=name,
                curr_cate_level_link_index=curr_cate_level_link_index,
                flag=flag,
            )

            if built is not None:
                results.append(built)

        return results

    # =========================================================
    # URL 正则
    # =========================================================

    def _match_regex(
        self,
        url: str,
    ) -> bool:
        """
        判断 URL 是否符合业务正则。

        Java 原版：

            Pattern.compile(
                strRegex_1,
                Pattern.CASE_INSENSITIVE
            );

            mc.matches();

        Python 使用 re.fullmatch，
        对应 Java Matcher.matches() 的整体匹配语义。

        如果没有配置 regex，则默认通过。

        注意：

        这里的“通过/过滤”属于链接业务规则，
        所以由 Builder 负责。
        """

        regex = self.config.regex.strip()

        if not regex:
            return True

        try:
            return (
                re.fullmatch(
                    regex,
                    url,
                    flags=re.IGNORECASE,
                )
                is not None
            )

        except re.error:
            # 配置正则错误时，不让单个链接异常
            # 直接破坏整个采集流程。
            return False

    # =========================================================
    # 分类 URL
    # =========================================================

    def _build_cate_url(
        self,
        url: str,
    ) -> str:
        """
        执行分类 URL 业务规则。

        对应 Java：

            needFilterTypeLink
            needTypeLinkAddStr
        """

        # -----------------------------------------------------
        # 分类 URL 正则提取
        # -----------------------------------------------------

        if self.config.need_filter_cate_link:
            new_last = extract_regex_key(
                url,
                self.config.cate_filter_regex,
            )

            if new_last:
                url = self.config.cate_filter_head + new_last

        # -----------------------------------------------------
        # 分类 URL 后缀
        # -----------------------------------------------------

        if self.config.need_cate_link_add_str:
            url += self.config.cate_link_add_str

        return url.strip()

    # =========================================================
    # Start Enter
    # =========================================================

    def _pass_start_enter_filter(
        self,
        url: str,
    ) -> bool:
        """
        判断 URL 是否通过 Start Enter 入口过滤。

        规则：

        1. 取 URL 最后一个 '=' 后面的字符串。
        2. 如果不是数字，则不进行范围过滤。
        3. delete_start_ids 优先。
        4. 支持最小值 / 最大值组合。
        """

        last_split_index = url.rfind("=")

        if last_split_index == -1:
            return True

        last_str = url[last_split_index + 1 :]

        if not last_str.isdigit():
            return True

        start_id = int(last_str)

        # -----------------------------------------------------
        # 指定删除 ID
        # -----------------------------------------------------

        delete_start_ids = self.config.delete_start_ids

        if delete_start_ids:
            if last_str in delete_start_ids:
                return False

            return True

        # -----------------------------------------------------
        # 最小 + 最大
        # -----------------------------------------------------

        min_id = self.config.min_start_id
        max_id = self.config.max_start_id

        if min_id > 0 and max_id > 0:
            return min_id <= start_id <= max_id

        # -----------------------------------------------------
        # 只有最小值
        # -----------------------------------------------------

        if min_id > 0:
            return start_id >= min_id

        # -----------------------------------------------------
        # 只有最大值
        # -----------------------------------------------------

        if max_id > 0:
            return start_id <= max_id

        return True

    # =========================================================
    # 分类文本
    # =========================================================

    def _normalize_link_cate_text(
        self,
        name: str,
    ) -> str | None:
        """
        标准化分类链接文本。

        处理流程与 Java 旧版保持一致：

            过滤导航文本
                ↓
            getCodeToString()
                ↓
            处理 &#8249;
                ↓
            getCodeToChinese()
                ↓
            getNormalCategoryStr()
                ↓
            空文本 → 默认分类
                ↓
            去除中文括号
                ↓
            去除英文括号
                ↓
            空文本 → 默认分类
                ↓
            interLinkType 拼接

        Args:
            name:
                CateLevelParser 提取出的原始分类名称。

        Returns:
            处理后的分类名称。

            None:
                当前文本属于需要过滤的导航文本。
        """

        link_cate_text = name.strip()

        # -----------------------------------------------------
        # Java：
        #
        # if (linkTypeText.indexOf("更多") != -1
        #     || linkTypeText.indexOf("more") != -1
        #     || linkTypeText.indexOf("查看上级分类") != -1)
        #     continue;
        # -----------------------------------------------------

        lower_text = link_cate_text.lower()

        if "更多" in link_cate_text or "more" in lower_text or "查看上级分类" in link_cate_text:
            return None

        # -----------------------------------------------------
        # Java：
        #
        # linkTypeText = MyText.getCodeToString(linkTypeText);
        #
        # HTML / URL 编码等基础转换
        # -----------------------------------------------------

        link_cate_text = get_code_to_string(link_cate_text)

        # -----------------------------------------------------
        # Java：
        #
        # if (linkTypeText.indexOf("&#8249;") != -1) {
        #     linkTypeText = linkTypeText.replace("&#8249;", " ");
        #     if (MyText.isTrimEmpty(linkTypeText)) {
        #         continue;
        #     }
        # }
        # -----------------------------------------------------

        if "&#8249;" in link_cate_text:
            link_cate_text = link_cate_text.replace(
                "&#8249;",
                " ",
            )

            if not link_cate_text.strip():
                return None

        # -----------------------------------------------------
        # Java：
        #
        # linkTypeText = MyText.getCodeToChinese(linkTypeText);
        #
        # &#27431;&#33298; → 欧舒
        # &27431;&33298;   → 欧舒
        # -----------------------------------------------------

        link_cate_text = get_code_to_chinese(link_cate_text)

        # -----------------------------------------------------
        # Java：
        #
        # linkTypeText = MyText.getNormalCategoryStr(linkTypeText);
        #
        # 分类名称规范化
        # -----------------------------------------------------

        link_cate_text = get_normal_category_str(link_cate_text)

        # -----------------------------------------------------
        # Java：
        #
        # if (MyText.isTrimEmpty(linkTypeText)) {
        #     linkTypeText = "其他";
        # }
        # -----------------------------------------------------

        if not link_cate_text.strip():
            link_cate_text = self.config.default_link_cate_text

        # -----------------------------------------------------
        # Java：
        #
        # int leftSplit = linkTypeText.indexOf("（");
        # if (leftSplit != -1) {
        #     linkTypeText = linkTypeText.substring(0, leftSplit);
        # }
        # -----------------------------------------------------

        index = link_cate_text.find("（")

        if index != -1:
            link_cate_text = link_cate_text[:index]

        # -----------------------------------------------------
        # Java：
        #
        # int rightSplit = linkTypeText.indexOf("(");
        # if (rightSplit != -1) {
        #     linkTypeText = linkTypeText.substring(0, rightSplit);
        # }
        # -----------------------------------------------------

        index = link_cate_text.find("(")

        if index != -1:
            link_cate_text = link_cate_text[:index]

        # -----------------------------------------------------
        # Java：
        #
        # if (MyText.isTrimEmpty(linkTypeText)) {
        #     linkTypeText = "其他";
        # }
        # -----------------------------------------------------

        link_cate_text = link_cate_text.strip()

        if not link_cate_text:
            link_cate_text = self.config.default_link_cate_text

        # -----------------------------------------------------
        # Java：
        #
        # if (MyText.isTrimEmpty(interLinkType) == false) {
        #     linkTypeText = interLinkType + "||" + linkTypeText;
        # }
        # -----------------------------------------------------

        inter_link_type = self.config.inter_link_cate.strip()

        if inter_link_type:
            link_cate_text = f"{inter_link_type}||{link_cate_text}"

        return link_cate_text

    # =========================================================
    # 最终业务字符串
    # =========================================================

    def _build_value(
        self,
        *,
        url: str,
        flag: int,
        # index: int,
        limit_cate_level_0_id: int,
        cate_name: str,
        cate_names_path: list[str] | None,
    ) -> str:
        """
        构建分类层业务字符串。

        当前格式：

            need_get_link_text=True:

                当 cate_names_path 长度 >= 2 时：

                    URL--flag>>>limit_cate_level_0_id>分类路径

                当 cate_names_path 长度 < 2 时：

                    URL--flag>>>limit_cate_level_0_id>当前分类名称

            need_get_link_text=False:

                URL--0>>>limit_cate_level_0_id>inter_link_cate

        其中：

            分类路径中的各级分类名称使用 "||" 连接。

        例如：

            cate_names_path = ["小说"]

                URL--0>>>-1>小说

            cate_names_path = ["小说", "科幻/魔幻"]

                URL--1>>>-1>小说||科幻/魔幻

            need_get_link_text=False:

                URL--0>>>15>小说||言情小说

        注意：

            分类文本 / 分类路径不是最终分类索引。

            当前层 links 中的 index 也不会写入这里。

            最终分类索引由后续分类匹配阶段产生。
        """

        # 有完整分类路径时，使用完整分类路径
        if cate_names_path and len(cate_names_path) >= 2:
            cate_text = "||".join(cate_names_path)
        else:
            cate_text = cate_name

        if self.config.need_get_link_text == True:
            return f"{url}--{flag}{self.config.link_separator}{limit_cate_level_0_id}>{cate_text}"

        return f"{url}--0{self.config.link_separator}{limit_cate_level_0_id}>{self.config.inter_link_cate}"
