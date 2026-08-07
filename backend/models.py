from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./heatshield.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="worker")  # worker | supervisor
    job_role = Column(String, default="General")  # Delivery, Construction, etc. (display only)
    shift_start = Column(DateTime, default=datetime.utcnow)

    readings = relationship("Reading", back_populates="worker", order_by="Reading.created_at.desc()")
    alerts = relationship("Alert", back_populates="worker")


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lat = Column(Float)
    lon = Column(Float)
    work_type = Column(String)
    clothing = Column(String)
    hydration_glasses = Column(Integer)
    rest_minutes = Column(Integer)
    health = Column(String)

    temp_c = Column(Float)
    humidity = Column(Float)
    heat_index_c = Column(Float)
    score = Column(Integer)
    label = Column(String)
    level = Column(String)

    worker = relationship("Worker", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    reading_id = Column(Integer, ForeignKey("readings.id"))
    score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)

    worker = relationship("Worker", back_populates="alerts")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
