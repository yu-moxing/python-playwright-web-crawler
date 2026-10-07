# -*- coding: utf-8 -*-
"""
keyword_utils - 关键词处理工具类

从 Java 版本转换而来，提供:
- 特殊字符映射 (全角转半角)
- 数字转中文
- 产品名称规范化
- 中英文分隔
- 字符串检查等功能
"""

import re
from typing import Optional, Tuple

from mini_text.string_utils import (
    get_first_big_letter_all_word as _string_get_first_big_letter_all_word,
)
from mini_text.string_utils import (
    is_blank as _string_is_blank,
)
from mini_text.string_utils import (
    is_trim_empty as _string_is_trim_empty,
)


class KeywordUtils:
    """关键词处理工具类"""

    # ==================== 常量定义 ====================
    # 最多支持合并8行
    # MY_TDC_HEAD_FLAG = ["##td92&&", "##td93&&", "##td94&&", "##td95&&",
    #                     "##td96&&", "##td97&&", "##td98&&"]
    # MY_TDR_HEAD_FLAG = ["##tdR2&&", "##tdR3&&", "##tdR4&&", "##tdR5&&",
    #                     "##tdR6&&", "##tdR7&&", "##tdR8&&"]

    # COMMON_SPLIT_FLAG = "\t\t---->"
    # MY_TABLE_END_FLAG = "##1BAT&&"
    # MY_TR_END_FLAG = "##78Tr&&"
    # MY_TD_END_FLAG = "##70td&&"
    # MAX_COLSPAN = len(MY_TDC_HEAD_FLAG)

    SEPARATOR = "------------"
    MIN_SEPARATOR = "--"

    # ==================== 类级别变量 ====================
    attributeKeyNameMap: set = set()
    specialCharMap: dict = {}
    numberToChineseCharMap: dict = {}
    unKeywords: set = set()

    # ==================== 初始化方法 ====================
    @staticmethod
    def init(cls) -> None:
        """主初始化入口"""
        # 特殊字符转换表
        cls._init_special_char_map()
        # 阿拉伯、大写数字转为：中文数字
        cls._init_number_to_chinese_char_map()
        # 属性名称表
        cls._init_attribute_key_name_map()
        # 需要排作的关键字
        cls._init_un_keywords()

    @classmethod
    def _init_special_char_map(cls) -> None:
        """初始化特殊字符映射 (全角转半角)"""
        print("初始化---specialCharMap！！！")
        cls.specialCharMap = {
            # 中文空格转英文空格
            "　": " ",  # 全角空格
            # 全角到半角的转换
            "●": "．",
            "é": "e",
            "è": "e",
            # 标点符号转换
            "，": ",",
            "。": ".",
            "＜": "<",
            "＞": ">",
            "｜": "|",
            "《": "<",
            "》": ">",
            "［": "[",
            "］": "]",
            "？": "?",
            "“": "'",
            "”": "'",
            "：": ":",
            "（": "(",
            "）": ")",
            "－": "-",
            "～": "~",
            "！": "!",
            # 全角数字转半角数字
            "０": "0",
            "１": "1",
            "２": "2",
            "３": "3",
            "４": "4",
            "５": "5",
            "６": "6",
            "７": "7",
            "８": "8",
            "９": "9",
            # 全角字母转半角字母 (大写)
            "Ａ": "A",
            "Ｂ": "B",
            "Ｃ": "C",
            "Ｄ": "D",
            "Ｅ": "E",
            "Ｆ": "F",
            "Ｇ": "G",
            "Ｈ": "H",
            "Ｉ": "I",
            "Ｊ": "J",
            "Ｋ": "K",
            "Ｌ": "L",
            "Ｍ": "M",
            "Ｎ": "N",
            "Ｏ": "O",
            "Ｐ": "P",
            "Ｑ": "Q",
            "Ｒ": "R",
            "Ｓ": "S",
            "Ｔ": "T",
            "Ｕ": "U",
            "Ｖ": "V",
            "Ｗ": "W",
            "Ｘ": "X",
            "Ｙ": "Y",
            "Ｚ": "Z",
            # 全角字母转半角字母 (小写)
            "ａ": "a",
            "ｂ": "b",
            "ｃ": "c",
            "ｄ": "d",
            "ｅ": "e",
            "ｆ": "f",
            "ｇ": "g",
            "ｈ": "h",
            "ｉ": "i",
            "ｊ": "j",
            "ｋ": "k",
            "ｌ": "l",
            "ｍ": "m",
            "ｎ": "n",
            "ｏ": "o",
            "ｐ": "p",
            "ｑ": "q",
            "ｒ": "r",
            "ｓ": "s",
            "ｔ": "t",
            "ｕ": "u",
            "ｖ": "v",
            "ｗ": "w",
            "ｘ": "x",
            "ｙ": "y",
            "ｚ": "z",
        }

    @classmethod
    def _init_number_to_chinese_char_map(cls) -> None:
        """初始化数字转中文映射"""
        print("初始化---numberToChineseCharMap！！！")
        cls.numberToChineseCharMap = {
            # 数字转中文
            "0": "零",
            "1": "一",
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
            "7": "七",
            "8": "八",
            "9": "九",
            # 繁体数字转简体
            "壹": "一",
            "贰": "二",
            "叁": "三",
            "肆": "四",
            "伍": "五",
            "陆": "六",
            "柒": "七",
            "捌": "八",
            "玖": "九",
        }

    @classmethod
    def _init_attribute_key_name_map(cls) -> None:
        """初始化属性关键词集合"""
        cls.attributeKeyNameMap = {
            "简介",
            "说明",
            "描述",
            "信息",
            "方法",
            "用法",
            "功效",
            "功能",
            "效果",
            "特性",
            "特点",
            "性能",
            "外观",
            "包装",
            "花语",
            "属性",
            "注意",
            "产地",
            "成分",
            "规格",
            "设计",
            "用途",
            "介绍",
            "详请",
            "详述",
            "插图",
            "图片",
            "细节",
            "尺寸",
            "大小",
            "参数",
            "声明",
            "售后",
            "服务",
        }

    @classmethod
    def _init_un_keywords(cls) -> None:
        """初始化排除关键词集合"""
        unKeywordText = (
            "我们,他们,它们,你们,一个,两个,这个,那个,这些,一些,我的,你的,她的,他的,它的,所有,东西,可是,但是,可以,"
            "可能,必须,需要,普通,时间,然后,中国,美国,美元,白色,黑色,红色,如果,就是,只是,也许,肯定,确定,非常,很好,"
            "太好,太大,很大,今天,昨天,明天,公司,全部,全都,全是,都是,总是,并且,而且,虽然,等等,"
            "鲜艳,美丽,漂亮,好看,银色,绿色,桔色,紫色,褐色,青色,黄色,蓝色,橙色,灰色,颜色,色彩,任何,使用,修改,免费,如何,"
            "更多,标准,格式,评论,这是,那是,通过,一年,两年,三年,一次,两次,多次,多个,一人,两人,多人,一次性,一般,不可能,不错,"
            "世界上,什么,时候,什么时候,价格,会出来,但我,使用,关于,决定,协议,访问,经常,即将,原价,参加,周一,周二,周三,周四,周五,周六,周日,"
            "部分,方法,方案,实施,执行,邻居,重置,自己,自动,英国,英寸,德国,法国,日本,俄罗斯,印度,俄国,加拿大,韩国,朝鲜,国际,计划,"
            "在你,这里,在这里,已经,您的,想法,想象,意味着,推出,提供,收藏,收费,文章,星期,记录,"
            "更换,更新,最后,最先,最大,最小,有一个,这一个,服务,没戏,点击,过去,现在,未来,用户,客户,买家,卖家,看到,真棒,真正,"
            "正确,错误,对的,观点,思想,观念,不对,谢谢,再见,欢迎,世界,地球,城市,国家,全球,工作,单位,上班,下班,早餐,午餐,晚餐,"
            "朋友,好友,亲人,爸爸,妈妈,姐姐,妹妹,哥哥,弟弟,父母,友情,亲情,爱情,爱人,男孩,女孩,男孩子,女孩子,男朋友,女朋友,"
            "一月,二月,三月,四月,五月,六月,七月,八月,九月,十月,十一月,十二月,男人,女人,"
            "1月,2月,3月,4月,5月,6月,7月,8月,9月,10月,11月,12月,2010年,2011年,2012年,"
            "星期一,星期二,星期三,星期四,星期五,星期六,星期日,月份,年度,"
        )
        unKeywordList = unKeywordText.split(",")
        cls.unKeywords = set(unKeywordList)
        print(f"初始化---initUnKeywords！！！要排除的keyWord个数= {len(unKeywordList)}")

    # ==================== 工具方法 ====================

    # @staticmethod
    @staticmethod
    def get_code_to_string(in_str: str) -> str:
        """
        将 Java 旧系统中的特殊编码转换为普通字符串。

        对应 Java：

            MyText.getCodeToString(inStr)

        处理：

            &amp;   -> &
            &nbsp;  -> 空格
            &gt;    -> >
            &raquo; -> ?

            %3A     -> :
            %3a     -> :
            %20     -> 空格

            //      -> /
            :/      -> ://

        注意：

        保持旧 Java 的处理顺序，
        不使用 urllib.parse.unquote() 等方式整体替换，
        避免改变旧系统行为。
        """

        if ";" in in_str:
            in_str = in_str.replace("&amp;", "&")
            in_str = in_str.replace("&AMP;", "&")

            in_str = in_str.replace("&nbsp;", " ")
            in_str = in_str.replace("&NBSP;", " ")

            in_str = in_str.replace("&gt;", ">")
            in_str = in_str.replace("&GT;", ">")

            in_str = in_str.replace("&raquo;", "?")
            in_str = in_str.replace("&raquo;", "?")

        code_list = [
            ("%3A", ":"),
            ("%3a", ":"),
            ("%20", " "),
            ("//", "/"),
            (":/", "://"),
        ]

        for old, new in code_list:
            if old in in_str:
                in_str = in_str.replace(old, new)

        return in_str

    @staticmethod
    def get_code_to_chinese(in_text: str) -> str:
        """
        将数字字符实体转换为中文字符。

        对应 Java：

            MyText.getCodeToChinese(inText)

        支持两种格式：

            &#27431;&#33298;&#20025;

        以及：

            &27431;&33298;&20025;

        只处理至少 2 位数字的实体，
        与旧 Java：

            [0-9]{2,}

        保持一致。
        """

        if not in_text or not in_text.strip():
            return ""

        # Java：
        #
        # int indexCommon = inText.indexOf(";");
        #
        # 只有存在 ; 才继续处理。
        if ";" not in in_text:
            return in_text

        # =========================================================
        # 格式一：
        #
        # &#27431;&#33298;&#20025;
        # =========================================================

        if "&#" in in_text:
            matches = re.findall(
                r"&#([0-9]{2,});",
                in_text,
            )

            for number_text in matches:
                value = int(number_text)

                in_text = in_text.replace(
                    f"&#{number_text};",
                    chr(value),
                )

        # =========================================================
        # 格式二：
        #
        # &27431;&33298;&20025;
        # =========================================================

        elif "&" in in_text:
            matches = re.findall(
                r"&([0-9]{2,});",
                in_text,
            )

            for number_text in matches:
                value = int(number_text)

                in_text = in_text.replace(
                    f"&{number_text};",
                    chr(value),
                )

        return in_text

    @staticmethod
    def get_normal_category_str(in_str: str) -> str:
        # def get_normal_category_str(cls, in_str: str) -> str:
        """
        Java MyText.getNormalCategoryStr 的 Python 版本。

        对分类名称进行规范化处理。

        Args:
            in_str: 输入分类名称

        Returns:
            规范化后的分类名称
        """
        normal_str_list = [
            "★",
            "",
            "☆",
            "",
            "专卖店",
            "",
            "专卖",
            "",
            "手机报价",
            "",
            "报价",
            "",
            "排序",
            "",
            "排列",
            "",
            "专区",
            "",
            "系列",
            "",
            "[",
            "",
            "]",
            "",
            "#",
            "",
            "　",
            " ",
            "■",
            " ",
            "·",
            " ",
            "。",
            " ",
            "．",
            " ",
            ".",
            " ",
            "\\",
            "/",
        ]

        for i in range(0, len(normal_str_list), 2):
            old_str = normal_str_list[i]
            new_str = normal_str_list[i + 1]

            if old_str in in_str:
                in_str = in_str.replace(old_str, new_str)

        return in_str.strip()

    @staticmethod
    def get_number_to_chinese(line: str) -> str:
        """
        将0-9转为中文零-九

        Args:
            line: 输入字符串

        Returns:
            转换后的字符串
        """
        if not KeywordUtils.numberToChineseCharMap:
            KeywordUtils._init_number_to_chinese_char_map()

        line = line.lower()

        for char in line:
            if char in KeywordUtils.numberToChineseCharMap:
                line = line.replace(
                    char,
                    KeywordUtils.numberToChineseCharMap[char],
                )

        return line

    @staticmethod
    def get_delete_and_lower_str(inStr: str) -> str:
        """
        删除特定词并转小写

        Args:
            inStr: 输入字符串

        Returns:
            处理后的字符串
        """
        if inStr == "":
            return ""

        deleteWords = [
            "品牌",
            "",
            "用品",
            "",
            "产品",
            "",
            "商品",
            "",
            "所有",
            "",
            "全部",
            "",
            "最新",
            "",
            "包装",
            "",
            "生活",
            "",
            "限时",
            "",
            "抢购",
            "",
            "优惠",
            "",
            "促销",
            "",
            "秒杀",
            "",
            "男士",
            "男",
            "男性",
            "男",
            "女士",
            "女",
            "女性",
            "女",
            "色",
            "",
            "馆",
            "",
            "区",
            "",
            "品",
            "",
        ]

        # 步距为2，第1个为源词，第2个为替换词
        for i in range(0, len(deleteWords), 2):
            if deleteWords[i] in inStr:
                inStr = inStr.replace(deleteWords[i], deleteWords[i + 1])

        # 将数字转中文
        inStr = KeywordUtils.get_number_to_chinese(inStr)

        return inStr.lower()

    @staticmethod
    def get_normal_product_name(line: str) -> str:
        """
        规范化产品名称

        Args:
            line: 输入产品名称

        Returns:
            规范化后的名称
        """
        replaceNameList = [
            "专卖店",
            " ",
            "专卖",
            " ",
            "网上",
            " ",
            "专区",
            " ",
            "发货",
            " ",
            "作者　　",
            "作者",
            "作　　者",
            "作者",
            "作　者",
            "author",
            "作    者",
            "作者",
            "作   者",
            "作者",
            "作  者",
            "作者",
            "作 者",
            "作者",
            "品牌名称",
            " ",
            "品牌名",
            " ",
            "品牌",
            " ",
            "更多",
            " ",
            "其他",
            " ",
            "其它",
            " ",
            "专柜",
            " ",
            "皇冠",
            " ",
            "正品",
            " ",
            "自由",
            " ",
            "未知",
            " ",
            "\r\n",
            " ",
            "品　　牌",
            " ",
            "品　牌",
            " ",
            "品    牌",
            " ",
            "品   牌",
            " ",
            "品  牌",
            " ",
            "品 牌",
            " ",
            "导　　演",
            "导演",
            "导　演",
            "导演",
            "导    演",
            "导演",
            "导   演",
            "导演",
            "导  演",
            "导演",
            "导 演",
            "导演",
            "演　　员",
            "主演",
            "演　员",
            "主演",
            "演    员",
            "主演",
            "演   员",
            "主演",
            "演  员",
            "主演",
            "演 员",
            "主演",
            "演员",
            "主演",
            "主　　演",
            "主演",
            "主　演",
            "主演",
            "主    演",
            "主演",
            "主   演",
            "主演",
            "主  演",
            "主演",
            "主 演",
            "主演",
            ":",
            "：",
            "’",
            "'",
        ]

        # 步距为2，每次循环替换
        for i in range(0, len(replaceNameList), 2):
            if replaceNameList[i] in line:
                line = line.replace(replaceNameList[i], replaceNameList[i + 1])

        # 正则替换 HTML 实体
        line = re.sub(r"&amp;", "&", line, flags=re.IGNORECASE)
        line = re.sub(r"&nbsp;", " ", line, flags=re.IGNORECASE)

        line = line.strip()
        if line.startswith(":") or line.startswith("："):
            if len(line) > 1:
                line = line[1:]

        return line

    @staticmethod
    def split_name_and_type(nameType: str) -> Tuple[str, str]:
        """
        拆分品牌名和类型

        Args:
            nameType: 品牌名型号组合字符串

        Returns:
            (品牌名, 类型) 元组

        Note:
            Python 版改为返回 tuple，不再修改输入数组
        """
        name = ""
        typeStr = ""

        tempNameType = nameType.strip()
        if _string_is_trim_empty(tempNameType):
            return (name, typeStr)

        # 如果包含空格且第一个字符为英文或空格前后是中文时用空格分隔
        spaceIndex = tempNameType.find(" ")
        if spaceIndex >= 1 and spaceIndex + 2 <= len(tempNameType):
            str1 = tempNameType[spaceIndex - 1 : spaceIndex]
            str2 = tempNameType[spaceIndex + 1 : spaceIndex + 2]

            # 判断第一个字符是否为英文 (ASCII)
            firstCharIsAscii = ord(tempNameType[0]) < 128
            # 判断空格前后是否都是中文
            str1IsChinese = ord(str1) > 127
            str2IsChinese = ord(str2) > 127

            if firstCharIsAscii or (str1IsChinese and str2IsChinese):
                name = tempNameType[:spaceIndex]
                typeStr = tempNameType[spaceIndex + 1 :]
                return (name, typeStr)

        # 异或分法：根据字符类型变化分割
        firstCharIsAscii = ord(tempNameType[0]) < 128

        for i, char_one in enumerate(tempNameType):
            charIsAscii = ord(char_one) < 128

            if charIsAscii != firstCharIsAscii:
                name = tempNameType[:i]
                if char_one == " ":
                    typeStr = tempNameType[i + 1 :]
                else:
                    typeStr = tempNameType[i:]
                return (name, typeStr)

        # 全部是同类型字符，尝试用空格分割
        if " " in tempNameType:
            spaceIndex = tempNameType.find(" ")
            name = tempNameType[:spaceIndex]
            typeStr = tempNameType[spaceIndex + 1 :]
            print(f"使用特殊分法——英文名: {name} {typeStr}")

        return (name, typeStr)

    @staticmethod
    def split_chinese_english(inputStr: str) -> str:
        """
        将字符串中的中文和英文用空格分开

        Args:
            inputStr: 输入字符串

        Returns:
            中英文分隔后的字符串
        """
        if _string_is_trim_empty(inputStr):
            return ""

        oldType = 0  # 0英文，1中文
        reStr = []
        isLastSpace = False

        for i, char in enumerate(inputStr):
            # 遇到空格
            if char == " ":
                if not isLastSpace:
                    isLastSpace = True
                    reStr.append(" ")
                continue

            # 判断字符类型：ASCII 为英文(0)，否则为中文(1)
            newType = 0 if ord(char) < 128 else 1

            if i == 0:
                oldType = newType

            # 类型变化时添加空格
            if newType != oldType and i > 0:
                oldType = newType
                if not isLastSpace:
                    isLastSpace = True
                    reStr.append(" ")

            isLastSpace = False
            reStr.append(char)

        return "".join(reStr).strip()

    @staticmethod
    def ignore_case_replace(source: str, oldstring: str, newstring: str) -> str:
        """
        不区分大小写的替换

        Args:
            source: 源字符串
            oldstring: 要替换的模式
            newstring: 替换后的字符串

        Returns:
            替换后的字符串
        """
        pattern = re.compile(oldstring, re.IGNORECASE)
        return pattern.sub(newstring, source)

    @staticmethod
    def delete_country(cls, line: str) -> str:
        """
        删除国家或地区名称

        Args:
            line: 输入字符串

        Returns:
            删除国家名后的字符串
        """
        deleteCountryList = [
            "澳大利亚",
            "委内瑞拉",
            "白俄罗斯",
            "马来西亚",
            "新加坡",
            "新西兰",
            "叙利亚",
            "西班牙",
            "意大利",
            "俄罗斯",
            "加拿大",
            "阿根廷",
            "以色列",
            "奥地利",
            "韩国",
            "瑞士",
            "中国",
            "大陆",
            "港台",
            "台湾",
            "香港",
            "澳门",
            "美国",
            "法国",
            "日本",
            "英国",
            "德国",
            "印度",
            "泰国",
            "荷兰",
            "巴西",
            "丹麦",
            "瑞典",
            "捷克",
            "俄国",
            "国际",
        ]

        reLine = line
        for country in deleteCountryList:
            if country in reLine:
                reLine = reLine.replace(country, " ")

        return reLine.strip()

    @staticmethod
    def delete_not_use_name(line: str) -> str:
        """
        删除无用的名称词

        Args:
            line: 输入字符串

        Returns:
            处理后的字符串
        """
        deleteNotUseNameList = [
            "本书编写组",
            "本书编辑部",
            "本书编委会",
            "本书编委",
            "本书编辑",
            "编委会",
            "艺术家",
            "演奏者",
            "编委员",
            "委员会",
            "编辑部",
            "杂志社",
            "教材组",
            "歌手",
            "未知",
            "组编",
            "监制",
            "简介",
            "编辑",
            "编译",
            "翻译",
            "译者",
            "创编",
            "编著",
            "编者",
            "选注",
            "解说词",
            "解说",
            "说词",
            "合著者",
            "合著",
            "合编",
            "原著",
            "著者",
            "校注",
            "校对",
            "选编",
            "其他",
            "主演",
            "导演",
            "演员",
            "配音",
            "主讲",
            "写字",
            "书者",
            "改编",
            "改写",
            "编选",
            "作者",
            "主编",
            "编写",
            "编审",
            "组织",
            "辑校",
            "丛书",
            "注释",
            "注译",
            "教学",
            "讲解",
            "绘画",
            "插图",
            "示范",
            "春秋",
            "战国",
            "晋国",
            "宋代",
            "清代",
            "东晋",
            "明代",
            "唐代",
            "元代",
            "国语",
            "韩语",
            "日语",
            "俄语",
            "英语",
            "国粤",
            "粤语",
            "双语",
            "双音",
            "美语",
            "发音",
            "字幕",
            "中文",
            "等编",
            "等写",
            "等作",
            "等著",
            "等导",
            "等演",
            "等唱",
            "本社",
            " 书",
            "译",
            "等",
            "著",
            "编",
            "dubber",
            "www",
            "com",
            "http",
        ]

        for word in deleteNotUseNameList:
            if word in line:
                line = line.replace(word, " ")

        # 删除国家或地区信息
        line = KeywordUtils.delete_country(line)

        # 按空格分割，去重，跳过长度为1的词
        lines = line.split(" ")
        reLineParts = []
        seen = set()

        for word in lines:
            if len(word) <= 1:
                continue
            if word not in seen:
                seen.add(word)
                reLineParts.append(word)

        return " ".join(reLineParts)


