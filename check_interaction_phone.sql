-- Check interactions for phone number +918586081540
-- Since phone number is not directly stored in interactions table,
-- we need to join with customers table or check callDisposition JSON

-- First, let's check if there's a customer with this phone number
SELECT 
    c.id as customer_id,
    c."firstName",
    c."lastName",
    c.phone,
    c."organizationId"
FROM customers c
WHERE c.phone = '+918586081540' OR c.phone = '8586081540' OR c.phone = '918586081540';

-- Now check interactions - looking in callDisposition for phone number
\echo '\n=== INTERACTIONS WITH PHONE NUMBER +918586081540 ==='
SELECT 
    i.id,
    i.status,
    i.outcome,
    i."startTime",
    i."endTime",
    i.duration,
    i."callDisposition"->>'phone_number' as called_number,
    i."callDisposition"->>'disposition' as disposition,
    i."callDisposition"->>'room_name' as room_name,
    i."paymentDiscussed",
    i."paymentAmount",
    i."createdAt"
FROM interactions i
WHERE 
    i."callDisposition"->>'phone_number' = '+918586081540'
    OR i."callDisposition"->>'phone_number' = '918586081540'
    OR i."callDisposition"->>'phone_number' = '8586081540'
ORDER BY i."createdAt" DESC;

-- Also check by room name pattern
\echo '\n=== INTERACTIONS BY ROOM NAME PATTERN ==='
SELECT 
    i.id,
    i.status,
    i."customerId",
    i."callDisposition"->>'room_name' as room_name,
    i."callDisposition"->>'phone_number' as phone,
    i."createdAt"
FROM interactions i
WHERE 
    i."callDisposition"->>'room_name' LIKE '%918586081540%'
    OR i."callDisposition"->>'room_name' LIKE '%8586081540%'
ORDER BY i."createdAt" DESC
LIMIT 10;
EOF < /dev/null