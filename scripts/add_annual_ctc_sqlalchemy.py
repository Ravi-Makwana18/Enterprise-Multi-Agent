from backend.db.database import engine
from sqlalchemy import text

def add_column():
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(employees);"))
        cols = [row[1] for row in result]
        if "annual_ctc" in cols:
            print("annual_ctc column already exists.")
            return
        conn.execute(text("ALTER TABLE employees ADD COLUMN annual_ctc FLOAT;"))
        print("annual_ctc column added.")

if __name__ == "__main__":
    add_column()
