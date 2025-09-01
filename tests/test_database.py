import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from store_monitoring.database import Base, get_db
from store_monitoring.models import StoreTimezone
from store_monitoring.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def test_db():
   
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_db_session_and_model(test_db):
   
    db = next(override_get_db())
    assert db is not None

    test_store = StoreTimezone(
        store_id="test_store_123", timezone_str="America/New_York"
    )
    db.add(test_store)
    db.commit()
    db.refresh(test_store)

    retrieved_store = db.query(StoreTimezone).filter_by(store_id="test_store_123").first()
    assert retrieved_store is not None
    assert retrieved_store.store_id == "test_store_123"
    assert retrieved_store.timezone_str == "America/New_York"

    db.close()