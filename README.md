
<p align="left">
  README Navigation
</p>

<p align="left">
  <strong>root</strong>
</p>

<pre>
root
│
├ <strong>README.md</strong>                项目架构全面分析报告.md
│
└ <a href="./核心模块详细设计分析.md">核心模块详细设计分析.md</a>        Core module detailed design
</pre>

---


# Python Playwright Web Crawler 项目架构全面分析报告

> 本报告基于对 `\python-playwright-web-crawler` 实际源码的只读扫描，排除部分非关键目录。所有结论以代码为准。
	
---

## 导读：未公开的文件及目录

出于知识产权保护，以下核心文件、目录及相关实现未包含在本公开仓库中。

### 1. 采集项目配置脚本

`/script/script.txt`
定义采集项目的执行流程及具体采集行为。

### 2. 核心采集逻辑

`processor/cate_list/cate_list_processor.py`
`processor/cate_level/cate_level_processor.py`
`processor/cate_level/cate_level_collector.py`
包含分类层级采集和分类列表采集的核心逻辑。

### 3. 浏览器及网络资源

`resource/`
包含代理 IP、浏览器指纹、浏览器启动路径及用户文件夹等资源。

### 4. 公共资源池

`pool/`
包含采集框架使用的 `.xlsx` 格式公共资源池文件。

### 5. 分类树及自动分类算法

`mini_cate/`
包含 2009–2011 年《伯乐购物搜索》Java 版迁移至 Python 版的分类树维护及商品自动分类算法，属于核心知识产权。

### 6. 采集项目配置加载器

`config/loader/`
负责加载和解析 `/script/script.txt`，属于配置驱动采集架构的核心实现。

> **说明：** 本仓库主要用于技术作品展示和工程能力演示，并非完整、可直接运行的项目发行版本。原系统的完整运行依赖于上述未公开内容。


---

## 1. 项目概述

一个使用 Python 和 Playwright 构建的配置驱动型网络爬行工具，支持多用户、分布式采集和断点续传。


技术栈（来自 `requirements.txt`）：

| 依赖 | 用途 |
|---|---|
| `scrapy>=2.11` / `scrapy-playwright>=0.0.47` / `twisted>=22.10` | 历史遗留，运行期未启用 Spider |
| `playwright>=1.45` | 浏览器自动化核心 |
| `playwright-stealth>=2.0.3` | 反检测（实际指纹由 `pool/browser_fingerprint_*.xlsx` 注入） |
| `redis>=8.0` | 爬取状态缓存 / 内容去重缓存 |
| `pymongo>=4.8` | 内容持久化 / 自增序列 |
| `openpyxl>=3.1.5` | 资源池 `*.xlsx` 读取 |
| `pydantic>=2.5` | （配置层未使用，运行期以 `@dataclass` 为主） |
| `pyyaml>=6.0` | `env/dev.yaml`、`env/pro.yaml` 环境配置 |
| `colorlog>=6.7` | 日志着色 |

`pyproject.toml` 仅为 ruff 配置（`line-length=120`、`target-version=py310`、`select=F,I`），无 `[project]` 元数据，非 PEP 521 构建文件。

项目根目录另含 `启动命令.txt`（示例启动命令）。

---

## 2. 项目定位

项目解决的核心问题是：**对多个异构电商/内容站点，以同一套框架 + 每站点一份 `script.txt` 配置 + 每站点一套 `login/*.py` 站点登录代码，完成「分类树采集 → 列表页内容采集 → 商品/文章详情采集」三段式抓取**，并在此过程中统一处理用户隔离、浏览器隔离、指纹注入、代理 IP、风控滑块、去重与持久化。

核心目标：

1. 配置驱动而非硬编码：站点差异通过 `script.txt` 描述，框架核心站点无关。
2. 资源强隔离：User / Browser / Fingerprint / IP 四层绑定，避免跨用户污染。
3. 通用爬虫框架 + 具体站点业务：框架核心 (`main`/`config`/`resource`/`page`/`parser`/`processor`/`database`) 站点无关；站点业务下沉到 `site/<id>/` 与 `item/<id>/`。
4. 可断点续跑：Redis 检查点 + 三层去重，保障爬取幂等。

---

## 3. 项目总体架构

实际分层（代码证实，非目录臆测）：

```
CLI (main/cli/args_parser, main/cate_*, main/item_detail)
  ↓
Config (config/loader/project_loader, script_config + 三层变量替换 config/context)
  ↓
Resource (resource/PoolLoader → ResourceMapper → ResourceAllocator → ResourceContext)
  ↓
Browser / Page (resource/BrowserSessionFactory → page/PageNavigator)
  ↓
Parser (parser/field_extractor + selector_parser + cate_level/cate_list 子层)
  ↓
Processor (processor/cate_level, cate_list, item_detail —— 流程编排层)
  ↓
Data (data/model/*DataItem → ContentRecordBuilder → ContentDataRecord)
  ↓
Database (Redis 状态缓存 + MongoDB 持久真相源) / Export (fileio/batch 输出)
```

子系统关系：

- **CLI 子系统**：参数解析、项目定位、用户/索引校验，产出 `CateRunArgs` / `ItemRunArgs`。
- **Config 子系统**：`script.txt` 解析为 `ScriptConfig` 聚合体；`env/*.yaml` 解析为 `AppConfig`。
- **Resource 子系统**：从 `pool/*.xlsx` 加载四层资源，校验约束，分配 `ResourceContext`。
- **Browser/Page 子系统**：`BrowserSessionFactory` 创建持久化 BrowserContext（注入指纹 + UA 对齐 + 代理），`PageNavigator` 管理页面加载/就绪/滚动。
- **Parser 子系统**：`FieldExtractor` + `SelectorParser` 两层，按 `NormalNodeConfig` 节点规则从 DOM 抽取字段。
- **Processor 子系统**：每业务类型一个 `Processor`（编排层），驱动 Collector / Parser / Filter / Builder / ItemHandler / DB 适配器完成业务流。
- **Database 子系统**：MongoDB（内容持久化 + 自增序列）与 Redis（状态缓存 + 去重缓存）。

数据进入：`script.txt` 配置 + `pool/*.xlsx` 资源 + `user_pool.xlsx` 用户清单。
数据经过：加载→解析→过滤→构建→三层去重→写库。
最终输出：`output/cate_level_index.txt`、`output/cate_level_link.txt`（CATE_LEVEL）；MongoDB `CONTENT-*` 集合 + Redis 缓存（CATE_LIST）；`item/` cookies/日志（ITEM_DETAIL）。

---

## 4. 项目目录架构

实际目录（已排除 `TEST_DIR_NAMES`）：

```
python-playwright-web-crawler/
├── main/                 CLI 入口与共享脚手架
│   ├── cate_level.py     CATE_LEVEL 入口
│   ├── cate_list.py      CATE_LIST 入口
│   ├── cli/              共享 CLI（args_parser, args_utils, index_spec, sort_spec, runner_base）
│   │   └── item_detail/  item_detail CLI（item_args, item_index_spec）
│   ├── item_detail/      ITEM_DETAIL 入口
│   │   ├── item_detail.py
│   │   └── cli/
│   └── site/             空占位
├── config/               配置解析层
│   ├── application/      AppConfig（env/*.yaml）
│   ├── backfill/         节点配置回填与校验
│   ├── context/          变量替换（pro_var, script_constant, script_var, node_var）
│   ├── database/         MongoDBConfig, RedisConfig
│   ├── loader/           script.txt 各段 loader（含 item_detail 子树）
│   └── model/            *Item 配置数据类
├── constants/            路径/浏览器/类目/单位/风控/自定义常量（无 __init__.py）
│   └── item_detail/      item_detail 专属常量
├── resource/             资源四层绑定（pool_loader, resource_mapper, resource_allocator, browser_session_factory, data_models, exceptions）
│   └── item_detail/      空占位
├── page/                 PageNavigator, PageReadyChecker
├── parser/               FieldExtractor, SelectorParser + cate_level/cate_list 子层
│   └── item_detail/      空占位（解析未实现）
├── processor/            业务编排层
│   ├── cate_level/       CateLevelProcessor + Collector/Filter/Builder/Normalizer/ItemHandler/Item/Validator/Stats/Runner
│   ├── cate_list/        CateListProcessor + Runner/CliiFilter/ContentRecordBuilder
│   ├── item_detail/      ItemDetailProcessor + Runner
│   ├── common/           DuplicateChecker, link_id_config
│   ├── unit/             UnitFilter
│   └── content/          空占位
├── request/              RetryManager（业务流重试）
├── database/             持久化
│   ├── mongodb/          MongoDBClient, MongoDBUtil, MongoWriter, ContentMongoDB, AllSequenceMongoDB
│   ├── redis/            RedisClient, RedisUtil, RedisTtlUtil, CateLevelRedis, CateListRedis, ContentRedis
│   └── postgresql/       空文件占位（未实现）
├── data/                 运行期数据模型
│   ├── model/            data_record/ cate_level/ cate_list/ detail/
│   ├── loader/           cate_level 文本回读 loader
│   └── backfill/         CateLevelLinkDataBackfill
├── fileio/               base_file, csv/json/jsonl/excel/txt_io, fileio_manager, file_backup, batch/
├── export/               cate_level 导出胶水（cate_level_index_writer 非空，cate_level_link_writer 空文件）
├── site/                 站点项目根（site/<id>/script/script.txt + login/ + output/...）
├── item/                 item_detail 项目根（item/<id>/cookies + input + script + user + logs）
├── pool/                 资源池 Excel（browser_pool_*, browser_fingerprint_*, ip_pool.xlsx）
├── captcha/              image_slider 滑块缺口检测
├── image_match/          滑块图像匹配（base/edge/feature/pixel/shape）
├── mini_cate/            类目树归一算法（Java 移植，业务能力）
├── mini_text/            文本/URL/正则工具（Java 移植，基础能力）
├── mouse_tracks/         滑块拖拽轨迹（UnifiedSliderDragger, SliderCaptchaManager）
├── utils/                delay_manager, comment_cleaner, value_utils, export/
├── tools/                开发辅助（project_tree, count_python_lines, export_custom_fields）非运行期
├── env/                  dev.yaml, pro.yaml（Redis/Mongo 连接）
├── logs/                 全局运行日志
├── docs/                 已有项目总结文档
├── prompt/               设计草稿 .txt（非代码）
├── pyproject.toml        ruff 配置
├── requirements.txt
├── scrapy.cfg            Scrapy 遗留配置
├── README.md             已过时（描述旧 user.txt/type-script.txt 布局）
└── .gitignore
```

---

## 5. 核心分层架构

### 5.1 CLI / Runner 层

- 目录：`main/`、`main/cli/`、`main/cli/item_detail/`
- 核心类/函数：
  - `main/cli/args_parser.py`：`@dataclass CateRunArgs`、`parse_cli_args(*, cate_keyword, cate_label, sort_keyword, sort_label)`、dev 预设 `PRESET_PROJECT_ID="1001-001"`、`PRESET_USER_INDEXES="0-2"`、`PRESET_CATE_INDEXES="0>-1"`、`PRESET_SO="-1"`。
  - `main/cli/args_utils.py`：`validate_project_id`、`parse_user_indexes`、`parse_cate_indexes`。
  - `main/cli/index_spec.py`：`parse_index_spec`、`INDEX_FORMAT_HELP`。
  - `main/cli/sort_spec.py`：`@dataclass SoSpec`、`parse_and_validate_so`、`SoValidationError`。
  - `main/cli/runner_base.py`：`create_logger(name, log_dir, project_id, level)`、`setup_directories(project_dir, logger)`、`load_configs(project_loader, logger)`、`BASE_DIR`、根 logger 路由（`_setup_root`、`_PPW_CONSOLE_TAG`、`_PPW_FILE_TAG`）。
  - `main/cli/item_detail/item_args.py`：`@dataclass ItemRunArgs`、`parse_item_cli_args()`。
  - `main/cli/item_detail/item_index_spec.py`：`ItemIndexSpec`、`parse_item_index_spec`。
- 职责：参数解析与标准化、项目定位、日志路由、目录初始化、共享配置加载。
- 上游：命令行；下游：Config / Resource / Processor。
- 输入：命令行 `params`（`p`/`u`/`clli`/`so` 或 `id_p`/`id_u`/`id_i`）；输出：`CateRunArgs` / `ItemRunArgs` + 已加载的 `ScriptConfig`/`PoolData`。

