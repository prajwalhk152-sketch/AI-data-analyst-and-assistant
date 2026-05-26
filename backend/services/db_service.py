from sqlalchemy import create_engine, text
from config import Config
from services.state import get_current_data
from pathlib import Path

TABLE_NAME = "uploaded_data"

if Config.DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = Config.DATABASE_URL.replace("sqlite:///", "", 1)
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(Config.DATABASE_URL, future=True)

def save_to_database(df, table_name=TABLE_NAME):
    df.to_sql(table_name, engine, if_exists="replace", index=False)

def fetch_query(sql):
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.mappings().all()
        return [dict(row) for row in rows]

def get_table_columns(table_name=TABLE_NAME):
    df = get_current_data()
    if df is None:
        return []
    return df.columns.tolist()
