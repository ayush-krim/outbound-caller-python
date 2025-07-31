import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from database.config import async_session
from database.models import (
    Call, CallConnectionMetrics, CallInteractionMetrics,
    CallSpeechAnalytics, CallSystemMetrics, CallEvent
)

logger = logging.getLogger("outbound-caller.tracker")


class CallTracker:
    """Tracks and stores call analytics in the database"""
    
    def __init__(self, dispatch_id: str, room_name: str, phone_number: str, 
                 transfer_to: Optional[str] = None, agent_name: Optional[str] = None):
        self.dispatch_id = dispatch_id
        self.room_name = room_name
        self.phone_number = phone_number
        self.transfer_to = transfer_to
        self.agent_name = agent_name
        
        # Tracking data
        self.call_id: Optional[uuid.UUID] = None
        self.timestamps: Dict[str, datetime] = {}
        self.metrics: Dict[str, Any] = {}
        self.events: list = []
        
        # Track conversation metrics
        self.utterance_count = {"agent": 0, "user": 0}
        self.response_times = []
        
    async def initialize(self):
        """Create the initial call record in the database"""
        try:
            async with async_session() as session:
                call = Call(
                    dispatch_id=self.dispatch_id,
                    room_name=self.room_name,
                    phone_number=self.phone_number,
                    transfer_to_number=self.transfer_to,
                    agent_name=self.agent_name,
                    status="initializing"
                )
                session.add(call)
                await session.commit()
                self.call_id = call.id
                
                # Initialize connection metrics
                conn_metrics = CallConnectionMetrics(
                    call_id=self.call_id,
                    dispatch_created_at=datetime.now(timezone.utc)
                )
                session.add(conn_metrics)
                await session.commit()
                logger.info(f"Database tracking initialized for call {self.call_id}")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Tracking will continue in memory only.")
            self.call_id = None
            
    def record_timestamp(self, event_name: str, timestamp: Optional[datetime] = None):
        """Record a timestamp for an event"""
        self.timestamps[event_name] = timestamp or datetime.now(timezone.utc)
        
    def record_metric(self, metric_name: str, value: Any):
        """Record a metric value"""
        self.metrics[metric_name] = value
        
    async def record_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """Record a call event"""
        if not self.call_id:
            logger.debug(f"Skipping event recording (no DB): {event_type}")
            return
            
        event_time = datetime.now(timezone.utc)
        call_start = self.timestamps.get("call_start")
        duration_ms = None
        
        if call_start:
            duration_ms = int((event_time - call_start).total_seconds() * 1000)
        
        try:
            async with async_session() as session:
                event = CallEvent(
                    call_id=self.call_id,
                    event_type=event_type,
                    event_timestamp=event_time,
                    event_details=details,
                    duration_from_call_start_ms=duration_ms
                )
                session.add(event)
                await session.commit()
        except Exception as e:
            logger.debug(f"Failed to record event {event_type}: {e}")
            
    async def update_connection_metrics(self):
        """Update connection metrics in the database"""
        if not self.call_id:
            return
            
        async with async_session() as session:
            # Get existing metrics
            result = await session.execute(
                f"SELECT * FROM call_connection_metrics WHERE call_id = '{self.call_id}'"
            )
            metrics = result.first()
            
            if not metrics:
                return
                
            # Update with recorded timestamps
            updates = {}
            
            # Map timestamp events to database columns
            timestamp_mappings = {
                "dispatch_accepted": "dispatch_accepted_at",
                "room_connection_start": "room_connection_start",
                "room_connection_completed": "room_connection_completed",
                "agent_init_start": "agent_init_start",
                "agent_init_completed": "agent_init_completed",
                "session_creation_start": "session_creation_start",
                "session_creation_completed": "session_creation_completed",
                "sip_dial_start": "sip_dial_start",
                "sip_dial_completed": "sip_dial_completed",
                "call_answered": "call_answered_at",
                "participant_joined": "participant_joined_at"
            }
            
            for event, column in timestamp_mappings.items():
                if event in self.timestamps:
                    updates[column] = self.timestamps[event]
                    
            # Calculate durations
            if "room_connection_start" in self.timestamps and "room_connection_completed" in self.timestamps:
                updates["room_connection_duration_ms"] = int(
                    (self.timestamps["room_connection_completed"] - self.timestamps["room_connection_start"]).total_seconds() * 1000
                )
                
            if "agent_init_start" in self.timestamps and "agent_init_completed" in self.timestamps:
                updates["agent_init_duration_ms"] = int(
                    (self.timestamps["agent_init_completed"] - self.timestamps["agent_init_start"]).total_seconds() * 1000
                )
                
            if "session_creation_start" in self.timestamps and "session_creation_completed" in self.timestamps:
                updates["session_creation_duration_ms"] = int(
                    (self.timestamps["session_creation_completed"] - self.timestamps["session_creation_start"]).total_seconds() * 1000
                )
                
            if "sip_dial_start" in self.timestamps and "sip_dial_completed" in self.timestamps:
                updates["sip_dial_duration_ms"] = int(
                    (self.timestamps["sip_dial_completed"] - self.timestamps["sip_dial_start"]).total_seconds() * 1000
                )
                
            # Update the record
            if updates:
                await session.execute(
                    f"UPDATE call_connection_metrics SET {', '.join([f'{k} = :{k}' for k in updates.keys()])} WHERE call_id = :call_id",
                    {**updates, "call_id": self.call_id}
                )
                await session.commit()
                
    async def update_interaction_metrics(self):
        """Update interaction metrics"""
        if not self.call_id:
            return
            
        async with async_session() as session:
            # Create or update interaction metrics
            metrics = CallInteractionMetrics(
                call_id=self.call_id,
                call_start_time=self.timestamps.get("call_start"),
                call_end_time=self.timestamps.get("call_end"),
                agent_first_speech_at=self.timestamps.get("agent_first_speech"),
                user_first_speech_at=self.timestamps.get("user_first_speech"),
                total_agent_utterances=self.utterance_count["agent"],
                total_user_utterances=self.utterance_count["user"]
            )
            
            # Calculate durations
            if metrics.call_start_time and metrics.call_end_time:
                metrics.total_duration_seconds = (
                    metrics.call_end_time - metrics.call_start_time
                ).total_seconds()
                
            # Calculate response times
            if self.response_times:
                metrics.avg_agent_response_time_ms = sum(self.response_times) / len(self.response_times)
                metrics.max_agent_response_time_ms = max(self.response_times)
                metrics.min_agent_response_time_ms = min(self.response_times)
                
            session.add(metrics)
            await session.commit()
            
    async def finalize(self, status: str, end_reason: str):
        """Finalize the call record with final status"""
        if not self.call_id:
            return
            
        async with async_session() as session:
            # Update call status
            await session.execute(
                "UPDATE calls SET status = :status, end_reason = :end_reason WHERE id = :id",
                {"status": status, "end_reason": end_reason, "id": self.call_id}
            )
            
            # Update all metrics
            await self.update_connection_metrics()
            await self.update_interaction_metrics()
            
            await session.commit()
            
    def track_utterance(self, speaker: str):
        """Track when someone speaks"""
        if speaker in self.utterance_count:
            self.utterance_count[speaker] += 1
            
    def track_response_time(self, response_time_ms: int):
        """Track agent response time"""
        self.response_times.append(response_time_ms)