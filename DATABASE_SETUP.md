# Database Setup for Call Analytics

This guide explains how to set up PostgreSQL database for tracking voice agent call analytics.

## Prerequisites

- PostgreSQL 12+ installed
- Python environment with dependencies installed

## Quick Start

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE outbound_calls;

# Create user (optional)
CREATE USER outbound_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE outbound_calls TO outbound_user;

# Exit
\q
```

### 3. Configure Environment

Add to your `.env.local` file:
```env
# For local development with default postgres user
DATABASE_URL=postgresql://postgres@localhost:5432/outbound_calls

# Or with custom user
DATABASE_URL=postgresql://outbound_user:your_secure_password@localhost:5432/outbound_calls

# For production (example)
DATABASE_URL=postgresql://user:password@your-db-host:5432/outbound_calls
```

### 4. Run Database Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Create migration (if schema changed)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

## Database Schema Overview

The database tracks comprehensive call analytics with the following tables:

### 1. **calls** - Main call records
- Basic call information (dispatch_id, phone_number, status)
- Call outcomes and end reasons

### 2. **call_connection_metrics** - Connection performance
- Detailed timing for each connection phase
- Room connection, agent init, session creation, SIP dial times

### 3. **call_interaction_metrics** - Conversation analytics
- Call duration, utterance counts, response times
- Silence periods and interruptions

### 4. **call_speech_analytics** - Speech and sentiment
- Words spoken, speech rate, confidence scores
- User sentiment and emotion detection

### 5. **call_system_metrics** - System performance
- CPU/memory usage, network latency
- AI model performance (tokens, response times)

### 6. **call_events** - Event timeline
- All events during call lifecycle
- Voicemail detection, transfers, errors

## Key Performance Indicators (KPIs)

The system tracks these critical metrics:

1. **Connection Speed**: Time from dispatch to call answered
   - Target: < 5 seconds
   
2. **Time to First Response**: Time from answer to agent speaking
   - Target: < 1 second
   
3. **Average Response Time**: Agent response latency
   - Target: < 800ms
   
4. **Call Success Rate**: Percentage of successful calls
5. **Setup Efficiency**: Setup time vs total call time

## Usage in Code

The tracking is automatically integrated into the agent:

```python
# Tracking happens automatically in agent.py
# Key events tracked:
- dispatch_accepted
- room_connection_start/completed
- agent_init_start/completed
- session_creation_start/completed
- sip_dial_start/completed
- call_answered
- participant_joined
- voicemail_detected
- transfer_requested/completed
- call_end
```

## Querying Analytics

Example queries to analyze performance:

```sql
-- Average connection times by day
SELECT 
    DATE(dispatch_created_at) as date,
    AVG(total_setup_time_ms) / 1000.0 as avg_setup_seconds,
    COUNT(*) as total_calls
FROM call_connection_metrics
GROUP BY DATE(dispatch_created_at);

-- Call outcomes summary
SELECT 
    status,
    COUNT(*) as count,
    AVG(total_duration_seconds) as avg_duration
FROM calls c
JOIN call_interaction_metrics i ON c.id = i.call_id
GROUP BY status;

-- Performance over time
SELECT 
    DATE(call_start_time) as date,
    AVG(avg_agent_response_time_ms) as avg_response_ms,
    AVG(total_agent_utterances) as avg_utterances
FROM call_interaction_metrics
GROUP BY DATE(call_start_time);
```

## Troubleshooting

### Connection Refused Error
```
psycopg2.OperationalError: connection to server at "localhost" failed
```
**Solution**: Ensure PostgreSQL is running:
- macOS: `brew services start postgresql`
- Linux: `sudo systemctl start postgresql`

### Permission Denied
```
FATAL: role "username" does not exist
```
**Solution**: Create the user or use existing postgres user

### Database Does Not Exist
```
FATAL: database "outbound_calls" does not exist
```
**Solution**: Create the database: `createdb outbound_calls`

## Production Considerations

1. **Connection Pooling**: The app uses connection pooling (10 connections, 20 overflow)
2. **Async Operations**: All database operations are async for performance
3. **Indexes**: Key columns are indexed for query performance
4. **Data Retention**: Consider implementing data retention policies
5. **Backup**: Set up regular database backups

## Monitoring

Use these queries to monitor system health:

```sql
-- Calls in last hour
SELECT COUNT(*) FROM calls 
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Failed calls today
SELECT COUNT(*) FROM calls 
WHERE status = 'failed' 
AND created_at > CURRENT_DATE;

-- Average performance today
SELECT 
    AVG(total_setup_time_ms) as avg_setup_ms,
    AVG(avg_agent_response_time_ms) as avg_response_ms
FROM call_connection_metrics cm
JOIN call_interaction_metrics im ON cm.call_id = im.call_id
WHERE cm.dispatch_created_at > CURRENT_DATE;
```