### 5.2 Config 层

- 目录：`config/loader/`、`config/model/`、`config/context/`、`config/application/`、`config/database/`、`config/backfill/`
- 核心类/函数：
  - `config/loader/project_loader.py`：`@dataclass ProjectConfig`（main_id, sub_id, full_id, project_dir_path, project_dir_name, site_name, content_type, language；路径属性 `script_file_path`/`user_pool_file_path`/`cate_level_index_file_path`/`cate_level_link_file_path` 等）、`ProjectConfigLoader(full_project_id, base_dir=SITE_DIR_PATH)`（`_parse_project_id`、`_parse_project_dir_name`、`find_project_dir`、`load_configs`、`get_program_vars`）、`ProjectNotFoundError`、`ProjectAmbiguousError`。
  - `config/loader/script_config.py`：`@dataclass ScriptConfig`（聚合 `cate_level`/`cate_level_unit`/`cate_list`/`cate_list_unit`/`cate_list_product`/`cate_list_article`/`detail_unit`/`detail_product`/`detail_article`/`browser`/`login`/`risk`/`system`/`page`/`redis`/`mongodb`）、`parse_script_config(file_path, program_vars)`、`_process_config_item`、`_validate_config`、`print_config_summary`、`ScriptConfigError`。
  - `config/loader/item_detail/item_detail_loader.py`：`parse_item_detail_script_config(file_path, program_vars)` → `ItemDetailScriptConfig`。
  - `config/loader/item_detail/item_project_loader.py`：`@dataclass ItemProjectConfig`、`ItemProjectConfigLoader`。
  - `config/loader/item_detail/item_resource_loader.py`：`build_item_resource_context(item_user, pool_loader, project_config, logger)` → `ResourceContext`。
  - `config/loader/item_detail/item_user_pool_loader.py`：`ItemUserPoolLoader.load() → dict[int, ItemUserConfig]`、`ItemUserPoolLoadError`。
  - `config/application/app_config.py`：`AppConfig`（加载 `env/dev.yaml`/`env/pro.yaml`）、`get_app_config(env)` 缓存。
  - `config/context/`：`pro_var.replace_program_vars`、`script_constant.read_script_constants`/`replace_script_constants`（`@[NAME]`）、`script_var.read_script_vars`/`replace_script_vars`（`@{NAME}`）、`node_var`。
  - `config/backfill/node_config_backfill.py`：`backfill_unit_node_parent_filters`、`build_normal_node_lists`、`build_normal_child_lists`、`validate_layer_default_values`、`validate_layer_filters`、`validate_unit_child_filters`。
  - 各段 loader：`base/base_loader.py`、`cate_level/cate_level_loader.py`、`cate_list/cate_list_loader.py`、`detail/detail_loader.py`、`browser/browser_loader.py`、`system/system_loader.py`、`page/page_loader.py`、`login/login_loader.py`、`risk/risk_loader.py`、`redis/redis_loader.py`、`mongodb/mongodb_loader.py`、`unit/unit_loader.py`。
- 职责：`script.txt` → `ScriptConfig`；`env/*.yaml` → `AppConfig`；目录名解析为 `ProjectConfig` + `program_vars`；节点配置回填与校验。
- 上游：CLI；下游：Resource / Browser / Parser / Processor / Database。
- 输入：`script.txt` + `env/*.yaml` + 站点目录名；输出：`ScriptConfig`/`ProjectConfig`/`AppConfig`/`program_vars`。

### 5.3 Resource 层

- 目录：`resource/`
- 核心类/函数：`PoolLoader`（`load_all`/`load_user_pool`/`load_browser_pool`/`load_fingerprint_pool`/`load_ip_pool`/`validate_user_browser`）、`ResourceMapper`（`validate_constraints`/`build_mapping`/`validate_user_ip`）、`ResourceAllocator`（`allocate`/`allocate_all`/`allocate_no_user`/`_select_proxy`）、`BrowserSessionFactory`（`create_context`/`close_all`/`get_context`/`close_context`）。
- 数据类：`FingerprintConfig`、`BrowserConfig`、`IPConfig`、`UserConfig`、`PoolData`、`ResourceContext`、`ResourceMapping`。
- 常量：`DEFAULT_BROWSER_TYPE=0`、`DEFAULT_BROWSER_INDEX=0`。
- 辅助：`resolve_ip_index(spec)`（`-1`/`N`/`N-M` 随机/`A,B,C` 随机）、`expand_ip_spec(spec)`。
- 异常：`ResourceError`、`PoolLoadError`、`ResourceValidationError`、`ResourceNotFoundError`。
- 职责：四层资源加载、约束校验、运行期分配、BrowserContext 创建（指纹 + UA/时区/locale 对齐 + 代理 + 反自动化启动参数）。
- 上游：CLI；下游：Browser/Page。
- 输入：`pool/*.xlsx` + `user_pool.xlsx`；输出：`ResourceContext` + Playwright `BrowserContext`。

### 5.4 Browser / Page 层

- 目录：`resource/browser_session_factory.py`、`page/`
- 核心类/函数：`BrowserSessionFactory.create_context`、`page/page_navigator.py: PageNavigator`（`load`/`_navigate`/`scroll_to_load_more`）、`page/page_ready_checker.py: PageReadyChecker.wait`。
- 常量：`constants/browser_const.py`（`MIN/MAX_SCROLL_STEP_FACTOR`、`SCROLL_BOTTOM_THRESHOLD=800`、`MAX_SCROLL_TIMES=16`、`SCROLL_TO_BOTTOM_ON_MAX_TIMES_EXCEEDED=True`）。
- 页面类型映射 `_PAGE_TYPE_ATTR`：HOME/LOGIN/RISK/CATE_LEVEL/CATE_LIST/DETAIL → `PageItem` 的 `*_ready_selector`。
- 职责：BrowserContext 生命周期（Factory）+ 页面加载/就绪检查/滚动懒加载（PageNavigator）。
- 上游：Resource / Processor；下游：Parser。
- 输入：URL + `ResourceContext` + `PageItem`；输出：Playwright `Page`。
- 关键设计：`PageNavigator` 禁止 `self.page` 单例（注释 line 113），Page 由调用方持有，防多用户/多 Processor 串扰；BrowserContext 按 `user_data_dir` 懒缓存。

### 5.5 Parser 层

- 目录：`parser/`
- 核心类/函数：
  - `parser/selector_parser.py: SelectorParser.extract_values(page, selector, attr)`（底层 DOM，CSS 直传 / XPath 前缀 `xpath=`，属性抽取用 JS `e.getAttribute` 保序）。
  - `parser/field_extractor.py: FieldExtractor.extract(element_region, css, xpath, attr, regex)`（四后缀 `_CSS`/`_XPATH`/`_ATTR`/`_REGEX`，`_pick_selector` → `selector_parser.extract_values` → `_apply_if_regex_not_empty`）。
  - `parser/cate_level/cate_level_parser.py: CateLevelParser`（`parse_cate_level_items` → `(links, names, ids)`、`_parse_cate_level_normal_nodes`、`_extract_cate_level_many_node`、`_derive_ids`、`_deduplicate`）。
  - `parser/cate_list/cate_list_parser.py: CateListParser` + `@dataclass CateListParsedItem`（`parse_cate_list_items` → `(valid, invalid)`、`_parse_cate_list_normal_nodes`、`_extract_cate_list_node_values`、`_parse_cate_list_combine_values`、`_extract_cate_list_many_node`、`_reset_item_is_parsed`、`_clean`）。
  - `parser/cate_list/cate_list_filter.py: filter_cate_list_items(records, cate_list_item)`（四规则 AND：`FILTER_ALLOW_VALUE`/`FILTER_REJECT_VALUE`/`FILTER_AND_NOT_EMPTY_NODE_LIST`/`FILTER_OR_NOT_EMPTY_NODE_LIST`，`Decimal` 范围比较）。
- 职责：按 `NormalNodeConfig` 节点规则从 DOM 抽取字段并清洗/正则化。
- 上游：Processor / Collector；下游：Data Model。
- 输入：Playwright `Page` / `Locator` + 节点配置；输出：`DataItem` 列表。
- 注：`parser/item_detail/` 为空目录，ITEM_DETAIL 阶段尚未实现解析层。

### 5.6 Processor 层（编排层）

- 目录：`processor/cate_level/`、`processor/cate_list/`、`processor/item_detail/`、`processor/common/`、`processor/unit/`、`processor/content/`（空）
- 核心类/函数见第 11 节。
- 职责（`CateLevelProcessor` docstring 自述）：流程编排层，只负责「初始化组件 → 登录/页面准备 → 启动 Collector → 采集结束 → Flush → 关闭 Page」，具体业务交给对应组件（Parser/Filter/Builder/ItemHandler/DB 适配器）。
- 上游：Runner；下游：Parser / DB / fileio。
- 输入：`ScriptConfig` + `ResourceContext` + `PageNavigator`；输出：写入 `output/*.txt` / MongoDB / Redis。

### 5.7 Database / Export 层

- 目录：`database/mongodb/`、`database/redis/`、`database/postgresql/`（空）、`fileio/`、`export/`
- 核心类/函数见第 13 节。
- 职责：Redis 状态缓存 + 去重；MongoDB 内容持久化 + 自增序列；fileio 批量输出 TXT/CSV/JSON/Excel/Mongo。
- 上游：Processor；下游：外部存储。
- 输入：`ContentDataRecord` / 检查点 / 去重键；输出：Redis 键 / MongoDB 文档 / 输出文件。

---

## 6. 核心运行链路

### 6.1 CLI 启动链

以 CATE_LEVEL 为例（`main/cate_level.py: main()`）：

```
命令 python -m main.cate_level --dev p 1001-001 u -1 clli "-1>-1"
  → parse_cli_args(cate_keyword="clli", cate_label="cate level link index") → CateRunArgs
  → create_logger(name="cate_level", log_dir=<root>/logs, project_id)  # main.cli.runner_base
  → ProjectConfigLoader("1001-001").load_configs()
  → PoolLoader(<root>/pool).load_all(project_id="1001", project_dir=..., browser_type=0)
  → project_loader.get_program_vars()
  → parse_script_config(script_file, program_vars) → ScriptConfig
  → print_config_summary(script_config, output_file=...)
  → setup_directories(...)
  → 用户校验：parse_user_indexes ∩ pool_data.users；ResourceMapper.validate_user_ip
  → ResourceAllocator(pool_data, main_id, project_dir).allocate(user_index) → ResourceContext
  → execute_cate_level(...) → run_cate_level(...)  # processor.cate_level.cate_level_runner
```

CATE_LIST 入口 `main/cate_list.py` 复用 `runner_base.load_configs`/`setup_directories`，额外加载 `cate_level_index.txt`（`CateLevelIndexDataLoader.load`）与 `cate_level_link.txt`（`CateLevelLinkDataLoader.load`），并通过 `CateLevelLinkDataBackfill.backfill` 回填 `cate_ids_path`/`cate_links_path`；`so` 参数经 `parse_and_validate_so` 校验。

ITEM_DETAIL 入口 `main/item_detail/item_detail.py` 走独立 `parse_item_cli_args()`（参数 `id_p`/`id_u`/`id_i`，非 `p`/`u`/`clli`），经 `ItemProjectConfigLoader` 定位、`ItemUserPoolLoader` 加载用户、`_resolve_item_users`/`_select_item_urls` 解析用户与 URL 子集、`parse_item_detail_script_config` 加载配置，最后 `run_item_detail(...)`。

### 6.2 配置加载链

