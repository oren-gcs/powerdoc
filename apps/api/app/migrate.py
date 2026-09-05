from sqlalchemy import text

from app.config import get_settings


def ensure_sqlite_columns(engine) -> None:
    if not get_settings().database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)"))]
        if cols and "locale" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN locale VARCHAR(16) DEFAULT 'en'"))

        form_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(forms)"))]
        if form_cols and "answered_folder_id" not in form_cols:
            conn.execute(text("ALTER TABLE forms ADD COLUMN answered_folder_id INTEGER"))
        if form_cols and "archived_at" not in form_cols:
            conn.execute(text("ALTER TABLE forms ADD COLUMN archived_at DATETIME"))
        if form_cols and "archive_keep_answers" not in form_cols:
            conn.execute(text("ALTER TABLE forms ADD COLUMN archive_keep_answers BOOLEAN"))

        sub_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(form_submissions)"))]
        if sub_cols and "actions" not in sub_cols:
            conn.execute(text("ALTER TABLE form_submissions ADD COLUMN actions JSON DEFAULT '[]'"))
