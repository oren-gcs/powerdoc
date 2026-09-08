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
        if sub_cols and "upload_scans" not in sub_cols:
            conn.execute(text("ALTER TABLE form_submissions ADD COLUMN upload_scans JSON DEFAULT '[]'"))

        share_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(form_shares)"))]
        if share_cols:
            if "token" not in share_cols:
                conn.execute(text("ALTER TABLE form_shares ADD COLUMN token VARCHAR(64)"))
            if "status" not in share_cols:
                conn.execute(text("ALTER TABLE form_shares ADD COLUMN status VARCHAR(24) DEFAULT 'pending'"))
            if "submission_id" not in share_cols:
                conn.execute(text("ALTER TABLE form_shares ADD COLUMN submission_id INTEGER"))
            # Best-effort unique index for personal tokens (ignore if already present).
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_form_shares_token ON form_shares(token)"))
            except Exception:
                pass
