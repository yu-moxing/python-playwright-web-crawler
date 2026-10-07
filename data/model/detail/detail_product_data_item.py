"""
详情（Detail）页面 Product 数据项

职责：

    - 保存详情（Detail）页面采集得到的商品专有字段
    - 对应 DETAIL_PRODUCT_* 配置
    - 作为 Detail Parser / Processor 阶段的商品业务数据结构
    - 不负责数据库持久化

说明：

    DetailProductDataItem 表示从详情（Detail）页面采集得到的、
    只有商品类型才具有的业务字段。

    商品、文章共有字段由：

        DetailCommonDataItem

    负责。

    本数据项只对应：

        DETAIL_PRODUCT_*

    分类列表（CL）页面商品专有字段对应：

        CateListProductDataItem

    因此，CL Product 和 Detail Product 虽然存在相同的价格、
    销量字段，但由于采集来源不同，仍然分别定义 DataItem。

    最终这些数据可以汇聚到：

        ContentDataRecord.content
"""

from dataclasses import dataclass


@dataclass
class DetailProductDataItem:
    """
    详情（Detail）页面 Product 数据项。

    对应配置：

        DETAIL_PRODUCT_PRICE_*
        DETAIL_PRODUCT_PRICE_CURRENCY_*
        DETAIL_PRODUCT_PRICE_TEXT_*

        DETAIL_PRODUCT_SALES_COUNT_*
        DETAIL_PRODUCT_SALES_TEXT_*

        DETAIL_PRODUCT_SKU_COLOR_NAMES_*
        DETAIL_PRODUCT_SKU_COLOR_LINKS_*

        DETAIL_PRODUCT_SKU_TYPE_NAMES_*
        DETAIL_PRODUCT_SKU_TYPE_LINKS_*

        DETAIL_PRODUCT_SKU_PLAN_NAMES_*
        DETAIL_PRODUCT_SKU_PLAN_LINKS_*
    """

    # =========================================================
    # 价格
    # =========================================================

    # 价格数值
    price: float = 0.0

    # 价格货币单位，例如：
    # USD、CNY、TWD
    price_currency: str = ""

    # 价格原始文本，例如：
    # "$99.99"
    price_text: str = ""

    # =========================================================
    # 销量
    # =========================================================

    # 销量数值
    sales_count: int = 0

    # 销量原始文本，例如：
    # "5万+"
    # "2千"
    sales_text: str = ""

    # =========================================================
    # SKU - 颜色
    # =========================================================

    # SKU 颜色名列表（JSON 字符串）
    sku_color_names: str = ""

    # SKU 颜色链接列表（JSON 字符串）
    sku_color_links: str = ""

    # =========================================================
    # SKU - 类型
    # =========================================================

    # SKU 类型名列表（JSON 字符串）
    sku_type_names: str = ""

    # SKU 类型链接列表（JSON 字符串）
    sku_type_links: str = ""

    # =========================================================
    # SKU - 套餐
    # =========================================================

    # SKU 组合名列表（JSON 字符串）
    sku_plan_names: str = ""

    # SKU 组合链接列表（JSON 字符串）
    sku_plan_links: str = ""
