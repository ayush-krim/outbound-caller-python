from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Index, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database.config import Base


class Call(Base):
    """Main call record table"""
    __tablename__ = "calls"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id = Column(String(255), unique=True, nullable=False, index=True)
    room_name = Column(String(255), nullable=False)
    
    # Call participants
    phone_number = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(100))
    transfer_to_number = Column(String(50))
    
    # High-level outcomes
    status = Column(String(50), index=True)  # 'completed', 'failed', 'voicemail', 'transferred', 'abandoned'
    end_reason = Column(String(255))  # 'user_hangup', 'agent_hangup', 'timeout', 'error', 'transfer_completed'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    connection_metrics = relationship("CallConnectionMetrics", back_populates="call", uselist=False, cascade="all, delete-orphan")
    interaction_metrics = relationship("CallInteractionMetrics", back_populates="call", uselist=False, cascade="all, delete-orphan")
    speech_analytics = relationship("CallSpeechAnalytics", back_populates="call", uselist=False, cascade="all, delete-orphan")
    system_metrics = relationship("CallSystemMetrics", back_populates="call", uselist=False, cascade="all, delete-orphan")
    events = relationship("CallEvent", back_populates="call", cascade="all, delete-orphan", order_by="CallEvent.event_timestamp")


class CallConnectionMetrics(Base):
    """Connection performance metrics"""
    __tablename__ = "call_connection_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    
    # Dispatch to Answer Timeline
    dispatch_created_at = Column(DateTime(timezone=True), nullable=False)
    dispatch_accepted_at = Column(DateTime(timezone=True))
    
    # Room Connection Phase
    room_connection_start = Column(DateTime(timezone=True))
    room_connection_completed = Column(DateTime(timezone=True))
    room_connection_duration_ms = Column(Integer)
    
    # Agent Initialization Phase
    agent_init_start = Column(DateTime(timezone=True))
    agent_init_completed = Column(DateTime(timezone=True))
    agent_init_duration_ms = Column(Integer)
    
    # Session Creation Phase
    session_creation_start = Column(DateTime(timezone=True))
    session_creation_completed = Column(DateTime(timezone=True))
    session_creation_duration_ms = Column(Integer)
    
    # SIP Dialing Phase
    sip_dial_start = Column(DateTime(timezone=True))
    sip_dial_completed = Column(DateTime(timezone=True))
    sip_dial_duration_ms = Column(Integer)
    sip_dial_status = Column(String(50))  # 'ringing', 'answered', 'busy', 'no_answer', 'failed'
    
    # Call Answered
    call_answered_at = Column(DateTime(timezone=True))
    participant_joined_at = Column(DateTime(timezone=True))
    
    # Calculated Total Metrics
    total_setup_time_ms = Column(Integer)  # dispatch_created to call_answered
    time_to_connect_ms = Column(Integer)  # dispatch_accepted to participant_joined
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    call = relationship("Call", back_populates="connection_metrics")


class CallInteractionMetrics(Base):
    """Call interaction and conversation metrics"""
    __tablename__ = "call_interaction_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    
    # Call Duration
    call_start_time = Column(DateTime(timezone=True))
    call_end_time = Column(DateTime(timezone=True))
    total_duration_seconds = Column(Float)
    
    # Conversation Metrics
    agent_first_speech_at = Column(DateTime(timezone=True))
    user_first_speech_at = Column(DateTime(timezone=True))
    time_to_first_agent_response_ms = Column(Integer)
    time_to_first_user_response_ms = Column(Integer)
    
    # Interaction Counts
    total_agent_utterances = Column(Integer, default=0)
    total_user_utterances = Column(Integer, default=0)
    total_interruptions = Column(Integer, default=0)
    total_silence_periods = Column(Integer, default=0)
    total_silence_duration_ms = Column(Integer, default=0)
    
    # Response Time Analytics
    avg_agent_response_time_ms = Column(Float)
    max_agent_response_time_ms = Column(Integer)
    min_agent_response_time_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    call = relationship("Call", back_populates="interaction_metrics")


class CallSpeechAnalytics(Base):
    """Speech and conversation analytics"""
    __tablename__ = "call_speech_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    
    # Speech Recognition Metrics
    total_words_spoken_agent = Column(Integer)
    total_words_spoken_user = Column(Integer)
    avg_words_per_minute_agent = Column(Float)
    avg_words_per_minute_user = Column(Float)
    
    # Sentiment/Tone (if available)
    user_sentiment_score = Column(Float)  # -1 to 1 (negative to positive)
    detected_user_emotion = Column(String(50))  # 'neutral', 'happy', 'frustrated', 'confused'
    
    # Speech Quality
    avg_confidence_score = Column(Float)  # STT confidence
    low_confidence_utterances = Column(Integer)  # Count of low confidence recognitions
    
    # Conversation Flow
    topic_changes = Column(Integer)
    clarification_requests = Column(Integer)
    
    # Call transcript (optional, can be large)
    transcript = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    call = relationship("Call", back_populates="speech_analytics")


class CallSystemMetrics(Base):
    """System performance and resource usage metrics"""
    __tablename__ = "call_system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    
    # Resource Usage
    peak_cpu_usage_percent = Column(Float)
    avg_cpu_usage_percent = Column(Float)
    peak_memory_usage_mb = Column(Integer)
    avg_memory_usage_mb = Column(Integer)
    
    # Network Performance
    total_bandwidth_used_mb = Column(Float)
    avg_latency_ms = Column(Float)
    packet_loss_percent = Column(Float)
    
    # AI Model Performance
    llm_requests_count = Column(Integer)
    llm_total_tokens_used = Column(Integer)
    llm_avg_response_time_ms = Column(Float)
    stt_processing_time_ms = Column(Float)
    tts_processing_time_ms = Column(Float)
    
    # Errors and Warnings
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    call = relationship("Call", back_populates="system_metrics")


class CallEvent(Base):
    """Individual events during the call lifecycle"""
    __tablename__ = "call_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"))
    
    event_type = Column(String(100), nullable=False)  # 'voicemail_detected', 'transfer_requested', etc.
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    event_details = Column(JSON)  # Flexible field for event-specific data
    duration_from_call_start_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    call = relationship("Call", back_populates="events")
    
    # Indexes
    __table_args__ = (
        Index("idx_call_events_type", "event_type"),
        Index("idx_call_events_timestamp", "event_timestamp"),
        Index("idx_call_events_call_id", "call_id"),
    )