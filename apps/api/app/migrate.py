from sqlalchemy import text

from app.config import get_settings


def ensure_sqlite_columns(engine) -> None:
    if not get_settings().database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
        if cols and "locale" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN locale VARCHAR(16) DEFAULT 'en'"))