```
script.txt 原文
  → utils.comment_cleaner.clean_lines  # 去 // 与 /* */ 注释
  → 读取 script constants (config.context.script_constant)
  → 读取 script vars (config.context.script_var)
  → 逐行替换：@[NAME] 常量 → @{NAME} 变量 → ${PRO_*} program_vars (config.context.pro_var.replace_program_vars)
  → _process_config_item 按前缀优先级分发：
       *_UNIT_*  → unit_loader     (必须先于 CATE_LEVEL)
       CATE_LEVEL_*  → cate_level_loader
       CATE_LIST_*   → cate_list_loader
       DETAIL_*      → detail_loader
       BROWSER_*     → browser_loader
       SYSTEM_*      → system_loader
       PAGE_*        → page_loader
       LOGIN_*       → login_loader
       RISK_*        → risk_loader
       REDIS_*       → redis_loader
       MONGODB_*     → mongodb_loader
  → backfill_unit_node_parent_filters / build_normal_node_lists / build_normal_child_lists
  → finalize_level0_links / finalize_floor_config
  → _validate_config（validate_unit_child_filters / validate_layer_default_values / validate_layer_filters + 各段 validate_*）
  → ScriptConfig
```

`program_vars` 来自 `ProjectConfigLoader.get_program_vars()`：`PRO_MAIN_ID`/`PRO_SUB_ID`/`PRO_SITE_NAME`/`PRO_CONTENT_TYPE`/`PRO_LANGUAGE`/`PRO_PROJECT_DIR_NAME`。`content_type`（"product"/"article"，源自站点目录名）驱动 `ScriptConfig.get_cate_list_item()`/`get_detail_item()` 在 product/article 分支间切换。

item_detail 不复用 `parse_script_config`（其键不在该分发表内），用独立的 `parse_item_detail_script_config` 产出 `ItemDetailScriptConfig`（字段如 `cookie_domain`/`home_url`/`access_home_page`/`headless`/`network_response_*`/`user_level_ranges`）。

### 6.3 Resource 资源链

```
PoolLoader.load_all(project_id, project_dir, browser_type)
  → load_user_pool(project_dir)        # user/user_pool.xlsx → Dict[int, UserConfig]
  → load_browser_pool(browser_type)    # browser_pool_<type>_<name>.xlsx → Dict[int, BrowserConfig]
  → load_fingerprint_pool(browser_type) # browser_fingerprint_<type>_<name>.xlsx → Dict[int, FingerprintConfig]
  → load_ip_pool()                     # ip_pool.xlsx → Dict[int, IPConfig]
  → PoolData(users, browsers, fingerprints, ips)
  → ResourceMapper.validate_constraints(pool_data)   # 7 条约束，前 3 硬约束
  → ResourceAllocator(pool_data, project_id, project_dir, browser_type).allocate(user_index)
       → 查 self.mappings[user_index] (ResourceMapping)
       → 取 user/browser/fingerprint
       → _select_proxy(user) → resolve_ip_index(user.ip_spec) → Optional[IPConfig]
       → ResourceContext(user, browser, fingerprint, proxy)
  → BrowserSessionFactory.create_context(context, headless)
       → 按 user_data_dir 复用缓存 BrowserContext
       → async_playwright().start()
       → _get_browser_type_name (0=chromium, 1=firefox, 2=webkit)
       → _get_launch_args() (--disable-blink-features=AutomationControlled, WebRTC IP 泄漏防护等)
       → _parse_fingerprint_profile / _parse_chrome_version / _parse_screen_profile
       → UA / Sec-Ch-Ua / Accept-Language / locale / timezone_id 对齐
       → launch_persistent_context(user_data_dir, executable_path, proxy, user_agent, viewport, ...)
       → browser_context.add_init_script(fingerprint.js_script)
       → BrowserContext
```

四层关系：`UserConfig.browser_index` → `BrowserConfig`；`BrowserConfig.fingerprint_index` → `FingerprintConfig`；`UserConfig.ip_spec` → `IPConfig`（IP 规范在用户层，非浏览器层，`PoolLoader.load_browser_pool` docstring 明确「Browser pool no longer holds IP binding」）。

`ResourceMapper` 7 条约束：①用户→浏览器索引存在 ②浏览器→指纹索引存在 ③用户↔浏览器 1:1 ④浏览器↔指纹绑定 ⑤指纹复用(警告) ⑥IP 索引存在(警告) ⑦IP 复用(警告)。`validate_user_ip` 是面向选中用户的硬校验（区别于 `validate_constraints` 中的警告级 IP 检查）。

item_detail 资源链不复用 `ResourceAllocator`，用 `build_item_resource_context(item_user, pool_loader, project_config, logger)`：因 item_detail 按 `browser_index` 查指纹（而非 `fingerprint_index`），复用 `PoolLoader` 三池 + `resolve_ip_index` + 数据类。

### 6.4 Browser / Page 链

```
BrowserSessionFactory.create_context(ResourceContext, headless)
  → (缓存或新建) BrowserContext  # 指纹 JS 注入 + UA/时区/locale 对齐 + 代理 + 反自动化参数
PageNavigator.load(url, page=None, page_type=None, ready_selector, delay_ms)
  → 懒创建 BrowserContext (browser_factory.create_context)
  → 懒创建 Page (context.new_page())
  → _PAGE_TYPE_ATTR[page_type] → PageItem.<type>_ready_selector
  → _navigate(page, url, ready_selector)
       → page.goto(url, wait_until="domcontentloaded", timeout=page_goto_timeout)
       → PageReadyChecker.wait(page, ready_selector, timeout, network_idle_enabled, network_idle_timeout)
            → 可选 networkidle → 必选业务元素 wait_for_selector
       → 失败重试 max_retries 次，最后一次抛 PlaywrightError
  → delay_ms 后置等待
PageNavigator.scroll_to_load_more(page, duration_ms, stable_rounds=2)
  → 视口/滚动高度评估 → 随机步长 [0.8, 0.95]×视口 → MAX_SCROLL_TIMES=16 上限
  → 终止条件：时长耗尽 / 到底 + 稳定 stable_rounds / SCROLL_BOTTOM_THRESHOLD(800px) 内 / 超限且配置强冲底
```

页面生命周期归属：**Runner 拥有 `BrowserSessionFactory`**（创建 + `close_all()` in finally）；**Processor 拥有工作 Page**（`page_navigator.load` 取得，`finally` 关闭）；`PageNavigator` 仅持有 Context 引用，禁止单例 Page。

### 6.5 Parser 链

```
Page / Locator (来自 PageNavigator.load / Collector._open)
  → FieldExtractor.extract(region, css, xpath, attr, regex)
       → _pick_selector(css, xpath)  # CSS 优先，其次 xpath=<...>
       → SelectorParser.extract_values(region, selector, attr)
            → locator.all_inner_texts() 或 _get_attributes (JS evaluate_all 保序)
       → _apply_if_regex_not_empty(values, regex)  # 去 regex: 前缀，re.search，捕获组优先
  → 清洗 / 长度对齐 / 去重
  → DataItem (CateListProductDataItem / CateLevelLinkDataItem / ...)
```

`CateLevelParser.parse_cate_level_items` 返回 `(links, names, ids)`，三阶段：先链、后名、再由 `_derive_ids(links, link_id_regex)` 派生 ID，最后 `_deduplicate` 按 ID（优先）或 link 去重并长度对齐。

`CateListParser.parse_cate_list_items` 返回 `(valid, invalid)`，逐 unit（`child_block==1`）定位 father 节点 → `_parse_cate_list_normal_nodes` 三阶段：COMMON 多值抽取 + RAW_COMMON id/tags → PRODUCT（仅 `content_type=="product"`）→ `_COMBINE` 节点替换（`config.context.node_var.replace_node_vars`）→ 多值展开为单值记录。`link` 字段经 `urljoin(page_url, value)` 绝对化。`filter_cate_list_items` 对记录施加四规则过滤。

### 6.6 Processor / Runner 链

Runner（同步门面，内部 `asyncio.run`）：

- `processor/cate_level/cate_level_runner.py: run_cate_level`：建 `TxtBatchFile`（index/link，`batch_size=-1` close 时 flush）→ `BrowserSessionFactory` → `PageNavigator`（注入 `script_config.system` 页面参数 + `script_config.page` PageItem）→ `CateLevelProcessor` → `await processor.run()` → finally 关闭 txt 文件 + `browser_factory.close_all()`。
- `processor/cate_list/cate_list_runner.py: run_cate_list`：建 `BrowserSessionFactory` + `PageNavigator` + Redis(`RedisConfig`→`RedisClient`→`RedisUtil`) + MongoDB(`MongoDBConfig`→`MongoDBClient`→`MongoDBUtil`) → `CateListProcessor` → `await processor.run()` → finally `browser_factory.close_all()`。
- `processor/item_detail/item_detail_runner.py: run_item_detail`：逐用户 `BrowserSessionFactory` + `PoolLoader` + `build_item_resource_context` + cookies 路径 + `PageNavigator` + `ItemDetailProcessor` → `await processor.run()` → finally `browser_factory.close_all()`。

Processor（编排，`CateLevelProcessor` docstring 自述）：

- `CateLevelProcessor.run`：`login()` → `collector.set_page` → `collector.collect()` → `_process_after_collect` → finally `item_handler.flush()` + `_close_page()`。
- `CateLevelCollector.collect`：`collect_level0()`（迭代 `cate_level.level0_list`，`_allow_parent` 过滤 → `CateLevelLinkNormalizer.normalize` → `CateLevelLinkBuilder.build` → `_build_dedup_key` → `_open(url, page_type="CATE_LEVEL")` → `accept_link` 回调 → `parser.parse_cate_level_items` → 递归 `_collect_sublevel(level=2)`）→ 返回 `floor_link_list`。
- `CateLevelProcessor._process_after_collect`：仅 `first_all_update` 时检测「头部共同分类」并剥离，对末层 cate_path 跑 `mini_cate.cate_level_index_normalizer.CateLevelIndexNormalizer.get_normal_cate` + `close_and_save` 写索引文件。
- `CateListProcessor.run`：`_login()` → `_collect()` → finally `_close_page()`。
- `CateListProcessor._collect`：**逆序**迭代 `link_items`（最深类目路径优先）→ clii 过滤 → 首页 URL 规范化 → `cate_level_redis.get(link_index)` 检查点（命中 `STATUS_COMPLETED_END` 跳过）→ `_collect_cate_list_per_cate_level_link`。
- `CateListProcessor._collect_cate_list_per_cate_level_link`：分页迭代 `page_data.page_urls`，受限于每用户上限（`browser.cate_list_crawl_max_per_user_range`）与每链接上限（`browser.cate_list_crawl_max_per_cate_level_link_on_user_range`），逐页 `_collect_cate_list_per_page`，全部完成才 `cate_level_redis.set_completed(link_index)`。
- `CateListProcessor._collect_cate_list_per_page`（最重方法）：URL 规范化 → `cate_list_redis.exists` 去重 → 滑块检测（DOM 模式预加载 / URL 模式后加载 `_check_slider_captcha_by_dom`/`_by_url`）→ `page_navigator.load(page_url, page_type="CATE_LIST")` → `scroll_to_load_more` → 发现新页 URL（`field_extractor.extract(page, css/xpath, attr="href")`）去重扩展 → `parser.parse_cate_list_items` → 逐条 `ContentRecordBuilder.build_from_cate_list` → **三层去重**：页内 set → Redis `content_redis.get_batch` → MongoDB `content_mongodb.get_batch`（Mongo 回填 Redis）→ `AllSequenceMongoDB.allocate_id_range` 批量分配 iid → `content_mongodb.set_batch` → 更新 `content_redis.set_batch` → `cate_list_redis.set_crawled` + `cate_level_redis.update_page_url`。
- `ItemDetailProcessor.run`：`browser_factory.create_context` → `_inject_cookies`（支持 JSON 与 `name=value;` 两格式，`script_config.cookie_domain`）→ `_context.new_page()` → `login()`（仅 `access_home_page` 时加载首页 + 滚动，登录态来自 cookies）→ `crawl_item()`（逐 URL `page_navigator.load(page_type="ITEM_DETAIL")` + `scroll_to_load_more`，单条失败继续）→ finally close page（不关 factory）。

**Processor 在本项目中承担的职责结论**：流程编排层。它不做 DOM 抽取（Parser）、URL 规范化（LinkNormalizer）、URL 业务规则（LinkBuilder）、过滤（Filter）、去重（DuplicateChecker）、写库（ItemHandler/Writer）、统计（Stats）。这些职责由其编排的子组件承担。

### 6.7 Database 链

