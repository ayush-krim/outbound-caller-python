#!/usr/bin/env python3
import asyncio
import os
from livekit import api
from dotenv import load_dotenv
import json

load_dotenv(dotenv_path=".env.local")

async def test_dispatch():
    # Create API client
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    
    room_name = "test-room-debt-collection"
    
    # Create room
    print(f"Creating room: {room_name}")
    room_request = api.CreateRoomRequest(name=room_name)
    room = await livekit_api.room.create_room(room_request)
    print(f"Room created: {room.name}")
    
    # Create agent dispatch
    print("Creating agent dispatch...")
    metadata = {
        "phone_number": "+15076269649,+917827470456",
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
    
    dispatch_request = api.CreateAgentDispatchRequest(
        room=room_name,
        agent_name="outbound-caller-local",
        metadata=json.dumps(metadata)
    )
    
    dispatch = await livekit_api.agent_dispatch.create_dispatch(dispatch_request)
    print(f"Dispatch created: {dispatch.agent_name} in room {dispatch.room}")
    print(f"Dispatch ID: {dispatch.id}")
    
    # List dispatches
    print("\nListing dispatches...")
    list_request = api.ListAgentDispatchRequest(room=room_name)
    dispatches = await livekit_api.agent_dispatch.list_dispatch(list_request)
    
    for d in dispatches:
        print(f"  - {d.id}: {d.agent_name} (state: {d.state})")

if __name__ == "__main__":
    asyncio.run(test_dispatch())