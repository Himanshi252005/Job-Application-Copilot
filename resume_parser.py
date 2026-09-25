"""Extracts plain text from an uploaded resume (PDF or DOCX)."""
import io
import docx
import pdfplumber


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """Returns the resume's plain text content."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return _parse_docx(file_bytes)
    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError("Unsupported resume format. Please upload a .pdf, .docx, or .txt file.")


def _parse_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _parse_docx(file_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    # Also pull text out of any tables in the source resume
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text)
    return "\n".join(paragraphs)