```
CateListProcessor
  ├── CateLevelRedis    (3 态检查点：缺省=未爬 / {page_url}=续爬 / END=完成)
  ├── CateListRedis     (URL 存在性去重，TTL 由 sort_field 决定)
  ├── ContentRedis      (CONTENT-{project}:{hash_suffix}:{md5} 缓存，默认 7 天 TTL)
  ├── ContentMongoDB    (CONTENT-{hash_suffix} 分片集合，按 md5 末 N 位路由，MongoDB 为真相源)
  └── AllSequenceMongoDB (原子 $inc 分配连续 iid 区间)
```

`CateLevelRedis` 编码 3 态状态机：键缺失=未爬；值=`{page_url}`=续爬；值=`END`(`STATUS_COMPLETED_END`)=完成。head_key = `CATE_LEVEL_LINK-{project}:{sort_field}` 或 `:{sort_field}-{sort_order}`。

`ContentMongoDB` 按 `content_collection_hash_length`（2 或 3）取 md5 `_id` 末 N 位作集合后缀，`get_batch` 按 ID 分组到集合再 `find _id $in`，`set_batch` 分组 `insert_many ordered=False` 容忍 `BulkWriteError` 仅返回成功文档。

`AllSequenceMongoDB.allocate_id_range(count)` 用 `find_one_and_update(..., {"$inc": {"value": count}}, return_document=ReturnDocument.AFTER)` 原子分配 `[start, end)` 区间。

项目隔离：MongoDB 按**数据库名**（`MongoDBUtil.__init__(client, database_name)` 绑定 `self.database`）；Redis 按 **head_key 前缀**（`RedisUtil.make_key(head_key, key, separator=":")`，但 `ContentRedis` 绕过 `RedisUtil` 前缀逻辑，自行拼全键）。

### 6.8 Export 链

```
Processor / ItemHandler
  → StructuredBatchFile.add(item)   # fileio/batch/structured_batch_file.py
       → _build_writer(output_type)  # CsvIO/JsonIO/JsonlIO/ExcelIO/MongoWriter
       → read_existing() 去重种子
       → flush()  # write_batch 或逐条 write
  → TxtBatchFile                   # fileio/batch/txt_batch_file.py（CATE_LEVEL 用，batch_size=-1）
  → FileIoManager                  # fileio/fileio_manager.py（按 SystemItem 的 all_fields_save_csv/json/txt 路由）
  → fileio.file_backup.backup      # 备份
  → 输出：output/cate_level_index.txt, output/cate_level_link.txt, MongoDB CONTENT-*
```

`MongoWriter`（`database/mongodb/mongodb_writer.py`）是 `StructuredBatchFile` 在 `output_type="mongodb"` 时的薄写器，包装 `MongoDBUtil`。`export/cate_level/cate_level_index_writer.py: CateLevelIndexWriter.build_record/build_records` 仅做对象→记录字符串转换，实际写盘委托 `StructuredBatchFile`/`FileIO`；`export/cate_level/cate_level_link_writer.py` 为空文件。

---

## 7. 核心模块分析

### 7.1 `config/loader/script_config.py` —— 配置分发中心

- 目录：`config/loader/`
- 核心职责：`script.txt` → `ScriptConfig` 的总调度与校验。
- 核心类/函数：`ScriptConfig`、`parse_script_config`、`_process_config_item`、`_validate_config`、`print_config_summary`、`ScriptConfigError`。
- 上游：CLI（`runner_base.load_configs`）；下游：所有业务层。
- 关键数据：`ScriptConfig` 聚合 16 个 `*Item` 配置模型；`content_type` 选择 product/article 分支。
- 扩展方式：新增配置段需在 `_process_config_item` 前缀分发表加分支 + 新建 loader + 新建 model。
- 重要程度：极高（配置层是整个框架的神经中枢）。

### 7.2 `resource/` —— 资源四层绑定

- 目录：`resource/`
- 核心职责：资源加载、约束校验、运行期分配、BrowserContext 创建。
- 核心类：`PoolLoader`、`ResourceMapper`、`ResourceAllocator`、`BrowserSessionFactory`。
- 核心函数：`PoolLoader.load_all`、`ResourceMapper.validate_constraints`/`build_mapping`/`validate_user_ip`、`ResourceAllocator.allocate`/`allocate_no_user`、`BrowserSessionFactory.create_context`、`resolve_ip_index`。
- 上游：CLI；下游：Browser/Page。
- 关键数据：`PoolData`（4 池）、`ResourceContext`（运行期上下文）、`ResourceMapping`（用户→四层映射）。
- 扩展方式：新增浏览器类型扩展 `BROWSER_TYPE_NAMES` 与池 Excel 模板。
- 重要程度：极高（决定运行期隔离质量）。

### 7.3 `processor/cate_list/cate_list_processor.py` —— CATE_LIST 编排核心

- 目录：`processor/cate_list/`
- 核心职责：列表页内容采集编排，含分页、风控检测、三层去重、写库。
- 核心类/函数：`CateListProcessor.run`/`_collect`/`_collect_cate_list_per_cate_level_link`/`_collect_cate_list_per_page`、`CliiFilter.match`、`ContentRecordBuilder.build_from_cate_list`。
- 上游：`run_cate_list` Runner；下游：`CateListParser`、Redis/MongoDB 适配器、`PageNavigator`。
- 关键数据：`ContentDataRecord`（最终持久化记录）、`CateLevelPageDataItem`（分页状态）。
- 扩展方式：新增内容类型扩展 `_collect_cate_list_per_page` 的 record 构建分支。
- 重要程度：极高（CATE_LIST 是内容采集的主战场）。

### 7.4 `processor/cate_level/cate_level_collector.py` —— 类目树遍历

- 目录：`processor/cate_level/`
- 核心职责：5 层类目树递归遍历，产出 `floor_link_list`。
- 核心类/函数：`CateLevelCollector.collect`/`collect_level0`/`_collect_sublevel`/`_open`/`_build_dedup_key`。
- 上游：`CateLevelProcessor`；下游：`CateLevelParser`、`CateLevelLinkBuilder`、`CateLevelLinkNormalizer`、`PageNavigator`。
- 关键数据：`floor_link_list: list[list[str]]`（按层 0-4 索引）、`collector_duplicate_checker`。
- 扩展方式：层级扩展由 `MAX_CATE_LEVEL_INDEX=4` 约束。
- 重要程度：高（CATE_LEVEL 的核心算法）。

### 7.5 `parser/cate_list/cate_list_parser.py` —— 列表解析

- 核心职责：按 unit/normal node 规则从列表页 DOM 抽取记录并展开多值为单值。
- 核心类/函数：`CateListParser.parse_cate_list_items`、`_parse_cate_list_normal_nodes`、`_extract_cate_list_node_values`、`_parse_cate_list_combine_values`、`CateListParsedItem`、`_reset_item_is_parsed`、`_clean`。
- 上游：`CateListProcessor`；下游：`CateListCommonDataItem`/`CateListProductDataItem`。
- 关键数据：`_COMMON_FIELDS`/`_PRODUCT_FIELDS` 元组、`node_vars`（`_COMBINE` 替换上下文）。
- 重要程度：高。

### 7.6 `database/mongodb/content_mongodb.py` 与 `database/redis/content_redis.py` —— 内容双层存储

- 核心职责：MongoDB 为 CONTENT 真相源（分片集合）；Redis 为 CONTENT 去重缓存（7 天 TTL）。
- 核心函数：`ContentMongoDB._build_collection_name`/`get_batch`/`set_batch`、`ContentRedis._build_head_key`/`get_batch`/`set_batch`。
- 上游：`CateListProcessor`；下游：MongoDB/Redis 实例。
- 关键数据：md5 `_id`、`content_collection_hash_length`、`content_default_ttl`（默认 604800s）。
- 重要程度：极高（去重与持久化的交汇点）。

### 7.7 `mini_cate/cate_level_index_normalizer.py` —— 类目归一算法

- 核心职责：Java 移植的 `TypeProcessor` 算法，将站点异构类目路径归一到 5 级标准索引（含 `OTHER_CATE_ID=999`「其他」兜底）。
- 核心类/函数：`CateLevelIndexNormalizer.get_normal_cate`/`close_and_save`/`sort_cate_list`/`split_compare`/`_match_existing_cate`/`_ensure_other_cate`/`reset`。
- 上游：`CateLevelProcessor._process_after_collect`；下游：`cate_level_index.txt`。
- 关键数据：`index_cate_map`、`compare_cate_list`、`from_index_to_cate_id`。
- 重要程度：高（业务域核心算法，docstring 标注「不要修改算法」）。

---

## 8. 配置驱动架构分析

代码证实的配置驱动特征：

1. **站点目录名即元数据**：`{main_id}-{sub_id}-{site_name}-{content_type}-{language}` 由 `ProjectConfigLoader._parse_project_dir_name` 解析为 `ProjectConfig` 字段与 `program_vars`。
2. **`script.txt` 单文件配置全站点**：经 `parse_script_config` 分发到 16 个 `*Item` 模型；前缀分发表见 6.2。
3. **三层变量替换**：`@[NAME]`（`script_constant`）、`@{NAME}`（`script_var`）、`${PRO_*}`（`pro_var`）。`DEFERRED_PROGRAM_VARS = {"PRO_CATE_LEVEL_SORT_FIELD", "PRO_CATE_LEVEL_SORT_ORDER"}` 在运行期由 `build_sort_program_vars(field, order)` 解析。
4. **content_type 多态**：`ScriptConfig.get_cate_list_item()`/`get_detail_item()` 按 `content_type`（product/article）切换分支模型。
5. **节点配置回填**：`config/backfill/node_config_backfill.py` 在解析后回填 `UnitNodeConfig.child_node_list` → 子 `NormalNodeConfig.father_css/father_xpath`，并做 `validate_layer_default_values`/`validate_layer_filters`/`validate_unit_child_filters`。
6. **节点抽取规则统一**：`NormalNodeConfig`（`node_name`/`node_type`/`father_css`/`father_xpath`/`father_child_max_count`/`css`/`xpath`/`attr`/`regex`/`id_regex`/`combine`/`is_parsed`/`locator_enabled`/`combine_enabled`）是通用 DOM 抽取节点，被 CATE_LEVEL/CATE_LIST 共用。
7. **环境分离**：`AppConfig` 加载 `env/dev.yaml`/`env/pro.yaml`，`MongoDBConfig`/`RedisConfig` 从中取连接参数。

**不贴「低代码」标签**：上述仅证明项目具备配置驱动特征；是否称「低代码」取决于定义，本报告只陈述代码事实。

---

## 9. Resource 资源架构分析

见 6.3。补充：

- `BrowserSessionFactory` 反自动化启动参数：`--disable-blink-features=AutomationControlled`、`--no-first-run`、`--force-webrtc-ip-handling-policy=disable_non_proxied_udp`（防 WebRTC IP 泄漏）等。
- 指纹对齐：`_parse_fingerprint_profile` 取 `platform`/`languages`，`_parse_chrome_version` 取 `__fp.chromeVersion`，`_parse_screen_profile` 取 `__fp.screen`（availWidth/availHeight/dpr）；据此对齐 UA、`Sec-Ch-Ua`、`Accept-Language`、`locale`、`timezone_id`（`_LOCALE_TIMEZONE` 映射）。
- 职责切分（`browser_session_factory.py` docstring lines 14-17）：`ResourceAllocator` 决定用哪个 proxy（业务决策）；`BrowserSessionFactory` 只创建 BrowserContext（执行）。
- 浏览器池与 IP 解耦：`PoolLoader.load_browser_pool` docstring line 297 明确「Browser pool no longer holds IP binding」，IP 规范在 `UserConfig.ip_spec`。
- 无用户模式：`allocate_no_user()` 用 `DEFAULT_BROWSER_INDEX=0` + 其 1:1 指纹，无代理，`user=None`（用于 `u -1`）。

---

## 10. Browser / Page 架构分析

见 6.4。补充：

- `PageNavigator` 构造参数全部来自 `script_config.system`（页面加载）与 `script_config.page`（`PageItem`）：`headless`、`max_retries`、`ready_check_enabled`、`page_goto_timeout`、`timeout`、`network_idle_enabled`、`network_idle_timeout`、`page_item`。
- `PageReadyChecker.wait` 顺序：可选 `networkidle`（异常吞掉）→ 必选 `wait_for_selector(ready_selector)`。
- `scroll_to_load_more` 终止条件详见 6.4，受 `constants/browser_const.py` 常量约束。
- `PageNavigator` 禁 `self.page` 单例的设计意图（注释 line 113）：避免多 Processor / 多用户共享同一 Page 造成状态污染。

