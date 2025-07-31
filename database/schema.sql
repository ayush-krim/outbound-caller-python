-- Voice Agent Call Analytics Database Schema
-- PostgreSQL 12+

-- Create database (run as superuser)
-- CREATE DATABASE outbound_calls;

-- Main call records table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_id VARCHAR(255) UNIQUE NOT NULL,
    room_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    agent_name VARCHAR(100),
    transfer_to_number VARCHAR(50),
    status VARCHAR(50), -- 'completed', 'failed', 'voicemail', 'transferred', 'abandoned'
    end_reason VARCHAR(255), -- 'user_hangup', 'agent_hangup', 'timeout', 'error', 'transfer_completed'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_calls_dispatch_id ON calls(dispatch_id);
CREATE INDEX idx_calls_phone_number ON calls(phone_number);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_calls_created_at ON calls(created_at);

-- Connection performance metrics
CREATE TABLE IF NOT EXISTS call_connection_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    
    -- Dispatch to Answer Timeline
    dispatch_created_at TIMESTAMPTZ NOT NULL,
    dispatch_accepted_at TIMESTAMPTZ,
    
    -- Room Connection Phase
    room_connection_start TIMESTAMPTZ,
    room_connection_completed TIMESTAMPTZ,
    room_connection_duration_ms INTEGER,
    
    -- Agent Initialization Phase
    agent_init_start TIMESTAMPTZ,
    agent_init_completed TIMESTAMPTZ,
    agent_init_duration_ms INTEGER,
    
    -- Session Creation Phase
    session_creation_start TIMESTAMPTZ,
    session_creation_completed TIMESTAMPTZ,
    session_creation_duration_ms INTEGER,
    
    -- SIP Dialing Phase
    sip_dial_start TIMESTAMPTZ,
    sip_dial_completed TIMESTAMPTZ,
    sip_dial_duration_ms INTEGER,
    sip_dial_status VARCHAR(50), -- 'ringing', 'answered', 'busy', 'no_answer', 'failed'
    
    -- Call Answered
    call_answered_at TIMESTAMPTZ,
    participant_joined_at TIMESTAMPTZ,
    
    -- Calculated Total Metrics
    total_setup_time_ms INTEGER, -- dispatch_created to call_answered
    time_to_connect_ms INTEGER, -- dispatch_accepted to participant_joined
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Call interaction and conversation metrics
CREATE TABLE IF NOT EXISTS call_interaction_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    
    -- Call Duration
    call_start_time TIMESTAMPTZ,
    call_end_time TIMESTAMPTZ,
    total_duration_seconds FLOAT,
    
    -- Conversation Metrics
    agent_first_speech_at TIMESTAMPTZ,
    user_first_speech_at TIMESTAMPTZ,
    time_to_first_agent_response_ms INTEGER,
    time_to_first_user_response_ms INTEGER,
    
    -- Interaction Counts
    total_agent_utterances INTEGER DEFAULT 0,
    total_user_utterances INTEGER DEFAULT 0,
    total_interruptions INTEGER DEFAULT 0,
    total_silence_periods INTEGER DEFAULT 0,
    total_silence_duration_ms INTEGER DEFAULT 0,
    
    -- Response Time Analytics
    avg_agent_response_time_ms FLOAT,
    max_agent_response_time_ms INTEGER,
    min_agent_response_time_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Speech and conversation analytics
CREATE TABLE IF NOT EXISTS call_speech_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    
    -- Speech Recognition Metrics
    total_words_spoken_agent INTEGER,
    total_words_spoken_user INTEGER,
    avg_words_per_minute_agent FLOAT,
    avg_words_per_minute_user FLOAT,
    
    -- Sentiment/Tone (if available)
    user_sentiment_score FLOAT, -- -1 to 1 (negative to positive)
    detected_user_emotion VARCHAR(50), -- 'neutral', 'happy', 'frustrated', 'confused'
    
    -- Speech Quality
    avg_confidence_score FLOAT, -- STT confidence
    low_confidence_utterances INTEGER, -- Count of low confidence recognitions
    
    -- Conversation Flow
    topic_changes INTEGER,
    clarification_requests INTEGER,
    
    -- Call transcript (optional, can be large)
    transcript TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System performance and resource usage metrics
