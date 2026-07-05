# models.py
"""
Shared SQLAlchemy models — imported by both main.py (API) and celery_tasks.py
(worker) so the schema can never drift between the two processes.
"""
import os
import uuid
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, Uuid, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True, unique=True)
    api_key_hash = Column(String(64), unique=True, nullable=True, index=True)
    razorpay_customer_id = Column(String(255))
    razorpay_subscription_id = Column(String(255))
    credits = Column(Integer, default=0, nullable=False)  # 1 credit = 1 minute of processed video
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    input_url = Column(Text, nullable=False)
    output_url = Column(Text)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending|processing|completed|failed
    
    # Customization settings
    target_vmaf = Column(Float, default=94.0)
    codec = Column(String, default="vp9")
    resolution = Column(String, default="original")
    audio_bitrate = Column(String, default="96k")
    
    original_size_mb = Column(Float)
    optimized_size_mb = Column(Float)
    optimal_crf = Column(Integer)
    sampled_vmaf = Column(Float)   # actual measured average at the chosen CRF — honest, not hardcoded
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class WebhookEvent(Base):
    """Dedup table so retried Razorpay webhooks don't double-credit users."""
    __tablename__ = "webhook_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    razorpay_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100))
    processed_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
