-- Migration 002: Add Document Ingestion Tables
-- Feature: Document Ingestion and Knowledge Base Management
-- Created: 2025-02-12
-- Branch: 002-document-ingestion

-- This migration adds three new tables for document ingestion:
-- 1. subjects: Subject categories for organizing documents
-- 2. documents: Uploaded document metadata
-- 3. chunks: Semantic chunks of documents for retrieval

-- =============================================================================
-- TABLE: subjects
-- =============================================================================
-- Represents subject categories/areas (e.g., biology, programming, history)
-- Predefined list prevents inconsistencies (e.g., "bio" vs "biology")

CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,                    -- UUID v4 or slug-based ID
    name TEXT UNIQUE NOT NULL,              -- Lowercase slug (e.g., "biology")
    display_name TEXT NOT NULL,             -- Human-readable (e.g., "Biology")
    created_at TEXT NOT NULL                -- ISO 8601 timestamp
);

-- Index for fast subject lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_name ON subjects(name);

-- =============================================================================
-- TABLE: documents
-- =============================================================================
-- Represents uploaded educational documents with metadata

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,                    -- UUID v4
    filename TEXT NOT NULL,                 -- Original filename
    subject TEXT NOT NULL,                  -- Foreign key to subjects.name
    content_hash TEXT UNIQUE NOT NULL,      -- SHA-256 hex (64 chars) for duplicate detection
    file_format TEXT NOT NULL,              -- "markdown" | "txt" | "pdf"
    file_size_bytes INTEGER NOT NULL,       -- Original file size
    chunks_created INTEGER NOT NULL,        -- Number of chunks generated
    ingestion_time_ms INTEGER NOT NULL,     -- Total processing time
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    
    FOREIGN KEY (subject) REFERENCES subjects(name) ON DELETE RESTRICT
);

-- Indexes for performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_subject ON documents(subject);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- =============================================================================
-- TABLE: chunks
-- =============================================================================
-- Represents semantic segments of documents optimized for retrieval
-- Embeddings are stored in ChromaDB (vector store), not SQLite

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,                    -- UUID v4
    document_id TEXT NOT NULL,              -- Foreign key to documents.id
    chunk_index INTEGER NOT NULL,           -- Sequential position (0-based)
    text TEXT NOT NULL,                     -- Chunk content (300-500 tokens typical)
    token_count INTEGER NOT NULL,           -- Actual token count
    source_filename TEXT NOT NULL,          -- Denormalized from document for query performance
    subject TEXT NOT NULL,                  -- Denormalized from document for filtering
    
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE (document_id, chunk_index)       -- No duplicate indexes per document
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_subject ON chunks(subject);

-- =============================================================================
-- SEED DATA: Pre-populate subjects for v1
-- =============================================================================
-- Insert default subjects to prevent free-form entry inconsistencies

INSERT OR IGNORE INTO subjects (id, name, display_name, created_at) VALUES
    ('subj_bio', 'biology', 'Biology', datetime('now')),
    ('subj_prog', 'programming', 'Programming', datetime('now')),
    ('subj_hist', 'history', 'History', datetime('now')),
    ('subj_math', 'mathematics', 'Mathematics', datetime('now')),
    ('subj_gen', 'general', 'General', datetime('now'));

-- =============================================================================
-- VALIDATION QUERIES (for manual verification)
-- =============================================================================
-- Run these after migration to verify schema:
-- 
-- SELECT name FROM sqlite_master WHERE type='table' AND name IN ('subjects', 'documents', 'chunks');
-- SELECT COUNT(*) FROM subjects; -- Should return 5
-- SELECT * FROM subjects ORDER BY name;
-- PRAGMA table_info(documents);
-- PRAGMA foreign_key_list(documents);
-- PRAGMA foreign_key_list(chunks);
