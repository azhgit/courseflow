"""Database initialization script.

Creates the SQLite database schema with proper indexes for query metadata.
Run this script once during setup: python scripts/init_db.py
"""

import asyncio
import os

from courseflow.config import settings
from courseflow.infrastructure.repositories.query_repo import SQLiteQueryRepository


async def init_database() -> None:
    """Initialize the SQLite database with schema and indexes."""

    db_path = settings.database_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Initializing database at: {db_path}")

    repo = SQLiteQueryRepository(db_path=db_path)
    await repo.initialize()

    print("✓ Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_database())
