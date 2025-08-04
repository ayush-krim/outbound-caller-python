#!/usr/bin/env python3
import asyncio
import os
from livekit import api
from dotenv import load_dotenv
import json

load_dotenv(dotenv_path=".env.local")

async def test_call():
    # Phone number to call
    phone_number = "+917827470456"
    
    # Create API client
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    
    room_name = f"outbound-{phone_number}"
    
    # Create room
    print(f"Creating room: {room_name}")
    room_request = api.CreateRoomRequest(name=room_name)
    room = await livekit_api.room.create_room(room_request)
    print(f"Room created: {room.name}")
    
    # Create dispatch with debt collection metadata
    metadata = {
        "phone_number": f"+15076269649,{phone_number}",
        "transfer_to": "+15076269649",
        "account_info": {
            "customer_name": "John Smith",
            "last_4_digits": "4532",
            "emi_amount": 1500,
            "days_past_due": 15,
            "total_balance": 47250,
            "late_fee": 250,
            "apr": 8.75
        }
    }
    
    print("Creating dispatch for debt collection call...")
    dispatch_request = api.CreateAgentDispatchRequest(
        room=room_name,
        agent_name="",  # Let system auto-assign
        metadata=json.dumps(metadata)
    )
    
    dispatch = await livekit_api.agent_dispatch.create_dispatch(dispatch_request)
    print(f"Dispatch created successfully!")
    print(f"Room: {room_name}")
    print(f"Customer: John Smith")
    print(f"Account: ***4532")
    print(f"Amount Due: $1500 (15 days past due)")
    print("\nThe agent will call and start the debt collection conversation.")

if __name__ == "__main__":
    asyncio.run(test_call())