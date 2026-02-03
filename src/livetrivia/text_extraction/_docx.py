import typing_extensions as tp
from pathlib import Path
import docx

def _get_docx_text(f: str | Path | tp.IO[bytes]) -> str:
    f = str(f.absolute()) if isinstance(f, Path) else f
    document = docx.Document(f)
    return "\n\n".join(paragraph.text for paragraph in document.paragraphs)
