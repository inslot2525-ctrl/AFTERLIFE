"""Feature registry. A Sunset MR removes the feature's import and its MODULES entry."""

from app.features import (
    admin_reindex,
    books_v2,
    embed_widget,
    wrapped,
)

MODULES = [
    books_v2,
    wrapped,
    embed_widget,
    admin_reindex,
]

FEATURES = [module.FEATURE for module in MODULES]
