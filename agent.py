from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
from typing import Any
import time
from datetime import datetime

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    RoomInputOptions,
)
from livekit.plugins import (
    deepgram,
    openai,
    cartesia,
    silero,
    noise_cancellation,  # noqa: F401
)
from livekit.plugins.turn_detector.english import EnglishModel


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
        days_past_due = account_info.get('days_past_due', 30)
        
        super().__init__(
            instructions=f"""
            You are Sarah from XYZ Bank calling about overdue monthly payment.
            
            CRITICAL: Be concise. Short responses. Natural conversation.
            
            Customer: {customer_name}
            Account: ***{last_4_digits}
            Overdue: ${emi_amount} ({days_past_due} days)
            Minimum payment: ${emi_amount * 0.5} (50% of monthly payment)
            
            CONVERSATION STEPS:
            1. "Good {time_of_day}, this is Sarah from XYZ Bank. Am I speaking with {customer_name}?"
            2. "Your monthly payment of ${emi_amount} is past due. Can we resolve this today?"
            3. Listen to their situation briefly
            4. Offer ONE solution at a time:
               - Full payment today
               - Partial payment now
               - Payment plan
            
            NEGOTIATION RULES:
            - If customer asks for more than 2 days: "I understand you need time. How about we settle this within 2 days instead?"
            - If customer says they can't pay full amount: "I hear you. Let's work together - can you manage ${emi_amount * 0.5} today?"
            - Minimum acceptable payment is 50% (${emi_amount * 0.5}). If offered less: "I appreciate the effort, but we need at least ${emi_amount * 0.5} to help your account."
            - If customer mentions hardship: "I'm sorry to hear that. Let me see how I can help. Can you manage even ${emi_amount * 0.5} to keep your account active?"
            - If customer says they'll pay online: "Perfect! I'll share the payment link right now."
            
            RESPONSES MUST BE:
            - Under 2 sentences
            - Empathetic but persuasive
            - Focus on immediate action
            
            If asked about account details, use check_account_balance tool.
            If they agree to pay, use process_payment tool.
            Only use transfer_call tool AFTER trying to help with hardship cases first.
            
            NEVER lecture. NEVER threaten. Keep it conversational.
            """
        )
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.dial_info = dial_info
        self.start_time = time.time()

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant
        # Start 180 second timer when participant joins
        asyncio.create_task(self._timeout_handler())

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
    async def check_account_balance(
        self,
        ctx: RunContext,
    ):
        """Called when customer asks about their account details, balance, or payment history"""
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


async def entrypoint(ctx: JobContext):
    start_time = time.time()
    logger.info(f"[TIMING] Starting entrypoint for room {ctx.room.name}")
    
    room_conn_start = time.time()
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()
    room_conn_time = time.time() - room_conn_start
    logger.info(f"[TIMING] Room connection: {room_conn_time:.3f}s")

    # when dispatching the agent, we'll pass it the approriate info to dial the user
    # dial_info is a dict with the following keys:
    # - phone_number: the phone number to dial
    # - transfer_to: the phone number to transfer the call to when requested
    dial_info = json.loads(ctx.job.metadata)
    
    # Extract the actual phone number to dial (format: "from_number,to_number")
    phone_number_parts = dial_info["phone_number"].split(",")
    if len(phone_number_parts) == 2:
        from_number, to_number = phone_number_parts
        participant_identity = phone_number = to_number.strip()
    else:
        participant_identity = phone_number = dial_info["phone_number"]

    # look up the user's phone number and appointment details
    agent_create_start = time.time()
    agent = OutboundCaller(
        name="Jayden",
        appointment_time="next Tuesday at 3pm",
        dial_info=dial_info,
    )
    agent_create_time = time.time() - agent_create_start
    logger.info(f"[TIMING] Agent creation: {agent_create_time:.3f}s")

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
        
        total_time = time.time() - start_time
        logger.info(f"[TIMING] Total connection time: {total_time:.3f}s")
        logger.info(f"[TIMING BREAKDOWN] Room: {room_conn_time:.3f}s, Agent: {agent_create_time:.3f}s, Session: {session_create_time:.3f}s, SIP: {sip_dial_time:.3f}s")

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller-local",
        )
    )