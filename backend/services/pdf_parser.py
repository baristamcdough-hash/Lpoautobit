import io
import logging

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from PDF bytes using PyPDF2.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted text content as a string. Returns empty string on failure.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts)

        if not full_text.strip():
            logger.warning(
                "No text extracted from PDF. "
                "The PDF may be scanned/image-based and require OCR."
            )
            return ""

        return full_text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return ""
