"""E2E test for complete golden dataset evaluation run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from courseflow.application.evaluation_service import EvaluationService
from courseflow.config import settings
from courseflow.domain.models import Answer, Document, DocumentMetadata, Query, SearchResult
from courseflow.infrastructure.repositories.evaluation_repo import EvaluationRepository


class _DeterministicRagService:
    def __init__(self, dataset_path: Path):
        with dataset_path.open(encoding="utf-8") as file:
            pairs = json.load(file)["pairs"]
        self._pairs = {pair["question"]: pair for pair in pairs}

    async def answer_query(self, query: Query, subject: str | None = None):  # noqa: ARG002
        pair = self._pairs[query.text]
        sources: list[SearchResult] = []
        for idx, chunk_id in enumerate(pair["expected_chunks"]):
            doc = Document(
                id=chunk_id,
                content=("context " * 20).strip(),
                metadata=DocumentMetadata(
                    source="golden.md",
                    subject=pair.get("subject", "general"),
                    chunk_index=idx,
                    total_chunks=len(pair["expected_chunks"]),
                ),
            )
            sources.append(SearchResult(document=doc, similarity_score=0.95))

        answer_text = f"{pair['expected_answer']} {' '.join(pair['keywords'])}"
        return Answer(query_id=query.id, answer_text=answer_text, sources=sources, latency_ms=5)


@pytest.mark.asyncio
async def test_full_evaluation_run_executes_all_15_pairs(tmp_path) -> None:
    repo = EvaluationRepository(db_path=tmp_path / "eval.db")
    await repo.initialize()

    service = EvaluationService(
        repository=repo,
        rag_service=_DeterministicRagService(Path(settings.eval_golden_dataset_path)),
        golden_dataset_path=settings.eval_golden_dataset_path,
    )

    run = await service.run_evaluation()

    assert run.status.value == "completed"
    assert run.metrics is not None
    assert run.metrics.tests_passed + run.metrics.tests_failed == 15
    assert run.metrics.retrieval_precision_avg == pytest.approx(1.0)
    assert run.metrics.keyword_match_avg == pytest.approx(1.0)

    persisted = await repo.get_run_by_id(run.run_id)
    assert persisted is not None
    assert persisted.status.value == "completed"
