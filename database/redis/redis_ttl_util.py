def get_sort_field_ttl(
    sort_field: str,
    sort_fields_ttl: dict[str, int],
) -> int | None:
    return sort_fields_ttl.get(sort_field)
