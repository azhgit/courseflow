#!/usr/bin/env bash
set -euo pipefail

echo "[zeabur-start] preparing data directories"
mkdir -p data/chroma

echo "[zeabur-start] initializing sqlite schema"
python scripts/init_db.py

CHROMA_SQLITE="data/chroma/chroma.sqlite3"
CHROMA_INDEX_COUNT=$(find data/chroma -maxdepth 2 -name "header.bin" | wc -l | tr -d ' ')

if [[ ! -f "$CHROMA_SQLITE" || "$CHROMA_INDEX_COUNT" -eq 0 ]]; then
  echo "[zeabur-start] chroma data missing, running docs ingestion"
  python scripts/ingest_docs.py
else
  echo "[zeabur-start] chroma data detected, skip ingestion"
fi

echo "[zeabur-start] starting API on port ${PORT}"
exec uvicorn courseflow.api.main:app --host 0.0.0.0 --port "${PORT}"
