from dotenv import load_dotenv
import os
import json
from livekit import api
import argparse
import asyncio
import uuid
import time

load_dotenv(dotenv_path=".env.local")

server_url = os.getenv("LIVEKIT_URL")
api_key = os.getenv("LIVEKIT_API_KEY")
api_secret = os.getenv("LIVEKIT_API_SECRET")

async def dispatch_job(phone_number: str):
    # Create LiveKit API client
    livekit_api = api.LiveKitAPI(
        server_url,
        api_key=api_key,
        api_secret=api_secret,
    )

    # Create room first (remove + from phone number for room name)
    room_name = f"outbound-{phone_number.replace('+', '')}"
    room_request = api.CreateRoomRequest(name=room_name)
    room = await livekit_api.room.create_room(room_request)
    print(f"Created room: {room.name}")

    # Generate unique IDs for this call
    call_id = str(uuid.uuid4())
    dispatch_id = f"dispatch_{int(time.time())}_{phone_number.replace('+', '')}"
    
    # Dispatch agent to room
    print(f"Dispatching job to call {phone_number}...")
    print(f"Call ID: {call_id}")
    print(f"Dispatch ID: {dispatch_id}")
    
    # Use the agent dispatch method
    dispatch_request = api.CreateAgentDispatchRequest(
        room=room.name,
        agent_name="outbound-caller-local",
        metadata=json.dumps({
            "phone_number": f"+1 507 626 9649,{phone_number}",  # Format: "from_number,to_number"
            "transfer_to": "+1 507 626 9649",
            "call_id": call_id,
            "dispatch_id": dispatch_id,
            "account_info": {
                "customer_name": "John Smith",
                "last_4_digits": "4532",
                "emi_amount": 1500,
                "days_past_due": 15,
                "total_balance": 47250,
                "late_fee": 250,
                "apr": 8.75
            }
        })
    )
    
    dispatch = await livekit_api.agent_dispatch.create_dispatch(dispatch_request)
    print(f"Dispatch created: {dispatch.agent_name} in room {dispatch.room}")
    print(f"Dispatch ID: {dispatch.id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", required=True, help="Phone number to call")
    args = parser.parse_args()
    
    asyncio.run(dispatch_job(args.number))