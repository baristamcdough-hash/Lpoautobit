import logging

import fitz  # pymupdf

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 100_000


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from PDF bytes using pymupdf (fitz).

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted text content as a string. Returns empty string on failure.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts = []
        for page in doc:
            text = page.get_text()
            if text:
                text_parts.append(text)
        doc.close()

        full_text = "\n".join(text_parts)

        if not full_text.strip():
            logger.warning(
                "No text extracted from PDF. The PDF may be scanned/image-based."
            )
            return ""

        if len(full_text) > MAX_TEXT_LENGTH:
            logger.warning(
                f"Text exceeds {MAX_TEXT_LENGTH} chars, truncating."
            )
            full_text = full_text[:MAX_TEXT_LENGTH]

        return full_text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return ""
