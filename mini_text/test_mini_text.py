#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniText 工具库完整测试示例

展示所有功能模块的使用方法
"""

import io
import logging
import sys
from pathlib import Path

# 解决 Windows 命令行中文乱码问题
if sys.platform == "win32":
    # 设置 stdout 和 stderr 为 UTF-8 编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 配置日志输出（仅在直接运行本测试脚本时配置，避免导入时污染 root logger）
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# 导入 MiniText 工具库（使用相对导入，因为测试文件在包内部）
# 文件读写工具已迁移至 fileio/txt_io.py
from fileio.txt_io import read_lines, write_lines

from . import string_utils


def test_string_utils():
    """测试字符串验证工具"""
    print("=" * 60)
    print("测试字符串验证工具")
    print("=" * 60)

    # 1. 测试空值判断
    print("\n1. 测试空值判断")
    test_cases = [None, "", "  ", "void(null)", "void(0)", "hello"]
    for case in test_cases:
        result = string_utils.is_trim_empty(case)
        print(f"   is_trim_empty({repr(case)}): {result}")

    # 2. 测试字符类型判断
    print("\n2. 测试字符类型判断")
    letter_tests = ["Hello", "Hello123", "12345", "Hello World"]
    for test in letter_tests:
        is_letter = string_utils.is_all_letter(test)
        is_number = string_utils.is_all_number(test)
        is_alnum = string_utils.is_all_letter_or_number(test)
        print(f"   '{test}': 字母={is_letter}, 数字={is_number}, 字母数字={is_alnum}")

    # 3. 测试浮点数判断
    print("\n3. 测试浮点数判断")
    float_tests = ["123.45", "-123.45", "+99.99", "123", "12.34.56", "12-3"]
    for test in float_tests:
        result = string_utils.is_all_float(test)
        print(f"   is_all_float('{test}'): {result}")

    # 4. 测试中文字符判断
    print("\n4. 测试中文字符判断")
    chinese_tests = ["你好世界", "Hello世界", "Hello", "你好123"]
    for test in chinese_tests:
        has_cn = string_utils.has_chinese(test)
        all_cn = string_utils.is_all_chinese(test)
        all_en = string_utils.is_all_english(test)
        print(f"   '{test}': 有中文={has_cn}, 全中文={all_cn}, 全英文={all_en}")

    # 5. 测试是否包含数字
    print("\n5. 测试是否包含数字")
    number_tests = ["Hello123", "Hello", "12345", "test@123"]
    for test in number_tests:
        result = string_utils.has_number(test)
        print(f"   has_number('{test}'): {result}")

    # 6. 测试单个字符判断
    print("\n6. 测试单个字符判断")
    char_tests = [("A", "字母"), ("z", "字母"), ("5", "数字"), ("@", "符号")]
    for char, desc in char_tests:
        is_letter = string_utils.is_letter_char(char)
        is_number = string_utils.is_number_char(char)
        print(f"   '{char}' ({desc}): 字母={is_letter}, 数字={is_number}")

    # 7. 测试数字格式化
    print("\n7. 测试数字格式化")
    format_tests = [(42, 5), (123, 3), (999999, 10)]
    for value, length in format_tests:
        result = string_utils.normalize_int_string(value, length)
        print(f"   normalize_int_string({value}, {length}): '{result}'")

    # 8. 测试字符串比较
    print("\n8. 测试字符串比较")
    compare_tests = [
        ("hello", "hello"),
        (None, ""),
        ("", None),
        (None, None),
        ("hello", "world"),
    ]
    for str1, str2 in compare_tests:
        result = string_utils.is_same(str1, str2)
        print(f"   is_same({repr(str1)}, {repr(str2)}): {result}")

    print("\n")


def test_web_utils():
    """测试 URL 请求工具"""
    print("=" * 60)
    print("测试 URL 请求工具")
    print("=" * 60)

    # 注意：实际测试需要网络连接，这里只展示用法

    print("\n1. 简单 URL 请求示例:")
    print("   html = web_utils.get_url_text('http://example.com', encoding='utf-8')")

    print("\n2. 自定义 User-Agent 示例:")
    print("   html = web_utils.get_url_text_with_user_agent(")
    print("       'http://example.com',")
    print("       user_agent='Mozilla/5.0 ...'")
    print("   )")

    print("\n3. 伪造 Referer 示例:")
    print("   html = web_utils.get_url_text_with_referer(")
    print("       'http://example.com',")
    print("       referer='http://referrer.com'")
    print("   )")

    print("\n4. 获取 JS 渲染页面示例 (需要安装 playwright):")
    print("   html = web_utils.get_url_text_with_js(")
    print("       'http://example.com',")
    print("       wait_time=5")
    print("   )")

    print("\n5. 使用 Selenium 示例 (需要安装 selenium):")
    print("   html = web_utils.get_url_text_with_selenium(")
    print("       'http://example.com',")
    print("       browser='chrome',")
    print("       headless=True")
    print("   )")

    # 实际网络请求测试（如果需要，取消注释）
    # print("\n实际测试网络请求...")
    # try:
    #     html = web_utils.get_url_text("http://www.example.com", encoding="utf-8")
    #     print(f"   获取到内容长度: {len(html)}")
    #     print(f"   前 100 个字符: {html[:100]}...")
    # except Exception as e:
    #     print(f"   网络请求失败: {e}")

    print("\n")


def demo_usage():
    """综合使用示例"""
    print("=" * 60)
    print("综合使用示例")
    print("=" * 60)

    # 示例：处理文本文件
    print("\n示例 1: 处理文本文件")
    print("-" * 40)

    # 创建测试文件
    test_data = [
        "用户名: Alice",
        "邮箱: alice@example.com",
        "年龄: 25",
        "简介: 你好，我是 Alice",
    ]

    file_path = "user_data.txt"
    write_lines(test_data, file_path, encoding="utf-8")
    print(f"已创建测试文件: {file_path}")

    # 读取并验证数据
    lines = read_lines(file_path, encoding="utf-8")
    print("\n读取数据并验证:")
    for line in lines:
        # 检查是否包含中文
        if string_utils.has_chinese(line):
            print(f"  [包含中文] {line}")
        else:
            print(f"  [纯英文] {line}")

    # 示例：数据清洗
    print("\n\n示例 2: 数据清洗")
    print("-" * 40)

    raw_data = ["  ", "", "void(null)", "valid_data", "12345", "Hello123"]
    cleaned_data = []

    for item in raw_data:
        # 过滤空值
        if not string_utils.is_trim_empty(item):
            cleaned_data.append(item.strip())

    print(f"原始数据: {raw_data}")
    print(f"清洗后数据: {cleaned_data}")

    # 示例：字符串分类
    print("\n\n示例 3: 字符串分类")
    print("-" * 40)

    test_strings = ["Hello", "12345", "123.45", "你好世界", "Hello123", "Test@123"]

    categories = {
        "纯字母": [],
        "纯数字": [],
        "浮点数": [],
        "纯中文": [],
        "字母+数字": [],
        "其他": [],
    }

    for s in test_strings:
        if string_utils.is_all_letter(s):
            categories["纯字母"].append(s)
        elif string_utils.is_all_number(s):
            categories["纯数字"].append(s)
        elif string_utils.is_all_float(s):
            categories["浮点数"].append(s)
        elif string_utils.is_all_chinese(s):
            categories["纯中文"].append(s)
        elif string_utils.is_all_letter_or_number(s):
            categories["字母+数字"].append(s)
        else:
            categories["其他"].append(s)

    for category, items in categories.items():
        if items:
            print(f"{category}: {items}")

    print("\n")


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " MiniText Python 工具库测试 ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # 运行所有测试
    test_string_utils()
    test_web_utils()
    demo_usage()

    # 清理测试文件
    print("=" * 60)
    print("清理测试文件")
    print("=" * 60)
    test_files = ["test_output.txt", "test_content.txt", "user_data.txt"]
    for file_name in test_files:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"   已删除: {file_name}")

    print("\n测试完成！\n")


if __name__ == "__main__":
    main()
