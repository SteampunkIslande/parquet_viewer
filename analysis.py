import duckdb as db


def init_analysis_db(path: str):
    conn = db.connect(path)
    conn.sql(f"""CREATE TYPE STATUS AS ENUM ('pending', 'done')""")
    conn.sql(
        f"""CREATE TABLE validations (validation_name TEXT, status STATUS, username TEXT, date_time DATETIME)"""
    )
