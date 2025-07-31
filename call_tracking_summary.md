# Call Tracking Summary

Based on your call with the voice agent, here's what data would typically be tracked in the PostgreSQL database:

## 1. Connection Metrics (call_connection_metrics table)

- **Dispatch ID**: AD_3QBJGjxRtFJg
- **Room Name**: room-XnDfBEpiQVNi
- **Phone Number**: +917827470456
- **Dispatch Created**: When you ran the lk dispatch command
- **Room Connection Time**: ~200-300ms (connecting to LiveKit)
- **Agent Init Time**: ~100-150ms (creating AI agent)
- **Session Creation Time**: ~80-100ms (OpenAI Realtime setup)
- **SIP Dial Time**: 3-5 seconds (calling your phone)
- **Total Setup Time**: ~4-6 seconds (from dispatch to answered)

## 2. Interaction Metrics (call_interaction_metrics table)

- **Call Duration**: Length of your conversation
- **Agent Utterances**: Number of times the agent spoke
- **User Utterances**: Number of times you spoke
- **Average Response Time**: How quickly agent responded (target < 800ms)
- **Time to First Response**: Time until agent's greeting (target < 1s)

## 3. Events Tracked (call_events table)

Each event with timestamp from call start:
- `call_started` - When you answered
- `participant_joined` - When you connected to room
- `user_first_speech` - Your first utterance
- `agent_first_speech` - Agent's greeting
- Any special events like:
  - `transfer_requested` - If you asked for transfer
  - `appointment_confirmed` - If you confirmed appointment
  - `voicemail_detected` - If it was voicemail
- `call_ended` - When call finished

## 4. System Metrics (call_system_metrics table)

- **Resource Usage**: CPU/Memory during call
- **Network Performance**: Latency, packet loss
- **AI Performance**: 
  - OpenAI API response times
  - Token usage
  - Number of LLM requests

## 5. Speech Analytics (call_speech_analytics table)

- **Words Spoken**: Total by agent and user
- **Speech Rate**: Words per minute
- **Conversation Flow**: Topic changes, clarifications
- **Transcript**: Full conversation text (if enabled)

## What This Data Enables:

1. **Performance Monitoring**
   - Is the agent meeting response time targets?
   - Are calls connecting quickly enough?
   - Which phases have bottlenecks?

2. **Quality Analysis**
   - Are conversations natural (good response times)?
   - Is the agent understanding users (few clarifications)?
   - Are users satisfied (call duration, transfer requests)?

3. **Cost Optimization**
   - Token usage per call
   - Call duration trends
   - Resource utilization

4. **Business Insights**
   - Peak calling times
   - Common user requests
   - Success rates (appointments confirmed, etc.)

## Viewing the Data

Once PostgreSQL is properly configured, you can:

1. **Run the analytics dashboard**:
   ```bash
   python analytics_dashboard.py
   ```

2. **Query specific metrics**:
   ```sql
   -- Average setup time today
   SELECT AVG(total_setup_time_ms) / 1000.0 as avg_setup_seconds
   FROM call_connection_metrics
   WHERE dispatch_created_at > CURRENT_DATE;
   
   -- Call outcomes
   SELECT status, COUNT(*) 
   FROM calls 
   GROUP BY status;
   ```

The tracking system captures everything needed to optimize the voice agent's performance and user experience!