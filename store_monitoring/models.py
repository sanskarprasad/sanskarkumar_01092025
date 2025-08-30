from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Time,
    Float,
    ForeignKey,
    PrimaryKeyConstraint,
    Text,
)
from sqlalchemy.sql import func
from .database import Base


class StoreStatusPoll(Base):
    __tablename__ = "store_status_polls"
    __table_args__ = (PrimaryKeyConstraint("store_id", "timestamp_utc"),)

    store_id = Column(String, index=True)
    timestamp_utc = Column(DateTime(timezone=True), index=True)
    status = Column(String, nullable=False)  # "active" or "inactive"


class BusinessHours(Base):
    __tablename__ = "business_hours"
    __table_args__ = (PrimaryKeyConstraint("store_id", "day_of_week"),)

    store_id = Column(String, index=True)
    day_of_week = Column(Integer, index=True)  # 0=Monday, 6=Sunday
    start_time_local = Column(Time)
    end_time_local = Column(Time)


class StoreTimezone(Base):
    __tablename__ = "store_timezones"

    store_id = Column(String, primary_key=True, index=True)
    timezone_str = Column(String, default="America/Chicago")


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String, primary_key=True, index=True)
    status = Column(String, default="Running")  # "Running", "Complete", "Error"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)


class ReportRow(Base):
    __tablename__ = "report_rows"
    __table_args__ = (PrimaryKeyConstraint("report_id", "store_id"),)

    report_id = Column(String, ForeignKey("reports.report_id"), index=True)
    store_id = Column(String, index=True)
    uptime_last_hour_minutes = Column(Integer)
    uptime_last_day_hours = Column(Float)
    uptime_last_week_hours = Column(Float)
    downtime_last_hour_minutes = Column(Integer)
    downtime_last_day_hours = Column(Float)
    downtime_last_week_hours = Column(Float)