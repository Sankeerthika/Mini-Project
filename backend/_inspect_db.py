import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def show_cols(table):
    with engine.connect() as conn:
        r = conn.execute(text(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = :t
            ORDER BY ordinal_position
        """), {"t": table})
        print(f"\n=== TABLE {table} ===")
        for row in r:
            print(f"  {row[0]:<30} {str(row[1]):<20} NULL={row[2]:<4} DEFAULT={row[3]}")

for t in ["users", "meetings", "tasks"]:
    show_cols(t)