### 10.2 Cookie / 登录状态管理

Cookie 是登录态的载体，本项目的 Cookie 管理分三类场景：

**存储位置**

- cate（`site/<id>/`）：`user/0/{cookie, local-storage, session-storage}/`，由 `ProjectConfigLoader.load_configs` 创建目录（`constants/path_const.py: COOKIE_DIR_NAME`/`LOCAL_STORAGE_DIR_NAME`/`SESSION_STORAGE_DIR_NAME`）。
- item_detail（`item/<id>/`）：`cookies/<user-index>_cookies.txt`，模板 `{user-index}_cookies.txt`（`constants/item_detail/path_const.py: COOKIES_FILE_TEMPLATE` + `COOKIES_DIR_NAME="cookies"`）。

**注入机制（item_detail）**

- `processor/item_detail/item_detail_processor.py: ItemDetailProcessor._inject_cookies`（line 126）读取 `cookies.txt`，支持两格式：
  - `_try_parse_json_cookies`：JSON 数组或 `{cookies: [...]}` 包装格式；
  - `_parse_name_value_cookies`：`name=value;name=value` 文本格式。
- 用 `script_config.cookie_domain`（lines 135/233/243）限定 cookie 作用域；空文件跳过注入；解析失败抛错。

**登录态来源**

- item_detail 不走账号密码登录，登录态完全来自注入 cookies；`ItemDetailProcessor.login` 仅在 `script_config.access_home_page` 为真时加载首页（`page_type="HOME"`）+ 滚动以激活会话。
- cate 侧登录由站点代码承担（站点能力，见 §17）：`site/<id>/login/{host_login,page_login,login_checker,login_slider,login_verify,image_match}.py`；`LoginChecker.is_logged_in(page)` 校验登录态。

**Cookie 与 BrowserContext 的关系**

- `BrowserSessionFactory.create_context` 用 `launch_persistent_context(user_data_dir=...)`，`user_data_dir`（`BrowserConfig.user_data_dir`）本身由 Playwright 持久化 cookie/local-storage/session-storage，跨运行保留会话。
- `UserConfig` 的 `browser_index` → `BrowserConfig.user_data_dir`，即每用户绑定独立浏览器档案目录，天然隔离会话。

**登录态校验**

- 页面层：`PageItem.login_ready_selector` + `_PAGE_TYPE_ATTR["LOGIN"]`（`page/page_navigator.py`）→ `PageReadyChecker.wait` 等待登录页关键元素。

---

## 11. Parser / Processor 架构分析

### 11.1 Parser 双层结构

- 底层 `SelectorParser`：仅做 DOM 原语（`all_inner_texts` / 属性 `evaluate_all`）。
- 上层 `FieldExtractor`：四后缀规则 + 正则后处理，被 `CateLevelParser`/`CateListParser` 复用。
- 业务子层 `parser/cate_level/`、`parser/cate_list/`：按 `NormalNodeConfig` 与 `UnitNodeConfig` 编排多节点抽取。
- `parser/item_detail/` 空目录：ITEM_DETAIL 阶段解析未实现。

### 11.2 Processor 编排模式

每业务类型一个 Processor + 一组子组件：

| 业务 | Processor | 子组件 |
|---|---|---|
| CATE_LEVEL | `CateLevelProcessor` | `CateLevelCollector`/`CateLevelParser`/`CateLevelFilter`/`CateLevelLinkBuilder`/`CateLevelLinkNormalizer`/`CateLevelItemHandler`/`CateLevelItem`(预留)/`CateLevelValidator`(预留)/`CateLevelStats`(预留) |
| CATE_LIST | `CateListProcessor` | `CateListParser`/`CliiFilter`/`ContentRecordBuilder`/4 个 DB 适配器 |
| ITEM_DETAIL | `ItemDetailProcessor` | （无独立 Collector/Parser，仅 `PageNavigator` + cookies 注入） |

`processor/common/duplicate_checker.py: DuplicateChecker` 提供通用去重（`seed`/`is_duplicate`/`add`/`check_and_add`/`clear`），被 `CateLevelCollector`（页内去重）与 `CateLevelItemHandler`（输出层去重）复用。`processor/common/link_id_config.py` 提供 `get_level_link_id_regex`/`extract_link_id`。`processor/unit/unit_filter.py: UnitFilter` 包装 `UnitNodeConfig` 提供 `has_selector`/`use_css`/`use_xpath`/`is_enable`。

### 11.3 Network Response 拦截（item_detail）

> 本节区分「现状」与「架构计划」。现状部分以代码为准；计划部分依据 loader 注释与用户确认的近期实现方向，**代码尚未落地**，不作现状陈述。

#### 11.3.1 现状（代码确认：config-only，非功能性）

配置侧 `config/model/item_detail/item_detail_item.py: ItemDetailScriptConfig`（lines 53-63）声明 4 个 `network_response_*` 字段：

```python
network_response_intercept_enable: int = 0
network_response_name: str = ""
network_response_regex: str = ""
network_response_json_nodes: str = ""
```

- 类型：`network_response_intercept_enable` 为 `int`（0/1 布尔语义，模块 docstring line 46-51 说明「布尔字段为 int 仅 0/1」）；其余 3 字段为 `str`。无嵌套 dataclass，全部扁平到顶层。
- 模块 docstring（lines 1-13）将「有 Network Response 配置」列为 item_detail 的区分特性。

解析侧 `config/loader/item_detail/item_detail_loader.py`：

- `_process_item_detail_key`（lines 133-178）分发 4 键：`NETWORK_RESPONSE_INTERCEPT_ENABLE` 走 `_BOOL_FIELD_MAP` + `_parse_bool_strict`（仅收 `0`/`1`）；`NETWORK_RESPONSE_NAME`/`NETWORK_RESPONSE_REGEX`/`NETWORK_RESPONSE_JSON_NODES` 原样存字符串，**无 JSON 解析、无正则编译、无非空校验**。
- `print_item_detail_summary`（lines 250-289）仅打印 4 字段值。
- `_validate_item_detail_config`（lines 227-242）尾注释（lines 240-242）为关键证据：

  > Network Response：本阶段只确保配置进入模型，不校验 REGEX/JSON_NODES 是否非空，也不实现优先级与拦截业务（任务§四/§三十三）。优先级规则（REGEX 有值优先；否则用 JSON_NODES）留到后续 Processor/Parser 阶段。

消费侧（全代码库实测，排除禁扫目录）：

- `grep network_response` 全库仅 3 文件命中：`config/model/item_detail/item_detail_item.py`（声明）、`config/loader/item_detail/item_detail_loader.py`（解析）、`docs/项目架构全面分析报告.md`（本报告）。
- `grep "page.route|context.route|on(\"response\")|on(\"request\")|response.body|response.json"` 在 `processor/`/`page/`/`resource/`/`config/`/`main/` 中**零命中**。
- `resource/browser_session_factory.py` 唯一的 `add_init_script`（line 180）是浏览器指纹 JS 注入，**非**网络拦截。
- `processor/item_detail/item_detail_processor.py: ItemDetailProcessor.run` 与 `item_detail_runner.py` 从不引用任何 `network_response_*` 字段；`run` 仅消费 `script_config.headless`/`cookie_domain`/`access_home_page`/`home_url`。

现状结论：**Network Response 拦截在当前代码中仅为配置占位，无任何运行期消费方，非功能性。** `docs/Python-PlayWright-Web-项目总结.md:134` 亦明确佐证「network response 的配置也只进入模型」。

#### 11.3.2 架构计划（未实现，文档先行）

依据 loader 注释 + 用户确认的近期实现方向。下列内容为**计划**，代码尚未落地：

- **主开关**：`network_response_intercept_enable`（0/1）控制是否启用网络响应拦截。
- **响应名标签**：`network_response_name` 为目标响应的业务名标签，用于结果归属与日志。
- **URL 匹配**：`network_response_regex` 为 URL 正则；`network_response_json_nodes` 为 JSON 节点提取规格字符串。
- **优先级规则**：REGEX 有值时优先按 URL 正则匹配；否则回退用 JSON_NODES。
- **落地形态（待定）**：计划在 `ItemDetailProcessor.run` 的 `_context.new_page()` 之后、导航之前安装 Playwright 拦截，两候选方案：
  - 方案 A：`page.route(url_regex, handler)` 拦截匹配请求并读取 `response.body()`/`response.json()`（会阻断/改写请求）；
  - 方案 B：`page.on("response", handler)` + URL 过滤被动捕获，不阻断请求；
  - 具体方案待实现时确定，本报告仅记录设计意图。
- **结果去向（计划）**：拦截到的 JSON 节点数据并入 item_detail 解析产物，最终经 `ContentRecordBuilder`（item_detail 分支待建）进入 `ContentDataRecord.content: Dict[str, Any]`。当前 `parser/item_detail/` 为空目录、`ItemDetailProcessor` 仅导航滚动，此「拦截 → 解析 → 持久化」链路待打通。

#### 11.3.3 与其他业务类型的关系

- 该机制仅出现在 item_detail 配置侧（`ItemDetailScriptConfig`）；CATE_LEVEL/CATE_LIST 的 `ScriptConfig` 无 `network_response_*` 字段。
- 设计上与 `parser/item_detail/`（待建）互为补充：DOM 抽取与网络响应拦截是 item_detail 数据采集的两条互补通道。

---

## 12. 数据模型架构

三层 `@dataclass`：

### 12.1 Config Model（`config/model/`）—— 配置层

解析 `script.txt` 的产物，描述「怎么抽」：

- `node/normal_node_config.py: NormalNodeConfig`、`node/unit_node_config.py: UnitNodeConfig`
- `cate_level/`: `CateLevelItem`（5 级 `level0_list` + `level1..4: CateLevelConfig`，每级含 `link: NormalNodeConfig`、`name: NormalNodeConfig`、`link_id_regex`、`max_count`、`floor_open`、`last_floor_id`、filter/default-value 列表）、`CateLevel0Entry`、`CateLevelUnitItem`
- `cate_list/`: `CateListItem`（URL 参数顺序、sort 字段、`page: CateListPageConfig`）、`CateListProductItem`、`CateListArticleItem`、`CateListCommon`、`CateListUnitItem`
- `detail/`: `DetailProductItem`、`DetailArticleItem`、`DetailCommon`、`DetailUnitItem`
- `browser/BrowserItem`、`login/LoginItem`、`risk/RiskItem`、`system/SystemItem`、`page/PageItem`、`redis/RedisItem`、`mongodb/MongodbItem`
- `item_detail/item_detail_item.py: ItemDetailScriptConfig`、`item_detail/item_user_config.py: ItemUserConfig`

### 12.2 Data Model（`data/model/`）—— 采集结果层

描述「抽到了什么」，无 CSS/XPath，无持久化职责：

- `cate_level/cate_level_link_data_item.py: CateLevelLinkDataItem`（url, level, limit_cate_level_0_id, cate_name, cate_names_path, cate_ids_path, cate_links_path）
- `cate_level/cate_level_index_data_item.py: CateLevelIndexDataItem`
- `cate_list/cate_list_common_data_item.py: CateListCommonDataItem`、`cate_list_product_data_item.py: CateListProductDataItem`
- `detail/detail_common_data_item.py: DetailCommonDataItem`、`detail_product_data_item.py: DetailProductDataItem`
- `data/loader/cate_level/`: `CateLevelIndexDataLoader.load`、`CateLevelLinkDataLoader.load`（回读 .txt 输出为 DataItem）
- `data/backfill/cate_level_link_data_backfill.py: CateLevelLinkDataBackfill.backfill`（`cate_level_link.txt` 不持久化 `cate_ids_path`/`cate_links_path`，由 index 反推回填）

### 12.3 Data Record（`data/model/data_record/content_data_record.py`）—— 持久化层

