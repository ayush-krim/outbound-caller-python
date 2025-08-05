#!/usr/bin/env python3
"""
Test LiveKit Egress functionality directly
"""
import asyncio
import os
from livekit import api
from dotenv import load_dotenv
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=".env.local")

async def test_egress():
    # Create API client
    livekit_api = api.LiveKitAPI(
        os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )
    
    try:
        # List existing egresses to test API access
        logger.info("Testing egress API access...")
        egresses = await livekit_api.egress.list_egress(api.ListEgressRequest())
        logger.info(f"Successfully accessed egress API. Found {len(egresses.items) if egresses.items else 0} existing egresses")
        
        # Create a test room
        room_name = "test-egress-room"
        logger.info(f"Creating test room: {room_name}")
        room = await livekit_api.room.create_room(api.CreateRoomRequest(name=room_name))
        logger.info(f"Room created: {room.name}")
        
        # Check S3 configuration
        s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        s3_bucket = os.getenv("S3_BUCKET_NAME")
        s3_region = os.getenv("S3_REGION", "us-east-1")
        
        if not all([s3_access_key, s3_secret_key, s3_bucket]):
            logger.error("❌ S3 credentials not configured!")
            logger.error("Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in .env.local")
            logger.error("See S3_SETUP.md for instructions")
            return
        
        logger.info(f"Using S3 bucket: {s3_bucket} in region: {s3_region}")
        
        # Try to start a room composite egress with S3 output
        logger.info("Attempting to start room composite egress with S3 output...")
        
        # Configure S3 upload
        s3_output = api.S3Upload(
            access_key=s3_access_key,
            secret=s3_secret_key,
            bucket=s3_bucket,
            region=s3_region,
        )
        
        # Configure file output with S3 destination
        file_output = api.EncodedFileOutput(
            file_type=api.EncodedFileType.MP4,
            filepath=f"test-recordings/{room_name}.mp4",
            s3=s3_output,
        )
        
        request = api.RoomCompositeEgressRequest(
            room_name=room_name,
            audio_only=True,
            file_outputs=[file_output]
        )
        
        response = await livekit_api.egress.start_room_composite_egress(request)
        
        if response and response.egress_id:
            logger.info(f"✅ Egress started successfully! Egress ID: {response.egress_id}")
            
            # Stop the egress
            await asyncio.sleep(2)
            logger.info("Stopping egress...")
            await livekit_api.egress.stop_egress(api.StopEgressRequest(egress_id=response.egress_id))
            logger.info("Egress stopped")
        else:
            logger.error("❌ Failed to start egress - no egress_id returned")
            
        # Clean up room
        await livekit_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
        logger.info("Test room deleted")
        
    except Exception as e:
        logger.error(f"❌ Error during egress test: {type(e).__name__}: {e}")
        if hasattr(e, 'code'):
            logger.error(f"Error code: {e.code}")
        if hasattr(e, 'message'):
            logger.error(f"Error message: {e.message}")

if __name__ == "__main__":
    asyncio.run(test_egress())