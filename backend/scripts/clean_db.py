import sys
from pathlib import Path
from sqlalchemy import text

# Ensure backend package is importable when running this script directly
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import sync_engine


def main():
    with sync_engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        print("Cleaned database schema and recreated public schema.")


if __name__ == '__main__':
    main()