- `ContentCommonData`：link, id, main_title/sub_title, main_image/sub_images, view/favorite/comment_count, summary, description, publish_time/edited_time, main_owner_*, sub_owner_*。
- `ContentDataRecord`：`_id=md5(raw_id)`、`iid`、`user_index/user_name/is_logged_in`、`system_version`、`mongodb_database_version`、`raw_id/raw_url/crawl_url/crawl_time/update_url/update_time`、`ects_0..ects_4`（5 个客户导出计数器）、`common: ContentCommonData`、`content: Dict[str, Any]`（动态业务 JSON，Product/Article/扩展无关）。

关系：`script.txt` → `ScriptConfig`(Config Model) → Parser 用 `NormalNodeConfig` 抽取 → `*DataItem`(Data Model) → `ContentRecordBuilder` 合并 → `ContentDataRecord`(Data Record) → `ContentMongoDB`/`ContentRedis`。`ContentDataRecord.content: Dict` 设计使 DB schema 不随内容类型变化。

---

## 13. MongoDB / Redis 数据架构

### 13.1 MongoDB

| 模块 | 类/函数 | 职责 |
|---|---|---|
| `mongodb_client.py` | `MongoDBClient` | `pymongo.MongoClient` 连接（池、auth、超时） |
| `mongodb_util.py` | `MongoDBUtil(mongodb_client, database_name)` | CRUD 包装（`get_collection`/`insert_one`/`insert_many`/`find_one`/`find`/`update_one`/`delete_one`） |
| `mongodb_writer.py` | `MongoWriter` | `StructuredBatchFile` 在 `output_type="mongodb"` 时的薄写器 |
| `content_mongodb.py` | `ContentMongoDB` | CONTENT 真相源，分片到 `CONTENT-{hash_suffix}` 集合，`get_batch`/`set_batch` |
| `all_sequence_mongodb.py` | `AllSequenceMongoDB` | 原子 `$inc` 自增 iid 区间 |

项目隔离：按**数据库名**。

### 13.2 Redis

| 模块 | 类/函数 | 职责 |
|---|---|---|
| `redis_client.py` | `RedisClient` | `redis.ConnectionPool` + `redis.Redis` |
| `redis_util.py` | `RedisUtil` | `make_key(head_key, key, separator)`、`set/get/set_batch/get_batch` |
| `redis_ttl_util.py` | `get_sort_field_ttl(sort_field, sort_fields_ttl)` | sort 字段 TTL 查找 |
| `cate_level_redis.py` | `CateLevelRedis` | CATE_LEVEL_LINK 3 态检查点 |
| `cate_list_redis.py` | `CateListRedis` | CATE_LIST URL 存在性去重 |
| `content_redis.py` | `ContentRedis` | CONTENT 缓存（默认 7 天 TTL） |

项目隔离：按 **head_key 前缀**（`ContentRedis` 绕过 `RedisUtil` 前缀逻辑自拼全键）。

职责分工结论：**MongoDB = 内容持久真相源 + 自增序列**；**Redis = 爬取状态缓存 + 去重缓存**。Redis 缺失非致命——`CateListProcessor` 在 Redis 去重未命中时回退到 MongoDB 去重并回填 Redis。

PostgreSQL：`database/postgresql/postgresql_client.py`、`postgresql_util.py` 为空文件，未实现。

---

## 14. Site / Item 项目架构

- **`site/<id>/`**：CATE_LEVEL/CATE_LIST 项目根。目录名 `{main}-{sub}-{site}-{content}-{lang}` 由 `ProjectConfigLoader._parse_project_dir_name` 解析。布局：`script/script.txt`、`logs/`、`input/`、`user/user_pool.xlsx`、`output/{brand_dict, cate_level_index, cate_level_link, link}/`、`backup/{cate_level_index, cate_level_link}/`、`user/0/{cookie, local-storage, session-storage}/`、`login/*.py`（站点级登录/滑块代码）。示例：`site/1001-001-dangdang_com-product-zh_cn/`、`site/1051-001-shopee_tw-product-zh_tw/`。
- **`item/<id>/`**：ITEM_DETAIL 项目根。布局：`cookies/<idx>_cookies.txt`、`input/item_list_link.txt`、`script/script.txt`、`user/user_pool.xlsx`、`logs/`。无 `.py`，业务由 `config/loader/item_detail/` + `processor/item_detail/` 承载。示例：`item/1051-001-taobao_com-product-zh_cn/`。

字段作用：

- `main_id`/`sub_id`：项目编号（如 `1001`/`001`），用于定位项目目录、生成 `program_vars`、作为 Redis head_key / MongoDB 数据库名组成。
- `site_name`：站点标识（如 `dangdang_com`），用于 `PRO_SITE_NAME` 变量与站点级 login 代码定位。
- `content_type`：`product`/`article`，驱动 `ScriptConfig` 的 product/article 分支选择。
- `language`：`zh_cn`/`zh_tw` 等，用于 `PRO_LANGUAGE` 与指纹 locale 对齐。

核心框架与具体站点项目关系：**框架核心站点无关**（`main`/`config`/`resource`/`page`/`parser`/`processor`/`database`/`fileio`/`utils`）；**站点业务下沉**到 `site/<id>/login/*.py`（登录/滑块 DOM 逻辑）+ `site/<id>/script/script.txt`（站点差异配置）。`item/<id>/` 仅存运行期数据。这是「通用爬虫框架 + 具体站点业务」架构的代码依据。

---

## 15. 数据流分析

以 CATE_LIST 为例（最完整数据流）：

```
输入：script.txt + user_pool.xlsx + pool/*.xlsx + env/*.yaml
  ↓
配置：parse_script_config → ScriptConfig
  ↓
资源：PoolLoader.load_all → ResourceAllocator.allocate → ResourceContext
  ↓
浏览器：BrowserSessionFactory.create_context（指纹/UA/代理对齐）
  ↓
页面：PageNavigator.load（goto + ready + scroll）
  ↓
解析：CateListParser.parse_cate_list_items → CateListParsedItem
  ↓
过滤：filter_cate_list_items（四规则）
  ↓
构建：ContentRecordBuilder.build_from_cate_list → ContentDataRecord（_id=md5）
  ↓
去重三层：页内 set → ContentRedis.get_batch → ContentMongoDB.get_batch（回填 Redis）
  ↓
序列：AllSequenceMongoDB.allocate_id_range → iid
  ↓
写库：ContentMongoDB.set_batch（CONTENT-XX 集合）+ ContentRedis.set_batch（7 天 TTL）
  ↓
状态：CateListRedis.set_crawled(page_url) + CateLevelRedis.update_page_url(link_index, page_url)
  ↓
输出：MongoDB CONTENT-* 文档 + Redis 缓存键
```

CATE_LEVEL 数据流：

```
配置 + 资源 + 浏览器 + 页面
  ↓
CateLevelCollector.collect_level0 → 递归 _collect_sublevel(2..4)
  ↓ (每层)
CateLevelLinkNormalizer.normalize → CateLevelLinkBuilder.build → URL--flag>>>limit_id>cate_text
  ↓
CateLevelParser.parse_cate_level_items → links/names/ids
  ↓
CateLevelItemHandler.accept_link → link_duplicate_checker → TxtBatchFile(cate_level_link.txt)
  ↓
CateLevelIndexNormalizer.get_normal_cate + close_and_save → cate_level_index.txt
```

ITEM_DETAIL 数据流：

```
配置 + 资源 + cookies + item_list_link.txt
  ↓
ItemDetailProcessor.run: create_context → inject_cookies → new_page → login → crawl_item
  ↓ (每 URL)
PageNavigator.load(page_type="ITEM_DETAIL") + scroll_to_load_more
  ↓ （无解析层，仅导航）
```

---

## 16. 业务类型架构

| 业务类型 | 入口 | Runner | Processor | Parser | DB | 状态 |
|---|---|---|---|---|---|---|
| CATE_LEVEL | `main/cate_level.py` | `run_cate_level` | `CateLevelProcessor` + Collector/Filter/Builder/Normalizer/ItemHandler | `CateLevelParser` | fileio TxtBatchFile（无 DB） | 已落地 |
| CATE_LIST | `main/cate_list.py` | `run_cate_list` | `CateListProcessor` | `CateListParser` + `filter_cate_list_items` | Redis 3 + MongoDB 2 | 已落地 |
| ITEM_DETAIL | `main/item_detail/item_detail.py` | `run_item_detail` | `ItemDetailProcessor` | （空，未实现） | （无 DB 写入） | 仅导航，未实现解析 |
| DETAIL | （无入口） | （无） | （无 processor/detail/） | （无 parser/detail/） | 仅 `config/model/detail/*` | 仅配置模型，未落地 |
| LOGIN | 站点 `site/<id>/login/*.py` | — | 由 Processor 调用 | — | cookies 文件 | 站点能力 |
| RISK | `CateListProcessor._check_slider_captcha_*` + `mouse_tracks` | — | 内嵌于 CateListProcessor | — | RiskItem 配置 | 已落地（DOM/URL 双模式，PAUSE/AUTO/EXIT） |

共用代码：`main/cli/runner_base`（日志/目录/配置加载）、`resource/`（四层绑定）、`page/PageNavigator`、`parser/field_extractor`+`selector_parser`、`fileio/batch`、`utils/`、`request/RetryManager`、`processor/common/DuplicateChecker`。

独立代码：每业务独立 `processor/<biz>/` 子树与 `parser/<biz>/`；item_detail 独立 `config/loader/item_detail/` 与 `main/cli/item_detail/`。

配置控制：`script.txt` 段前缀决定配置归属；`content_type` 控制 product/article 分支；`RiskItem`/`LoginItem`/`PageItem` 控制风控/登录/页面行为。

「通用爬虫框架 + 具体站点业务」是否形成：**已形成**。框架核心站点无关，站点差异由 `site/<id>/script/script.txt` + `site/<id>/login/*.py` 承载。代码依据：`ProjectConfigLoader` 按目录名解析站点元数据；`parse_script_config` 站点无关；`BrowserSessionFactory`/`PageNavigator`/`Parser`/`Processor` 均不引用具体站点；站点 login 代码位于 `site/<id>/login/`。

---

## 17. 异常 / 重试 / 风控架构

- `request/retry_manager.py: RetryManager.execute(func, max_retry=3, delay=0.0, randomize_delay=False, on_retry)` —— 通用异步重试，替代旧 Scrapy `ErrorRetryMiddleware`。docstring 警告：`PageNavigator.load` 已内置页面加载重试，包装它会致 9 次重试；`RetryManager` 仅用于业务流（登录/解析/写库）。
- `utils/delay_manager.py: DelayManager.delay(seconds, randomize=True)`（jitter `[0.5x, 1.5x]`）/`delay_range(min, max)` —— `asyncio.sleep`，不阻塞事件循环。
- 风控：`config/model/risk/risk_item.py: RiskItem`（`slider_check_dialog`/`slider_check_mode`(DOM/URL)/`slider_verify_url_keywords`/`slider_show_next_action`(PAUSE/AUTO/EXIT)/`slider_type`/`human_slider_track_enabled`/`max_slider_trigger_count`/`max_slider_auto_fail_count`）。
- 滑块管理：`mouse_tracks/slider_captcha_manager.py: SliderCaptchaManager.handle_slider`（熔断 `max_slider_trigger_count`，超 `max_slider_auto_fail_count` 升级人工 `input()` 在线程执行器上）。
- 滑块拖拽：`mouse_tracks/unified_slider_dragger_v2.py: UnifiedSliderDragger.drag`（JS 注入 `_drag_with_js` 优先，CDP `Input.dispatchMouseEvent` 回退；轨迹池 LRU `MAX_TRACKS=100`，`aiofiles` 异步持久化；成功轨迹回写）。
- 缺口检测：`captcha/image_slider/image_slider_gap_x_detector.py: ImageSliderGapXDetector.detect`（Playwright 截图 + OpenCV Canny + X 轴边缘投影）+ `gap_x_result.py: GapXResult`。
- 图像匹配：`image_match/base.py: ImageMatcher(ABC)`、`image_match/shape/contour_v3.py: ContourMatcher`（Otsu 自适应 Canny + 粗细两级模板匹配）、`image_match/pixel/transparency.py: TransparencyMatcher`。
- 处置策略：`CateListProcessor._handle_slider_show_next_action` 支持 `PAUSE`（30/120/300s 退避循环）、`AUTO`（未实现）、`EXIT`（存盘 + 延迟 + `SystemExit(0)`）。`check_slider_captcha_dialog_show`/`check_slider_captcha_verified` 为 `return True` 占位桩（lines 1986-2000）。
- 站点级风控：`site/<id>/login/login_slider.py`、`login_verify.py`、`login_checker.py`、`image_match.py`、`各站点风控链接收集.txt`。

