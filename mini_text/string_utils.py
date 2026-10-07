"""
字符串验证工具模块
提供各种字符串类型判断功能
"""

import re
from typing import Optional

# ============================================================================
# 字符串分隔符常量
# ============================================================================

# 节点分隔符
NODE_SPLIT = "##"

# 通用分隔符
MY_SPLIT = "%%"

# 小分隔符
SMALL_SPLIT = "##&&"

# 大分隔符
BIG_SPLIT = "##NEWLINE&&"

# 通用分隔线
SEPARATOR = "------------"

# ============================================================================
# 品牌名称相关常量
# ============================================================================

# 英文品牌最大长度
LIMIT_ENGLISH_LENGTH = 20

# 中文品牌最大长度
LIMIT_CHINESE_LENGTH = 8

# 中文品牌映射文件
CHINESE_NAME_MAP_FILE = "chinaNameMap.txt"

# 英文品牌映射文件
ENGLISH_NAME_MAP_FILE = "englishNameMap.txt"

# 中英文品牌对应关系文件
NAME_HASH_MAP_FILE = "nameHashMap.txt"

# 品牌名Map分隔线
NAME_MAP_SPLIT = "-->"


def is_trim_empty(text: Optional[str]) -> bool:
    """
    判断字符串去除空格后是否为空

    包括以下情况：
    - None 或空字符串
    - 仅包含空白字符
    - 等于 "void(null)" 或 "void(0)"

    Args:
        text: 待检查的字符串

    Returns:
        为空返回 True，否则返回 False

    Examples:
        >>> is_trim_empty(None)
        True
        >>> is_trim_empty("  ")
        True
        >>> is_trim_empty("void(null)")
        True
        >>> is_trim_empty("hello")
        False
    """
    if text is None or len(text) == 0:
        return True

    trimmed = text.strip()
    if not trimmed:
        return True

    # 检查特殊值
    if trimmed == "void(null)" or trimmed == "void(0)":
        return True

    return False


def is_blank(text: Optional[str]) -> bool:
    """
    判断字符串是否为空（None 或长度为 0）

    Args:
        text: 待检查的字符串

    Returns:
        为空返回 True，否则返回 False

    Examples:
        >>> is_blank(None)
        True
        >>> is_blank("")
        True
        >>> is_blank("  ")
        False
    """
    return text is None or len(text) == 0


def is_all_letter(text: str) -> bool:
    """
    判断字符串是否全部由字母组成

    Args:
        text: 待检查的字符串

    Returns:
        全部是字母返回 True，否则返回 False

    Examples:
        >>> is_all_letter("Hello")
        True
        >>> is_all_letter("Hello123")
        False
    """
    return text.isalpha()


def is_all_number(text: str) -> bool:
    """
    判断字符串是否全部由数字组成

    Args:
        text: 待检查的字符串

    Returns:
        全部是数字返回 True，否则返回 False

    Examples:
        >>> is_all_number("12345")
        True
        >>> is_all_number("12.345")
        False
    """
    return text.isdigit()


def is_all_float(text: str) -> bool:
    """
    判断字符串是否是有效的浮点数格式

    允许：数字、小数点、正负号
    正负号只能在开头

    Args:
        text: 待检查的字符串

    Returns:
        是有效浮点数格式返回 True，否则返回 False

    Examples:
        >>> is_all_float("123.45")
        True
        >>> is_all_float("-123.45")
        True
        >>> is_all_float("12-3")
        False
    """
    if not text:
        return False

    # 使用正则表达式匹配浮点数
    pattern = r"^[+-]?\d+\.?\d*$"
    return bool(re.match(pattern, text))


def is_all_letter_or_number(text: str) -> bool:
    """
    判断字符串是否全部由字母或数字组成

    Args:
        text: 待检查的字符串

    Returns:
        全部是字母或数字返回 True，否则返回 False

    Examples:
        >>> is_all_letter_or_number("Hello123")
        True
        >>> is_all_letter_or_number("Hello 123")
        False
    """
    return text.isalnum()


