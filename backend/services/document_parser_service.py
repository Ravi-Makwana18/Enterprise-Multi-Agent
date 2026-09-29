import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """Strip null bytes and non-printable control characters while preserving standard formatting."""
    if not text:
        return ""
    # Strip null characters and unprintable control codes (keep \n, \r, \t)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    # Normalize excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Normalize multiple inline spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from a PDF document using pypdf."""
    import pypdf

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                logger.warning("PDF is password protected; attempting unauthenticated read")

        pages_text = []
        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")
            except Exception as page_err:
                logger.warning("PDF page %d extract warning: %s", idx + 1, page_err)
                continue

        return _clean_text("\n\n".join(pages_text))
    except Exception as exc:
        logger.error("pypdf error: %s", exc)
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract clean text from a DOCX document using python-docx."""
    import docx

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        # Also capture table contents if present
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        return _clean_text("\n\n".join(paragraphs))
    except Exception as docx_err:
        logger.warning("DOCX parsing error: %s", docx_err)
        return ""


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode plain text file with UTF-8 and fallback encodings."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"):
        try:
            decoded = file_bytes.decode(encoding)
            return _clean_text(decoded)
        except UnicodeDecodeError:
            continue
    return _clean_text(file_bytes.decode("utf-8", errors="ignore"))


def parse_document(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Parse text from uploaded PDF, Word (.docx/.doc), or TXT/Markdown documents."""
    if not file_bytes:
        return {
            "success": False,
            "filename": filename,
            "extension": "",
            "error": f"The uploaded file '{filename}' is empty.",
            "text": "",
            "char_count": 0,
            "word_count": 0,
            "preview": "",
        }

    ext = filename.lower().split(".")[-1] if "." in filename else ""

    try:
        if ext == "pdf":
            text = extract_text_from_pdf(file_bytes)
        elif ext in ("docx", "doc"):
            text = extract_text_from_docx(file_bytes)
            # If docx parser returned empty (e.g. older legacy .doc), attempt plain text decoding
            if not text:
                text = extract_text_from_txt(file_bytes)
        elif ext in ("txt", "md", "markdown", "rtf", "csv", "json"):
            text = extract_text_from_txt(file_bytes)
        else:
            text = extract_text_from_txt(file_bytes)

        text = _clean_text(text)
        words = text.split()

        if not text or len(words) == 0:
            return {
                "success": False,
                "filename": filename,
                "extension": ext,
                "error": (
                    f"No readable text could be extracted from '{filename}'. "
                    "If this is a scanned or image-based PDF, please ensure it has selectable text, "
                    "or submit as a Word (.docx) or plain text (.txt) document."
                ),
                "text": "",
                "char_count": 0,
                "word_count": 0,
                "preview": "",
            }

        return {
            "success": True,
            "filename": filename,
            "extension": ext,
            "char_count": len(text),
            "word_count": len(words),
            "text": text,
            "preview": text[:250] + ("..." if len(text) > 250 else ""),
        }
    except Exception as exc:
        logger.error("Failed to parse document %s: %s", filename, exc, exc_info=True)
        return {
            "success": False,
            "filename": filename,
            "extension": ext,
            "error": f"Failed to extract text from {filename}: {str(exc)}",
            "text": "",
            "char_count": 0,
            "word_count": 0,
            "preview": "",
        }
