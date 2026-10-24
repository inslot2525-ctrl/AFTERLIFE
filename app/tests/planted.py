"""The six features Shelf was planted with, frozen for tests.

Tests that need "a legacy API", "a never-called importer" and so on use this
list, not app.features.FEATURES: AFTERLIFE deletes features from the live
registry, and a test that reads it would break on every retirement.
"""

from app.registry import Feature

PLANTED_FEATURES = [
    Feature("books_v1", "/v1/books", "app/features/books_v1.py", "shelf-api", "2023-02-14",
            "Legacy flat books list, replaced by /v2/books"),
    Feature("books_v2", "/v2/books", "app/features/books_v2.py", "shelf-api", "2024-05-02",
            "Paginated books list with status filter"),
    Feature("import_goodreads", "/import/goodreads", "app/features/import_goodreads.py", "shelf-growth",
            "2023-06-30", "Imports a Goodreads library export"),
    Feature("wrapped", "/wrapped/{year}", "app/features/wrapped.py", "shelf-growth", "2023-11-20",
            "Year-in-review summary of finished books"),
    Feature("embed_widget", "/embed/widget", "app/features/embed_widget.py", "shelf-partners", "2024-01-09",
            "HTML card partners embed to show what a reader is reading"),
    Feature("admin_reindex", "/admin/reindex", "app/features/admin_reindex.py", "shelf-platform", "2023-02-14",
            "Rebuilds the search index; used during incidents"),
]
