-- View How Call Data is Stored in Interactions Table

-- 1. Current state of test interactions
\echo '=== CURRENT TEST INTERACTIONS ==='
SELECT 
    SUBSTRING(id, 1, 30) as id,
    status,
    channel,
    outcome,
    duration,
    "paymentDiscussed"
FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "createdAt" DESC;

-- 2. Simulate a complete call lifecycle
\echo '\n=== SIMULATING COMPLETE CALL LIFECYCLE ==='

-- Reset interaction for demo
UPDATE interactions 
SET status = 'INITIATED',
    outcome = NULL,
    duration = NULL,
    "callDisposition" = NULL,
    transcript = NULL,
    recording = NULL
WHERE id = 'test_interaction_1754628065_1';

-- Step 1: Call starts
\echo '\nStep 1: Call Initiated (agent.py starts)'
UPDATE interactions 
SET status = 'IN_PROGRESS'
WHERE id = 'test_interaction_1754628065_1';

-- Step 2: Call completes successfully
\echo '\nStep 2: Call Completed with Payment Promise'
UPDATE interactions 
SET 
    status = 'COMPLETED',
    "endTime" = NOW(),
    duration = 240,  -- 4 minute call
    outcome = 'PAYMENT_PROMISED',
    "callDisposition" = jsonb_build_object(
        'disposition', 'USER_CLAIMED_PAYMENT_WITH_DATE',
        'connection_status', 'CONNECTED', 
        'call_duration', 240,
        'payment_date_mentioned', '2025-08-09',
        'keywords_detected', ARRAY['pay', 'tomorrow', 'online', 'promise']
    ),
    transcript = 'Full conversation transcript stored here...',
    recording = 'https://recordings.example.com/call_12345.mp4',
    "recordingConsent" = true,
    "paymentDiscussed" = true,
    "paymentAmount" = 2500.00,
    "paymentDate" = '2025-08-09',
    "followUpRequired" = true,
    "followUpTiming" = '2025-08-09 10:00:00',
    "followUpType" = 'Payment confirmation'
WHERE id = 'test_interaction_1754628065_1';

-- 3. View the complete record
\echo '\n=== COMPLETE CALL RECORD ==='
SELECT 
    id,
    status,
    outcome,
    duration || ' seconds' as call_duration,
    jsonb_pretty("callDisposition") as disposition_details,
    "paymentDiscussed",
    "paymentAmount",
    "paymentDate",
    recording,
    "followUpRequired",
    "followUpTiming"
FROM interactions 
WHERE id = 'test_interaction_1754628065_1' \gx

-- 4. Show how different dispositions are stored
\echo '\n=== DIFFERENT DISPOSITION EXAMPLES ==='

-- Create temporary examples
INSERT INTO interactions 
    (id, "customerId", "organizationId", "agentId", channel, direction, status, "startTime", outcome, "callDisposition", "createdAt", "updatedAt", "campaignId")
VALUES 
    ('demo_no_answer', 'test_customer_001', 'test_org_001', 'test_agent_001', 'VOICE', 'OUTBOUND', 'FAILED', NOW(), 'NO_ANSWER', 
     '{"disposition": "NO_ANSWER", "connection_status": "NOT_CONNECTED", "ring_duration": 30}'::jsonb, NOW(), NOW(), 'test_campaign_001'),
    
    ('demo_busy', 'test_customer_001', 'test_org_001', 'test_agent_001', 'VOICE', 'OUTBOUND', 'FAILED', NOW(), 'BUSY',
     '{"disposition": "BUSY", "connection_status": "NOT_CONNECTED", "sip_status": "busy"}'::jsonb, NOW(), NOW(), 'test_campaign_001'),
    
    ('demo_payment_plan', 'test_customer_001', 'test_org_001', 'test_agent_001', 'VOICE', 'OUTBOUND', 'COMPLETED', NOW(), 'PAYMENT_PLAN_AGREED',
     '{"disposition": "NEGOTIATED_PAYMENT_PLAN", "connection_status": "CONNECTED", "plan_details": {"installments": 3, "amount": 1000}}'::jsonb, NOW(), NOW(), 'test_campaign_001');

-- View all dispositions
SELECT 
    SUBSTRING(id, 1, 20) as interaction_id,
    status,
    outcome,
    "callDisposition"->>'disposition' as disposition,
    "callDisposition"->>'connection_status' as connection,
    "callDisposition" as full_disposition
FROM interactions 
WHERE "customerId" = 'test_customer_001'
AND "callDisposition" IS NOT NULL
ORDER BY "createdAt" DESC;

-- Clean up demo records
DELETE FROM interactions WHERE id LIKE 'demo_%';

-- 5. Summary statistics
\echo '\n=== INTERACTION SUMMARY ==='
SELECT 
    status,
    COUNT(*) as count,
    COUNT(CASE WHEN "callDisposition" IS NOT NULL THEN 1 END) as with_disposition,
    COUNT(CASE WHEN "paymentDiscussed" = true THEN 1 END) as payment_discussed
FROM interactions 
WHERE "customerId" = 'test_customer_001'
GROUP BY status
ORDER BY status;