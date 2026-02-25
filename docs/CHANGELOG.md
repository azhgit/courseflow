# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-02-25

### Added

#### 001-rag-qa
- Core RAG (Retrieval-Augmented Generation) system foundation
- Vector similarity retrieval using ChromaDB
- AI-powered answer generation with Google Gemini API
- Source citation and document attribution
- <2s P95 query latency optimization

#### 002-doc-ingestion
- Document loading and ingestion pipeline
- Batch embedding generation
- Automatic vector database synchronization
- Support for multiple document formats (Markdown, PDF)

#### 003-conversation-context
- Multi-turn conversation support
- Conversation history persistence
- Context-aware query understanding
- Session management

#### 004-streaming-responses
- Server-Sent Events (SSE) streaming endpoint: `POST /api/v1/query/stream`
- Incremental answer delivery with real-time chunks
- Structured SSE event types: `chunk`, `sources`, `done`, `error`
- Streaming error handlers for edge cases
- Conversation persistence with chunk reconstruction
- `/api/v1/metrics` endpoint for streaming metrics

#### 005-production-polish
- Rate limiting (configurable per user/IP)
- Token usage tracking and monitoring
- Structured logging across all services
- Health check endpoints and readiness probes
- Error handling and graceful degradation

#### 006-demo-protection
- Authentication and authorization layer
- API key management
- Role-based access control (RBAC)
- Request validation and sanitization

#### 007-react-frontend-mvp
- Interactive web frontend built with React
- Real-time query interface
- Conversation history UI
- Document source visualization

#### 008-zeabur-deployment
- Container configuration (Dockerfile)
- Zeabur deployment setup
- Environment variable management
- CI/CD pipeline automation

#### 009-wikipedia-scraper
- Automated Wikipedia web scraper
- MediaWiki API integration
- Rate limiting and retry mechanisms
- HTML cleaning and text normalization
- Batch document processing
- ChromaDB vector storage integration
- CLI tool for scraping management

### Fixed

- Improved error handling across all services
- Fixed edge cases in streaming response handling
- Optimized embedding generation performance
- Fixed ChromaDB connection reliability issues

### Changed

- Upgraded dependencies to latest stable versions
- Enhanced logging verbosity and clarity
- Improved API response consistency
- Refactored storage layer for better maintainability

### Security

- Added input validation for all API endpoints
- Implemented rate limiting to prevent abuse
- Secure API key management in environment variables

---

For detailed information on each feature, see the [docs/features/](docs/features/) directory.

