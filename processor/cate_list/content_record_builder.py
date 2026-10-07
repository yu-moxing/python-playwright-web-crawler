"""将 CATE_LIST 解析结果转换为数据库使用的 ContentDataRecord。"""

from __future__ import annotations

import hashlib
import json
import re
import time

from data.model.data_record.content_data_record import (
    ContentCommonData,
    ContentDataRecord,
)


class ContentRecordBuilder:
    """负责类型转换和最终数据记录组装，不负责 DOM 内容提取。"""

    def build_from_cate_list(self, item, *, page_url: str) -> ContentDataRecord:
        """将 CATE_LIST 解析项组装为 ContentDataRecord。"""

        # 提取公共字段
        source = item.common

        common = ContentCommonData(
            link=source.link,
            id=item.id,
            main_title=source.main_title,
            sub_title=source.sub_title,
            main_image=source.main_image,
            sub_images=self._json_list(source.sub_images),
            view_count=self._integer(source.view_count),
            favorite_count=self._integer(source.favorite_count),
            comment_count=self._integer(source.comment_count),
            main_owner_name=source.main_owner_name,
            main_owner_id=source.main_owner_id,
            main_owner_link=source.main_owner_link,
            sub_owner_name=source.sub_owner_name,
            sub_owner_id=source.sub_owner_id,
            sub_owner_link=source.sub_owner_link,
        )

        # tags 统一转换为列表
        content = {
            "tags": self._json_list(item.tags),
        }

        # 商品数据存在时，转换并加入 product
        if item.product is not None:
            product = item.product

            content["product"] = {
                "price": self._number(product.price),
                "price_currency": product.price_currency,
                "price_text": product.price_text,
                "sales_count": self._integer(product.sales_count),
                "sales_text": product.sales_text,
            }

        # 组装最终数据库记录
        return ContentDataRecord(
            _id=self._md5(item.id),
            raw_id=item.raw_id,
            raw_url=source.link,
            crawl_url=page_url,
            # Unix 时间戳，单位是秒
            crawl_time=int(time.time()),
            common=common,
            content=content,
        )

    @staticmethod
    def _json_list(value: str) -> list[str]:
        """将 JSON 字符串转换为字符串列表。"""

        if not value:
            return []

        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            # 非 JSON 数据直接作为单个字符串处理
            return [str(value)]

        # 只有 JSON 数组才转换为列表
        return [str(item) for item in decoded] if isinstance(decoded, list) else []

    @staticmethod
    def _integer(value) -> int:
        """从文本中提取整数，支持逗号分隔格式。"""

        match = re.search(r"-?[\d,]+", str(value))

        # 未提取到数字时返回 0
        return int(match.group(0).replace(",", "")) if match else 0

    @staticmethod
    def _number(value) -> float:
        """从文本中提取浮点数，支持逗号分隔格式。"""

        match = re.search(r"-?[\d,]+(?:\.\d+)?", str(value))

        # 未提取到数字时返回 0.0
        return float(match.group(0).replace(",", "")) if match else 0.0

    @staticmethod
    def _md5(value: str) -> str:
        """生成字符串的 MD5 十六进制摘要。"""

        return hashlib.md5(value.encode("utf-8")).hexdigest()
