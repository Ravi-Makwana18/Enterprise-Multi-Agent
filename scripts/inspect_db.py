"""Convenience CLI script to inspect and query the SQLite database."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "enterprise_multi_agent.db"


def show_summary():
    if not DB_PATH.exists():
        print(f"Database not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cur.fetchall()]

    print("=" * 60)
    print(f"DATABASE: {DB_PATH.name}")
    print("=" * 60)

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  * {table:<20} ({count} rows)")

    print("\n" + "=" * 60)
    print("SAMPLE EMPLOYEES:")
    print("-" * 60)
    cur.execute("SELECT employee_id, employee_name, basic_salary FROM employees LIMIT 5;")
    for row in cur.fetchall():
        print(f"  {row[0]:<10} | {row[1]:<20} | Basic: Rs. {row[2]:,.2f}")

    print("\n" + "=" * 60)
    print("SAMPLE CHAT SESSIONS:")
    print("-" * 60)
    cur.execute("SELECT session_id, employee_id, title, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 5;")
    sessions = cur.fetchall()
    if not sessions:
        print("  (No chat sessions yet)")
    for row in sessions:
        print(f"  {row[0]} | Owner: {row[1] or 'Admin'} | {row[2]}")

    conn.close()


if __name__ == "__main__":
    show_summary()
