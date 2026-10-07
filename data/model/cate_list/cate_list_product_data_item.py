"""
分类列表（CL）页面 Product 数据项

职责：

    - 保存分类列表（CL）页面采集得到的商品专有字段
    - 对应 CATE_LIST_PRODUCT_* 配置
    - 作为 CL Parser / Processor 阶段的商品业务数据结构
    - 不负责数据库持久化

说明：

    CateListProductDataItem 表示从分类列表（CL）页面采集得到的、
    只有商品类型才具有的业务字段。

    商品、文章共有字段由：

        CateListCommonDataItem

    负责。

    本数据项只对应：

        CATE_LIST_PRODUCT_*

    最终可以与：

        CateListCommonDataItem

    一起组成分类列表页面采集到的一条商品数据。
"""

from dataclasses import dataclass


@dataclass
class CateListProductDataItem:
    """
    分类列表（CL）页面 Product 数据项。

    对应配置：

        CATE_LIST_PRODUCT_PRICE_*
        CATE_LIST_PRODUCT_PRICE_CURRENCY_*
        CATE_LIST_PRODUCT_PRICE_TEXT_*

        CATE_LIST_PRODUCT_SALES_COUNT_*
        CATE_LIST_PRODUCT_SALES_TEXT_*
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
