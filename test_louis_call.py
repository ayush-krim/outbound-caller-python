#!/usr/bin/env python3
"""
Test script to call Louis at +15103455686
"""

import asyncio
import json
import os
import time
from livekit import api
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env.local")

async def call_louis():
    """Fire a test call to Louis"""
    
    # Initialize LiveKit API
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        os.getenv("LIVEKIT_API_KEY"),
        os.getenv("LIVEKIT_API_SECRET"),
    )
    
    # Create a room
    room_name = f"louis_call_{int(time.time())}"
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
        "phone_number": "+15103455686",
        "transfer_to": "",
        "dispatch_id": f"louis_{int(time.time())}",
        "account_info": {
            "customer_name": "Louis",
            "last_4_digits": "5678",
            "total_balance": 35000,
            "emi_amount": 2500,
            "emi_due_date": "2024-12-15",
            "late_fee": 350,
            "apr": 9.25
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
    
    print(f"Dispatched call to {dial_info['phone_number']} for customer: {dial_info['account_info']['customer_name']}")
    print("Monitor the agent logs: tail -f agent_louis_test.log")
    print("\nCall Details:")
    print(f"- Customer: {dial_info['account_info']['customer_name']}")
    print(f"- Phone: {dial_info['phone_number']}")
    print(f"- Account ending in: {dial_info['account_info']['last_4_digits']}")
    print(f"- Past due amount: ${dial_info['account_info']['emi_amount']}")
    print(f"- Late fee: ${dial_info['account_info']['late_fee']}")
    
    # Keep the script running to monitor
    print("\nPress Ctrl+C to exit...")
    try:
        await asyncio.sleep(300)  # Wait 5 minutes
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    asyncio.run(call_louis())