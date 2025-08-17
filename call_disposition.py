"""
Call Disposition System for Voice AI Agent
Tracks and categorizes call outcomes based on customer responses
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status for the call"""
    CONNECTED = "CONNECTED"
    NOT_CONNECTED = "NOT_CONNECTED"


class CallDisposition(Enum):
    """All possible call dispositions with their connection requirements"""
    
    # CONNECTED dispositions
    USER_CLAIMED_PAYMENT_WITH_DATE = "User Claimed Payment with Payment Date"
    USER_CLAIMED_PAYMENT = "User Claimed Payment"
    USER_AGREES_TO_MAINTAIN_BALANCE = "User Agrees to Maintain Balance"
    AGREE_TO_PAY = "Agree To Pay"
    GENERAL = "General"
    PAYMENT_DUE_REMINDER = "Payment Due Reminder"
    REFUSED_TO_PAY = "Refused to Pay"
    RTP_COUNSELLED = "RTP - Counselled"
    HUMAN_HANDOFF_REQUESTED = "Human Handoff Requested"
    RAISE_DISPUTE_WITH_DETAIL = "Raise Dispute with Detail"
    USER_BUSY_NOW = "User Busy Now"
    NO_RESPONSE = "No Response"
    CUSTOMER_HANGUP = "Customer Hangup"
    DELAY_REASON = "Delay Reason"
    UNCERTAIN_PROPENSITY_TO_PAY = "Uncertain Propensity to Pay"
    ACCEPTABLE_PROMISE_TO_PAY = "Acceptable Promise To Pay"
    UNACCEPTABLE_PROMISE_TO_PAY = "Unacceptable Promise To Pay"
    DO_NOT_CALL = "Do Not Call - Opted Out"
    
    # NOT_CONNECTED dispositions
    BUSY = "Busy"
    FAILED = "Failed"
    NO_ANSWER = "No Answer"


# Mapping of dispositions to their required connection status
DISPOSITION_CONNECTION_MAP = {
    # CONNECTED dispositions
    CallDisposition.USER_CLAIMED_PAYMENT_WITH_DATE: ConnectionStatus.CONNECTED,
    CallDisposition.USER_CLAIMED_PAYMENT: ConnectionStatus.CONNECTED,
    CallDisposition.USER_AGREES_TO_MAINTAIN_BALANCE: ConnectionStatus.CONNECTED,
    CallDisposition.AGREE_TO_PAY: ConnectionStatus.CONNECTED,
    CallDisposition.GENERAL: ConnectionStatus.CONNECTED,
    CallDisposition.PAYMENT_DUE_REMINDER: ConnectionStatus.CONNECTED,
    CallDisposition.REFUSED_TO_PAY: ConnectionStatus.CONNECTED,
    CallDisposition.RTP_COUNSELLED: ConnectionStatus.CONNECTED,
    CallDisposition.HUMAN_HANDOFF_REQUESTED: ConnectionStatus.CONNECTED,
    CallDisposition.RAISE_DISPUTE_WITH_DETAIL: ConnectionStatus.CONNECTED,
    CallDisposition.USER_BUSY_NOW: ConnectionStatus.CONNECTED,
    CallDisposition.NO_RESPONSE: ConnectionStatus.CONNECTED,
    CallDisposition.CUSTOMER_HANGUP: ConnectionStatus.CONNECTED,
    CallDisposition.DELAY_REASON: ConnectionStatus.CONNECTED,
    CallDisposition.UNCERTAIN_PROPENSITY_TO_PAY: ConnectionStatus.CONNECTED,
    CallDisposition.ACCEPTABLE_PROMISE_TO_PAY: ConnectionStatus.CONNECTED,
    CallDisposition.UNACCEPTABLE_PROMISE_TO_PAY: ConnectionStatus.CONNECTED,
    CallDisposition.DO_NOT_CALL: ConnectionStatus.CONNECTED,
    
    # NOT_CONNECTED dispositions
    CallDisposition.BUSY: ConnectionStatus.NOT_CONNECTED,
    CallDisposition.FAILED: ConnectionStatus.NOT_CONNECTED,
    CallDisposition.NO_ANSWER: ConnectionStatus.NOT_CONNECTED,
}


