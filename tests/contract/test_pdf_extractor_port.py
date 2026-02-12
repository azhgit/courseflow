"""Contract test for PDFExtractorPort implementations (T071)."""

from __future__ import annotations

import pytest

from courseflow.domain.exceptions import InvalidFileFormatError
from courseflow.domain.ports import PDFExtractorPort
from courseflow.infrastructure.document_processing.pymupdf_extractor import PyMuPDFExtractor


def _assert_pdf_extractor_contract(extractor: PDFExtractorPort) -> None:
    assert hasattr(extractor, "extract_text")
    assert callable(extractor.extract_text)


@pytest.mark.asyncio
async def test_pymupdf_extractor_implements_pdf_extractor_port_contract():
    extractor = PyMuPDFExtractor()
    _assert_pdf_extractor_contract(extractor)

    with pytest.raises(InvalidFileFormatError):
        await extractor.extract_text(b"not-a-pdf", "broken.pdf")