# ==================== 模块级初始化 ====================
# 自动执行初始化（可选）
# KeywordUtils.init()


# ==================== 便捷函数（模块级别名） ====================
def init():
    """初始化快捷函数"""
    KeywordUtils.init()


def get_code_to_string(in_str: str) -> str:
    return KeywordUtils.get_code_to_string(in_str)


def get_code_to_chinese(in_text: str) -> str:
    return KeywordUtils.get_code_to_chinese(in_text)


def get_normal_category_str(in_str: str) -> str:
    return KeywordUtils.get_normal_category_str(in_str)


def get_number_to_chinese(line: str) -> str:
    return KeywordUtils.get_number_to_chinese(line)


def get_delete_and_lower_str(inStr: str) -> str:
    return KeywordUtils.get_delete_and_lower_str(inStr)


def get_normal_product_name(line: str) -> str:
    return KeywordUtils.get_normal_product_name(line)


def get_first_big_letter_all_word(inStr: str) -> str:
    return _string_get_first_big_letter_all_word(inStr)


def split_name_and_type(nameType: str) -> Tuple[str, str]:
    return KeywordUtils.split_name_and_type(nameType)


def split_chinese_english(inputStr: str) -> str:
    return KeywordUtils.split_chinese_english(inputStr)


def ignore_case_replace(source: str, oldstring: str, newstring: str) -> str:
    return KeywordUtils.ignore_case_replace(source, oldstring, newstring)


def delete_country(line: str) -> str:
    return KeywordUtils.delete_country(line)


def delete_not_use_name(line: str) -> str:
    return KeywordUtils.delete_not_use_name(line)


def is_blank(astr: Optional[str]) -> bool:
    return _string_is_blank(astr)


def is_trim_empty(astr: Optional[str]) -> bool:
    return _string_is_trim_empty(astr)
