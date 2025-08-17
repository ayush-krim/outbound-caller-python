#!/usr/bin/env python3
"""
Test script to verify S3 recordings work even when database fails
"""

import asyncio
import json
import os
from livekit import api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env.local")

async def test_call():
    """Fire a test call to verify recording functionality"""
    
    # Initialize LiveKit API
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    # Create a room
    room_name = f"test_recording_{int(time.time())}"
    room = await livekit_api.room.create_room(
        api.CreateRoomRequest(
            name=room_name,
            empty_timeout=30,
            max_participants=2,
        )
    )
    print(f"Created room: {room.name}")
    
    # Dispatch a job to make the call
    dial_info = {
        "phone_number": "+917827470456",
        "transfer_to": "",
        "dispatch_id": f"test_recording_{int(time.time())}",
        "account_info": {
            "customer_name": "Test User",
            "last_4_digits": "1234",
            "total_balance": 47250,
            "emi_amount": 1500,
            "emi_due_date": "2024-01-15",
            "late_fee": 250,
            "apr": 8.75
        }
    }
    
    # Create agent dispatch
    await livekit_api.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            room=room_name,
            agent_name="outbound-caller-local",
            metadata=json.dumps(dial_info),
        )
    )
    
    print(f"Dispatched call to {dial_info['phone_number']}")
    print("Check the agent logs to monitor the call and recording status")
    
    # Wait for the call to complete
    await asyncio.sleep(60)  # Give it a minute for the call
    
    print("Test completed. Check S3 bucket for recordings.")

if __name__ == "__main__":
    import time
    asyncio.run(test_call())