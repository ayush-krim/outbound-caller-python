"""
Database models for call recordings and analytics
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Call(Base):
    """Call record model"""
    __tablename__ = "calls"
    
    id = Column(String, primary_key=True)
    dispatch_id = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=False)
    room_name = Column(String, unique=True, nullable=False)
    status = Column(String, default="initiated")  # initiated, connected, completed, failed
    
    # Call metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    connected_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Additional metadata
    call_metadata = Column(JSON, nullable=True)  # Store dial_info and other metadata
    
    # Relationships
    recordings = relationship("CallRecording", back_populates="call", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Call(id={self.id}, dispatch_id={self.dispatch_id}, status={self.status})>"


class CallRecording(Base):
    """Call recording model"""
    __tablename__ = "call_recordings"
    
    id = Column(Integer, primary_key=True)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False)
    egress_id = Column(String, unique=True, nullable=False, index=True)
    room_name = Column(String, nullable=False)
    
    # Recording status
    status = Column(String, default="recording")  # recording, completed, failed
    
    # Timestamps
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # File information
    file_path = Column(String, nullable=True)
    file_url = Column(String, nullable=True)  # S3 URL if uploaded
    file_size = Column(Integer, nullable=True)  # in bytes
    duration_seconds = Column(Float, nullable=True)
    format = Column(String, default="mp4")
    
    # Relationships
    call = relationship("Call", back_populates="recordings")
    
    def __repr__(self):
        return f"<CallRecording(id={self.id}, egress_id={self.egress_id}, status={self.status})>"