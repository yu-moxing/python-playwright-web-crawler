"""
MiniText - Python 版本的文本处理工具库

从 Java MiniText.java 迁移而来，提供字符串验证、URL 请求等功能
（文件读写已迁移至 fileio/txt_io.py）

示例用法:
    from mini_text import string_utils, web_utils

    # 字符串验证
    if string_utils.is_all_letter("Hello"):
        print("全是字母")

    # URL 请求
    html = web_utils.get_url_text("http://example.com")
"""

from . import string_utils, web_utils

__version__ = "1.0.0"
__author__ = "MiniText Migration"

__all__ = [
    "string_utils",
    "web_utils",
]
