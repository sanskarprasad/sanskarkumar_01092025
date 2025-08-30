from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base # Updated import

# Use SQLite for local development. The file will be created in the project root.
SQLALCHEMY_DATABASE_URL = "sqlite:///./store_monitoring.db"

# Create the SQLAlchemy engine.
# connect_args is needed only for SQLite to allow multi-threaded access.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our ORM models.
Base = declarative_base() # This usage is now correct with the new import

def get_db():
    """
    FastAPI dependency to get a DB session for a single request.
    Ensures the session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    """
    Creates all database tables defined by the models.
    This is typically called once on application startup.
    """
    Base.metadata.create_all(bind=engine)