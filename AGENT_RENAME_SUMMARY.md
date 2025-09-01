# Agent Rename Complete: AGENT_001 → POST_BOUNCE_AGENT

## ✅ Changes Made

The agent `AGENT_001` has been renamed to `POST_BOUNCE_AGENT` throughout the system.

### Files Updated:
1. **config/agent_instructions.json** - Agent configuration
2. **api_server.py** - API documentation and examples
3. **test_multi_agent.sh** - Test scripts
4. **test_instructions.py** - Unit tests
5. **TESTING_GUIDE.md** - Testing documentation
6. **MULTI_AGENT_INSTRUCTIONS.md** - Multi-agent documentation

## 📋 Current Agents

| Agent ID | Name | Purpose |
|----------|------|---------|
| **POST_BOUNCE_AGENT** | Sarah | Post-bounce/overdue payment collection |
| **PREDUE_AGENT** | Michael | Pre-due payment reminders |

## 🎯 Key Differences

### POST_BOUNCE_AGENT (Sarah)
- **When to use:** Payment has already bounced or is past due
- **Approach:** Collection-focused, firm but empathetic
- **Minimum payment:** 50% of EMI amount
- **Timeline:** 2-day maximum for payment
- **Opening:** "I'm calling about your payment that's X days past due"

### PREDUE_AGENT (Michael)
- **When to use:** Payment is coming up soon (not yet due)
- **Approach:** Prevention-focused, friendly and helpful
- **Payment:** Flexible, focuses on scheduling
- **Timeline:** Before the due date
- **Opening:** "I'm calling about your upcoming payment due in X days"

## 📝 Example API Calls

### Post-Bounce Collection Call:
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "POST_BOUNCE_AGENT",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456",
    "customer_info": {
      "customer_name": "John Doe",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02"
    }
  }'
```

### Pre-Due Reminder Call:
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "PREDUE_AGENT",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456",
    "customer_info": {
      "customer_name": "Jane Smith",
      "emi_amount": 3000,
      "emi_due_date": "2025-09-10"
    }
  }'
```

## ⚠️ Important Notes

1. **Case Sensitive:** Agent IDs are case-sensitive. Use exactly `POST_BOUNCE_AGENT` or `PREDUE_AGENT`
2. **Required Field:** agent_id is required in all API calls
3. **No Fallback:** Invalid agent_id will return an error, not fall back to base instructions
4. **Error Message:** Invalid agents will show: "Invalid agent_id 'XXX'. Available agents: POST_BOUNCE_AGENT, PREDUE_AGENT"

## 🧪 Testing

Run the comprehensive test suite:
```bash
./test_multi_agent.sh
```

This will test:
- ✅ Valid POST_BOUNCE_AGENT calls
- ✅ Valid PREDUE_AGENT calls
- ❌ Missing agent_id (error)
- ❌ Invalid agent_id (error)
- ❌ Case sensitivity (error)