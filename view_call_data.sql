-- View how call data is stored in the interactions table

-- 1. Show current state of test interactions
\echo 'Current Interactions:'
SELECT 
    id,
    status,
    channel,
    direction,
    "startTime",
    "endTime",
    duration,
    outcome,
    "callDisposition"::text as disposition
FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "createdAt" DESC;

-- 2. Simulate a successful call with payment promise
\echo '\nSimulating successful call with payment promise...'
UPDATE interactions 
SET 
    status = 'IN_PROGRESS',
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1'
RETURNING id, status;

UPDATE interactions 
SET 
    status = 'COMPLETED',
    "endTime" = NOW(),
    duration = 180,
    outcome = 'PAYMENT_PROMISED',
    "callDisposition" = '{
        "disposition": "USER_CLAIMED_PAYMENT",
        "connection_status": "CONNECTED",
        "call_duration": 180,
        "keywords_detected": ["payment", "tomorrow", "pay online"],
        "payment_discussed": true,
        "agent_notes": "Customer agreed to pay tomorrow online"
    }'::jsonb,
    transcript = 'Agent: Good evening, this is Sarah from XYZ Bank. Am I speaking with Test Customer?
Customer: Yes, this is Test.
Agent: Your monthly payment of $2500 is past due. Can we resolve this today?
Customer: I can pay tomorrow online.
Agent: Perfect! I will share the payment link right now.
Customer: Thank you.
Agent: You are welcome. Have a great day!',
    "paymentDiscussed" = true,
    "paymentAmount" = 2500,
    "paymentDate" = (NOW() + INTERVAL '1 day'),
    "followUpRequired" = true,
    "followUpDate" = (NOW() + INTERVAL '2 days'),
    recording = 'https://recordings.example.com/test_interaction_1754628065_1.mp4',
    "recordingConsent" = true,
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1'
RETURNING id, status, outcome;

-- 3. Show the updated record with all details
\echo '\nDetailed view of completed call:'
SELECT 
    id,
    status,
    outcome,
    duration || ' seconds (' || (duration/60) || ' minutes)' as call_length,
    "callDisposition"->>'disposition' as disposition,
    "callDisposition"->>'connection_status' as connection,
    "callDisposition"->'keywords_detected' as keywords,
    LEFT(transcript, 150) || '...' as transcript_preview,
    "paymentDiscussed",
    "paymentAmount" as amount_promised,
    to_char("paymentDate", 'YYYY-MM-DD') as payment_due,
    recording as recording_url
FROM interactions 
WHERE id = 'test_interaction_1754628065_1';

-- 4. Simulate a failed call (no answer)
\echo '\nSimulating failed call (no answer)...'
UPDATE interactions 
SET 
    status = 'FAILED',
    outcome = 'NO_ANSWER',
    "callDisposition" = '{
        "disposition": "NO_ANSWER",
        "connection_status": "NOT_CONNECTED",
        "sip_status": "timeout",
        "attempt_time": "2025-08-08T04:50:00Z",
        "ring_duration": 30
    }'::jsonb,
    "followUpRequired" = true,
    "followUpDate" = NOW() + INTERVAL '1 day',
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_2'
RETURNING id, status, outcome;

-- 5. Summary view of all interactions
\echo '\nSummary of all interactions:'
SELECT 
    SUBSTRING(id FROM 1 FOR 30) as interaction_id,
    status,
    outcome,
    CASE 
        WHEN "callDisposition" IS NOT NULL 
        THEN "callDisposition"->>'disposition' 
        ELSE 'No disposition' 
    END as disposition,
    CASE 
        WHEN "callDisposition" IS NOT NULL 
        THEN "callDisposition"->>'connection_status' 
        ELSE 'Not attempted' 
    END as connection,
    COALESCE(duration::text || 's', 'N/A') as duration,
    "paymentDiscussed",
    "paymentAmount"
FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "updatedAt" DESC;

-- 6. Reset the data (optional - uncomment to reset)
-- UPDATE interactions 
-- SET 
--     status = 'INITIATED',
--     "endTime" = NULL,
--     duration = NULL,
--     outcome = NULL,
--     "callDisposition" = NULL,
--     transcript = NULL,
--     "paymentDiscussed" = false,
--     "paymentAmount" = NULL,
--     "paymentDate" = NULL,
--     recording = NULL,
--     "recordingConsent" = false,
--     "followUpRequired" = false,
--     "followUpDate" = NULL
-- WHERE "customerId" = 'test_customer_001' 
-- AND id IN ('test_interaction_1754628065_1', 'test_interaction_1754628065_2');