def is_all_letter_or_float(text: str) -> bool:
    """
    判断字符串是否全部由字母、数字、小数点、正负号组成

    Args:
        text: 待检查的字符串

    Returns:
        符合格式返回 True，否则返回 False

    Examples:
        >>> is_all_letter_or_float("ABC123.45")
        True
        >>> is_all_letter_or_float("ABC@123")
        False
    """
    if not text:
        return False

    # 允许的字符：字母、数字、小数点、正负号
    allowed_pattern = r"^[a-zA-Z0-9.+\-]+$"
    return bool(re.match(allowed_pattern, text))


def has_number(text: str) -> bool:
    """
    判断字符串中是否包含数字

    Args:
        text: 待检查的字符串

    Returns:
        包含数字返回 True，否则返回 False

    Examples:
        >>> has_number("Hello123")
        True
        >>> has_number("Hello")
        False
    """
    return any(char.isdigit() for char in text)


def has_chinese(text: str) -> bool:
    """
    判断字符串中是否包含中文字符

    Args:
        text: 待检查的字符串

    Returns:
        包含中文返回 True，否则返回 False

    Examples:
        >>> has_chinese("Hello世界")
        True
        >>> has_chinese("Hello")
        False
    """
    # 使用 Unicode 范围判断中文字符
    chinese_pattern = r"[一-鿿]+"
    return bool(re.search(chinese_pattern, text))


def is_all_chinese(text: str) -> bool:
    """
    判断字符串是否全部由中文字符组成

    Args:
        text: 待检查的字符串

    Returns:
        全部是中文返回 True，否则返回 False

    Examples:
        >>> is_all_chinese("你好世界")
        True
        >>> is_all_chinese("Hello世界")
        False
    """
    if not text:
        return False

    # 使用 Unicode 范围匹配中文字符
    chinese_pattern = r"^[一-鿿]+$"
    return bool(re.match(chinese_pattern, text))


def is_all_english(text: str) -> bool:
    """
    判断字符串是否全部由英文字符组成（不包含中文）

    注意：这与 is_all_letter 不同，is_all_letter 要求全部是字母
    而 is_all_english 仅排除中文字符，允许数字、符号等

    Args:
        text: 待检查的字符串

    Returns:
        全部是英文（不含中文）返回 True，否则返回 False

    Examples:
        >>> is_all_english("Hello123!")
        True
        >>> is_all_english("Hello世界")
        False
    """
    return not has_chinese(text)


def has_letter(text: str) -> bool:
    """
    判断字符串中是否包含英文字母（A-Z、a-z）。

    与 Java 版 isHaveLetter() 保持一致，仅判断 ASCII 英文字母，
    不认为中文、日文、俄文等其它 Unicode 字母属于英文。

    Args:
        text: 待检查的字符串。

    Returns:
        包含英文字母返回 True，否则返回 False。

    Examples:
        >>> has_letter("Apple123")
        True

        >>> has_letter("123456")
        False

        >>> has_letter("苹果")
        False

        >>> has_letter("苹果Apple")
        True

        >>> has_letter("")
        False
    """
    for ch in text:
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            return True

    return False


def is_letter_char(char: str) -> bool:
    """
    判断单个字符是否是字母

    Args:
        char: 单个字符

    Returns:
        是字母返回 True，否则返回 False

    Examples:
        >>> is_letter_char('A')
        True
        >>> is_letter_char('9')
        False
    """
    if len(char) != 1:
        return False
    return char.isalpha()


def is_number_char(char: str) -> bool:
    """
    判断单个字符是否是数字

    Args:
        char: 单个字符

    Returns:
        是数字返回 True，否则返回 False

    Examples:
        >>> is_number_char('9')
        True
        >>> is_number_char('A')
        False
    """
    if len(char) != 1:
        return False
    return char.isdigit()


# normalize_int_string 对应原版JAVA的：public static String getNormalValToString(int norLength, int val) 函数
def normalize_int_string(value: int, length: int) -> str:
    """
    将整数转换为固定位数字符串（前导零填充）

    Args:
        value: 整数值
        length: 目标长度

    Returns:
        固定位数的字符串

    Examples:
        >>> normalize_int_string(42, 5)
        '00042'
        >>> normalize_int_string(123, 3)
        '123'
    """
    return str(value).zfill(length)


