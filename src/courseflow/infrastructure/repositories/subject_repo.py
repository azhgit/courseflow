"""SQLite subject repository implementing SubjectRepositoryPort."""

import sqlite3

import aiosqlite

from courseflow.config import settings
from courseflow.domain.exceptions import ServiceUnavailableError
from courseflow.domain.models import Subject
from courseflow.domain.ports import SubjectRepositoryPort


class SQLiteSubjectRepository(SubjectRepositoryPort):
    """Async SQLite repository for predefined subjects."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or settings.database_path

    async def initialize(self) -> None:
        """Ensure subjects table exists with default subjects."""
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS subjects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # Insert default subjects if table is empty
                await db.execute(
                    "INSERT OR IGNORE INTO subjects (name, display_name) VALUES (?, ?)",
                    ("programming", "Programming"),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO subjects (name, display_name) VALUES (?, ?)",
                    ("biology", "Biology"),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO subjects (name, display_name) VALUES (?, ?)",
                    ("history", "History"),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO subjects (name, display_name) VALUES (?, ?)",
                    ("general", "General"),
                )
                await db.commit()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to initialize subjects table: {str(e)}") from e

    async def find_all(self) -> list[Subject]:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    "SELECT id, name, display_name, created_at FROM subjects ORDER BY name"
                ) as cur:
                    rows = await cur.fetchall()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to list subjects: {str(e)}") from e

        return [
            Subject(id=row[0], name=row[1], display_name=row[2], created_at=row[3]) for row in rows
        ]

    async def find_by_name(self, name: str) -> Subject | None:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    "SELECT id, name, display_name, created_at FROM subjects WHERE name = ?",
                    (name,),
                ) as cur:
                    row = await cur.fetchone()
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to read subject: {str(e)}") from e

        if not row:
            return None
        return Subject(id=row[0], name=row[1], display_name=row[2], created_at=row[3])

    async def subject_exists(self, name: str) -> bool:
        try:
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute("SELECT 1 FROM subjects WHERE name = ? LIMIT 1", (name,)) as cur:
                    row = await cur.fetchone()
                    return row is not None
        except sqlite3.Error as e:
            raise ServiceUnavailableError(f"Failed to check subject existence: {str(e)}") from e

