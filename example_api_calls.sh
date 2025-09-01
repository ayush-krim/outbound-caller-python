#!/bin/bash

# Example API calls to demonstrate multi-agent system
# Each call uses a different agent_id to get different behavioral instructions

echo "=========================================="
echo "MULTI-AGENT INSTRUCTION SYSTEM - API EXAMPLES"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}Example 1: Base Instructions Only (No Agent ID)${NC}"
echo "Uses only compliance and base instructions without any agent-specific behavior"
echo ""
cat <<EOF
curl -X POST http://localhost:8003/call \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: admin-api-key-12345" \\
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test Customer",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02",
      "late_fee": 350
    }
  }'
EOF

echo ""
echo "=========================================="
echo ""
echo -e "${BLUE}Example 2: Collection Agent (AGENT_001)${NC}"
echo "This agent uses Sarah's identity and focuses on 50% minimum payment with 2-day timeline"
echo ""
cat <<EOF
curl -X POST http://localhost:8003/call \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: admin-api-key-12345" \\
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "agent_id": "AGENT_001",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test Customer",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02",
      "late_fee": 350
    }
  }'
EOF

echo ""
echo "=========================================="
echo ""
echo -e "${BLUE}Example 3: Pre-Due Reminder Agent (PREDUE_AGENT)${NC}"
echo "This agent uses Michael's identity and focuses on upcoming payment reminders"
echo ""
cat <<EOF
curl -X POST http://localhost:8003/call \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: admin-api-key-12345" \\
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "agent_id": "PREDUE_AGENT",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test Customer",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-09-05",
      "late_fee": 0
    }
  }'
EOF

echo ""
echo "=========================================="
echo ""
echo -e "${BLUE}Example 4: Unknown Agent (Will use base instructions only)${NC}"
echo "When an unknown agent_id is provided, system uses only base instructions"
echo ""
cat <<EOF
curl -X POST http://localhost:8003/call \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: admin-api-key-12345" \\
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "agent_id": "CUSTOM_AGENT_NOT_DEFINED",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test Customer",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02",
      "late_fee": 350
    }
  }'
EOF

echo ""
echo "=========================================="
echo ""
echo -e "${GREEN}How to add new agents:${NC}"
echo ""
echo "1. Edit config/agent_instructions.json"
echo "2. Add a new agent under the 'agents' section"
echo "3. Define the agent's identity, negotiation rules, and behavioral instructions"
echo "4. Use the new agent_id in your API calls"
echo ""
echo "Example structure for a new agent:"
cat <<EOF
"SOFT_COLLECTION_AGENT": {
  "identity": "You are Emma from XYZ Bank's customer service team.",
  "minimum_payment": "Suggested payment: \${half_emi}",
  "conversation_steps": [...],
  "negotiation_rules": {...},
  "response_style": [...],
  "empathy_guidelines": [...]
}
EOF

echo ""
echo "=========================================="
echo ""
echo -e "${GREEN}Key Features:${NC}"
echo "✓ Base instructions (compliance, opt-out, consequences) are the default"
echo "✓ No agent_id or unknown agent → uses only base instructions"
echo "✓ Each agent adds unique behavioral instructions (identity, tone, negotiation)"
echo "✓ Customer information is dynamically inserted into instructions"
echo "✓ Easy to add new agents via JSON configuration"
echo ""
echo "==========================================