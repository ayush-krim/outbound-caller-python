# Recording API Documentation

## Overview
The API provides endpoints to generate dynamic presigned URLs for S3 recordings that can be directly accessed for listening or downloading.

## Endpoints

### 1. Get Recording URL
```
GET /recordings/{dispatch_id}
```

Returns presigned URLs for a specific call recording.

**Parameters:**
- `dispatch_id` (path): The dispatch ID from the call (e.g., `dispatch_1754653479_15103455686`)
- `expires_in` (query, optional): URL expiration time in seconds (default: 3600, max: 604800)

**Example Request:**
```bash
curl http://localhost:8000/recordings/dispatch_1754653479_15103455686
```

**Example Response:**
```json
{
  "recording_url": "https://your-bucket.s3.amazonaws.com/egress-recordings/2025/08/08/outbound-15103455686_1754653479.mp4?...",
  "download_url": "https://your-bucket.s3.amazonaws.com/egress-recordings/2025/08/08/outbound-15103455686_1754653479.mp4?...&response-content-disposition=attachment",
  "dispatch_id": "dispatch_1754653479_15103455686",
  "s3_key": "egress-recordings/2025/08/08/outbound-15103455686_1754653479.mp4",
  "expires_in": 3600,
  "expires_at": "2025-08-08T12:44:39.000Z"
}
```

**Usage:**
- `recording_url`: Use this URL to stream/play the recording in a browser or media player
- `download_url`: Use this URL to download the recording as a file

### 2. List All Recordings
```
GET /recordings
```

Lists all available recordings with basic information.

**Parameters:**
- `limit` (query, optional): Number of recordings to return (default: 10)
- `offset` (query, optional): Offset for pagination (default: 0)

**Example Request:**
```bash
curl http://localhost:8000/recordings?limit=5
```

**Example Response:**
```json
{
  "recordings": [
    {
      "interaction_id": "test_interaction_louis_001",
      "customer_name": "Louis Smith",
      "phone": "+15103455686",
      "status": "COMPLETED",
      "outcome": "PAYMENT_PROMISED",
      "duration": 180,
      "start_time": "2025-08-08T11:44:39.000Z",
      "end_time": "2025-08-08T11:47:39.000Z",
      "recording_url": "https://...",
      "dispatch_id": "dispatch_1754653479_15103455686"
    }
  ],
  "limit": 5,
  "offset": 0
}
```

## URL Expiration

- Default expiration: 1 hour (3600 seconds)
- Maximum expiration: 7 days (604800 seconds)
- To get a URL with custom expiration:
  ```bash
  curl "http://localhost:8000/recordings/dispatch_1754653479_15103455686?expires_in=86400"
  ```
  This creates a URL valid for 24 hours.

## Direct Usage Examples

### 1. Play in Browser
Simply paste the `recording_url` in any modern browser. Most browsers support MP4 audio playback.

### 2. Download with curl
```bash
curl -o "call_recording.mp4" "PASTE_DOWNLOAD_URL_HERE"
```

### 3. Play with VLC
```bash
vlc "PASTE_RECORDING_URL_HERE"
```

### 4. Embed in HTML
```html
<audio controls>
  <source src="PASTE_RECORDING_URL_HERE" type="audio/mp4">
  Your browser does not support the audio element.
</audio>
```

### 5. Share Link
You can share the recording URL directly. It will work for anyone until it expires.

## Error Responses

### 404 Not Found
```json
{
  "detail": "Recording not found. Call may still be in progress or recording failed."
}
```

### 500 Server Error
```json
{
  "detail": "S3 configuration missing. Recording URLs not available."
}
```

## Notes

1. Recording URLs are generated on-demand and expire after the specified time
2. The recording must be completed and uploaded to S3 before it can be accessed
3. If a call is still in progress, the recording won't be available yet
4. The system automatically finds recordings based on the dispatch_id pattern