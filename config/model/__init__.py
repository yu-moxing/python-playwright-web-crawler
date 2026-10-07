"""
配置模型包

统一导出各层配置数据结构。

    DetailArticleItem / DetailProductItem / DetailUnitItem  ← config.model.detail

供 config.loader 通过父包快捷导入：

    from config.model import DetailUnitItem
"""

from .detail import DetailArticleItem, DetailProductItem, DetailUnitItem

__all__ = [
    "DetailArticleItem",
    "DetailProductItem",
    "DetailUnitItem",
]
