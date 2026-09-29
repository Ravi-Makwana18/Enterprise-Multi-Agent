"""Migrate enterprise employees from CSV into SQLite database."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.db.database import initialize_database
from backend.services.employee_service import migrate_csv_to_sqlite, query_department_analytics


def main():
    print("=" * 65)
    print("MIGRATING ENTERPRISE EMPLOYEES TO SQLITE DATABASE")
    print("=" * 65)

    print("\n1. Initializing SQLite tables & running schema column migrations...")
    initialize_database()
    print("   [OK] SQLite schema verified and up-to-date.")

    print("\n2. Loading records from backend/data/enterprise_employees.csv...")
    result = migrate_csv_to_sqlite()
    print(f"   Status: {result.get('status')}")
    print(f"   Migrated new rows: {result.get('migrated', 0)}")
    print(f"   Updated existing rows: {result.get('updated', 0)}")
    print(f"   Total processed: {result.get('total_processed', 0)}")

    print("\n3. Verifying department aggregations in SQLite (in INR):")
    print("-" * 65)
    analytics = query_department_analytics()
    print(f"{'Department':<24} | {'Headcount':<10} | {'Avg Basic':<14} | {'Avg CTC':<14}")
    print("-" * 65)
    for d in analytics:
        print(f"{d['department']:<24} | {d['headcount']:<10} | Rs. {d['avg_basic']:<10,.2f} | Rs. {d['avg_annual_ctc']:<10,.2f}")
    print("-" * 65)
    print("\n[SUCCESS] SQLite migration complete! Salary Agent can now query SQLite directly.")


if __name__ == "__main__":
    main()
