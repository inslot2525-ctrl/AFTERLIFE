"""Feature registry. A Sunset MR removes the feature's import and its MODULES entry."""

from app.features import (
    admin_reindex,
    books_v2,
    embed_widget,
    import_goodreads,
    wrapped,
)

MODULES = [
    books_v2,
    import_goodreads,
    wrapped,
    embed_widget,
    admin_reindex,
]

FEATURES = [module.FEATURE for module in MODULES]
