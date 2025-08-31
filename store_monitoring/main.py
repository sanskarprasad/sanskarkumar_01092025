import string, random, io, csv
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from . import ingestion, models, reporting
from . import ingestion, models, reporting
from .database import create_db_and_tables, get_db, SessionLocal, engine # Import engine





@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    print("Creating database and tables...")
    create_db_and_tables()
    yield
    print("Application shutdown.")

class IngestRequest(BaseModel):
    path: str

class IngestResponse(BaseModel):
    message: str

class TriggerResponse(BaseModel):
    report_id: str

app = FastAPI(
    title="Store Monitoring API",
    description="API for triggering and retrieving store uptime/downtime reports.",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

def ingest_task(path_str: str):
    """Background task for ingesting data from CSV files."""
    try:
        data_dir = Path(path_str)
        print(f"Starting background ingestion from: {data_dir}")
        # Pass the engine to the ingestion function
        counts = ingestion.ingest_csv_data(engine, data_dir)
        print(f"Background ingestion finished successfully. Counts: {counts}")
    except Exception as e:
        print(f"Error during background ingestion: {e}")


def generate_report_task(report_id: str):
    """Background task that generates the full report for all stores."""
    db = SessionLocal()
    try:
        print(f"[{report_id}] Starting report generation...")
        now_utc = reporting.get_max_poll_timestamp(db)
        store_ids = [item[0] for item in db.query(models.StoreStatusPoll.store_id).distinct().all()]
        
        for i, store_id in enumerate(store_ids):
            print(f"[{report_id}] Processing store {i+1}/{len(store_ids)}: {store_id}")
            report_data = reporting.calculate_store_report(store_id, now_utc, db)
            db.add(models.ReportRow(report_id=report_id, store_id=store_id, **report_data))
        
        report_record = db.query(models.Report).filter_by(report_id=report_id).first()
        if report_record:
            report_record.status = "Complete"
            report_record.completed_at = datetime.now(timezone.utc)
        db.commit()
        print(f"[{report_id}] Report generation complete.")
    except Exception as e:
        db.rollback()
        report_record = db.query(models.Report).filter_by(report_id=report_id).first()
        if report_record:
            report_record.status = "Error"
            report_record.error = str(e)
            db.commit()
        print(f"[{report_id}] Error during report generation: {e}")
    finally:
        db.close()

@app.post("/ingest", tags=["Data"], response_model=IngestResponse)
def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    """Triggers a background task to ingest CSV data."""
    if not Path(request.path).is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")
    background_tasks.add_task(ingest_task, request.path)
    return {"message": "Data ingestion started in the background. Check server logs for progress."}

@app.post("/trigger_report", tags=["Reports"], response_model=TriggerResponse)
def trigger_report(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Kicks off a background task to generate a new report."""
    report_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    db.add(models.Report(report_id=report_id, status="Running"))
    db.commit()
    background_tasks.add_task(generate_report_task, report_id)
    return {"report_id": report_id}

@app.get("/get_report", tags=["Reports"])
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Retrieves report status or streams the completed CSV."""
    report = db.query(models.Report).filter_by(report_id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report ID not found.")
    if report.status == "Running":
        return {"status": "Running"}
    if report.status == "Error":
        raise HTTPException(status_code=500, detail=f"Report failed: {report.error}")

    rows = db.query(models.ReportRow).filter_by(report_id=report_id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    header = [
        "store_id", "uptime_last_hour(minutes)", "uptime_last_day(hours)", "uptime_last_week(hours)",
        "downtime_last_hour(minutes)", "downtime_last_day(hours)", "downtime_last_week(hours)"
    ]
    writer.writerow(header)
    for row in rows:
        writer.writerow([
            row.store_id, row.uptime_last_hour_minutes, row.uptime_last_day_hours,
            row.uptime_last_week_hours, row.downtime_last_hour_minutes,
            row.downtime_last_day_hours, row.downtime_last_week_hours
        ])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", 
                             headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"})