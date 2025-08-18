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
from datetime import datetime, timedelta
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
DEFAULT_HOST = "0.0.0.0"
API_PORT = int(os.getenv("API_PORT", DEFAULT_PORT))
API_HOST = os.getenv("API_HOST", DEFAULT_HOST)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Store active calls for status tracking
active_calls: Dict[str, Dict[str, Any]] = {}

# Import disposition types
from call_disposition import CallDisposition, ConnectionStatus
from database.interaction_service import InteractionService
from database.config import async_session
from sqlalchemy import text


# Pydantic models for request/response
class CustomerInfo(BaseModel):
    customer_name: str = "Customer"
    last_4_digits: str = "0000"
    emi_amount: float = 1500.0
    emi_due_date: str = Field(..., description="EMI due date in YYYY-MM-DD format")
    total_balance: Optional[float] = None
    late_fee: Optional[float] = None
    apr: Optional[float] = None


class CallRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID from platform")
    organization_id: str = Field(..., description="Organization ID")
    campaign_id: Optional[str] = Field(None, description="Campaign ID if applicable")
    agent_id: str = Field(..., description="Agent ID")
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


async def dispatch_job(
    phone_number: str, 
    customer_info: CustomerInfo, 
    transfer_to: str, 
    from_number: str,
    interaction_id: str,
    customer_id: str,
    organization_id: str,
    campaign_id: Optional[str],
    agent_id: str
) -> Dict[str, Any]:
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
            "account_info": account_info,
            "interaction_id": interaction_id,
            "customer_id": customer_id,
            "organization_id": organization_id,
            "campaign_id": campaign_id,
            "agent_id": agent_id
        })
    )
    
    try:
        dispatch = await livekit_api.agent_dispatch.create_dispatch(dispatch_request)
        
        # Store call info for status tracking
        active_calls[dispatch_id] = {
            "dispatch_id": dispatch_id,
            "call_id": call_id,
            "interaction_id": interaction_id,
            "room_name": room.name,
            "phone_number": phone_number,
            "status": "dispatched",
            "created_at": datetime.utcnow().isoformat(),
            "customer_info": account_info,
            "customer_id": customer_id,
            "organization_id": organization_id,
            "campaign_id": campaign_id,
            "agent_id": agent_id,
            "disposition": None,
            "connection_status": None
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
        "customer_id": "cust_123",
        "organization_id": "org_456",
        "campaign_id": "camp_789",
        "agent_id": "agent_001",
        "phone_number": "+1234567890",
        "from_number": "+15076269649",
        "customer_info": {
          "customer_name": "John Doe",
          "last_4_digits": "1234",
          "emi_amount": 1500,
          "emi_due_date": "2025-07-01"
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
    
    # Initialize interaction service
    interaction_service = InteractionService()
    
    try:
        # Validate interaction exists with NOT_STARTED status
        async with async_session() as session:
            interaction = await interaction_service.validate_interaction(
                session,
                customer_id=request.customer_id,
                organization_id=request.organization_id,
                campaign_id=request.campaign_id
            )
            
            if not interaction:
                raise HTTPException(
                    status_code=400,
                    detail="No pending interaction found for customer. Ensure interaction exists with NOT_STARTED status."
                )
            
            interaction_id = interaction["id"]
            
            # Dispatch the call
            result = await dispatch_job(
                phone_number=request.phone_number,
                customer_info=request.customer_info or CustomerInfo(),
                transfer_to=request.transfer_to,
                from_number=request.from_number,
                interaction_id=interaction_id,
                customer_id=request.customer_id,
                organization_id=request.organization_id,
                campaign_id=request.campaign_id,
                agent_id=request.agent_id
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


@app.get("/dispositions")
async def get_dispositions():
    """Get list of all available call dispositions"""
    return {
        "dispositions": [
            {
                "value": disp.value,
                "name": disp.name,
                "connection_required": "CONNECTED" if disp != CallDisposition.BUSY 
                    and disp != CallDisposition.FAILED 
                    and disp != CallDisposition.NO_ANSWER else "NOT_CONNECTED"
            }
            for disp in CallDisposition
        ]
    }


@app.post("/calls/{dispatch_id}/disposition")
async def update_call_disposition(dispatch_id: str, disposition: str):
    """Update the disposition of a specific call"""
    if dispatch_id not in active_calls:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Validate disposition
    try:
        disp_enum = next(d for d in CallDisposition if d.value == disposition)
    except StopIteration:
        raise HTTPException(status_code=400, detail=f"Invalid disposition: {disposition}")
    
    active_calls[dispatch_id]["disposition"] = disposition
    active_calls[dispatch_id]["updated_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "disposition": disposition}


@app.get("/recordings/{dispatch_id}")
async def get_recording_url(dispatch_id: str, expires_in: int = 3600):
    """
    Get a presigned URL for the call recording
    
    Args:
        dispatch_id: The dispatch ID of the call
        expires_in: URL expiration time in seconds (default 1 hour, max 7 days)
        
    Returns:
        Presigned URL that can be used to directly access/download the recording
    """
    import boto3
    from botocore.exceptions import ClientError
    
    # Validate expiration time (max 7 days)
    expires_in = min(expires_in, 604800)
    
    # Check if S3 is configured
    s3_bucket = os.getenv("S3_BUCKET_NAME")
    s3_region = os.getenv("S3_REGION", "us-east-1")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not all([s3_bucket, aws_access_key, aws_secret_key]):
        raise HTTPException(
            status_code=500,
            detail="S3 configuration missing. Recording URLs not available."
        )
    
    # First, check if call exists and get interaction_id
    if dispatch_id not in active_calls:
        # Try to get from database
        async with async_session() as session:
            result = await session.execute(
                text("""
                    SELECT i.id, i.recording, i."callDisposition"
                    FROM interactions i
                    WHERE i."callDisposition"->>'dispatch_id' = :dispatch_id
                    LIMIT 1
                """),
                {"dispatch_id": dispatch_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Call not found")
            
            # Check if recording URL exists in database
            if row.recording:
                # Recording URL already stored, just return it
                return {
                    "recording_url": row.recording,
                    "dispatch_id": dispatch_id,
                    "expires_in": expires_in,
                    "download_url": f"{row.recording}&response-content-disposition=attachment"
                }
    
    # Generate S3 key based on dispatch_id pattern
    # Extract timestamp and phone from dispatch_id (format: dispatch_TIMESTAMP_PHONE)
    parts = dispatch_id.split('_')
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid dispatch_id format")
    
    timestamp = parts[1]
    phone = parts[2]
    
    # Try multiple possible S3 paths
    from datetime import datetime
    
    # Convert timestamp to date for S3 path
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        year = dt.year
        month = f"{dt.month:02d}"
        day = f"{dt.day:02d}"
    except:
        # Fallback to current date if timestamp parsing fails
        dt = datetime.now()
        year = dt.year
        month = f"{dt.month:02d}"
        day = f"{dt.day:02d}"
    
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=s3_region
    )
    
    # List of possible S3 keys to check
    possible_keys = [
        f"egress-recordings/{year}/{month}/{day}/outbound-{phone}_{timestamp}.mp4",
        f"egress-recordings/{year}/{month}/{day}/outbound-{phone}_*.mp4",
        f"call-recordings/{year}/{month}/{day}/{dispatch_id}.mp4",
        f"recordings/{year}/{month}/{day}/{dispatch_id}.mp4"
    ]
    
    recording_key = None
    
    # Try to find the recording
    for key_pattern in possible_keys:
        if '*' in key_pattern:
            # List objects with prefix
            prefix = key_pattern.replace('*', '')
            prefix = prefix.rsplit('/', 1)[0] + '/'
            
            try:
                response = s3_client.list_objects_v2(
                    Bucket=s3_bucket,
                    Prefix=prefix,
                    MaxKeys=10
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if phone in obj['Key'] and obj['Key'].endswith('.mp4'):
                            recording_key = obj['Key']
                            break
                            
            except ClientError:
                continue
        else:
            # Check if specific key exists
            try:
                s3_client.head_object(Bucket=s3_bucket, Key=key_pattern)
                recording_key = key_pattern
                break
            except ClientError:
                continue
    
    if not recording_key:
        raise HTTPException(
            status_code=404,
            detail="Recording not found. Call may still be in progress or recording failed."
        )
    
    # Generate presigned URLs
    try:
        # URL for streaming/playback
        streaming_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_bucket, 'Key': recording_key},
            ExpiresIn=expires_in
        )
        
        # URL for download (with content-disposition header)
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': s3_bucket,
                'Key': recording_key,
                'ResponseContentDisposition': f'attachment; filename="{dispatch_id}.mp4"'
            },
            ExpiresIn=expires_in
        )
        
        return {
            "recording_url": streaming_url,
            "download_url": download_url,
            "dispatch_id": dispatch_id,
            "s3_key": recording_key,
            "expires_in": expires_in,
            "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        }
        
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recording URL")


@app.get("/recordings")
async def list_recordings(limit: int = 10, offset: int = 0):
    """List recent recordings with their URLs"""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT 
                    i.id,
                    i."customerId",
                    i.status,
                    i.outcome,
                    i.recording,
                    i.duration,
                    i."startTime",
                    i."endTime",
                    i."callDisposition"->>'dispatch_id' as dispatch_id,
                    c."firstName",
                    c."lastName",
                    c.phone
                FROM interactions i
                LEFT JOIN customers c ON i."customerId" = c.id
                WHERE i.channel = 'VOICE'
                AND i.recording IS NOT NULL
                ORDER BY i."startTime" DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )
        
        recordings = []
        for row in result:
            recordings.append({
                "interaction_id": row.id,
                "customer_name": f"{row.firstName} {row.lastName}" if row.firstName else "Unknown",
                "phone": row.phone,
                "status": row.status,
                "outcome": row.outcome,
                "duration": row.duration,
                "start_time": row.startTime.isoformat() if row.startTime else None,
                "end_time": row.endTime.isoformat() if row.endTime else None,
                "recording_url": row.recording,
                "dispatch_id": row.dispatch_id
            })
        
        return {
            "recordings": recordings,
            "limit": limit,
            "offset": offset
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
