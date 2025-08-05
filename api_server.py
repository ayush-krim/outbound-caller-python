"""
HTTP API Server for triggering outbound calls
Run this alongside the agent worker to enable REST API calls
"""

import os
import json
import socket
import asyncio
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from livekit import api
import uvicorn

# Load environment variables
load_dotenv(dotenv_path=".env.local")

# Configuration
DEFAULT_PORT = 8000
DEFAULT_HOST = "127.0.0.1"
API_PORT = int(os.getenv("API_PORT", DEFAULT_PORT))
API_HOST = os.getenv("API_HOST", DEFAULT_HOST)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Store active calls for status tracking
active_calls: Dict[str, Dict[str, Any]] = {}


# Pydantic models for request/response
class CustomerInfo(BaseModel):
    customer_name: str = "Customer"
    last_4_digits: str = "0000"
    emi_amount: float = 1500.0
    days_past_due: int = 30
    total_balance: Optional[float] = None
    late_fee: Optional[float] = None
    apr: Optional[float] = None


class CallRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to call (E.164 format)")
    customer_info: Optional[CustomerInfo] = None
    transfer_to: Optional[str] = Field(default="+1 507 626 9649", description="Transfer number")
    from_number: Optional[str] = Field(default="+1 507 626 9649", description="Outbound caller ID")


class CallResponse(BaseModel):
    success: bool
    dispatch_id: str
    call_id: str
    room_name: str
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    livekit_connected: bool
    active_calls: int


def find_free_port(start_port: int = 8000) -> int:
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports available in range {start_port}-{start_port + 100}")


async def dispatch_job(phone_number: str, customer_info: CustomerInfo, transfer_to: str, from_number: str) -> Dict[str, Any]:
    """Dispatch an outbound call job to LiveKit"""
    
    # Create LiveKit API client
    livekit_api = api.LiveKitAPI(
        LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )

    # Create room first (remove + from phone number for room name)
    room_name = f"outbound-{phone_number.replace('+', '')}"
    room_request = api.CreateRoomRequest(name=room_name)
    
    try:
        room = await livekit_api.room.create_room(room_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")

    # Generate unique IDs for this call
    call_id = str(uuid.uuid4())
    dispatch_id = f"dispatch_{int(time.time())}_{phone_number.replace('+', '')}"
    
    # Prepare customer info
    account_info = customer_info.dict() if customer_info else {}
    
    # Dispatch agent to room
    dispatch_request = api.CreateAgentDispatchRequest(
        room=room.name,
        agent_name="outbound-caller-local",
        metadata=json.dumps({
            "phone_number": f"{from_number},{phone_number}",  # Format: "from_number,to_number"
            "transfer_to": transfer_to,
            "call_id": call_id,
            "dispatch_id": dispatch_id,
            "account_info": account_info
        })
    )
    
    try:
        dispatch = await livekit_api.agent_dispatch.create_dispatch(dispatch_request)
        
        # Store call info for status tracking
        active_calls[dispatch_id] = {
            "dispatch_id": dispatch_id,
            "call_id": call_id,
            "room_name": room.name,
            "phone_number": phone_number,
            "status": "dispatched",
            "created_at": datetime.utcnow().isoformat(),
            "customer_info": account_info
        }
        
        return {
            "dispatch_id": dispatch_id,
            "call_id": call_id,
            "room_name": room.name,
            "dispatch": dispatch
        }
    except Exception as e:
        # Clean up room if dispatch fails
        try:
            await livekit_api.room.delete_room(api.DeleteRoomRequest(room=room.name))
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to dispatch agent: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(f"\n🚀 Starting API server on http://{API_HOST}:{API_PORT}")
    print(f"📚 Documentation available at http://{API_HOST}:{API_PORT}/docs")
    print("\n⚡ Ready to receive call requests!")
    yield
    # Shutdown
    print("\n👋 Shutting down API server")


# Create FastAPI app
app = FastAPI(
    title="Outbound Call API",
    description="HTTP API for triggering outbound calls via LiveKit agents",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/call", response_model=CallResponse)
async def make_call(request: CallRequest, background_tasks: BackgroundTasks):
    """
    Trigger an outbound call
    
    Example:
    ```bash
    curl -X POST http://localhost:8000/call \\
      -H "Content-Type: application/json" \\
      -d '{
        "phone_number": "+1234567890",
        "customer_info": {
          "customer_name": "John Doe",
          "last_4_digits": "1234",
          "emi_amount": 1500,
          "days_past_due": 30
        }
      }'
    ```
    """
    
    # Validate LiveKit configuration
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise HTTPException(
            status_code=500,
            detail="LiveKit configuration missing. Please check environment variables."
        )
    
    try:
        # Dispatch the call
        result = await dispatch_job(
            phone_number=request.phone_number,
            customer_info=request.customer_info or CustomerInfo(),
            transfer_to=request.transfer_to,
            from_number=request.from_number
        )
        
        return CallResponse(
            success=True,
            dispatch_id=result["dispatch_id"],
            call_id=result["call_id"],
            room_name=result["room_name"],
            message=f"Call dispatched successfully to {request.phone_number}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API server health and LiveKit connection"""
    
    # Test LiveKit connection
    livekit_connected = False
    try:
        if all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            livekit_api = api.LiveKitAPI(
                LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET,
            )
            # Try to list rooms as a connection test
            await livekit_api.room.list_rooms(api.ListRoomsRequest(limit=1))
            livekit_connected = True
    except:
        pass
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        livekit_connected=livekit_connected,
        active_calls=len(active_calls)
    )


@app.get("/calls/{dispatch_id}")
async def get_call_status(dispatch_id: str):
    """Get status of a specific call"""
    if dispatch_id not in active_calls:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return active_calls[dispatch_id]


@app.get("/calls")
async def list_calls(limit: int = 10):
    """List recent calls"""
    # Sort by creation time and return most recent
    sorted_calls = sorted(
        active_calls.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]
    
    return {
        "total": len(active_calls),
        "calls": sorted_calls
    }


if __name__ == "__main__":
    # Check if the desired port is available
    actual_port = API_PORT
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', API_PORT))
        sock.close()
    except OSError:
        print(f"⚠️  Port {API_PORT} is in use, finding a free port...")
        actual_port = find_free_port(API_PORT)
        print(f"✅ Using port {actual_port} instead")
    
    # Run the server
    uvicorn.run(
        "api_server:app",
        host=API_HOST,
        port=actual_port,
        reload=True if os.getenv("ENV", "development") == "development" else False,
        log_level="info"
    )