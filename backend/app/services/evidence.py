"""Evidence image storage.

Images are stored under EVIDENCE_DIR/YYYY/MM/DD/<uuid>_<suffix>.jpg and the
database keeps the path relative to EVIDENCE_DIR, so the storage root can move
(or be mounted elsewhere) without rewriting rows.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings


def _root() -> Path:
    root = Path(get_settings().evidence_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_evidence(content: bytes, suffix: str = "frame") -> str:
    now = datetime.now(timezone.utc)
    rel_dir = Path(f"{now:%Y}/{now:%m}/{now:%d}")
    directory = _root() / rel_dir
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{suffix}.jpg"
    (directory / filename).write_bytes(content)
    return str(rel_dir / filename)


def resolve_evidence_path(rel_path: str) -> Path | None:
    root = _root().resolve()
    path = (root / rel_path).resolve()
    # Prevent path traversal out of the evidence root.
    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path
