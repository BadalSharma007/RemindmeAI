"""Shared fixtures and environment setup for unit tests.

Sets the minimum required environment variables so that
``app.config.Settings`` can be instantiated without a real ``.env`` file.
All values are fake — no real services are contacted.
"""
from __future__ import annotations

import os

# Set required env vars BEFORE any app module is imported.
# These run at collection time, so they must be set at module level.
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long-xx")
os.environ.setdefault("FERNET_KEY", "C5sBiHUWHMimoBQwt3HxbRN3kFpCQlMn3FQ2fMiQxQM=")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
