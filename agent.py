from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
from typing import Any
import time
from datetime import datetime
import wave
import struct
import uuid

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    JobRequest,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    RoomInputOptions,
    llm,
)
from livekit.plugins import (
    deepgram,
    openai,
    cartesia,
    silero,
    noise_cancellation,  # noqa: F401
)
from livekit.plugins.turn_detector.english import EnglishModel

# from database.recording_manager import RecordingManager  # Depends on removed tables
from database.config import init_db, async_session
# from database.models import Call  # Table removed
from database.interaction_service import InteractionService
from call_disposition import DispositionTracker, CallDisposition
from services.agent_instructions import AgentInstructions


# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")



class OutboundCaller(Agent):
    def __init__(
        self,
        *,
        name: str,
        appointment_time: str,
        dial_info: dict[str, Any],
    ):
        # Determine time of day
        current_hour = datetime.now().hour
        time_of_day = "morning" if current_hour < 12 else "afternoon" if current_hour < 17 else "evening"
        
        # Extract account info from dial_info if available
        account_info = dial_info.get('account_info', {})
        customer_name = account_info.get('customer_name', name)
        last_4_digits = account_info.get('last_4_digits', '0000')
        emi_amount = account_info.get('emi_amount', 1500)
        
        # Extract account details
        late_fee = account_info.get('late_fee', 250)  # Default late fee
        
        # Calculate days past due from emi_due_date
        emi_due_date_str = account_info.get('emi_due_date', '')
        days_past_due = 30  # Default
        if emi_due_date_str:
            try:
                emi_due_date = datetime.strptime(emi_due_date_str, '%Y-%m-%d')
                days_diff = (datetime.now() - emi_due_date).days
                if days_diff < 0:
                    # Future date - not yet due
                    days_past_due = 0
                else:
                    days_past_due = days_diff
            except ValueError:
                days_past_due = 30  # Default if date parsing fails
        
        # Initialize transcript tracking
        self.transcript_items = []
        # Initialize audio tracking
        self.audio_frames = []
        self.audio_stream = None
        self.audio_data = []  # Store actual audio data
        
        # Recording manager will be set by entrypoint
        # self.recording_manager = None  # Disabled - tables removed
        self.call_id = None
        self.egress_id = None
        
        # Initialize disposition tracker
        self.disposition_tracker = DispositionTracker()
        self.disposition_tracker.call_start_time = datetime.now()
        
        # Extract interaction_id and other platform data
        self.interaction_id = dial_info.get('interaction_id')
        self.customer_id = dial_info.get('customer_id')
        self.organization_id = dial_info.get('organization_id')
        self.campaign_id = dial_info.get('campaign_id')
        self.agent_id = dial_info.get('agent_id')
        
        # Initialize interaction service
        self.interaction_service = InteractionService()
        
        # Load dynamic instructions based on agent_id
        instruction_service = AgentInstructions()
        
        # Prepare customer info for instruction formatting
        customer_info = {
            "customer_name": customer_name,
            "last_4_digits": last_4_digits,
            "emi_amount": emi_amount,
            "days_past_due": days_past_due,
            "late_fee": late_fee
        }
        
        # Get formatted instructions for this agent (uses base only if not found)
        agent_id = dial_info.get('agent_id', None)  # Don't default to AGENT_001
        formatted_instructions = instruction_service.get_instructions(agent_id, customer_info)
        
        super().__init__(
            instructions=formatted_instructions
        )
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.dial_info = dial_info
        self.start_time = time.time()

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant
        # Start 180 second timer when participant joins
        asyncio.create_task(self._timeout_handler())
        # Start audio capture
        asyncio.create_task(self._capture_audio(participant))

    async def hangup(self):
        """Helper function to hang up the call by deleting the room"""

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @function_tool()
    async def transfer_call(self, ctx: RunContext):
        """Transfer the call to a human agent, called after confirming with the user"""

        transfer_to = self.dial_info["transfer_to"]
        if not transfer_to:
            return "cannot transfer call"

        logger.info(f"transferring call to {transfer_to}")

        # let the message play fully before transferring
        await ctx.session.generate_reply(
            instructions="let the user know you'll be transferring them"
        )

        job_ctx = get_job_context()
        try:
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=self.participant.identity,
                    transfer_to=f"tel:{transfer_to}",
                )
            )

            logger.info(f"transferred call to {transfer_to}")
        except Exception as e:
            logger.error(f"error transferring call: {e}")
            await ctx.session.generate_reply(
                instructions="there was an error transferring the call."
            )
            await self.hangup()

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Called when the user wants to end the call"""
        logger.info(f"ending the call for {self.participant.identity}")

        # let the agent finish speaking
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

    @function_tool()
    async def opt_out_future_calls(self, ctx: RunContext):
        """Called when the user says 'stop', 'stop calling' or requests to stop future calls"""
        logger.info(f"User requested to opt out of future calls: {self.participant.identity}")
        
        # Acknowledge the opt-out request
        await ctx.session.generate_reply(
            instructions="Acknowledge that you've noted their request to stop future calls and confirm it will be processed."
        )
        
        # TODO: Here you would typically update the database to mark this customer as opted-out
        # For now, we'll just log it and end the call
        
        # Mark disposition as opted out
        self.disposition_tracker.update_disposition(CallDisposition.DO_NOT_CALL)
        
        # End the call after acknowledgment
        await self.end_call(ctx)

    @function_tool()
    async def check_account_balance(
        self,
        ctx: RunContext,
    ):
        """Called when customer asks about their account details, balance, payment history, interest rate, APR, or any account-related information"""
        account_info = self.dial_info.get('account_info', {})
        logger.info(f"checking account balance for {self.participant.identity}")
        
        total_balance = account_info.get('total_balance', 47250)
        emi_amount = account_info.get('emi_amount', 1500)
        late_fee = account_info.get('late_fee', 250)
        apr = account_info.get('apr', 8.75)
        
        return f"Total balance: ${total_balance}. Past due monthly payment: ${emi_amount}. Late fee: ${late_fee}. APR: {apr}%"

    @function_tool()
    async def process_payment(
        self,
        ctx: RunContext,
        amount: float,
        payment_type: str = "full",
    ):
        """Called when customer agrees to make a payment
        
        Args:
            amount: Payment amount in dollars
            payment_type: Type of payment - 'full', 'partial', or 'plan'
        """
        logger.info(
            f"processing {payment_type} payment of ${amount} for {self.participant.identity}"
        )
        # In production, this would integrate with payment gateway
        return f"Payment of ${amount} processed successfully. Confirmation number: PAY{int(time.time())}"

    @function_tool()
    async def schedule_followup(
        self,
        ctx: RunContext,
        date: str,
        amount: float,
    ):
        """Called when customer needs time to arrange funds
        
        Args:
            date: When to follow up
            amount: Expected payment amount
        """
        logger.info(
            f"scheduling followup with {self.participant.identity} on {date} for ${amount}"
        )
        return f"Followup scheduled for {date}. We'll call about your ${amount} payment."

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()

    async def _timeout_handler(self):
        """Automatically hang up the call after 180 seconds"""
        await asyncio.sleep(180)
        logger.info("Call reached 180 second limit, hanging up")
        await self.hangup()
    
    async def _capture_audio(self, participant: rtc.RemoteParticipant):
        """Capture audio frames from the participant"""
        try:
            # Wait for audio track to be available
            audio_track = None
            for _ in range(10):  # Try for 10 seconds
                for track in participant.track_publications.values():
                    if track.track and track.track.kind == rtc.TrackKind.KIND_AUDIO:
                        audio_track = track.track
                        break
                if audio_track:
                    break
                await asyncio.sleep(1)
            
            if not audio_track:
                logger.warning("No audio track found for participant")
                return
                
            logger.info(f"Starting audio capture from {participant.identity}")
            
            # Create audio stream
            self.audio_stream = rtc.AudioStream(
                track=audio_track,
                sample_rate=16000,  # 16kHz for voice
                num_channels=1
            )
            
            frame_count = 0
            async for audio_frame_event in self.audio_stream:
                frame_count += 1
                # Log every 100th frame to avoid flooding logs
                if frame_count % 100 == 0:
                    logger.info(f"[AUDIO] Captured {frame_count} audio frames")
                
                # Store the actual audio data
                if hasattr(audio_frame_event.frame, 'data'):
                    # Get the audio data as bytes
                    audio_bytes = audio_frame_event.frame.data
                    self.audio_data.append(audio_bytes)
                
                # Store frame metadata (limit storage to prevent memory issues)
                if len(self.audio_frames) < 1000:  # Store first 1000 frames as sample
                    self.audio_frames.append({
                        "timestamp": datetime.now().isoformat(),
                        "frame_number": frame_count,
                        "samples": audio_frame_event.frame.samples_per_channel,
                        "sample_rate": audio_frame_event.frame.sample_rate,
                        "channels": audio_frame_event.frame.num_channels
                    })
                    
        except Exception as e:
            logger.error(f"Error capturing audio: {e}")


async def entrypoint(ctx: JobContext):
    # Load environment variables for job subprocess
    load_dotenv(dotenv_path=".env.local")
    
    start_time = time.time()
    logger.info(f"[TIMING] Starting entrypoint for room {ctx.room.name}")
    
    # Initialize LiveKit API
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    # Initialize database
    database_enabled = True  # Enable database for interaction tracking
    if database_enabled:
        try:
            await init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            # Continue without database functionality
    
    room_conn_start = time.time()
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()
    room_conn_time = time.time() - room_conn_start
    logger.info(f"[TIMING] Room connection: {room_conn_time:.3f}s")

    # when dispatching the agent, we'll pass it the approriate info to dial the user
    # dial_info is a dict with the following keys:
    # - phone_number: the phone number to dial
    # - transfer_to: the phone number to transfer the call to when requested
    # - call_id: unique ID for this call (optional, will be generated if not provided)
    dial_info = json.loads(ctx.job.metadata)
    
    # Generate or use provided call ID
    call_id = dial_info.get('call_id', str(uuid.uuid4()))
    dispatch_id = dial_info.get('dispatch_id', f"dispatch_{int(time.time())}")
    
    # Extract the actual phone number to dial (format: "from_number,to_number")
    phone_number_parts = dial_info["phone_number"].split(",")
    if len(phone_number_parts) == 2:
        from_number, to_number = phone_number_parts
        participant_identity = phone_number = to_number.strip()
    else:
        participant_identity = phone_number = dial_info["phone_number"]

    # Call record creation removed - using interactions table instead
    # if database_enabled:
    #     # Call table has been removed
    
    # look up the user's phone number and appointment details
    agent_create_start = time.time()
    agent = OutboundCaller(
        name="Jayden",
        appointment_time="next Tuesday at 3pm",
        dial_info=dial_info,
    )
    agent.call_id = call_id
    agent_create_time = time.time() - agent_create_start
    logger.info(f"[TIMING] Agent creation: {agent_create_time:.3f}s")
    
    # Initialize recording manager - DISABLED (tables removed)
    # recording_manager = RecordingManager(livekit_api)
    # await recording_manager.initialize()
    # agent.recording_manager = recording_manager

    # ULTRA-FAST: Use OpenAI Realtime API (speech-to-speech)
    session_create_start = time.time()
    session = AgentSession(
        # Single model handles everything - eliminates pipeline delays
        llm=openai.realtime.RealtimeModel(
            voice="alloy",  # Young American female voice
        ),
    )
    session_create_time = time.time() - session_create_start
    logger.info(f"[TIMING] Session creation: {session_create_time:.3f}s")
    
    # Set up transcript capture event handlers
    @session.on("user_input_transcribed")
    def on_user_transcribed(event):
        timestamp = datetime.now().isoformat()
        # Check for the correct attribute name
        text = getattr(event, 'content', None) or getattr(event, 'transcript', None) or str(event)
        logger.info(f"[TRANSCRIPT] User ({timestamp}): {text}")
        agent.transcript_items.append({
            "timestamp": timestamp,
            "speaker": "user",
            "text": text
        })
        # Track for disposition
        agent.disposition_tracker.add_transcript_item("customer", text)
        agent.disposition_tracker.update_disposition()
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        timestamp = datetime.now().isoformat()
        if hasattr(event.item, 'role') and hasattr(event.item, 'text_content'):
            role = event.item.role
            text = event.item.text_content
            logger.info(f"[TRANSCRIPT] {role} ({timestamp}): {text}")
            agent.transcript_items.append({
                "timestamp": timestamp,
                "speaker": role,
                "text": text
            })
            # Track for disposition based on speaker
            if role.lower() in ['user', 'customer']:
                agent.disposition_tracker.add_transcript_item("customer", text)
                agent.disposition_tracker.update_disposition()
            elif role.lower() in ['assistant', 'agent']:
                agent.disposition_tracker.add_transcript_item("agent", text)
    
    @session.on("close")
    def on_session_close(event):
        # Create async task for the async operations
        asyncio.create_task(_handle_session_close(agent, ctx, start_time, call_id, phone_number, database_enabled))
    
    async def _handle_session_close(agent, ctx, start_time, call_id, phone_number, database_enabled):
        # Print full transcript when session closes
        logger.info("=== FULL CALL TRANSCRIPT ===")
        for item in agent.transcript_items:
            logger.info(f"{item['speaker']} ({item['timestamp']}): {item['text']}")
        logger.info("=== END TRANSCRIPT ===")
        
        # Also print the conversation history from session
        logger.info("=== SESSION HISTORY ===")
        try:
            history = session.history
            if history and hasattr(history, 'messages'):
                for msg in history.messages:
                    logger.info(f"{msg.role}: {msg.content}")
            elif history:
                logger.info(f"History object: {history}")
        except Exception as e:
            logger.error(f"Error accessing session history: {e}")
            
        # Get final disposition
        final_disposition = agent.disposition_tracker.get_final_disposition()
        logger.info(f"Final call disposition: {final_disposition['disposition']}")
        
        # Update interaction with final disposition and data
        if agent.interaction_id:
            try:
                # Calculate duration
                duration = int(time.time() - start_time)
                
                # Get recording URL if available
                recording_url = None
                if agent.egress_id and False:  # recording_manager disabled
                    # Recording URL would be available from recording manager
                    # This is a placeholder - actual implementation depends on recording manager
                    pass
                
                async with async_session() as session:
                    await agent.interaction_service.update_call_completed(
                        session,
                        interaction_id=agent.interaction_id,
                        disposition_data=final_disposition,
                        transcript=agent.transcript_items,
                        duration=duration,
                        recording_url=recording_url
                    )
                    logger.info(f"Updated interaction {agent.interaction_id} - call completed")
            except Exception as e:
                logger.error(f"Failed to update interaction on completion: {e}")
        
        # Save transcript to file
        try:
            transcript_filename = f"transcript_{ctx.room.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(transcript_filename, 'w') as f:
                json.dump({
                    "room_name": ctx.room.name,
                    "phone_number": phone_number,
                    "transcript": agent.transcript_items,
                    "disposition": final_disposition,
                    "audio_frames_captured": len(agent.audio_frames),
                    "audio_frame_samples": agent.audio_frames[:10] if agent.audio_frames else [],  # Save first 10 frames as sample
                    "call_start": start_time,
                    "call_end": time.time()
                }, f, indent=2)
            logger.info(f"Transcript saved to {transcript_filename}")
            logger.info(f"[AUDIO SUMMARY] Total audio frames captured: {len(agent.audio_frames)}")
            
            # Save audio data as WAV file if we have any
            if agent.audio_data:
                try:
                    audio_filename = f"audio_{ctx.room.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                    
                    # Combine all audio bytes
                    all_audio_bytes = b''.join(agent.audio_data)
                    
                    # Create WAV file
                    with wave.open(audio_filename, 'wb') as wav_file:
                        wav_file.setnchannels(1)  # Mono
                        wav_file.setsampwidth(2)  # 16-bit audio (2 bytes)
                        wav_file.setframerate(16000)  # 16kHz
                        wav_file.writeframes(all_audio_bytes)
                    
                    logger.info(f"[AUDIO] Saved audio recording to {audio_filename}")
                    logger.info(f"[AUDIO] Total audio data size: {len(all_audio_bytes)} bytes")
                    logger.info(f"[AUDIO] Duration: {len(all_audio_bytes) / (16000 * 2):.2f} seconds")
                except Exception as e:
                    logger.error(f"Error saving audio file: {e}")
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
        
        # Stop recording if it was started
        if agent.egress_id:
            try:
                # await agent.recording_manager.stop_recording(agent.egress_id)  # Disabled
                logger.info(f"Stopped recording: {agent.egress_id}")
            except Exception as e:
                logger.error(f"Failed to stop recording: {e}")
        
        # Update call status to completed
        if database_enabled:
            try:
                async with async_session() as db_session:
                    from sqlalchemy import update
                    duration = int(time.time() - start_time)
                    stmt = update(Call).where(Call.id == call_id).values(
                        status="completed",
                        ended_at=datetime.utcnow(),
                        duration_seconds=duration
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()
                    logger.info(f"Updated call record as completed with duration: {duration}s")
            except Exception as e:
                logger.error(f"Failed to update call record: {e}")

    # start the session first before dialing, to ensure that when the user picks up
    # the agent does not miss anything the user says
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                # enable Krisp background voice and noise removal
                # OPTIMIZATION 1: Removed noise cancellation
            ),
        )
    )

    # Update interaction when call starts
    if agent.interaction_id:
        try:
            async with async_session() as session:
                await agent.interaction_service.update_call_started(
                    session,
                    interaction_id=agent.interaction_id,
                    room_name=ctx.room.name,
                    phone_number=phone_number
                )
                logger.info(f"Updated interaction {agent.interaction_id} - call started")
        except Exception as e:
            logger.error(f"Failed to update interaction on call start: {e}")
    
    # `create_sip_participant` starts dialing the user
    try:
        sip_dial_start = time.time()
        logger.info(f"[TIMING] Starting SIP dial to {phone_number}")
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # function blocks until user answers the call, or if the call fails
                wait_until_answered=True,
            )
        )
        sip_dial_time = time.time() - sip_dial_start
        logger.info(f"[TIMING] SIP dial completed: {sip_dial_time:.3f}s")

        # wait for the agent session start and participant join
        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        agent.set_participant(participant)
        
        # Mark call as connected for disposition
        agent.disposition_tracker.set_connection_status(connected=True)
        
        # Update interaction when call connects
        if agent.interaction_id:
            try:
                async with async_session() as session:
                    await agent.interaction_service.update_call_connected(
                        session,
                        interaction_id=agent.interaction_id
                    )
                    logger.info(f"Updated interaction {agent.interaction_id} - call connected")
            except Exception as e:
                logger.error(f"Failed to update interaction on connect: {e}")
        
        # Update call status to connected
        if database_enabled:
            try:
                async with async_session() as db_session:
                    from sqlalchemy import update
                    stmt = update(Call).where(Call.id == call_id).values(
                        status="connected",
                        connected_at=datetime.utcnow()
                    )
                    await db_session.execute(stmt)
                    await db_session.commit()
            except Exception as e:
                logger.error(f"Failed to update call status: {e}")
        
        # Start recording
        try:
            # egress_id = await recording_manager.start_room_recording(
            #     room_name=ctx.room.name,
            #     call_id=call_id)  # Disabled - tables removed
            egress_id = None
            if egress_id:
                agent.egress_id = egress_id
                logger.info(f"Started recording with egress_id: {egress_id}")
            else:
                logger.warning("Recording failed to start - egress may not be enabled")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            # Check if it's a billing error
            if "billing" in str(e).lower() or "payment" in str(e).lower():
                logger.warning("Egress recording requires billing to be enabled on your LiveKit account")
        
        total_time = time.time() - start_time
        logger.info(f"[TIMING] Total connection time: {total_time:.3f}s")
        logger.info(f"[TIMING BREAKDOWN] Room: {room_conn_time:.3f}s, Agent: {agent_create_time:.3f}s, Session: {session_create_time:.3f}s, SIP: {sip_dial_time:.3f}s")

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        
        # Handle disposition for failed calls
        agent.disposition_tracker.set_connection_status(connected=False)
        sip_status = e.metadata.get('sip_status', '')
        
        # Determine disposition based on SIP status
        if "busy" in sip_status.lower():
            agent.disposition_tracker.update_disposition(CallDisposition.BUSY)
        elif "no answer" in sip_status.lower() or "timeout" in sip_status.lower():
            agent.disposition_tracker.update_disposition(CallDisposition.NO_ANSWER)
        else:
            agent.disposition_tracker.update_disposition(CallDisposition.FAILED)
        
        # Log final disposition
        final_disposition = agent.disposition_tracker.get_final_disposition()
        logger.info(f"Call disposition: {final_disposition['disposition']}")
        
        # Update interaction for failed call
        if agent.interaction_id:
            try:
                async with async_session() as session:
                    await agent.interaction_service.update_call_failed(
                        session,
                        interaction_id=agent.interaction_id,
                        reason=final_disposition['disposition'] or "Failed",
                        sip_status=sip_status
                    )
                    logger.info(f"Updated interaction {agent.interaction_id} - call failed")
            except Exception as e:
                logger.error(f"Failed to update interaction on failure: {e}")
        
        ctx.shutdown()

async def job_request(job_req: JobRequest) -> None:
      """Handle incoming job requests"""
      logger.info(f"[JOB_REQUEST] Received job request for room: {job_req.room.name}")
      logger.info(f"[JOB_REQUEST] Agent name: {job_req.agent_name}")
      if hasattr(job_req, 'job') and job_req.job and hasattr(job_req.job, 'metadata'):
          logger.info(f"[JOB_REQUEST] Job metadata: {job_req.job.metadata}")
      # Accept all job requests for our agent
      await job_req.accept()

if __name__ == "__main__":
    # Add logging to see what's happening
    logger.info("Starting agent worker...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    logger.info(f"Agent name: outbound-caller-local")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller-local",
            request_fnc=job_request,
        )
    )
