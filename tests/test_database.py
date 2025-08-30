import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store_monitoring.database import Base, get_db
from store_monitoring.models import StoreTimezone
from store_monitoring.main import app

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for testing
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def test_db():
    """
    Pytest fixture to set up and tear down the test database.
    Creates all tables before a test and drops them afterwards.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_db_session_and_model(test_db):
    """
    Tests database session creation and basic model interaction.
    1. Gets a database session.
    2. Creates a sample StoreTimezone record.
    3. Adds it to the session and commits.
    4. Queries the database to verify the record was saved.
    """
    db = next(override_get_db())
    assert db is not None

    # Create a test object
    test_store = StoreTimezone(
        store_id="test_store_123", timezone_str="America/New_York"
    )
    db.add(test_store)
    db.commit()
    db.refresh(test_store)

    # Query and verify
    retrieved_store = db.query(StoreTimezone).filter_by(store_id="test_store_123").first()
    assert retrieved_store is not None
    assert retrieved_store.store_id == "test_store_123"
    assert retrieved_store.timezone_str == "America/New_York"

    db.close()