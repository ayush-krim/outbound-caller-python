"""
Service for managing interactions table operations
Handles validation and updates for voice call interactions
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from call_disposition import CallDisposition, ConnectionStatus, DISPOSITION_CONNECTION_MAP

logger = logging.getLogger(__name__)


class InteractionService:
    """Service for all interaction table operations"""
    
    @staticmethod
    def map_disposition_to_outcome(disposition: CallDisposition) -> str:
        """Map CallDisposition to InteractionOutcome enum value"""
        mapping = {
            CallDisposition.USER_CLAIMED_PAYMENT_WITH_DATE: "PAYMENT_MADE",
            CallDisposition.USER_CLAIMED_PAYMENT: "PAYMENT_MADE",
            CallDisposition.USER_AGREES_TO_MAINTAIN_BALANCE: "PAYMENT_PROMISED",
            CallDisposition.AGREE_TO_PAY: "PAYMENT_PROMISED",
            CallDisposition.ACCEPTABLE_PROMISE_TO_PAY: "PAYMENT_PROMISED",
            CallDisposition.UNACCEPTABLE_PROMISE_TO_PAY: "WILL_CALL_BACK",
            CallDisposition.REFUSED_TO_PAY: "NOT_INTERESTED",
            CallDisposition.RTP_COUNSELLED: "NOT_INTERESTED",
            CallDisposition.HUMAN_HANDOFF_REQUESTED: "TRANSFERRED_TO_HUMAN",
            CallDisposition.RAISE_DISPUTE_WITH_DETAIL: "DISPUTE_CLAIM",
            CallDisposition.USER_BUSY_NOW: "WILL_CALL_BACK",
            CallDisposition.NO_RESPONSE: "NO_ANSWER",
            CallDisposition.CUSTOMER_HANGUP: "HUNG_UP",
            CallDisposition.DELAY_REASON: "WILL_CALL_BACK",
            CallDisposition.UNCERTAIN_PROPENSITY_TO_PAY: "WILL_CALL_BACK",
            CallDisposition.BUSY: "BUSY",
            CallDisposition.FAILED: "INVALID_NUMBER",
            CallDisposition.NO_ANSWER: "NO_ANSWER",
            CallDisposition.GENERAL: "WILL_CALL_BACK",
            CallDisposition.PAYMENT_DUE_REMINDER: "WILL_CALL_BACK",
        }
        return mapping.get(disposition, "WILL_CALL_BACK")
    
    async def validate_interaction(
        self, 
        session: AsyncSession,
        customer_id: str, 
        organization_id: str, 
        campaign_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate that an interaction exists with NOT_STARTED status
        
        Args:
            session: Database session
            customer_id: Customer ID to validate
            organization_id: Organization ID
            campaign_id: Optional campaign ID
            
        Returns:
            Interaction record dict or None if not found
        """
        try:
            query = """
            SELECT id, status, channel, "customerId", "organizationId", "campaignId"
            FROM interactions 
            WHERE "customerId" = :customer_id 
              AND "organizationId" = :org_id
              AND status = 'NOT_STARTED'
              AND channel = 'VOICE'
            """
            
            params = {
                "customer_id": customer_id,
                "org_id": organization_id
            }
            
            if campaign_id:
                query += ' AND "campaignId" = :campaign_id'
                params["campaign_id"] = campaign_id
                
            query += " LIMIT 1"
            
            result = await session.execute(text(query), params)
            row = result.fetchone()
            
            if row:
                return {
                    "id": str(row.id),
                    "status": row.status,
                    "channel": row.channel,
                    "customerId": row.customerId,
                    "organizationId": row.organizationId,
                    "campaignId": row.campaignId
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating interaction: {e}")
            raise
    
    async def create_interaction(
        self,
        session: AsyncSession,
        customer_id: str,
        organization_id: str,
        agent_id: str,
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new interaction record with NOT_STARTED status
        
        Args:
            session: Database session
            customer_id: Customer ID
            organization_id: Organization ID
            agent_id: Agent ID
            campaign_id: Optional campaign ID
            
        Returns:
            Created interaction record dict
        """
        try:
            # Build insert query
            columns = [
                '"customerId"',
                '"organizationId"',
                '"agentId"',
                'status',
                'channel',
                'direction',
                '"createdAt"',
                '"updatedAt"'
            ]
            values = [
                ':customer_id',
                ':organization_id',
                ':agent_id',
                "'NOT_STARTED'",
                "'VOICE'",
                "'OUTBOUND'",
                'NOW()',
                'NOW()'
            ]
            
            params = {
                "customer_id": customer_id,
                "organization_id": organization_id,
                "agent_id": agent_id
            }
            
            if campaign_id:
                columns.append('"campaignId"')
                values.append(':campaign_id')
                params["campaign_id"] = campaign_id
            
            query = f"""
            INSERT INTO interactions ({', '.join(columns)})
            VALUES ({', '.join(values)})
            RETURNING id, status, channel, "customerId", "organizationId", "campaignId", "agentId"
            """
            
            result = await session.execute(text(query), params)
            row = result.fetchone()
            await session.commit()
            
            if row:
                logger.info(f"Created new interaction {row.id} for customer {customer_id}")
                return {
                    "id": str(row.id),
                    "status": row.status,
                    "channel": row.channel,
                    "customerId": row.customerId,
                    "organizationId": row.organizationId,
                    "campaignId": row.campaignId,
                    "agentId": row.agentId
                }
            
            raise Exception("Failed to create interaction - no row returned")
            
        except Exception as e:
            logger.error(f"Error creating interaction: {e}")
            await session.rollback()
            raise
    
    async def update_interaction_status(
        self, 
        session: AsyncSession,
        interaction_id: str, 
        status: str,
        **kwargs
    ) -> bool:
        """
        Update interaction status and related fields
        
        Args:
            session: Database session
            interaction_id: Interaction ID to update
            status: New status value
            **kwargs: Additional fields to update
            
        Returns:
            True if successful
        """
        try:
            # Build dynamic update query
            update_fields = ['status = :status', '"updatedAt" = NOW()']
            params = {"interaction_id": interaction_id, "status": status}
            
            # Add optional fields
            if 'start_time' in kwargs:
                update_fields.append('"startTime" = :start_time')
                params['start_time'] = kwargs['start_time']
                
            if 'end_time' in kwargs:
                update_fields.append('"endTime" = :end_time')
                params['end_time'] = kwargs['end_time']
            
            query = f"""
            UPDATE interactions 
            SET {', '.join(update_fields)}
            WHERE id = :interaction_id
            """
            
            await session.execute(text(query), params)
            await session.commit()
            
            logger.info(f"Updated interaction {interaction_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating interaction status: {e}")
            await session.rollback()
            raise
    
    async def update_call_started(
        self, 
        session: AsyncSession,
        interaction_id: str, 
        room_name: str, 
        phone_number: str
    ) -> bool:
        """
        Update interaction when call dial starts
        
        Args:
            session: Database session
            interaction_id: Interaction ID
            room_name: LiveKit room name
            phone_number: Phone number being called
            
        Returns:
            True if successful
        """
        try:
            call_disposition = {
                "room_name": room_name,
                "phone_number": phone_number,
                "dial_started_at": datetime.utcnow().isoformat()
            }
            
            query = """
            UPDATE interactions 
            SET 
                status = 'IN_PROGRESS',
                "startTime" = NOW(),
                "callDisposition" = CAST(:call_disposition AS jsonb),
                "updatedAt" = NOW()
            WHERE id = :interaction_id
            """
            
            await session.execute(text(query), {
                "call_disposition": json.dumps(call_disposition),
                "interaction_id": interaction_id
            })
            await session.commit()
            
            logger.info(f"Updated interaction {interaction_id} - call started")
            return True
            
        except Exception as e:
            logger.error(f"Error updating call started: {e}")
            await session.rollback()
            raise
    
    async def update_call_connected(
        self, 
        session: AsyncSession,
        interaction_id: str
    ) -> bool:
        """
        Update interaction when call connects
        
        Args:
            session: Database session
            interaction_id: Interaction ID
            
        Returns:
            True if successful
        """
        try:
            query = """
            UPDATE interactions 
            SET 
                "rightPartyVerified" = true,
                "connectionStability" = 1.0,
                "updatedAt" = NOW(),
                "callDisposition" = jsonb_set(
                    COALESCE("callDisposition", '{}'),
                    '{connected_at}',
                    to_jsonb(:connected_at::text)
                )
            WHERE id = :interaction_id
            """
            
            await session.execute(text(query), {
                "connected_at": datetime.utcnow().isoformat(),
                "interaction_id": interaction_id
            })
            await session.commit()
            
            logger.info(f"Updated interaction {interaction_id} - call connected")
            return True
            
        except Exception as e:
            logger.error(f"Error updating call connected: {e}")
            await session.rollback()
            raise
    
    async def update_call_completed(
        self, 
        session: AsyncSession,
        interaction_id: str,
        disposition_data: Dict[str, Any],
        transcript: List[Dict[str, Any]],
        duration: int,
        recording_url: Optional[str] = None
    ) -> bool:
        """
        Update interaction when call completes with all data
        
        Args:
            session: Database session
            interaction_id: Interaction ID
            disposition_data: Full disposition data from tracker
            transcript: Call transcript
            duration: Call duration in seconds
            recording_url: Optional recording URL
            
        Returns:
            True if successful
        """
        try:
            # Extract disposition value
            disposition_value = disposition_data.get('disposition')
            if disposition_value:
                # Convert string back to enum if needed
                disposition = next(
                    (d for d in CallDisposition if d.value == disposition_value),
                    CallDisposition.GENERAL
                )
                outcome = self.map_disposition_to_outcome(disposition)
            else:
                outcome = "WILL_CALL_BACK"
            
            # Build disposition notes
            disposition_notes = f"""DISPOSITION: {disposition_value}
CONNECTION_STATUS: {disposition_data.get('connection_status', 'UNKNOWN')}
CALL_DURATION: {duration} seconds
DISPOSITION_TIME: {datetime.utcnow().isoformat()}"""
            
            # Determine flags based on disposition
            payment_discussed = disposition_value and any(
                keyword in disposition_value.lower() 
                for keyword in ['payment', 'pay', 'paid', 'emi']
            )
            
            dispute_raised = disposition_value and 'dispute' in disposition_value.lower()
            
            follow_up_required = disposition_value and any(
                keyword in disposition_value.lower()
                for keyword in ['promise', 'will call', 'busy', 'uncertain']
            )
            
            # Update call disposition JSON
            call_disposition = disposition_data.get('callDisposition', {})
            if isinstance(call_disposition, str):
                call_disposition = json.loads(call_disposition)
            
            call_disposition.update({
                "completed_at": datetime.utcnow().isoformat(),
                "final_disposition": disposition_value,
                "duration_seconds": duration
            })
            
            query = """
            UPDATE interactions 
            SET 
                status = 'COMPLETED',
                outcome = :outcome,
                "endTime" = NOW(),
                duration = :duration,
                transcript = CAST(:transcript AS jsonb),
                recording = :recording,
                notes = :notes,
                "callDisposition" = CAST(:call_disposition AS jsonb),
                "paymentDiscussed" = :payment_discussed,
                "disputeRaised" = :dispute_raised,
                "followUpRequired" = :follow_up_required,
                "updatedAt" = NOW()
            WHERE id = :interaction_id
            """
            
            await session.execute(text(query), {
                "outcome": outcome,
                "duration": duration,
                "transcript": json.dumps(transcript),
                "recording": recording_url,
                "notes": disposition_notes,
                "call_disposition": json.dumps(call_disposition),
                "payment_discussed": payment_discussed,
                "dispute_raised": dispute_raised,
                "follow_up_required": follow_up_required,
                "interaction_id": interaction_id
            })
            await session.commit()
            
            logger.info(f"Updated interaction {interaction_id} - call completed with disposition: {disposition_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating call completed: {e}")
            await session.rollback()
            raise
    
    async def update_call_failed(
        self, 
        session: AsyncSession,
        interaction_id: str,
        reason: str,
        sip_status: Optional[str] = None
    ) -> bool:
        """
        Update interaction when call fails
        
        Args:
            session: Database session
            interaction_id: Interaction ID
            reason: Failure reason/disposition
            sip_status: Optional SIP status message
            
        Returns:
            True if successful
        """
        try:
            # Map reason to outcome
            outcome_mapping = {
                "Busy": "BUSY",
                "No Answer": "NO_ANSWER",
                "Failed": "INVALID_NUMBER"
            }
            outcome = outcome_mapping.get(reason, "INVALID_NUMBER")
            
            # Build failure notes
            notes = f"""DISPOSITION: {reason}
CONNECTION_STATUS: NOT_CONNECTED
SIP_STATUS: {sip_status or 'Unknown'}
FAILED_AT: {datetime.utcnow().isoformat()}"""
            
            call_disposition = {
                "failed_at": datetime.utcnow().isoformat(),
                "failure_reason": reason,
                "sip_status": sip_status
            }
            
            query = """
            UPDATE interactions 
            SET 
                status = 'FAILED',
                outcome = :outcome,
                "endTime" = NOW(),
                duration = 0,
                notes = :notes,
                "callDisposition" = CAST(:call_disposition AS jsonb),
                "updatedAt" = NOW()
            WHERE id = :interaction_id
            """
            
            await session.execute(text(query), {
                "outcome": outcome,
                "notes": notes,
                "call_disposition": json.dumps(call_disposition),
                "interaction_id": interaction_id
            })
            await session.commit()
            
            logger.info(f"Updated interaction {interaction_id} - call failed: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating call failed: {e}")
            await session.rollback()
            raise
