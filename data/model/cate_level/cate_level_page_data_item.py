from dataclasses import dataclass

from data.model.cate_level.cate_level_link_data_item import (
    CateLevelLinkDataItem,
)


@dataclass
class CateLevelPageDataItem:
    cate_level_link: CateLevelLinkDataItem
    page_urls: list[str]
    # page_ids: list[str]
    page_set: set[str]
    page_url_index: int
