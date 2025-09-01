# Multi-Agent Testing Guide

## Quick Start

### 1. Start the API Server
```bash
python api_server.py
```
The server will run on port 8003 (or find a free port automatically)

### 2. Run Comprehensive Tests
```bash
./test_multi_agent.sh
```
This will test all scenarios including error cases.

## Test Scenarios

### ✅ Valid Scenarios (Should Succeed)

#### 1. POST_BOUNCE_AGENT - Post-Bounce Collection (Sarah)
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "POST_BOUNCE_AGENT",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "John Doe",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02",
      "late_fee": 350
    }
  }'
```

**Agent Behavior:**
- Identity: Sarah from XYZ Bank
- Greeting: "This is Sarah from Unicorn Bank. This call may be recorded..."
- Strategy: 50% minimum payment, 2-day timeline
- Tone: Professional, empathetic but firm

#### 2. PREDUE_AGENT - Pre-Due Reminder (Michael)
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "PREDUE_AGENT",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Jane Smith",
      "last_4_digits": "5678",
      "emi_amount": 3000,
      "emi_due_date": "2025-09-10"
    }
  }'
```

**Agent Behavior:**
- Identity: Michael from XYZ Bank
- Greeting: "This is Michael from Unicorn Bank. This call may be recorded. I'm calling about your upcoming payment..."
- Strategy: Payment scheduling, prevention
- Tone: Friendly, proactive, helpful

### ❌ Error Scenarios (Should Fail)

#### 1. Missing agent_id
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456"
  }'
```
**Expected Error:** Field required (agent_id)

#### 2. Empty agent_id
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456"
  }'
```
**Expected Error:** Invalid agent_id

#### 3. Unknown agent_id
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "UNKNOWN_AGENT",
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456"
  }'
```
**Expected Error:** Invalid agent_id 'UNKNOWN_AGENT'. Available agents: POST_BOUNCE_AGENT, PREDUE_AGENT

#### 4. Case Sensitivity
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "agent_001",  # lowercase - will fail
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "phone_number": "+917827470456"
  }'
```
**Expected Error:** Invalid agent_id 'agent_001'. Available agents: POST_BOUNCE_AGENT, PREDUE_AGENT

## Understanding the Instruction Flow

### How Instructions are Built:

1. **API receives agent_id** → Validates it exists
2. **Agent.py gets agent_id** → Passes to instruction service
3. **Instruction Service**:
   - Loads base instructions (compliance, opt-out, tools)
   - Loads agent-specific instructions (identity, tone, strategy)
   - If agent has custom greeting, it overrides base greeting
   - Combines: base + agent instructions
4. **Agent receives formatted instructions** → Uses for the call

### Base Instructions Include:
- Compliance greeting (if no agent greeting)
- Opt-out rules
- Tool usage guidelines
- Account info response rules
- Consequences/fee disclosure scripts
- General behavioral rules

### Agent Instructions Add:
- Identity (who they are)
- Custom greeting (optional)
- Conversation flow
- Negotiation strategy
- Response style
- Empathy guidelines

## Adding New Agents

1. Edit `config/agent_instructions.json`
2. Add new agent under "agents" section:

```json
"SOFT_AGENT": {
  "identity": "You are Emma from XYZ Bank's customer care team.",
  "greeting": "Hi, this is Emma from Unicorn Bank's customer care. This call may be recorded. May I speak with {customer_name}?",
  "conversation_steps": [
    "Warmly greet and check on their wellbeing",
    "Gently mention the payment situation",
    "Focus on finding a comfortable solution"
  ],
  "negotiation_rules": {
    "first_response": {
      "hardship": "I completely understand. You can stop future calls by saying 'stop calling.' What would work best for your situation?"
    }
  },
  "response_style": [
    "Warm and caring",
    "Non-confrontational",
    "Solution-focused"
  ],
  "empathy_guidelines": [
    "Lead with empathy",
    "Validate all concerns",
    "Offer multiple options"
  ]
}
```

3. Test the new agent:
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "SOFT_AGENT",
    ...
  }'
```

## Troubleshooting

### API Server Issues
- Check logs: `tail -f api_server.log`
- Verify port: Server will auto-find free port if 8000 is busy
- Check database: `python seed_database.py` to create test data

### Agent Not Working
- Verify agent_id is exact match (case-sensitive)
- Check JSON syntax in config/agent_instructions.json
- Run: `python test_instructions.py` to validate configuration

### Call Not Connecting
- Ensure LiveKit server is running
- Check .env.local has correct LiveKit credentials
- Verify phone number is in E.164 format (+1234567890)