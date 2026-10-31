"""PDF text extraction using PyMuPDF."""
import fitz  # PyMuPDF
from typing import List


def extract_text(pdf_bytes: bytes, max_pages: int = 15, max_chars: int = 12000) -> str:
    """
    Extract text from PDF bytes.

    Args:
        pdf_bytes: Raw PDF file bytes
        max_pages: Maximum number of pages to process (default 15)
        max_chars: Maximum characters to return (default 12000)

    Returns:
        Extracted text, trimmed to max_chars
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []

        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                text_parts.append(text)

        doc.close()

        full_text = "\n\n".join(text_parts)

        # Trim to max_chars
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "..."

        return full_text

    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_pages(pdf_bytes: bytes, max_pages: int = 15) -> List[str]:
    """
    Extract text from each page separately.

    Args:
        pdf_bytes: Raw PDF file bytes
        max_pages: Maximum number of pages to process (default 15)

    Returns:
        List of page texts
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []

        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            text = page.get_text("text")
            pages.append(text)

        doc.close()
        return pages

    except Exception as e:
        return [f"Error extracting PDF: {str(e)}"]


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as f:
            text = extract_text(f.read())
            print(text[:500])
    else:
        print("Usage: python -m backend.pdf_reader <pdf_file>")