# normalize_long_string 对应原版JAVA的：public static String getNormalLongValToString(int norLength, long val) 函数
def normalize_long_string(value: int, length: int) -> str:
    """
    将长整数转换为固定位数字符串（前导零填充）

    Python 中 int 无大小限制，此方法保留以兼容 Java 接口

    Args:
        value: 长整数值
        length: 目标长度

    Returns:
        固定位数的字符串

    Examples:
        >>> normalize_long_string(123456789, 12)
        '000123456789'
    """
    return str(value).zfill(length)


def is_same(str1: Optional[str], str2: Optional[str]) -> bool:
    """
    判断两个字符串是否相等

    两个空字符串（None 或空）视为相等

    Args:
        str1: 第一个字符串
        str2: 第二个字符串

    Returns:
        相等返回 True，否则返回 False

    Examples:
        >>> is_same("hello", "hello")
        True
        >>> is_same(None, "")
        True
        >>> is_same("hello", "world")
        False
    """
    # 两个都是空，视为相等
    if is_trim_empty(str1) and is_trim_empty(str2):
        return True

    # 只有一个是空，不相等
    if is_trim_empty(str1) or is_trim_empty(str2):
        return False

    return str1 == str2


def get_first_big_letter_all_word(text: str) -> str:
    """
    将字符串中每个英文单词的首字母转换为大写，其余字母转换为小写。

    规则（与 Java 版保持一致）：
    1. 先整体转为小写并去除首尾空格。
    2. 每个连续英文单词（a-z）的首字母改为大写。
    3. 非英文字符保持不变，并作为新的单词分隔符。
    4. 如果整个字符串中的英文字母总数 <= 3，则整个结果全部转为大写。

    Args:
        text: 输入字符串

    Returns:
        规范化后的字符串

    Examples:
        >>> get_first_big_letter_all_word("mobile phone")
        'Mobile Phone'

        >>> get_first_big_letter_all_word("APPLE iphone")
        'Apple Iphone'

        >>> get_first_big_letter_all_word("usb")
        'USB'

        >>> get_first_big_letter_all_word("hp printer")
        'Hp Printer'

        >>> get_first_big_letter_all_word("sony-camera")
        'Sony-Camera'
    """
    if text is None:
        return ""

    text = text.lower().strip()

    result = []
    letter_start = False
    letter_count = 0

    for ch in text:
        # 与 Java 保持一致：只认为 a-z 是英文字符
        if "a" <= ch <= "z":
            if not letter_start:
                result.append(ch.upper())
            else:
                result.append(ch)

            letter_count += 1
            letter_start = True
        else:
            result.append(ch)
            letter_start = False

    result_str = "".join(result)

    # Java 原逻辑：如果英文字母总数 <= 3，则整体转大写
    if letter_count <= 3:
        return result_str.upper()

    return result_str


def to_space_replace(text: str) -> str:
    """
    将字符串中除中文、英文字母、数字之外的所有字符替换为空格。

    连续多个特殊字符只会生成一个空格，最后统一转换为小写，
    并去除首尾空格。

    Args:
        text: 原始字符串。

    Returns:
        规范化后的字符串。

    Examples:
        >>> to_space_replace("Apple-iPhone(15)")
        'apple iphone 15'

        >>> to_space_replace("【三星】Galaxy-S25!!!")
        '三星 galaxy s25'

        >>> to_space_replace("Sony@@@Camera###A7R5")
        'sony camera a7r5'

        >>> to_space_replace("￥1999.99")
        '1999 99'

        >>> to_space_replace("   Hello---World   ")
        'hello world'

        >>> to_space_replace("A@@@###B")
        'a b'

        >>> to_space_replace("中文ABC123")
        '中文abc123'

        >>> to_space_replace("......")
        ''

        >>> to_space_replace("")
        ''
    """

    result = []
    last_is_blank = False

    for ch in text:
        # 中文
        if "\u4e00" <= ch <= "\u9fff":
            result.append(ch)
            last_is_blank = False

        # 英文字母
        elif ch.isalpha():
            result.append(ch)
            last_is_blank = False

        # 数字
        elif ch.isdigit():
            result.append(ch)
            last_is_blank = False

        # 其它字符全部替换为空格（连续空格合并）
        else:
            if not last_is_blank:
                result.append(" ")
                last_is_blank = True

    return "".join(result).lower().strip()
