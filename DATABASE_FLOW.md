# How Call Data is Stored in the Database

## Overview
All call data is stored in the `interactions` table. There is no separate `calls` table.

## Data Flow

### 1. **Before Call Dispatch**
```sql
-- Initial state (created by platform)
id: test_interaction_1754628065_1
status: INITIATED
channel: VOICE
direction: OUTBOUND
customerId: test_customer_001
agentId: test_agent_001
startTime: 2025-08-08 04:41:05
```

### 2. **When API Receives Call Request**
- API validates that an INITIATED interaction exists
- Dispatches call to LiveKit with metadata
- **Note**: API doesn't update the interaction at this point

### 3. **When Agent Starts (agent.py)**
```python
# In entrypoint() function:
await interaction_service.update_call_started(
    session,
    interaction_id=agent.interaction_id,
    room_name=ctx.room.name,
    phone_number=phone_number
)
```
This would update:
- `status`: INITIATED → IN_PROGRESS
- Add room information

### 4. **When Call Connects**
```python
# In entrypoint() function:
await interaction_service.update_call_connected(
    session,
    interaction_id=agent.interaction_id
)
```
This would update:
- Connection timestamp

### 5. **When Call Ends**
```python
# In _handle_session_close() function:
await interaction_service.update_call_completed(
    session,
    interaction_id=agent.interaction_id,
    disposition_data=final_disposition,
    transcript=agent.transcript_items,
    duration=duration,
    recording_url=recording_url
)
```
This would update:
- `status`: IN_PROGRESS → COMPLETED
- `endTime`: Call end timestamp
- `duration`: Call duration in seconds
- `outcome`: General outcome (SUCCESS/FAILED)
- `callDisposition`: JSON with detailed disposition:
  ```json
  {
    "disposition": "USER_CLAIMED_PAYMENT",
    "connection_status": "CONNECTED",
    "call_duration": 180,
    "keywords_detected": ["payment", "tomorrow"]
  }
  ```
- `transcript`: Full conversation transcript
- `recording`: URL to recording (if available)

### 6. **For Failed Calls**
```python
# In entrypoint() exception handler:
await interaction_service.update_call_failed(
    session,
    interaction_id=agent.interaction_id,
    reason=final_disposition['disposition'],
    sip_status=sip_status
)
```
This would update:
- `status`: IN_PROGRESS → FAILED
- `outcome`: FAILED
- `callDisposition`: Failure reason

## Database Schema for Call Storage

Key columns in `interactions` table:

| Column | Type | Purpose |
|--------|------|---------|
| id | text | Unique interaction ID |
| status | enum | INITIATED → IN_PROGRESS → COMPLETED/FAILED |
| channel | enum | VOICE for calls |
| direction | enum | OUTBOUND/INBOUND |
| startTime | timestamp | When interaction started |
| endTime | timestamp | When interaction ended |
| duration | integer | Call duration in seconds |
| outcome | enum | General outcome |
| callDisposition | jsonb | Detailed disposition data |
| transcript | text | Full call transcript |
| recording | text | Recording URL |
| recordingConsent | boolean | Consent obtained |
| paymentDiscussed | boolean | Payment mentioned |
| paymentAmount | numeric | Amount discussed |
| paymentDate | timestamp | Promised payment date |
| followUpRequired | boolean | Needs follow-up |
| callQualityMetrics | jsonb | Quality data |
| sentiment | enum | Call sentiment |
| customerSatisfactionScore | integer | CSAT score |

## Example Query to View Call Data
```sql
-- View all call details
SELECT 
    id,
    status,
    channel,
    "startTime",
    "endTime",
    duration,
    outcome,
    "callDisposition",
    LEFT(transcript, 100) as transcript_preview,
    recording,
    "paymentDiscussed",
    "paymentAmount",
    sentiment
FROM interactions 
WHERE "customerId" = 'test_customer_001'
AND channel = 'VOICE'
ORDER BY "startTime" DESC;
```

## Why Data Isn't Showing Yet
1. The API successfully dispatches calls to LiveKit
2. The agent process (agent.py) needs to be running to process the call
3. LiveKit needs to be running to handle the SIP call
4. Without these services, the interactions remain in INITIATED status

To see the full flow:
1. Start LiveKit server
2. Run the agent: `python agent.py dev`
3. Make a call through the API
4. The database will be updated at each stage