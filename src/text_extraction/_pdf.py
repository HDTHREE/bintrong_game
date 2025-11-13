import pypdf as pdf
import typing as tp
from pathlib import Path


def _get_pdf_text(
    f: str | Path | tp.IO,
    page_range: tuple[int, int] | None = None,
    password: str | None = None
) -> str:
    reader: pdf.PdfReader = pdf.PdfReader(f, password=password)
    pages: list[pdf.PageObject] = reader.pages
    start, end = sorted(page_range) if page_range else (1, len(pages))
    start = max(0, start - 1)
    end = min(end, len(pages))
    return " ".join(map(lambda i: pages[i].extract_text(), range(start, end))).strip()


if __name__ == "__main__":
    import os

    module_file_path = os.path.abspath(__file__)
    file_path = Path(module_file_path).parent / "file.pdf"
    print(_get_pdf_text(file_path))


    