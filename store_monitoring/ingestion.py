import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from sqlalchemy.orm import Session
from pydantic import ValidationError

from . import models, schemas

def _parse_timestamp_utc(timestamp_str: str) -> datetime:
    """
    Parses timestamp strings from store_status.csv, accommodating formats
    with or without microseconds, and correctly handling the UTC timezone.
    """
    cleaned_str = timestamp_str.rsplit(' ', 1)[0].strip()
    fmt_with_ms = "%Y-%m-%d %H:%M:%S.%f"
    fmt_without_ms = "%Y-%m-%d %H:%M:%S"
    try:
        naive_dt = datetime.strptime(cleaned_str, fmt_with_ms)
    except ValueError:
        naive_dt = datetime.strptime(cleaned_str, fmt_without_ms)
    return naive_dt.replace(tzinfo=timezone.utc)


def ingest_csv_data(db: Session, data_dir_path: Path) -> Dict[str, int]:
    """
    Reads CSV data from a directory, truncates existing tables, and loads new data.
    """
    files = {
        "store_status": data_dir_path / "store_status.csv",
        "business_hours": data_dir_path / "menu_hours.csv",
        "timezones": data_dir_path / "timezones.csv",
    }
    for file_path in files.values():
        if not file_path.is_file():
            raise FileNotFoundError(f"Required data file not found: {file_path}")

    db.execute(models.StoreStatusPoll.__table__.delete())
    db.execute(models.BusinessHours.__table__.delete())
    db.execute(models.StoreTimezone.__table__.delete())
    db.commit()

    counts = {}

    # Ingest Store Status Polls
    status_polls_to_insert = []
    with open(files["store_status"], mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                row['timestamp_utc'] = _parse_timestamp_utc(row['timestamp_utc'])
                validated_data = schemas.StoreStatusPollCsv.model_validate(row)
                status_polls_to_insert.append(validated_data.model_dump())
            except (ValidationError, ValueError) as e:
                print(f"Skipping invalid row in store_status.csv: {row} | Error: {e}")
    db.bulk_insert_mappings(models.StoreStatusPoll, status_polls_to_insert)
    counts["store_status_polls"] = len(status_polls_to_insert)

    # Ingest Business Hours (with de-duplication)
    business_hours_map = {}
    with open(files["business_hours"], mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                validated_data = schemas.BusinessHoursCsv.model_validate(row)
                # Use a dict key to automatically handle duplicates; last one wins.
                key = (validated_data.store_id, validated_data.day_of_week)
                business_hours_map[key] = validated_data.model_dump()
            except ValidationError as e:
                print(f"Skipping invalid row in menu_hours.csv: {row} | Error: {e}")
    
    business_hours_to_insert = list(business_hours_map.values())
    db.bulk_insert_mappings(models.BusinessHours, business_hours_to_insert)
    counts["business_hours"] = len(business_hours_to_insert)

    # Ingest Store Timezones
    timezones_to_insert = []
    with open(files["timezones"], mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                validated_data = schemas.StoreTimezoneCsv.model_validate(row)
                timezones_to_insert.append(validated_data.model_dump())
            except ValidationError as e:
                print(f"Skipping invalid row in timezones.csv: {row} | Error: {e}")
    db.bulk_insert_mappings(models.StoreTimezone, timezones_to_insert)
    counts["store_timezones"] = len(timezones_to_insert)

    db.commit()
    return counts