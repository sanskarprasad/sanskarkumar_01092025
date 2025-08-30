import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store_monitoring.database import Base

@pytest.fixture
def test_db():
    """
    Provides an in-memory SQLite database session for testing.
    """
    # Use SQLite in-memory database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Provide a session to tests
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