CREATE TABLE IF NOT EXISTS call_system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    
    -- Resource Usage
    peak_cpu_usage_percent FLOAT,
    avg_cpu_usage_percent FLOAT,
    peak_memory_usage_mb INTEGER,
    avg_memory_usage_mb INTEGER,
    
    -- Network Performance
    total_bandwidth_used_mb FLOAT,
    avg_latency_ms FLOAT,
    packet_loss_percent FLOAT,
    
    -- AI Model Performance
    llm_requests_count INTEGER,
    llm_total_tokens_used INTEGER,
    llm_avg_response_time_ms FLOAT,
    stt_processing_time_ms FLOAT,
    tts_processing_time_ms FLOAT,
    
    -- Errors and Warnings
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual events during the call lifecycle
CREATE TABLE IF NOT EXISTS call_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- 'voicemail_detected', 'transfer_requested', 'error_occurred', etc.
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_details JSONB, -- Flexible field for event-specific data
    duration_from_call_start_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_call_events_call_id ON call_events(call_id);
CREATE INDEX idx_call_events_type ON call_events(event_type);
CREATE INDEX idx_call_events_timestamp ON call_events(event_timestamp);

-- Aggregate KPIs View
CREATE OR REPLACE VIEW call_kpis AS
SELECT 
    c.id,
    c.dispatch_id,
    c.status,
    c.phone_number,
    c.created_at,
    
    -- Connection Speed KPIs
    ccm.total_setup_time_ms / 1000.0 as setup_time_seconds,
    ccm.room_connection_duration_ms / 1000.0 as room_connection_seconds,
    ccm.agent_init_duration_ms / 1000.0 as agent_init_seconds,
    ccm.sip_dial_duration_ms / 1000.0 as sip_dial_seconds,
    
    -- Interaction KPIs
    cim.total_duration_seconds,
    cim.time_to_first_agent_response_ms / 1000.0 as time_to_first_response_seconds,
    cim.avg_agent_response_time_ms / 1000.0 as avg_response_time_seconds,
    cim.total_agent_utterances + cim.total_user_utterances as total_turns,
    
    -- Efficiency Scores (0-100)
    CASE 
        WHEN ccm.total_setup_time_ms < 3000 THEN 100
        WHEN ccm.total_setup_time_ms < 5000 THEN 80
        WHEN ccm.total_setup_time_ms < 8000 THEN 60
        ELSE 40
    END as connection_speed_score,
    
    CASE
        WHEN cim.avg_agent_response_time_ms < 500 THEN 100
        WHEN cim.avg_agent_response_time_ms < 1000 THEN 80
        WHEN cim.avg_agent_response_time_ms < 2000 THEN 60
        ELSE 40
    END as responsiveness_score

FROM calls c
LEFT JOIN call_connection_metrics ccm ON c.id = ccm.call_id
LEFT JOIN call_interaction_metrics cim ON c.id = cim.call_id;

-- Daily performance summary view
CREATE OR REPLACE VIEW daily_performance AS
SELECT 
    DATE(c.created_at) as date,
    COUNT(DISTINCT c.id) as total_calls,
    COUNT(DISTINCT CASE WHEN c.status = 'completed' THEN c.id END) as completed_calls,
    COUNT(DISTINCT CASE WHEN c.status = 'failed' THEN c.id END) as failed_calls,
    COUNT(DISTINCT CASE WHEN c.status = 'voicemail' THEN c.id END) as voicemail_calls,
    COUNT(DISTINCT CASE WHEN c.status = 'transferred' THEN c.id END) as transferred_calls,
    
    AVG(ccm.total_setup_time_ms) / 1000.0 as avg_setup_seconds,
    MIN(ccm.total_setup_time_ms) / 1000.0 as min_setup_seconds,
    MAX(ccm.total_setup_time_ms) / 1000.0 as max_setup_seconds,
    
    AVG(cim.total_duration_seconds) as avg_call_duration,
    AVG(cim.avg_agent_response_time_ms) as avg_response_time_ms,
    
    ROUND(COUNT(DISTINCT CASE WHEN c.status = 'completed' THEN c.id END)::FLOAT / 
          NULLIF(COUNT(DISTINCT c.id), 0) * 100, 2) as success_rate

FROM calls c
LEFT JOIN call_connection_metrics ccm ON c.id = ccm.call_id
LEFT JOIN call_interaction_metrics cim ON c.id = cim.call_id
GROUP BY DATE(c.created_at)
ORDER BY date DESC;

-- Grant permissions (adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO outbound_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO outbound_user;