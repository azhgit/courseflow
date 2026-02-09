"""Database initialization script.

Creates the SQLite database schema with proper indexes for query metadata.
Run this script once during setup: python scripts/init_db.py
"""

import asyncio
import os
import sqlite3
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import aiosqlite

from src.courseflow.config import settings


async def init_database() -> None:
    """Initialize the SQLite database with schema and indexes."""
    
    # Extract database path from URL
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        # Create queries table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                answer_text TEXT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                embedding_tokens INTEGER,
                generation_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms INTEGER NOT NULL,
                retrieval_count INTEGER,
                top_similarity_score REAL,
                error_type TEXT
            )
        """)
        
        # Create indexes for performance
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_timestamp
            ON queries(timestamp)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_error_type
            ON queries(error_type)
            WHERE error_type IS NOT NULL
        """)
        
        await db.commit()
        
        # Verify table creation
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='queries'"
        ) as cursor:
            result = await cursor.fetchone()
            if result:
                print("✓ Table 'queries' created successfully")
            else:
                print("✗ Failed to create table 'queries'")
                return
        
        # Verify indexes
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='queries'"
        ) as cursor:
            indexes = await cursor.fetchall()
            print(f"✓ Created {len(indexes)} indexes: {[idx[0] for idx in indexes]}")
    
    print(f"\n✓ Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_database())
