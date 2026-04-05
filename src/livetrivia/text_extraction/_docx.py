import io
import typing_extensions as tp
from pathlib import Path
import docx


def _get_docx_text(f: str | Path | bytes | tp.IO[bytes]) -> str:
    if isinstance(f, bytes):
        f = io.BytesIO(f)
    elif isinstance(f, Path):
        f = str(f.absolute())
    document = docx.Document(f)
    return "\n\n".join(paragraph.text for paragraph in document.paragraphs)
