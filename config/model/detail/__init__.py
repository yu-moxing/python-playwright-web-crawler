"""
详情层(DETAIL)模型包

统一导出详情配置相关数据结构。
"""

from .detail_article_item import DetailArticleItem
from .detail_product_item import DetailProductItem
from .detail_unit import DetailUnitItem

__all__ = [
    "DetailArticleItem",
    "DetailProductItem",
    "DetailUnitItem",
]
