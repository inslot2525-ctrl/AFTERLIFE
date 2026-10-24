"""Shelf's reading list. In-memory: the app is a prop for the lifecycle demo."""

BOOKS: list[dict] = [
    {"id": 1, "title": "The Pragmatic Programmer", "author": "David Thomas", "status": "read", "finished": "2025-12-03"},
    {"id": 2, "title": "Accelerate", "author": "Nicole Forsgren", "status": "read", "finished": "2025-08-19"},
    {"id": 3, "title": "Working in Public", "author": "Nadia Eghbal", "status": "reading", "finished": None},
    {"id": 4, "title": "Team Topologies", "author": "Matthew Skelton", "status": "to-read", "finished": None},
    {"id": 5, "title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "status": "read", "finished": "2026-03-11"},
]
