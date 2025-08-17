#!/bin/bash

echo "Making call..."
curl -X POST http://localhost:8003/call \
    -H "Content-Type: application/json" \
    -d '{
      "customer_id": "user_dummy_1",
      "organization_id": "krim_ai_dummy_org",
      "campaign_id": "",
      "agent_id": "agent_01921c9d-9f2e-7494-a76f-f96b73b66e13",
      "phone_number": "+918586081540",
      "from_number": "+15076269649",
      "customer_info": {
        "customer_name": "Abhishek",
        "last_4_digits": "1234",
        "emi_amount": 5000,
        "days_past_due": 25,
        "emi_due_date": "2025-08-01",
        "late_fee": 500
      }
    }'

echo -e "\n\nWatching agent log for job request..."
tail -f agent_fixed_final.log | grep --line-buffered -E "job_request|interaction|database|error|failed"