能力归属判定：

| 模块 | 归属 |
|---|---|
| `request/RetryManager`、`utils/delay_manager`、`utils/value_utils`、`utils/comment_cleaner`、`fileio/`、`mini_text/` | 基础能力 |
| `image_match/`、`mouse_tracks/`、`captcha/` | 基础能力（OpenCV/Playwright，站点无关） |
| `mini_cate/` | 业务能力（类目树归一算法） |
| `site/<id>/login/` | 站点能力 |
| `processor/cate_list` 内嵌风控逻辑 | 业务 + 站点能力交界（配置由 `RiskItem` 驱动） |

---

## 18. 模块依赖关系

真实依赖方向（基于 import 与实例化）：

```
main/cli  → config/loader, resource, processor/<biz>, constants, fileio, utils
config/loader  → config/model, config/context, config/backfill, constants, utils, mini_text
config/application  → env/*.yaml
resource  → constants, config (无), playwright
page  → resource(BrowserSessionFactory), config/model(PageItem), constants/browser_const
parser  → config/model(NormalNodeConfig 等), data/model(*DataItem), constants/unit_const, config/context/node_var
processor  → page, parser, resource, database, fileio, config/loader, config/model, data/model, mini_cate, utils, request
database  → config/database, config/model(RedisItem/MongodbItem)
fileio  → database/mongodb/mongodb_writer (StructuredBatchFile 的 MongoWriter), config/model(SystemItem)
export  → config/model, fileio
mini_cate  → mini_text, constants/cate_const
mouse_tracks  → constants/path_const, playwright
captcha  → playwright, image_match
image_match  → cv2, numpy
```

核心依赖：`processor` 是依赖最广的层（汇聚 page/parser/resource/database/fileio/config/data/utils）；`config/loader` 是配置分发中枢。

高耦合点：

- `CateListProcessor._collect_cate_list_per_page` 单方法承担 URL 规范化 + 风控检测 + 加载 + 滚动 + 分页发现 + 解析 + 三层去重 + 序列分配 + 写库 + 状态更新，方法体极长，职责密集。
- `script_config.py:_process_config_item` 单分发表耦合所有段 loader。
- item_detail 与 cate 双项目根存在并行配置/资源/CLI 子树，未完全复用。

双向/循环依赖：未在 import 层面发现循环依赖（`__init__.py` 导出与跨层 import 方向单一）。`fileio/batch/structured_batch_file.py` → `database/mongodb/mongodb_writer.py` → `database/mongodb/mongodb_util.py`，方向单一。

基础模块（被广泛依赖，无下游业务依赖）：`utils/`、`fileio/base_file`、`constants/`、`mini_text/`、`config/context/`、`config/application/`。
上层模块：`main/`、`processor/<biz>/`、`site/<id>/login/`。

---

## 19. 核心模块与非核心模块划分

### 19.1 核心架构模块

- `config/loader/`（`script_config`、`project_loader`、`item_detail/*`）—— 配置分发中枢
- `resource/`（`pool_loader`、`resource_mapper`、`resource_allocator`、`browser_session_factory`）—— 资源调度
- `processor/cate_level/`、`processor/cate_list/`、`processor/item_detail/`—— 业务编排
- `parser/cate_level/`、`parser/cate_list/`、`parser/field_extractor`、`parser/selector_parser` —— 解析
- `page/page_navigator` —— 页面生命周期
- `database/mongodb/content_mongodb`、`database/redis/{cate_level,cate_list,content}_redis`、`database/mongodb/all_sequence_mongodb` —— 持久化与状态
- `main/cli/`（`args_parser`、`runner_base`、`sort_spec`）—— CLI 与共享脚手架

### 19.2 基础能力模块

- `utils/`（`delay_manager`、`comment_cleaner`、`value_utils`、`export/`）
- `fileio/`（`base_file`、`csv/json/jsonl/excel/txt_io`、`fileio_manager`、`file_backup`、`batch/`）
- `request/retry_manager`
- `mini_text/`、`image_match/`、`mouse_tracks/`、`captcha/`
- `config/application/app_config`、`config/database/{mongodb,redis}_config`、`config/context/`、`config/backfill/`

### 19.3 业务模块

- `mini_cate/`（类目树归一算法）
- `data/model/`、`data/loader/`、`data/backfill/`
- `export/cate_level/`

### 19.4 工具模块

- `tools/project_tree`、`tools/count_python_lines`、`tools/export_custom_fields`（非运行期）

### 19.5 站点项目（运行期数据 + 站点代码）

- `site/<id>/`（script.txt + login/ + output/ + user/）
- `item/<id>/`（cookies + input + script + user + logs）
- `pool/*.xlsx`（资源池）

### 19.6 历史/遗留/空占位

- `scrapy.cfg`、`scrapy-playwright` 依赖、`twisted` 依赖（Scrapy 遗留，未启用）
- `database/postgresql/*`（空文件）
- `parser/item_detail/`、`resource/item_detail/`、`processor/content/`、`main/site/`（空目录）
- `export/cate_level/cate_level_link_writer.py`、`image_match/edge/canny.py`、`image_match/feature/orb.py`、`mini_cate/cate_index.py`（空文件）
- `processor/cate_level/cate_level_validator.py`、`cate_level_stats.py`、`cate_level_item.create_item()`（自述预留未接入）
- `README.md`（已过时）
- `prompt/`（设计草稿，非代码）
- 排除目录（不进入报告主体）：`.git/`、`.idea/`、`.ruff_cache/`、`backup/`、`test/`、`tests/`、`DEL/`、`fingerprint_work/`

---

## 20. 当前架构优点

1. **配置驱动已落地**：`script.txt` + 三层变量替换 + `content_type` 多态 + 节点回填校验，站点差异集中配置化。代码依据：`config/loader/script_config.py`、`config/context/`、`config/backfill/`。
2. **资源四层强绑定 + 职责切分**：User↔Browser↔Fingerprint↔IP 强约束（前 3 硬）；Allocator 决定 proxy（业务）、Factory 创建 Context（执行）分离。代码依据：`resource/__init__.py` 包文档、`resource/resource_mapper.py` 7 约束、`browser_session_factory.py` docstring lines 14-17。
3. **页面生命周期归属清晰**：Runner 拥有 Factory，Processor 拥有 Page，PageNavigator 禁 `self.page` 单例。代码依据：各 Runner 的 `finally: browser_factory.close_all()`、`page_navigator.py` 注释 line 113。
4. **三层去重保障幂等**：页内 set → Redis → MongoDB（回填 Redis），断点续跑可靠。代码依据：`CateListProcessor._collect_cate_list_per_page`、`ContentRedis`/`ContentMongoDB`/`CateLevelRedis` 3 态。
5. **内容 schema 内容类型无关**：`ContentDataRecord.content: Dict[str, Any]` 承载动态业务 JSON，新内容类型不改 DB schema。代码依据：`data/model/data_record/content_data_record.py`。
6. **Parser 双层复用**：`SelectorParser`（原语）+ `FieldExtractor`（规则）被 CATE_LEVEL/CATE_LIST 复用。代码依据：`parser/field_extractor.py` 构造 `self.selector_parser = SelectorParser()`。
7. **能力分层清晰**：基础/业务/站点三级能力目录隔离，`mini_cate` docstring 明示 Java 移植且不可改算法。代码依据：`mini_cate/`、`site/<id>/login/`。
8. **指纹深度对齐**：从指纹 Excel 解析 platform/chromeVersion/screen，对齐 UA/Sec-Ch-Ua/Accept-Language/locale/timezone。代码依据：`browser_session_factory.py` 的 `_parse_*` 方法。
9. **日志统一路由**：`runner_base.create_logger` 根 logger 路由，叶子模块日志自动归到当前阶段文件。代码依据：`main/cli/runner_base.py` `_setup_root`。
10. **DB 职责正交**：MongoDB 真相源 + 自增序列；Redis 状态缓存 + 去重；Redis 缺失非致命。代码依据：`ContentMongoDB`/`AllSequenceMongoDB`/`ContentRedis`/`CateLevelRedis`/`CateListRedis`。

---

## 21. 当前架构问题与风险

1. **README 严重过时**：描述旧 `user.txt`/`type-script.txt`/CSV 布局，与实际 `site/<id>`/`item/<id>` 编号项目模式不符，会误导 GitHub 新贡献者。建议：基于本报告重写 README。
2. **CateListProcessor._collect_cate_list_per_page 职责过载**：单方法承担 10+ 步骤（URL 规范化/风控/加载/滚动/分页/解析/三层去重/序列/写库/状态），可读性与可维护性差。建议：拆分为 `UrlNormalizer`/`RiskGuard`/`DedupChain`/`WriteSink` 等子组件，Processor 仅编排。
3. **item_detail 与 cate 双项目根并行**：`ItemProjectConfigLoader`/`parse_item_detail_script_config`/`build_item_resource_context`/`ItemUserPoolLoader` 与 cate 侧并行存在，未充分复用，配置/资源/CLI 子树重复。docstring 解释了不复用原因（item 按 browser_index 查指纹），但仍存在重复维护成本。建议：评估抽象共同基类或共享 loader 入口。
4. **空占位文件/目录较多且未标注**：`database/postgresql/*`、`parser/item_detail/`、`resource/item_detail/`、`processor/content/`、`main/site/`、若干 `_v1`/`_v2`/`_old` 文件并存。新贡献者难以判断哪些是活跃代码。建议：在 CONTRIBUTING 或目录 README 标注状态，或移至 `DEL/`。
5. **遗留代码未清理**：`scrapy.cfg`、`scrapy-playwright`/`twisted` 依赖仍在 `requirements.txt`；`SelectorParser._get_attributes_old` 未用；`human_track_collector.py`/`slider_dragger.py`/`slider_dragger_cdp.py` 与 `UnifiedSliderDragger` 并存。建议：移除未用依赖与遗留实现。
6. **风控占位桩未实现**：`CateListProcessor.check_slider_captcha_dialog_show`/`check_slider_captcha_verified` 为 `return True` 占位（lines 1986-2000），`_handle_slider_show_next_action` 的 `AUTO` 模式未实现。生产环境遇 AUTO 会静默跳过。建议：补实现或显式抛错。
7. **ITEM_DETAIL 解析层缺失**：`parser/item_detail/` 为空，`ItemDetailProcessor` 仅导航滚动，无法产出数据。建议：补 `ItemDetailParser` 与 `ContentRecordBuilder` 的 item_detail 分支。
8. **DETAIL 业务仅配置未落地**：`config/model/detail/*` 存在但无 processor/parser，配置层与运行层脱节。建议：要么落地，要么在文档标注「planned」。
9. **`pyproject.toml` 无 `[project]` 元数据**：缺少版本/描述/作者/Python 版本要求，不利于 PyPI 化与 `pip install -e .`。建议：补 `[project]` 表。
10. **`constants/` 无 `__init__.py`**：包导入依赖命名空间包行为，跨 Python 版本可能不稳定。建议：补 `__init__.py`。
11. **`script_config._process_config_item` 前缀优先级硬编码**：分发表用 `if/elif` 链，新增段需改核心函数。建议：改为注册表（dict 映射前缀→loader 函数）。
12. **`cate_level_link.txt` 不持久化 `cate_ids_path`/`cate_links_path`**：需 `CateLevelLinkDataBackfill` 反推，存在数据不一致风险（index 与 link 不同步时）。建议：评估直接持久化或加一致性校验。

---

## 22. 可扩展性分析

扩展点与方式：

