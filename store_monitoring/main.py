import string
import random
import io
import csv
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import ingestion, models, reporting
from .database import create_db_and_tables, get_db, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

# --- Pydantic Models ---
class HealthCheck(BaseModel):
    status: str

class IngestRequest(BaseModel):
    path: str

class IngestResponse(BaseModel):
    message: str

class TriggerResponse(BaseModel):
    report_id: str

class ReportStatusResponse(BaseModel):
    status: str

# --- App Initialization ---
app = FastAPI(
    title="Store Monitoring API",
    description="API for triggering and retrieving store uptime/downtime reports.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Background Task Logic ---
def ingest_task(path_str: str):
    """Background task for ingesting data from CSV files."""
    db = SessionLocal()
    try:
        data_dir = Path(path_str)
        print(f"Starting background ingestion from: {data_dir}")
        counts = ingestion.ingest_csv_data(db, data_dir)
        print(f"Background ingestion finished successfully. Counts: {counts}")
    except Exception as e:
        print(f"Error during background ingestion: {e}")
    finally:
        db.close()

def generate_report_task(report_id: str):
    """The background task that generates the full report for all stores."""
    db = SessionLocal()
    try:
        print(f"[{report_id}] Starting report generation...")
        now_utc = reporting.get_max_poll_timestamp(db)
        store_ids_query = db.query(models.StoreStatusPoll.store_id).distinct().all()
        store_ids = [item[0] for item in store_ids_query]
        
        report_rows = []
        for i, store_id in enumerate(store_ids):
            print(f"[{report_id}] Processing store {i+1}/{len(store_ids)}: {store_id}")
            report_data = reporting.calculate_store_report(store_id, now_utc, db)
            report_row = models.ReportRow(
                report_id=report_id,
                store_id=store_id,
                uptime_last_hour_minutes=round(report_data.get("uptime_last_hour_minutes", 0)),
                uptime_last_day_hours=report_data.get("uptime_last_day_hours", 0),
                uptime_last_week_hours=report_data.get("uptime_last_week_hours", 0),
                downtime_last_hour_minutes=round(report_data.get("downtime_last_hour_minutes", 0)),
                downtime_last_day_hours=report_data.get("downtime_last_day_hours", 0),
                downtime_last_week_hours=report_data.get("downtime_last_week_hours", 0),
            )
            report_rows.append(report_row)
        
        db.add_all(report_rows)
        report_record = db.query(models.Report).filter_by(report_id=report_id).first()
        if report_record:
            report_record.status = "Complete"
            report_record.completed_at = datetime.now(timezone.utc)
        db.commit()
        print(f"[{report_id}] Report generation complete.")

    except Exception as e:
        print(f"[{report_id}] Error during report generation: {e}")
        db.rollback()
        report_record = db.query(models.Report).filter_by(report_id=report_id).first()
        if report_record:
            report_record.status = "Error"
            report_record.error = str(e)
            report_record.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

# --- API Endpoints ---
@app.get("/health", tags=["Health"], response_model=HealthCheck)
def health_check():
    return {"status": "ok"}

@app.post("/ingest", tags=["Data"], response_model=IngestResponse)
def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    """Triggers a background task to ingest CSV data from a server-side directory."""
    data_dir = Path(request.path)
    if not data_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")
    
    background_tasks.add_task(ingest_task, request.path)
    return {"message": "Data ingestion started in the background. Check server logs for progress."}

@app.post("/trigger_report", tags=["Reports"], response_model=TriggerResponse)
def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Kicks off a background task to generate a new report for all stores."""
    report_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    new_report = models.Report(report_id=report_id, status="Running")
    db.add(new_report)
    db.commit()
    background_tasks.add_task(generate_report_task, report_id)
    return {"report_id": report_id}

@app.get("/get_report", tags=["Reports"])
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Retrieves the status of a report or streams the CSV if it's complete."""
    report = db.query(models.Report).filter_by(report_id=report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found.")

    if report.status == "Running":
        return {"status": "Running"}
    
    if report.status == "Error":
        raise HTTPException(status_code=500, detail=f"Report failed: {report.error}")

    report_rows = db.query(models.ReportRow).filter_by(report_id=report_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    header = [
        "store_id", "uptime_last_hour", "uptime_last_day", "uptime_last_week",
        "downtime_last_hour", "downtime_last_day", "downtime_last_week",
    ]
    writer.writerow(header)
    for row in report_rows:
        writer.writerow([
            row.store_id, row.uptime_last_hour_minutes, row.uptime_last_day_hours,
            row.uptime_last_week_hours, row.downtime_last_hour_minutes,
            row.downtime_last_day_hours, row.downtime_last_week_hours,
        ])
    output.seek(0)
    
    return StreamingResponse(
        output, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"}
    )