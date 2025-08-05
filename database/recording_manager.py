"""
Recording Manager for handling LiveKit Egress recordings with SQLAlchemy and S3 storage
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from livekit import api
import time

# Make boto3 optional
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = None
    BOTO3_AVAILABLE = False

from database.models import CallRecording, Call
from database.config import async_session

logger = logging.getLogger(__name__)


class RecordingManager:
    """Manages call recordings using LiveKit Egress API with SQLAlchemy and S3 storage"""
    
    def __init__(self, livekit_api: api.LiveKitAPI, base_recording_path: str = "recordings"):
        self.api = livekit_api
        self.base_path = Path(base_recording_path)
        
        # S3 configuration from environment variables
        self.use_s3 = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
        self.s3_bucket = os.getenv("S3_BUCKET_NAME")
        self.s3_region = os.getenv("S3_REGION", "us-east-1")
        self.s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.s3_prefix = os.getenv("S3_RECORDING_PREFIX", "call-recordings")
        
        # Initialize S3 client if enabled
        self.s3_client = None
        if self.use_s3:
            if not BOTO3_AVAILABLE:
                logger.warning("S3 storage enabled but boto3 is not installed. Falling back to local storage.")
                self.use_s3 = False
            elif not all([self.s3_bucket, self.s3_access_key, self.s3_secret_key]):
                logger.warning("S3 storage enabled but missing required credentials. Falling back to local storage.")
                self.use_s3 = False
            else:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key,
                    region_name=self.s3_region
                )
                logger.info(f"S3 storage enabled. Bucket: {self.s3_bucket}")
        
    async def initialize(self):
        """Initialize the recording manager"""
        if not self.use_s3:
            # Create base recording directory for local storage
            self.base_path.mkdir(exist_ok=True)
        else:
            # Verify S3 bucket access (optional check)
            try:
                self.s3_client.head_bucket(Bucket=self.s3_bucket)
                logger.info(f"S3 bucket {self.s3_bucket} is accessible")
            except ClientError as e:
                logger.warning(f"Cannot verify S3 bucket access (this is normal if bucket permissions are restrictive): {e}")
                logger.info(f"Proceeding with S3 recording - will attempt uploads directly")
        
    async def start_room_recording(self, room_name: str, call_id: str) -> Optional[str]:
        """
        Start recording a room
        
        Args:
            room_name: The LiveKit room name
            call_id: The database call ID
            
        Returns:
            The egress ID if successful, None otherwise
        """
        try:
            # Create date-based subdirectory
            now = datetime.now()
            date_path = self.base_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
            date_path.mkdir(parents=True, exist_ok=True)
            
            # Configure S3 output for egress
            s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            s3_bucket = os.getenv("S3_BUCKET_NAME")
            s3_region = os.getenv("S3_REGION", "us-east-1")
            
            if not all([s3_access_key, s3_secret_key, s3_bucket]):
                logger.error("S3 credentials not configured for LiveKit Egress")
                logger.error("Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in .env.local")
                return None
            
            # Generate S3 path
            s3_key = f"egress-recordings/{now.year}/{now.month:02d}/{now.day:02d}/{room_name}_{int(time.time())}.mp4"
            
            # Set S3 output
            s3_output = api.S3Upload(
                access_key=s3_access_key,
                secret=s3_secret_key,
                bucket=s3_bucket,
                region=s3_region,
            )
            
            # Configure encoded file output with S3 destination
            file_output = api.EncodedFileOutput(
                file_type=api.EncodedFileType.MP4,
                filepath=s3_key,
                s3=s3_output,
            )
            
            # Configure room composite egress for audio recording with S3 output
            request = api.RoomCompositeEgressRequest(
                room_name=room_name,
                audio_only=True,  # We only need audio for call recordings
                file_outputs=[file_output]  # Pass file_outputs in constructor
            )
            
            # Start the egress
            logger.info(f"Starting room recording for {room_name}")
            response = await self.api.egress.start_room_composite_egress(request)
            
            if response and response.egress_id:
                # Create recording record in database
                async with async_session() as session:
                    recording = CallRecording(
                        call_id=call_id,
                        egress_id=response.egress_id,
                        room_name=room_name,
                        status="recording",
                        started_at=datetime.now(timezone.utc),
                        format="mp4",
                    )
                    
                    session.add(recording)
                    await session.commit()
                
                logger.info(f"Recording started with egress ID: {response.egress_id}")
                
                # Start monitoring task
                asyncio.create_task(self._monitor_recording(response.egress_id, call_id))
                
                return response.egress_id
            else:
                logger.error("Failed to start egress - no egress_id returned")
                return None
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return None
    
    async def stop_recording(self, egress_id: str):
        """Stop a recording"""
        try:
            logger.info(f"Stopping recording {egress_id}")
            await self.api.egress.stop_egress(
                api.StopEgressRequest(egress_id=egress_id)
            )
        except Exception as e:
            logger.error(f"Failed to stop recording {egress_id}: {e}")
    
    async def _monitor_recording(self, egress_id: str, call_id: str):
        """Monitor recording status and handle completion"""
        try:
            while True:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Get egress info
                egresses = await self.api.egress.list_egress(
                    api.ListEgressRequest(egress_id=egress_id)
                )
                
                if not egresses or not egresses.items:
                    logger.warning(f"No egress found for {egress_id}")
                    break
                
                egress = egresses.items[0]
                
                if egress.status == api.EgressStatus.EGRESS_COMPLETE:
                    logger.info(f"Recording {egress_id} completed")
                    
                    # Get the recording from database
                    async with async_session() as session:
                        result = await session.execute(
                            select(CallRecording).where(CallRecording.egress_id == egress_id)
                        )
                        recording = result.scalar_one_or_none()
                        
                        if recording:
                            # Update with completion info
                            recording.status = "completed"
                            recording.completed_at = datetime.now(timezone.utc)
                            
                            if hasattr(egress, 'file') and egress.file:
                                # Move file to proper location
                                dispatch_id = await self._get_dispatch_id(session, call_id)
                                if dispatch_id:
                                    final_path = await self._organize_recording_file(
                                        egress.file.filename if hasattr(egress.file, 'filename') else None, 
                                        dispatch_id
                                    )
                                    
                                    # Handle S3 upload if enabled
                                    if self.use_s3 and final_path.exists():
                                        s3_url = await self._upload_to_s3(final_path, dispatch_id)
                                        if s3_url:
                                            recording.file_url = s3_url
                                            recording.file_path = str(final_path)  # Keep local path for reference
                                            
                                            # Delete local file after successful S3 upload
                                            if os.getenv("DELETE_LOCAL_AFTER_S3", "true").lower() == "true":
                                                try:
                                                    final_path.unlink()
                                                    logger.info(f"Deleted local file after S3 upload: {final_path}")
                                                except Exception as e:
                                                    logger.error(f"Failed to delete local file: {e}")
                                        else:
                                            logger.error(f"S3 upload failed for {dispatch_id}, keeping local file")
                                    else:
                                        recording.file_path = str(final_path)
                                    
                                    # Get file size
                                    if final_path.exists():
                                        recording.file_size = final_path.stat().st_size
                            
                            if hasattr(egress, 'duration') and egress.duration:
                                recording.duration_seconds = egress.duration / 1_000_000_000  # Convert nanoseconds
                            
                            await session.commit()
                    break
                
                elif egress.status == api.EgressStatus.EGRESS_FAILED:
                    logger.error(f"Recording {egress_id} failed")
                    
                    # Update recording status
                    async with async_session() as session:
                        result = await session.execute(
                            select(CallRecording).where(CallRecording.egress_id == egress_id)
                        )
                        recording = result.scalar_one_or_none()
                        
                        if recording:
                            recording.status = "failed"
                            recording.completed_at = datetime.now(timezone.utc)
                            await session.commit()
                    break
                    
        except Exception as e:
            logger.error(f"Error monitoring recording {egress_id}: {e}")
    
    async def _get_dispatch_id(self, session: AsyncSession, call_id: str) -> Optional[str]:
        """Get dispatch ID for a call"""
        result = await session.execute(
            select(Call).where(Call.id == call_id)
        )
        call = result.scalar_one_or_none()
        return call.dispatch_id if call else None
    
    async def _organize_recording_file(self, source_path: str, dispatch_id: str) -> Path:
        """Organize recording file into date-based directory structure"""
        now = datetime.now()
        date_path = self.base_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        date_path.mkdir(parents=True, exist_ok=True)
        
        final_path = date_path / f"{dispatch_id}.mp4"
        
        # Move file if it exists
        if source_path:
            source = Path(source_path)
            if source.exists():
                source.rename(final_path)
                logger.info(f"Moved recording to {final_path}")
        
        return final_path
    
    async def _upload_to_s3(self, file_path: Path, dispatch_id: str) -> Optional[str]:
        """Upload recording file to S3
        
        Args:
            file_path: Local path to the recording file
            dispatch_id: Dispatch ID for the call
            
        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            # Generate S3 key with date-based structure
            now = datetime.now()
            s3_key = f"{self.s3_prefix}/{now.year}/{now.month:02d}/{now.day:02d}/{dispatch_id}.mp4"
            
            # Upload file
            logger.info(f"Uploading {file_path} to s3://{self.s3_bucket}/{s3_key}")
            
            # Use asyncio to run the synchronous boto3 call
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.s3_client.upload_file,
                str(file_path),
                self.s3_bucket,
                s3_key,
                {
                    'ContentType': 'video/mp4',
                    'Metadata': {
                        'dispatch_id': dispatch_id,
                        'uploaded_at': datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Generate URL (can be presigned URL or public URL based on bucket settings)
            if os.getenv("S3_USE_PRESIGNED_URLS", "true").lower() == "true":
                # Generate presigned URL valid for 7 days
                url = await loop.run_in_executor(
                    None,
                    self.s3_client.generate_presigned_url,
                    'get_object',
                    {'Bucket': self.s3_bucket, 'Key': s3_key},
                    604800  # 7 days in seconds
                )
            else:
                # Return public URL (assumes bucket is configured for public access)
                url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"
            
            logger.info(f"Successfully uploaded recording to S3: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload recording to S3: {e}")
            return None
    
    async def get_recording_info(self, dispatch_id: str) -> Optional[dict]:
        """Get recording info for a dispatch"""
        async with async_session() as session:
            result = await session.execute(
                select(Call, CallRecording)
                .join(CallRecording, Call.id == CallRecording.call_id)
                .where(Call.dispatch_id == dispatch_id)
            )
            row = result.first()
            
            if row:
                call, recording = row
                return {
                    "status": recording.status,
                    "file_path": recording.file_path,
                    "duration_seconds": recording.duration_seconds,
                    "file_size": recording.file_size,
                    "started_at": recording.started_at,
                    "completed_at": recording.completed_at,
                }
        
        return None
    
    async def cleanup(self):
        """Cleanup resources"""
        pass  # No persistent connections with SQLAlchemy async