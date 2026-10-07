# Windows 中文乱码问题解决方案

## 问题说明

在 Windows 命令行（PowerShell 或 CMD）中运行 Python 程序时，如果程序输出中文，可能会出现乱码。

**原因**：
- Windows 命令行默认使用 GBK 编码
- Python 3 默认使用 UTF-8 编码
- 编码不匹配导致乱码

---

## 解决方案

### ✅ 方案 1：在代码中设置（最推荐）

在 Python 文件开头添加：

```python
import sys
import io

# 解决 Windows 命令行中文乱码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
```

**优点**：
- 自动处理，无需手动设置
- 代码跨平台兼容
- 用户无需额外操作

---

### 方案 2：设置环境变量

#### Windows PowerShell
```powershell
$env:PYTHONIOENCODING = "utf-8"
python your_script.py
```

#### Windows CMD
```cmd
set PYTHONIOENCODING=utf-8
python your_script.py
```

**优点**：
- 不需要修改代码
- 临时生效，不影响其他程序

---

### 方案 3：切换命令行编码

```bash
# 先切换到 UTF-8 编码
chcp 65001

# 再运行 Python
python your_script.py
```

**注意**：
- 每次打开新命令行窗口都需要重新设置
- 可能会影响其他程序的显示

---

## 本项目的修复

`mini_text/test_mini_text.py` 已采用方案 1，在文件开头添加了编码设置：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import logging
from pathlib import Path

# 解决 Windows 命令行中文乱码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
```

**运行效果**：

### ❌ 修复前（乱码）
```
2026-06-21 17:57:35 - WARNING - ļ粻: nonexistent.txt
╔════════════════════════════════════════╗
║          MiniText Python ߿         ║
╚════════════════════════════════════════╝
============================================================
ļ
============================================================
```

### ✅ 修复后（正常）
```
2026-06-21 18:01:00 - WARNING - 文件不存在: nonexistent.txt
╔════════════════════════════════════════╗
║          MiniText Python 工具库测试        ║
╚════════════════════════════════════════╝
============================================================
测试文件操作工具
============================================================

1. 测试写入文件
   写入 test_output.txt: 成功
```

---

## 其他建议

### 1. 文件读写指定编码

读写文件时明确指定编码：

```python
# 读取文件
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 写入文件
with open("file.txt", "w", encoding="utf-8") as f:
    f.write(content)
```

### 2. 日志配置

配置日志时也可以指定编码：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
```

### 3. IDE 设置

如果使用 VS Code 或其他 IDE：

- 设置终端编码为 UTF-8
- 设置文件编码为 UTF-8
- 设置项目编码为 UTF-8

---

## 常见问题

### Q: 为什么 Linux/Mac 不需要这个设置？
A: Linux 和 Mac 系统默认使用 UTF-8 编码，与 Python 3 一致，不会出现乱码。

### Q: 这个设置会影响 Linux/Mac 吗？
A: 不会，代码中使用了 `if sys.platform == 'win32'` 判断，只在 Windows 系统上生效。

### Q: 设置后还是乱码怎么办？
A: 检查以下几点：
1. 文件本身的编码是否是 UTF-8
2. 字体是否支持中文显示
3. 命令行窗口是否支持 UTF-8

---

## 总结

**推荐做法**：
- ✅ 在代码开头添加编码设置（方案 1）
- ✅ 读写文件时明确指定 `encoding='utf-8'`
- ✅ 使用支持 UTF-8 的编辑器和终端

这样可以确保程序在任何平台上都能正确显示中文！