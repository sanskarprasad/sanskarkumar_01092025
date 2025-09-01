# Store Monitoring Service

This is a high-performance backend service built with FastAPI that calculates store uptime and downtime reports from raw poll data. It is designed to handle large datasets efficiently through asynchronous processing and optimized data ingestion.

The system follows a **trigger-poll** pattern: an endpoint initiates a report generation process in the background, and another endpoint is used to check the status and retrieve the completed report as a CSV file.

---

## Features

- **Asynchronous API**: Uses FastAPI's background tasks for non-blocking data ingestion and report generation.
- **High-Performance Ingestion**: Leverages `pandas` for rapid CSV parsing and bulk-loading into the database.
- **Intelligent Uptime Calculation**:
  - Calculates uptime/downtime only within a store's specified business hours.
  - Correctly handles overnight business schedules (e.g., 10 PM - 4 AM).
  - Uses interpolation (last observation carried forward) to estimate status for the entire business day from discrete polls.
- **Data-Driven "Current Time"**: Establishes a consistent point-in-time for each report by using the latest timestamp from the poll data.
- **Robust Data Handling**:
  - Defaults to 24/7 business hours for stores with missing data.
  - Defaults to `America/Chicago` for stores with a missing timezone.
  - Handles duplicate entries in the source data gracefully.
- **Database Agnostic**: Built with SQLAlchemy to easily support databases like SQLite, PostgreSQL, etc.

---

## Tech Stack

- **Python 3.11**
- **FastAPI**: Asynchronous web framework.
- **Pandas**: For high-performance data ingestion and manipulation.
- **SQLAlchemy**: ORM and database interaction.
- **Uvicorn**: ASGI server.
- **PostgreSQL** / **SQLite**: Databases.
- **Docker** & **Docker Compose**: Containerization and orchestration.

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (Recommended) or a local PostgreSQL instance.

### Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-folder>
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

Place Data Files
Create a directory named data in the project root.
Place store_status.csv, menu_hours.csv, and timezones.csv inside it.

###Running the Service
You can run the service directly with Uvicorn or using the provided Docker Compose setup.
Option A: Run with Docker Compose (Recommended)
Make sure Docker Desktop is running.
Update the placeholder credentials in the docker-compose.yml file.
Run the following command from your project root:

```bash
docker-compose up --build
```

This will build the application image and start both the API and a PostgreSQL database.
Option B: Run Locally with Uvicorn
Ensure you have a database running (e.g., PostgreSQL) and have updated the connection string in store_monitoring/database.py.
Run the following command from your project root:
```bash
uvicorn store_monitoring.main:app --reload
```

###API Usage Guide
The API will be available at http://127.0.0.1:8000.
##1. Ingest Data
Start the background process to load the CSV data into the database.

```bash
curl -X POST -H "Content-Type: application/json" -d '{"path": "./data"}' http://127.0.0.1:8000/ingest 
```
Response
```json
{"message":"Data ingestion started in the background..."}
```

Monitor the server logs to see when ingestion completes.

##2. Trigger Report Generation

After ingestion is complete, start generating a new report.
```bash
curl -X POST http://127.0.0.1:8000/trigger_report
```
Response
```json
curl -X POST http://127.0.0.1:8000/trigger_report

```

Response:

```json
{"report_id":"<your_unique_report_id>"}

```
Copy the report_id for the next step.

##3. Get the Report
Use the report_id to check the status or download the completed CSV file.

```bash
# Poll for the report status (it will show "Running" initially)
curl http://127.0.0.1:8000/get_report?report_id=<your_unique_report_id>

# Once complete, save the file
curl -o report.csv "http://127.0.0.1:8000/get_report?report_id=<your_unique_report_id>"

```


|Ideas for Improvement
Configuration Management

Move database credentials and other settings from the code into environment variables or a .env file for security and flexibility.

Docker Compose already supports environment variable injection.

API Authentication

Secure endpoints to prevent unauthorized access.

A simple API Key check in request headers is a good start. FastAPI has built-in support for authentication schemes.

Web Frontend

Build a simple UI with React, Vue, or Svelte to allow non-technical users to trigger and download reports easily.

Enhanced Reporting & Analytics

Modify /trigger_report to accept optional start_date and end_date for custom historical reports.

Add aggregation endpoints, e.g., average uptime across all stores.

Real-Time Data Ingestion

Replace batch CSV ingestion with a message queue (RabbitMQ) or streaming platform (Kafka) for live updates.

Advanced Monitoring & Logging

Implement structured logging (JSON format) for easier parsing and searching in tools like Splunk or ELK.

Expand /health endpoint to verify database connectivity and dependency health, not just API availability.
