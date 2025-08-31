import pandas as pd
from pathlib import Path
from typing import Dict
from sqlalchemy import text
from sqlalchemy.engine import Engine

from . import models

def ingest_csv_data(engine: Engine, data_dir_path: Path) -> Dict[str, int]:
    """
    Reads CSV data using pandas, truncates tables, and bulk-loads new data.

    Args:
        engine: The SQLAlchemy database engine.
        data_dir_path: The path to the directory containing the CSV files.

    Returns:
        A dictionary with the count of rows inserted for each table.
    """
    files = {
        "store_status": data_dir_path / "store_status.csv",
        "business_hours": data_dir_path / "menu_hours.csv",
        "timezones": data_dir_path / "timezones.csv",
    }
    counts = {}

    with engine.connect() as conn:
        # Truncate tables before inserting new data
        conn.execute(text(f"DELETE FROM {models.StoreStatusPoll.__tablename__}"))
        conn.execute(text(f"DELETE FROM {models.BusinessHours.__tablename__}"))
        conn.execute(text(f"DELETE FROM {models.StoreTimezone.__tablename__}"))
        conn.commit()

        # Ingest Store Status Polls
        df_status = pd.read_csv(files["store_status"], chunksize=10000)
        for chunk in df_status:
            chunk['timestamp_utc'] = pd.to_datetime(chunk['timestamp_utc'], utc=True)
            chunk.to_sql(models.StoreStatusPoll.__tablename__, conn, if_exists='append', index=False)
        counts["store_status_polls"] = sum(len(chunk) for chunk in pd.read_csv(files["store_status"], chunksize=10000))


        # Ingest Business Hours (with de-duplication)
        df_hours = pd.read_csv(files["business_hours"])
        df_hours.rename(columns={'dayOfWeek': 'day_of_week'}, inplace=True)
        df_hours.drop_duplicates(subset=['store_id', 'day_of_week'], keep='last', inplace=True)
        df_hours.to_sql(models.BusinessHours.__tablename__, conn, if_exists='append', index=False)
        counts["business_hours"] = len(df_hours)

        # Ingest Store Timezones
        df_tz = pd.read_csv(files["timezones"])
        df_tz.to_sql(models.StoreTimezone.__tablename__, conn, if_exists='append', index=False)
        counts["store_timezones"] = len(df_tz)
        
        conn.commit()

    return counts