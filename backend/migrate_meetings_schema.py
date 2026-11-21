"""
SAFE IDEMPOTENT MIGRATION — Milestone 8 DB schema fix.

Adds 4 missing columns to the existing 'meetings' table required by the
current SQLAlchemy Meeting model. Preserves ALL existing data. Can be run
multiple times safely because each ADD COLUMN checks information_schema first.

Missing columns identified:
  - original_filename  VARCHAR NOT NULL
  - content_type       VARCHAR NOT NULL
  - file_size          INTEGER NULL
  - status             meetingstatus NOT NULL DEFAULT 'UPLOADED'

Note: The 'meetingstatus' enum type (with labels UPLOADED/PROCESSING/
COMPLETED/FAILED) already exists in the DB, so we reuse it.

Run:
  cd backend
  ..\.venv\Scripts\python.exe migrate_meetings_schema.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2 import sql

DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOSTNAME = os.getenv("DATABASE_HOSTNAME")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")

MIGRATIONS = [
    {
        "column": "original_filename",
        "ddl_not_null": "VARCHAR NOT NULL",
        "ddl_nullable": "VARCHAR",
        "backfill": "'migrated_placeholder_' || id::text",
        "default_new": None,
    },
    {
        "column": "content_type",
        "ddl_not_null": "VARCHAR NOT NULL",
        "ddl_nullable": "VARCHAR",
        "backfill": "'application/octet-stream'",
        "default_new": None,
    },
    {
        "column": "file_size",
        "ddl_not_null": "INTEGER NULL",
        "ddl_nullable": "INTEGER NULL",
        "backfill": None,
        "default_new": None,
    },
    {
        "column": "status",
        "ddl_not_null": "meetingstatus NOT NULL DEFAULT 'UPLOADED'::meetingstatus",
        "ddl_nullable": "meetingstatus DEFAULT 'UPLOADED'::meetingstatus",
        "backfill": "'UPLOADED'::meetingstatus",
        "default_new": "'UPLOADED'::meetingstatus",
    },
]


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
        )
        """,
        (table, column),
    )
    return cur.fetchone()[0]


def table_row_count(cur, table: str) -> int:
    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
    return cur.fetchone()[0]


def main():
    conn = psycopg2.connect(
        user=DATABASE_USERNAME,
        password=DATABASE_PASSWORD,
        host=DATABASE_HOSTNAME,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
    )
    conn.autocommit = False  # Run everything in one transaction
    cur = conn.cursor()

    print("=" * 80)
    print("Milestone 8: Safe meetings table schema migration")
    print("=" * 80)

    try:
        n_rows = table_row_count(cur, "meetings")
        print("\nExisting rows in meetings: {}".format(n_rows))
        print("\nPlanned migrations (each checked for existence, idempotent):")
        for m in MIGRATIONS:
            exists = column_exists(cur, "meetings", m["column"])
            status = "SKIP (already present)" if exists else "RUN (will ADD COLUMN)"
            print("  - [{}] {}".format(status, m["column"]))

        print("\n" + "-" * 80)
        print("EXECUTING MIGRATIONS")
        print("-" * 80)

        for m in MIGRATIONS:
            col = m["column"]
            if column_exists(cur, "meetings", col):
                print("\n[SKIP]    meetings.{} already exists — no-op.".format(col))
                continue

            # Decide whether we can add NOT NULL directly.
            # - If table is empty: add NOT NULL directly (fast & clean, matches model).
            # - If table has rows: add NULLABLE, backfill with safe default, then SET NOT NULL.
            if n_rows == 0:
                stmt = sql.SQL(
                    "ALTER TABLE meetings ADD COLUMN {} {}"
                ).format(
                    sql.Identifier(col),
                    sql.SQL(m["ddl_not_null"]),
                )
                cur.execute(stmt)
                print("[ADD NN]  meetings.{}  -> empty table, ADD COLUMN ... NOT NULL OK".format(col))
            else:
                # Step 1: ADD nullable
                stmt = sql.SQL(
                    "ALTER TABLE meetings ADD COLUMN {} {}"
                ).format(
                    sql.Identifier(col),
                    sql.SQL(m["ddl_nullable"]),
                )
                cur.execute(stmt)
                print("[ADD  ]   meetings.{}  -> added as NULLABLE ({} existing rows)".format(col, n_rows))

                # Step 2: Backfill rows that are NULL
                if m["backfill"] is not None:
                    stmt = sql.SQL(
                        "UPDATE meetings SET {} = {} WHERE {} IS NULL"
                    ).format(
                        sql.Identifier(col),
                        sql.SQL(m["backfill"]),
                        sql.Identifier(col),
                    )
                    cur.execute(stmt)
                    updated = cur.rowcount
                    print("[FILL]   meetings.{}  -> backfilled {} rows".format(col, updated))

                # Step 3: If column requires NOT NULL (as per model), SET NOT NULL now
                if "NOT NULL" in m["ddl_not_null"]:
                    stmt = sql.SQL(
                        "ALTER TABLE meetings ALTER COLUMN {} SET NOT NULL"
                    ).format(sql.Identifier(col))
                    cur.execute(stmt)
                    print("[NOTNULL] meetings.{}  -> ALTER SET NOT NULL OK".format(col))

                # Step 4: If column has a DEFAULT for new rows, set it now
                if m["default_new"] is not None:
                    stmt = sql.SQL(
                        "ALTER TABLE meetings ALTER COLUMN {} SET DEFAULT {}"
                    ).format(
                        sql.Identifier(col),
                        sql.SQL(m["default_new"]),
                    )
                    cur.execute(stmt)
                    print("[DEFAULT] meetings.{}  -> SET DEFAULT = {}".format(col, m["default_new"]))

        # Verify: all 15 model columns present now
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='meetings'"
        )
        final_cols = set(r[0] for r in cur.fetchall())
        expected = {
            "id", "title", "description", "original_filename", "recording_path",
            "content_type", "file_size", "status", "transcript", "summary",
            "key_decisions", "meeting_date", "created_by_id", "created_at", "updated_at",
        }
        still_missing = expected - final_cols
        extra = final_cols - expected

        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print("\nModel required columns present now: {} / 15".format(len(expected & final_cols)))
        if still_missing:
            print("STILL MISSING: {}".format(sorted(still_missing)))
            raise RuntimeError("Migration incomplete, missing: {}".format(still_missing))
        else:
            print("OK: All 15 SQLAlchemy model columns exist.")
        if extra:
            print("Info: extra columns in DB (harmless): {}".format(sorted(extra)))

        # Also sanity-check the enum type label used by status default exists
        cur.execute(
            "SELECT enumlabel FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid "
            "WHERE t.typname = 'meetingstatus' ORDER BY enumsortorder"
        )
        labels = [r[0] for r in cur.fetchall()]
        print("\nmeetingstatus enum labels confirmed: {}".format(labels))
        assert 'UPLOADED' in labels, "UPLOADED label missing from meetingstatus enum"

        conn.commit()
        print("\nCOMMIT OK — migration succeeded. All data preserved.")
        return 0

    except Exception as e:
        conn.rollback()
        print("\nROLLBACK performed due to error: {}: {}".format(type(e).__name__, e))
        return 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
