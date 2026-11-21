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

conn = psycopg2.connect(
    user=DATABASE_USERNAME,
    password=DATABASE_PASSWORD,
    host=DATABASE_HOSTNAME,
    port=DATABASE_PORT,
    dbname=DATABASE_NAME,
)
conn.autocommit = True
cur = conn.cursor()

print("=" * 80)
print("MEETINGS TABLE - FULL DIFF")
print("=" * 80)

cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'meetings'
    ORDER BY ordinal_position
""")
actual_cols = set(r[0] for r in cur.fetchall())

expected_cols = [
    "id", "title", "description", "original_filename", "recording_path",
    "content_type", "file_size", "status", "transcript", "summary",
    "key_decisions", "meeting_date", "created_by_id", "created_at", "updated_at",
]

print("\nColumns PRESENT in DB ({} / 15):".format(len(actual_cols)))
for c in expected_cols:
    if c in actual_cols:
        print("  [ OK ] {}".format(c))
print("\nColumns MISSING in DB (need ADD):")
missing = []
for c in expected_cols:
    if c not in actual_cols:
        missing.append(c)
        print("  [ADD ] {}".format(c))
print("\nMissing count: {}".format(len(missing)))

print("\n" + "=" * 80)
print("ENUM TYPE EXISTENCE CHECK")
print("=" * 80)

cur.execute("""
    SELECT t.typname, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
    FROM pg_type t
    LEFT JOIN pg_enum e ON e.enumtypid = t.oid
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = 'public'
      AND t.typname IN ('meetingstatus', 'meeting_status_enum', 'taskstatus', 'priority', 'userrole')
    GROUP BY t.typname
    ORDER BY t.typname
""")
enum_rows = cur.fetchall()
print("\nExisting enum types:")
for typname, labels in enum_rows:
    print("  - {}: ({})".format(typname, labels or "no labels"))

if not any(t == 'meetingstatus' or t == 'meeting_status_enum' for t, _ in enum_rows):
    print("  - MeetingStatus enum MISSING — need to CREATE TYPE first")

print("\n" + "=" * 80)
print("EXISTING MEETINGS ROW COUNT")
print("=" * 80)
cur.execute("SELECT COUNT(*) FROM meetings")
cnt = cur.fetchone()[0]
print("\nRows currently in meetings: {}".format(cnt))

cur.close()
conn.close()
print("\nInspection complete.")
