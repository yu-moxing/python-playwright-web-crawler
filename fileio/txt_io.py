"""
TXT 普通文本文件读写模块

职责：

    - 普通文本文件读写
    - 读取 / 写入完整字符串
    - 按行读取 / 写入文本
    - 追加写入字符串 / 多行文本
    - 支持 txt / html / css / js / markdown / xml 等文本文件

说明：

    本模块为无状态的模块级函数，
    由 mini_text/file_utils.py 迁移而来。

    本模块提供通用文本文件读写能力，
    不负责特定的数据文件格式。

    string 系列与 lines 系列具有明确区别：

        string 系列：
            面向完整字符串，
            不自动添加或保证换行符。

        lines 系列：
            面向“每条数据一行”的行式文本，
            负责维护正确的行边界。

    因此：

        write_string()
        append_string()

            只处理字符串本身，
            不负责换行。

        write_lines()
        append_lines()

            按行处理数据，
            保证每条数据独占一行，
            并保证正确的文件末尾换行。

        append_lines()
            另外保证已有文件末尾没有换行符时，
            本次追加数据仍从新的一行开始。

    API：

        read_string()
            读取完整文件内容。

        write_string()
            覆盖写入完整字符串。

        read_lines()
            按行读取文件。

        write_lines()
            覆盖写入多行数据，每条数据一行。

        append_string()
            在文件末尾追加字符串。

        append_lines()
            在文件末尾追加多行数据，每条数据一行。

    本模块不包含 JSON 序列化逻辑。
"""

import logging
from typing import List

from fileio.base_file import ensure_parent_dir, exists, to_path

logger = logging.getLogger(__name__)


class FileReadError(Exception):
    """文件读取异常"""

    pass


class FileWriteError(Exception):
    """文件写入异常"""

    pass


def read_string(
    file_path: str,
    encoding: str = "GBK",
) -> str:
    """
    读取普通文本文件的全部内容。

    返回一个完整字符串。

    适合：

        - txt
        - html
        - css
        - js
        - xml
        - markdown
        - 其他普通文本文件

    Args:
        file_path:
            文件路径

        encoding:
            文件编码，默认 GBK

    Returns:
        文件全部内容字符串。

        文件不存在或读取失败时返回空字符串。
    """
    path = to_path(file_path)

    if not exists(path):
        logger.warning(
            "文件不存在: %s",
            file_path,
        )
        return ""

    try:
        with open(
            path,
            "r",
            encoding=encoding,
        ) as file:
            return file.read()

    except UnicodeDecodeError as e:
        logger.error(
            "编码错误: %s",
            e,
        )
        return ""

    except IOError as e:
        logger.error(
            "读取文件失败: %s",
            e,
        )
        return ""


def read_lines(
    file_path: str,
    encoding: str = "GBK",
) -> List[str]:
    """
    按行读取普通文本文件。

    每一行返回一个字符串。

    注意：

        本函数适用于普通文本文件，
        不限制文件扩展名。

        文件即使是 .txt、.log、.html 等，
        只要内容是文本，都可以按行读取。

    Args:
        file_path:
            文件路径

        encoding:
            文件编码，默认 GBK

    Returns:
        按行分割的字符串列表。

        文件不存在或读取失败时返回空列表。
    """
    path = to_path(file_path)

    if not exists(path):
        logger.warning(
            "文件不存在: %s",
            file_path,
        )
        return []

    try:
        with open(
            path,
            "r",
            encoding=encoding,
        ) as file:
            return [line.rstrip("\n\r") for line in file]

    except UnicodeDecodeError as e:
        logger.error(
            "编码错误，无法用 %s 解码文件: %s",
            encoding,
            e,
        )
        return []

    except IOError as e:
        logger.error(
            "读取文件失败: %s",
            e,
        )
        return []


def write_string(
    content: str,
    file_path: str,
    encoding: str = "utf-8",
) -> bool:
    """
    将一个字符串写入普通文本文件。

    默认采用覆盖写入。

    适合：

        - txt
        - html
        - css
        - js
        - xml
        - markdown
        - 大段文本

    Args:
        content:
            要写入的字符串

        file_path:
            目标文件路径

        encoding:
            文件编码，默认 utf-8

    Returns:
        写入成功返回 True，
        写入失败返回 False。
    """
    try:
        path = to_path(file_path)

        ensure_parent_dir(path)

        with open(
            path,
            "w",
            encoding=encoding,
        ) as file:
            file.write(content)

        return True

    except IOError as e:
        logger.error(
            "写入文件失败: %s",
            e,
        )
        return False


def write_lines(
    lines: List[str],
    file_path: str,
    encoding: str = "utf-8",
) -> bool:
    """
    将多个字符串按行写入普通文本文件。

    默认采用覆盖写入。

    每个字符串占一行。

    文件写入完成后，
    文件末尾保证存在换行符。

    Args:
        lines:
            字符串列表

        file_path:
            目标文件路径

        encoding:
            文件编码，默认 utf-8

    Returns:
        写入成功返回 True，
        写入失败返回 False。
    """
    if not lines:
        logger.warning("写入的行列表为空")

    try:
        path = to_path(file_path)

        ensure_parent_dir(path)

        with open(
            path,
            "w",
            encoding=encoding,
            newline="",
        ) as file:
            if lines:
                file.write("\n".join(lines))
                file.write("\n")

        return True

    except IOError as e:
        logger.error(
            "写入文件失败: %s",
            e,
        )
        return False


def append_string(
    content: str,
    file_path: str,
    encoding: str = "utf-8",
) -> bool:
    """
    在普通文本文件末尾追加一个字符串。

    文件不存在时自动创建。

    Args:
        content:
            要追加的字符串

        file_path:
            目标文件路径

        encoding:
            文件编码，默认 utf-8

    Returns:
        追加成功返回 True，
        追加失败返回 False。
    """
    try:
        path = to_path(file_path)

        ensure_parent_dir(path)

        with open(
            path,
            "a",
            encoding=encoding,
        ) as file:
            file.write(content)

        return True

    except IOError as e:
        logger.error(
            "追加文件失败: %s",
            e,
        )
        return False


def append_lines(
    lines: List[str],
    file_path: str,
    encoding: str = "utf-8",
) -> bool:
    """
    在普通文本文件末尾追加多个字符串。

    每个字符串占一行。

    文件不存在时自动创建。

    注意：

        无论已有文件最后一行是否存在换行符，
        都保证本次追加数据从新的一行开始。

    Args:
        lines:
            字符串列表

        file_path:
            目标文件路径

        encoding:
            文件编码，默认 utf-8

    Returns:
        追加成功返回 True，
        追加失败返回 False。
    """
    if not lines:
        logger.warning("追加的行列表为空")
        return True

    try:
        path = to_path(file_path)

        ensure_parent_dir(path)

        # -------------------------------------------------
        # 判断已有文件是否存在，以及文件末尾是否有换行符
        # -------------------------------------------------

        need_separator = False

        if exists(path) and path.stat().st_size > 0:
            with open(
                path,
                "rb",
            ) as file:
                file.seek(-1, 2)
                last_byte = file.read(1)

            need_separator = last_byte not in (b"\n", b"\r")

        # -------------------------------------------------
        # 追加写入
        # -------------------------------------------------

        with open(
            path,
            "a",
            encoding=encoding,
            newline="",
        ) as file:
            if need_separator:
                file.write("\n")

            file.write("\n".join(lines))
            file.write("\n")

        return True

    except IOError as e:
        logger.error(
            "追加文件失败: %s",
            e,
        )
        return False
