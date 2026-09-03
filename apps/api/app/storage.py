import hashlib
from pathlib import Path

from app.config import get_settings


class Storage:
    def __init__(self) -> None:
        self.root = Path(get_settings().storage_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, tenant_id: int, filename: str, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()[:12]
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        key = f"t{tenant_id}/{digest}_{safe}"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def path(self, key: str) -> Path:
        return self.root / key

    def delete(self, key: str) -> None:
        path = self.root / key
        if path.exists():
            path.unlink()


storage = Storage()