class DispositionAnalyzer:
    """Analyzes conversation to determine appropriate disposition"""
    
    def __init__(self):
        self.payment_keywords = [
            "paid", "payment", "pay", "made payment", "already paid",
            "cleared", "settled", "deposited"
        ]
        self.date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(yesterday|today|tomorrow|last\s+week|last\s+month)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b\d{1,2}(st|nd|rd|th)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b'
        ]
        self.refusal_keywords = [
            "won't pay", "not paying", "refuse", "can't pay", "no money",
            "not my responsibility", "won't", "can't", "unable"
        ]
        self.promise_keywords = [
            "will pay", "promise", "guarantee", "definitely", "surely",
            "tomorrow", "next week", "by", "on"
        ]
        self.dispute_keywords = [
            "dispute", "complaint", "issue", "problem", "error",
            "mistake", "wrong", "incorrect"
        ]
        self.human_agent_keywords = [
            "human", "agent", "person", "representative", "speak to someone",
            "talk to someone", "real person", "supervisor", "manager"
        ]
        self.busy_keywords = [
            "busy", "driving", "meeting", "not free", "call later",
            "bad time", "occupied"
        ]
    
    def analyze_transcript(self, transcript: List[Dict[str, Any]], call_duration: float = 0) -> CallDisposition:
        """
        Analyze the conversation transcript to determine disposition
        
        Args:
            transcript: List of transcript items with speaker and text
            call_duration: Duration of the call in seconds
            
        Returns:
            CallDisposition: The determined disposition
        """
        
        # Combine all customer responses
        customer_text = " ".join([
            item.get("text", "").lower() 
            for item in transcript 
            if item.get("speaker") == "customer"
        ])
        
        # Check for early hangup (less than 10 seconds)
        if call_duration < 10 and call_duration > 0:
            return CallDisposition.CUSTOMER_HANGUP
        
        # No customer response
        if not customer_text.strip():
            return CallDisposition.NO_RESPONSE
        
        # Check for human agent request
        if self._contains_keywords(customer_text, self.human_agent_keywords):
            return CallDisposition.HUMAN_HANDOFF_REQUESTED
        
        # Check for busy status
        if self._contains_keywords(customer_text, self.busy_keywords):
            return CallDisposition.USER_BUSY_NOW
        
        # Check for payment claims
        if self._contains_keywords(customer_text, self.payment_keywords):
            # Check if date is mentioned
            if self._contains_date(customer_text):
                return CallDisposition.USER_CLAIMED_PAYMENT_WITH_DATE
            else:
                return CallDisposition.USER_CLAIMED_PAYMENT
        
        # Check for refusal
        if self._contains_keywords(customer_text, self.refusal_keywords):
            # Check if agent tried to counsel (would need agent responses)
            return CallDisposition.REFUSED_TO_PAY
        
        # Check for promises
        if self._contains_keywords(customer_text, self.promise_keywords):
            # Would need logic to determine if promise is acceptable
            if self._contains_date(customer_text):
                return CallDisposition.ACCEPTABLE_PROMISE_TO_PAY
            else:
                return CallDisposition.AGREE_TO_PAY
        
        # Check for disputes
        if self._contains_keywords(customer_text, self.dispute_keywords):
            return CallDisposition.RAISE_DISPUTE_WITH_DETAIL
        
        # Check for balance maintenance agreement
        if "maintain" in customer_text and "balance" in customer_text:
            return CallDisposition.USER_AGREES_TO_MAINTAIN_BALANCE
        
        # Check for delay reasons
        delay_indicators = ["because", "due to", "reason", "why", "since"]
        if self._contains_keywords(customer_text, delay_indicators) and len(customer_text.split()) > 10:
            return CallDisposition.DELAY_REASON
        
        # If conversation happened but no clear outcome
        if len(customer_text.split()) > 5:
            return CallDisposition.GENERAL
        
        # Default to payment due reminder if agent spoke but customer gave minimal response
        return CallDisposition.PAYMENT_DUE_REMINDER
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _contains_date(self, text: str) -> bool:
        """Check if text contains a date reference"""
        for pattern in self.date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def determine_connection_disposition(self, sip_status: str) -> Optional[CallDisposition]:
        """
        Determine disposition for non-connected calls based on SIP status
        
        Args:
            sip_status: The SIP status or error message
            
        Returns:
            CallDisposition or None if connected
        """
        status_lower = sip_status.lower()
        
        if "busy" in status_lower:
            return CallDisposition.BUSY
        elif "no answer" in status_lower or "timeout" in status_lower:
            return CallDisposition.NO_ANSWER
        elif "failed" in status_lower or "error" in status_lower:
            return CallDisposition.FAILED
        
        return None


class DispositionTracker:
    """Tracks disposition throughout the call lifecycle"""
    
    def __init__(self):
        self.analyzer = DispositionAnalyzer()
        self.current_disposition: Optional[CallDisposition] = None
        self.disposition_history: List[tuple[datetime, CallDisposition]] = []
        self.connection_status: Optional[ConnectionStatus] = None
        self.transcript_items: List[Dict[str, Any]] = []
        self.call_start_time: Optional[datetime] = None
        self.call_connected_time: Optional[datetime] = None
        
    def set_connection_status(self, connected: bool):
        """Set whether the call connected"""
        self.connection_status = ConnectionStatus.CONNECTED if connected else ConnectionStatus.NOT_CONNECTED
        if connected:
            self.call_connected_time = datetime.utcnow()
    
    def add_transcript_item(self, speaker: str, text: str):
        """Add a transcript item for analysis"""
        self.transcript_items.append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def update_disposition(self, force_disposition: Optional[CallDisposition] = None):
        """
        Update the current disposition based on the conversation
        
        Args:
            force_disposition: Optionally force a specific disposition
        """
        if force_disposition:
            self.current_disposition = force_disposition
        else:
            # Calculate call duration
            duration = 0
            if self.call_start_time:
                duration = (datetime.utcnow() - self.call_start_time).total_seconds()
            
            # Analyze transcript
            self.current_disposition = self.analyzer.analyze_transcript(
                self.transcript_items,
                duration
            )
        
        # Add to history
        self.disposition_history.append((datetime.utcnow(), self.current_disposition))
        
    def get_final_disposition(self) -> Dict[str, Any]:
        """Get the final disposition data for the call"""
        return {
            "disposition": self.current_disposition.value if self.current_disposition else None,
            "connection_status": self.connection_status.value if self.connection_status else None,
            "disposition_history": [
                {
                    "timestamp": ts.isoformat(),
                    "disposition": disp.value
                }
                for ts, disp in self.disposition_history
            ],
            "transcript_items": self.transcript_items,
            "call_duration": (
                (datetime.utcnow() - self.call_start_time).total_seconds() 
                if self.call_start_time else 0
            )
        }