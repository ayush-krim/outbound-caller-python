-- How Call Data is Stored in the Database

-- Reset one interaction to show the flow
UPDATE interactions 
SET status = 'INITIATED', 
    "endTime" = NULL,
    duration = NULL,
    outcome = NULL,
    "callDisposition" = NULL
WHERE id = 'test_interaction_1754628065_1';

-- 1. Initial State (created by platform)
\echo '1. INITIAL STATE - Interaction ready for calling:'
SELECT id, status, channel, "startTime", outcome 
FROM interactions 
WHERE id = 'test_interaction_1754628065_1';

-- 2. Call Started (agent.py updates this)
\echo '\n2. CALL STARTED - Status changes to IN_PROGRESS:'
UPDATE interactions 
SET status = 'IN_PROGRESS',
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1';

SELECT id, status, channel, "startTime", outcome 
FROM interactions 
WHERE id = 'test_interaction_1754628065_1';

-- 3. Call Completed Successfully (agent.py updates when call ends)
\echo '\n3. CALL COMPLETED - Full update with disposition and transcript:'
UPDATE interactions 
SET 
    status = 'COMPLETED',
    "endTime" = "startTime" + INTERVAL '3 minutes',
    duration = 180,
    outcome = 'PAYMENT_PROMISED',
    "callDisposition" = jsonb_build_object(
        'disposition', 'USER_CLAIMED_PAYMENT',
        'connection_status', 'CONNECTED',
        'call_duration', 180,
        'keywords_detected', ARRAY['payment', 'tomorrow', 'online'],
        'payment_discussed', true
    ),
    transcript = 'Agent: Good evening, this is Sarah from XYZ Bank. Am I speaking with Test Customer?
Customer: Yes, speaking.
Agent: Your monthly payment of $2500 is past due. Can we resolve this today?
Customer: I''ll pay tomorrow online.
Agent: Perfect! I''ll share the payment link right now.',
    "paymentDiscussed" = true,
    "paymentAmount" = 2500,
    "paymentDate" = CURRENT_DATE + INTERVAL '1 day',
    recording = 'https://recordings.livekit.cloud/room_outbound-917827470456_20250808.mp4',
    "recordingConsent" = true,
    "followUpRequired" = true,
    "followUpTiming" = 'WITHIN_48_HOURS',
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1';

-- 4. View the Complete Record
\echo '\n4. COMPLETE CALL RECORD:'
SELECT 
    id,
    status,
    outcome,
    duration || ' seconds' as duration,
    "callDisposition"->>'disposition' as disposition,
    "callDisposition"->>'connection_status' as connected,
    ("callDisposition"->'keywords_detected')::text as keywords,
    LEFT(transcript, 100) || '...' as transcript_preview,
    "paymentAmount",
    "paymentDate"::date as payment_due,
    "followUpRequired",
    "followUpTiming"
FROM interactions 
WHERE id = 'test_interaction_1754628065_1' \gx

-- 5. Show Different Disposition Examples
\echo '\n5. EXAMPLES OF DIFFERENT DISPOSITIONS:'

-- No Answer
UPDATE interactions
SET "callDisposition" = '{"disposition": "NO_ANSWER", "connection_status": "NOT_CONNECTED"}'::jsonb,
    outcome = 'NO_ANSWER'
WHERE id = 'test_interaction_1754628065_2';

-- Busy
INSERT INTO interactions (id, "customerId", "organizationId", "agentId", channel, direction, status, "startTime", "createdAt", "updatedAt", "campaignId")
VALUES ('example_busy', 'test_customer_001', 'test_org_001', 'test_agent_001', 'VOICE', 'OUTBOUND', 'FAILED', NOW(), NOW(), NOW(), 'test_campaign_001');

UPDATE interactions
SET "callDisposition" = '{"disposition": "BUSY", "connection_status": "NOT_CONNECTED"}'::jsonb,
    outcome = 'BUSY',
    status = 'FAILED'
WHERE id = 'example_busy';

SELECT 
    SUBSTRING(id, 1, 20) as interaction_id,
    status,
    outcome,
    ("callDisposition"->>'disposition') as disposition,
    ("callDisposition"->>'connection_status') as connection
FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "updatedAt" DESC
LIMIT 5;

-- Clean up
DELETE FROM interactions WHERE id = 'example_busy';