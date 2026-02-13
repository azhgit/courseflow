"""PyMuPDF-based PDF text extraction adapter."""

import asyncio

from courseflow.domain.exceptions import (
    InvalidFileFormatError,
    PDFCorruptedError,
)
from courseflow.domain.ports import PDFExtractorPort


class PyMuPDFExtractor(PDFExtractorPort):
    """Extract plain text from PDFs using PyMuPDF."""

    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        if not file_bytes.startswith(b"%PDF"):
            raise InvalidFileFormatError(f"Invalid PDF file: {filename}")

        def _extract() -> str:
            try:
                # PyMuPDF historically uses the `fitz` import; newer versions also support `pymupdf`.
                import fitz  # type: ignore[import-not-found,import-untyped]

                doc = fitz.open(stream=file_bytes, filetype="pdf")
                try:
                    parts: list[str] = []
                    for page in doc:
                        parts.append(page.get_text("text"))
                    return "\n".join(parts).strip()
                finally:
                    doc.close()
            except InvalidFileFormatError:
                raise
            except Exception as e:  # PyMuPDF exceptions vary by version
                raise PDFCorruptedError(f"Failed to extract PDF text: {filename}") from e

        return await asyncio.to_thread(_extract)
