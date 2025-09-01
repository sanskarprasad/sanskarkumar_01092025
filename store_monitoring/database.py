from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Replace with your PostgreSQL connection details
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST =   "localhost"
DB_NAME = "store_monitoring_db"

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# The engine creation is now simpler
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    
    try:
        
        yield db
    finally:
        db.close()

def create_db_and_tables():
   
    Base.metadata.create_all(bind=engine)