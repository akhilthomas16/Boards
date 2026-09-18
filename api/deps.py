"""
Shared dependencies — pagination helper.
"""


def paginate(queryset, page: int = 1, page_size: int = 20):
    """Paginate a Django queryset."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = queryset.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": items,
    }