1. **新增站点**：在 `site/` 下建 `{main}-{sub}-{site}-{content}-{lang}/` 目录，写 `script/script.txt` + `user/user_pool.xlsx` + 可选 `login/*.py`，无需改框架核心。
2. **新增内容类型**：在 `config/model/cate_list/` 或 `config/model/detail/` 加 `*ArticleItem` 等模型；在 `ScriptConfig.get_*_item()` 加分支；在 `ContentRecordBuilder` 加 content 子 dict 构建分支。DB schema 不变（`content: Dict`）。
3. **新增业务类型**：在 `main/` 加入口；在 `processor/<biz>/` 加 Runner+Processor+子组件；在 `parser/<biz>/` 加 Parser；在 `config/loader/<biz>/` 加 loader（并在 `script_config._process_config_item` 注册前缀）。
4. **新增浏览器类型**：扩展 `BROWSER_TYPE_NAMES` + 池 Excel 模板 + `BrowserSessionFactory._get_browser_type_name`。
5. **新增资源层**：扩展 `UserConfig`/`PoolData`/`ResourceMapping` + `PoolLoader.load_*`。
6. **替换 DB**：`StructuredBatchFile._build_writer` 已支持多 output_type；新增实现 `MongoWriter` 接口的写器即可。

可扩展性评价：站点级与内容类型级扩展友好；业务类型级扩展需改 `script_config` 分发表（中等摩擦）；浏览器/资源层扩展需改多处常量与工厂（摩擦较大）。整体属「框架核心稳定 + 边界可扩展」形态。

---

## 23. 项目架构成熟度评价

- **配置驱动**：成熟。三层变量替换 + 节点回填 + 校验闭环。
- **资源隔离**：成熟。四层强绑定 + 反自动化 + 指纹深度对齐。
- **持久化与去重**：成熟（CATE_LIST）。三层去重 + 原子序列 + 分片集合 + 检查点。
- **业务编排**：CATE_LEVEL/CATE_LIST 成熟；ITEM_DETAIL 半成品（无解析）；DETAIL 仅配置。
- **风控**：基础能力齐全（图像匹配/轨迹/熔断），但 AUTO 模式与占位桩未实现。
- **工程化**：中等。`pyproject.toml` 不完整；README 过时；空占位与遗留代码多；无测试（`test/`/`tests/` 已排除但存在）；无 CI 配置。
- **文档**：弱。仅有 `docs/Python-PlayWright-Web-项目总结.md` 与过时 README，缺架构文档与贡献指南。

总体：**核心采集能力成熟，外围工程化与文档化不足**。适合作为内部框架演进为开源项目，但需先补文档、清理遗留、补元数据。

---

## 24. GitHub 开源项目视角下的架构总结

开源视角优势：

- 配置驱动 + 站点隔离，新站点接入门槛低，易吸引站点贡献。
- 能力分层清晰，基础能力（图像匹配/轨迹/类目归一）可作为独立子模块被复用。
- 双 DB 正交设计，幂等性强，适合长时爬取。

开源视角需补：

1. **README 重写**：基于本报告改写，含安装、env 配置、`pool/*.xlsx` 模板、`script.txt` 语法、启动命令、`site/<id>` 接入流程。
2. **LICENSE**：当前未见，开源前必须添加。
3. **CONTRIBUTING / ARCHITECTURE.md**：指向本报告作为架构入口。
4. **CI**：补 ruff lint + 基础 import 冒烟（当前无 `.github/`）。
5. **`pyproject.toml` `[project]`**：name/version/description/requires-python/authors。
6. **敏感信息清理**：`env/*.yaml` 含 Redis/Mongo 连接（已在 `.gitignore`），但 `site/<id>/user/user_pool.xlsx` 可能含账号，需确认脱敏策略。
7. **遗留清理**：移除 `scrapy.cfg`、Scrapy 依赖或显式说明遗留。
8. **示例站点**：保留 1-2 个示例 `site/`（如 `1001-001 dangdang`）作为可运行 demo。

---

## 25. 后续《核心模块详细设计分析》的建议范围

按优先级建议：

1. `config/loader/script_config.py` —— 配置分发与校验机制详设（含三层变量替换、前缀优先级、回填、`content_type` 多态）。
2. `resource/` —— 四层绑定约束矩阵与 BrowserContext 创建详设（含指纹对齐、代理选择、无用户模式）。
3. `processor/cate_list/cate_list_processor.py` —— CATE_LIST 编排详设（含分页、三层去重、序列分配、风控处置、状态机）。
4. `processor/cate_level/cate_level_collector.py` + `cate_level_link_builder.py` —— 类目树遍历与链接构建详设。
5. `mini_cate/cate_level_index_normalizer.py` —— 类目归一算法详设（Java 移植，需算法注释）。
6. `database/{mongodb,redis}/` —— 双 DB 状态机与去重链详设（含 `ContentMongoDB` 分片路由、`CateLevelRedis` 3 态、`AllSequenceMongoDB` 原子分配）。
7. `parser/cate_list/cate_list_parser.py` + `field_extractor` + `selector_parser` —— 节点抽取与 `_COMBINE` 详设。
8. `mouse_tracks/unified_slider_dragger_v2.py` + `image_match/shape/contour_v3.py` —— 滑块自动化详设。

---

## 26. 架构事实确认

### 26.1 已通过代码确认

- 项目基于 Playwright + `asyncio`，非 Scrapy 驱动（`docs/Python-PlayWright-Web-项目总结.md` + `requirements.txt` + 各 Runner `asyncio.run` + `BrowserSessionFactory` 使用 `playwright.async_api.async_playwright`）。
- 三条业务管线 CATE_LEVEL/CATE_LIST/ITEM_DETAIL 各有独立 entry/Runner/Processor（`main/cate_level.py`、`main/cate_list.py`、`main/item_detail/item_detail.py` + 对应 `processor/<biz>/`）。
- Processor 自述为「流程编排层」（`processor/cate_level/cate_level_processor.py` docstring lines 58-77）。
- 资源四层强绑定（`resource/__init__.py` 包文档 + `resource_mapper.py` 7 约束 + `resource_allocator.py` + `browser_session_factory.py`）。
- 双项目根 `site/` 与 `item/`（`ProjectConfigLoader` vs `ItemProjectConfigLoader`；`parse_script_config` vs `parse_item_detail_script_config`；`ResourceAllocator.allocate` vs `build_item_resource_context`）。
- 配置三层变量替换 `@[const]`/`@{var}`/`${PRO_*}`（`config/context/`）。
- `ScriptConfig` 聚合 16 个 `*Item` 模型，`content_type` 驱动 product/article 分支（`config/loader/script_config.py` + `config/model/`）。
- MongoDB 按**数据库名**隔离，Redis 按 **head_key 前缀**隔离（`MongoDBClient`/`RedisClient` docstring + `MongoDBUtil.__init__`/`RedisUtil.make_key`）。
- CATE_LIST 三层去重：页内 set → `ContentRedis` → `ContentMongoDB`（`CateListProcessor._collect_cate_list_per_page`）。
- `ContentMongoDB` 按 md5 末 N 位分片到 `CONTENT-{hash_suffix}` 集合（`content_mongodb.py._build_collection_name`）。
- `AllSequenceMongoDB.allocate_id_range` 用 `find_one_and_update` + `$inc` 原子分配（`all_sequence_mongodb.py`）。
- `CateLevelRedis` 3 态状态机：缺失/`{page_url}`/`END`（`cate_level_redis.py` + `STATUS_COMPLETED_END`）。
- `PageNavigator` 禁 `self.page` 单例（`page_navigator.py` 注释 line 113）。
- Runner 拥有 `BrowserSessionFactory`，Processor 拥有 Page（各 Runner `finally: browser_factory.close_all()`）。
- `mini_cate` 是 Java 移植算法（`mini_cate/cate_level_index_normalizer.py` docstring + `mini_text/__init__.py` 包文档）。
- 空占位：`database/postgresql/*`、`parser/item_detail/`、`resource/item_detail/`、`processor/content/`、`main/site/`、`export/cate_level/cate_level_link_writer.py`、`image_match/edge/canny.py`、`image_match/feature/orb.py`、`mini_cate/cate_index.py`（文件系统确认）。
- 预留未接入：`processor/cate_level/cate_level_validator.py`、`cate_level_stats.py`、`cate_level_item.create_item()`（各自 docstring 自述）。
- ITEM_DETAIL 无解析层（`parser/item_detail/` 空 + `ItemDetailProcessor` 仅 `page_navigator.load` + `scroll_to_load_more`）。
- Network Response 拦截当前为 config-only 非功能：`ItemDetailScriptConfig` 4 字段（`network_response_intercept_enable`/`_name`/`_regex`/`_json_nodes`）经 `item_detail_loader._process_item_detail_key` 解析进模型，但全代码库无任何消费方（`page.route`/`context.route`/`on("response")`/`on("request")`/`response.body`/`response.json` 在 processor/page/resource/config/main 中零命中）；loader 校验函数注释（`item_detail_loader.py:240-242`）自述拦截业务延后到「Processor/Parser 阶段」；`docs/Python-PlayWright-Web-项目总结.md:134` 佐证。
- DETAIL 仅配置模型（`config/model/detail/*` 存在，无 `processor/detail/`/`parser/detail/`）。
- 风控 AUTO 模式未实现 + `check_slider_captcha_dialog_show`/`check_slider_captcha_verified` 为 `return True` 占位（`cate_list_processor.py` lines 1986-2000）。
- README 过时（`README.md` 描述 `user.txt`/`type-script.txt`/CSV，与 `site/<id>` 模式不符）。
- `pyproject.toml` 仅 ruff 配置无 `[project]`（文件确认）。
- `constants/` 无 `__init__.py`（文件系统确认）。
- PostgreSQL 空文件占位（文件系统确认）。

### 26.2 根据代码高度推断

- 「通用爬虫框架 + 具体站点业务」架构已形成：框架核心目录均不引用具体站点，站点差异集中在 `site/<id>/script.txt` + `site/<id>/login/*.py`。推断依据：多个 `processor/`/`parser/`/`page/`/`resource/` 模块均接受 `script_config`/`resource_context` 参数，不硬编码站点。
- `ContentDataRecord.content: Dict[str, Any]` 的设计意图是为内容类型扩展留口子：`ContentRecordBuilder` 仅在 `item.product is not None` 时填 `content.product`，结构上预留 article 与未来类型。推断依据：字段类型为开放 `Dict` 而非封闭 dataclass。
- `request/RetryManager` 与 `PageNavigator.load` 的重试边界划分是有意为之：docstring 明确警告双重重试致 9 次，推断 RetryManager 定位为业务流重试。
- item_detail 不复用 `ResourceAllocator` 的根本原因是查询键不同（`browser_index` vs `fingerprint_index`）：`build_item_resource_context` docstring 与代码体现此差异，推断为刻意设计而非遗漏。
- Network Response 拦截的设计意图（master enable + 响应名标签 + URL 正则 + JSON 节点回退字符串 + 正则优先于 JSON_NODES）来自 `item_detail_loader.py:240-242` 注释，属「根据代码高度推断」的架构意图；落地形态（`page.route` vs `page.on("response")` 两方案）尚未在代码中确定，仅文档先行记录（见 §11.3.2）。

### 26.3 当前无法确认

- `ects_0..ects_4`（`ContentDataRecord` 的 5 个客户导出计数器）的具体业务含义与消费方：代码中未见写入逻辑，仅作为字段存在。
- `PRO_COMMON_MAIN_OWNER` 等 `program_vars` 的运行期消费链路：`combine-link-pending.md` 记忆条目提示「`_COMBINE` 已接入加载层，运行期消费与 `PRO_COMMON_MAIN_OWNER` 变量待下一步」，即部分 `_COMBINE` 运行期消费尚未完成。
- `network_idle_enabled`/`network_idle_timeout` 在生产 `script.txt` 中的实际配置值（未读站点 script.txt 内容，仅在代码层确认参数存在）。
- `playwright-stealth` 依赖在运行期是否实际生效：`BrowserSessionFactory` 用指纹 Excel 注入，未直接引用 `playwright-stealth` API，依赖可能为遗留或间接使用。
- `mini_cate` 算法的 Java 原始版本与 Python 移植的等价性（需算法级对拍，超出架构分析范围）。
- 各 `site/<id>/login/*.py` 的具体站点逻辑差异（站点级代码，非框架核心）。

---

> 报告生成依据：3 个并行 Explore 子代理对项目实际源码的只读扫描（已排除 `.git`、`.idea`、`.ruff_cache`、`backup`、`test`、`tests`、`DEL`、`fingerprint_work`）。所有类名/函数名/文件路径均可在仓库中检索命中。本报告不修改任何源代码。
