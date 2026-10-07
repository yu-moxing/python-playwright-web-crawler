from dataclasses import dataclass


@dataclass
class CateLevelLinkDataItem:
    url: str
    level: int
    limit_cate_level_0_id: int
    cate_name: str
    cate_names_path: list[str]
    cate_ids_path: list[int]
    cate_links_path: list[str]
