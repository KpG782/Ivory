"""Global pytest configuration.

Sets SESSIONS_BACKEND=memory before any module is imported so the
existing test suite stays hermetic — no SQLite file is created, and
reset_all() replaces the MemorySaver instance (effectively clearing
all sessions) exactly as before.

Tests that explicitly want the sqlite backend override this with
monkeypatch.setenv("SESSIONS_BACKEND", "sqlite").
"""
import os

os.environ.setdefault("SESSIONS_BACKEND", "memory")
