import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def run_safe_migration():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'meetings'
                  AND column_name = 'action_items_json'
            """))
            exists = result.fetchone() is not None
            if exists:
                print("[MIGRATION] Column 'action_items_json' already exists. No action needed.")
            else:
                conn.execute(text("ALTER TABLE meetings ADD COLUMN action_items_json TEXT"))
                print("[MIGRATION] Added column 'action_items_json' to meetings table successfully.")
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"[MIGRATION] FAILED: {type(e).__name__}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_safe_migration()
