from dataclasses import dataclass


@dataclass
class CateLevelIndexDataItem:
    cate_ids_path: list[int]
    cate_names_path: list[str]
    cate_level_index: int
