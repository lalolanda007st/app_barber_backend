import shutil
from pathlib import Path
from uuid import uuid4

from app.core.config import UPLOADS_DIR


def save_file(upload_file) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload_file.filename or "").suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    filepath = UPLOADS_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return filepath
