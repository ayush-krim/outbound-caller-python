-- Simulate what the data would look like after a successful call
-- This shows how the interactions table is updated during the call lifecycle

-- 1. View current state
SELECT id, status, "startTime", "endTime", duration, outcome, "callDisposition"
FROM interactions 
WHERE "customerId" = 'test_customer_001';

-- 2. Simulate call start (what agent.py would do)
UPDATE interactions 
SET 
    status = 'IN_PROGRESS',
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1';

-- 3. Simulate call completion (what agent.py would do on call end)
UPDATE interactions 
SET 
    status = 'COMPLETED',
    "endTime" = NOW(),
    duration = 180, -- 3 minute call
    outcome = 'SUCCESS',
    "callDisposition" = '{
        "disposition": "USER_CLAIMED_PAYMENT",
        "connection_status": "CONNECTED",
        "call_duration": 180,
        "call_start_time": "2025-08-08T04:45:00Z",
        "call_end_time": "2025-08-08T04:48:00Z",
        "keywords_detected": ["payment", "tomorrow", "pay online"],
        "payment_discussed": true
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
    "paymentDate" = (NOW() + INTERVAL '1 day')::date,
    sentiment = 'POSITIVE',
    "customerSatisfactionScore" = 4,
    "fdcpaCompliant" = true,
    "tcpaCompliant" = true,
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_1';

-- 4. View the updated record
SELECT 
    id,
    status,
    channel,
    "startTime",
    "endTime",
    duration || ' seconds' as duration,
    outcome,
    "callDisposition",
    LEFT(transcript, 200) || '...' as transcript_preview,
    "paymentDiscussed",
    "paymentAmount",
    "paymentDate",
    sentiment,
    "customerSatisfactionScore"
FROM interactions 
WHERE id = 'test_interaction_1754628065_1';

-- 5. Example of a failed call
UPDATE interactions 
SET 
    status = 'FAILED',
    outcome = 'FAILED',
    "callDisposition" = '{
        "disposition": "NO_ANSWER",
        "connection_status": "NOT_CONNECTED",
        "sip_status": "timeout",
        "attempt_time": "2025-08-08T04:50:00Z"
    }'::jsonb,
    "updatedAt" = NOW()
WHERE id = 'test_interaction_1754628065_2';

-- 6. View summary of all interactions
SELECT 
    id,
    status,
    outcome,
    ("callDisposition"->>'disposition') as disposition,
    ("callDisposition"->>'connection_status') as connection,
    duration,
    "paymentDiscussed",
    "paymentAmount"
FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "createdAt" DESC;