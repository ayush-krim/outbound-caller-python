# Multi-Agent Instruction System

## Overview
The multi-agent instruction system allows different AI agents to have unique behavioral instructions while sharing common compliance and regulatory requirements. This enables testing different collection strategies, tones, and approaches without duplicating compliance code.

## Architecture

### Components
1. **config/agent_instructions.json** - JSON configuration file containing all instructions
2. **services/agent_instructions.py** - Service class for loading and formatting instructions
3. **agent.py** - Modified to use dynamic instructions based on agent_id

### Instruction Structure
Instructions are split into two parts:
- **Base Instructions**: Complete compliance-focused instructions that work standalone
  - Recording notices, opt-out rules
  - Tool usage guidelines
  - Consequences scripts, fee disclosures
  - General behavioral rules (concise, no threats)
  - Used when no agent_id provided or unknown agent
  
- **Behavioral Instructions**: Agent-specific additions/overrides
  - Agent identity and greeting
  - Negotiation strategy
  - Tone and empathy guidelines
  - Conversation flow

## Configuration File Structure

```json
{
  "base_instructions": {
    "greeting": "...",           // Initial compliance greeting
    "opt_out_compliance": {...}, // Opt-out rules
    "tool_usage": {...},         // Tool usage guidelines
    "consequences_response": {...}, // What happens if customer doesn't pay
    "compliance_script_fees": {...} // Fee disclosure scripts
  },
  "agents": {
    "AGENT_001": {
      "identity": "You are Sarah from XYZ Bank...",
      "negotiation_rules": {...},
      "response_style": [...],
      "empathy_guidelines": [...]
    },
    "PREDUE_AGENT": {
      "identity": "You are Michael from XYZ Bank...",
      // Different behavioral instructions
    }
  }
}
```

## Adding New Agents

1. Edit `config/agent_instructions.json`
2. Add a new agent under the `agents` section:

```json
"SOFT_COLLECTION_AGENT": {
  "identity": "You are Emma from XYZ Bank's customer service team.",
  "minimum_payment": "Suggested payment: ${half_emi}",
  "conversation_steps": [
    "Greet warmly and ask about their day",
    "Gently mention the overdue payment",
    "Focus on finding a solution that works for them"
  ],
  "negotiation_rules": {
    "first_response": {
      "note": "Include opt-out",
      "hardship": "I completely understand. You can stop future calls by saying 'stop calling.' What amount would be comfortable for you today?"
    }
  },
  "response_style": [
    "Warm and friendly",
    "Non-confrontational",
    "Solution-oriented"
  ],
  "empathy_guidelines": [
    "Always validate their feelings",
    "Use a supportive tone",
    "Focus on partnership rather than collection"
  ]
}
```

## Using Different Agents in API Calls

### Base Instructions Only (No Agent)
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    # No agent_id field - uses base instructions only
    "customer_id": "test_customer_001",
    "phone_number": "+917827470456",
    "customer_info": {
      "customer_name": "John Doe",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02"
    }
  }'
```

### With Specific Agent
```bash
curl -X POST http://localhost:8003/call \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-api-key-12345" \
  -d '{
    "agent_id": "POST_BOUNCE_AGENT",  # Specify which agent to use
    "customer_id": "test_customer_001",
    "phone_number": "+917827470456",
    "customer_info": {
      "customer_name": "John Doe",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02"
    }
  }'
```

## Available Agents

### Base Instructions (No Agent ID)
- **Identity**: None (generic compliance-focused)
- **Style**: Concise, professional
- **Strategy**: Basic compliance and information gathering
- **Use Case**: When you need minimal agent behavior, just compliance

### POST_BOUNCE_AGENT (Post-Bounce Collection Agent)
- **Identity**: Sarah from XYZ Bank
- **Style**: Professional, empathetic but firm
- **Strategy**: 50% minimum payment, 2-day timeline
- **Use Case**: Standard collection calls for past-due accounts

### PREDUE_AGENT (Pre-Due Reminder Agent)
- **Identity**: Michael from XYZ Bank
- **Style**: Friendly, proactive, helpful
- **Strategy**: Payment scheduling, preventing late payments
- **Use Case**: Reminder calls before payment due date

## Variable Substitution

The following variables are automatically substituted in instructions:

| Variable | Description | Example |
|----------|-------------|---------|
| `{customer_name}` | Customer's full name | "John Doe" |
| `{last_4_digits}` | Last 4 digits of account | "1234" |
| `{emi_amount}` | Monthly payment amount | "2500" |
| `{days_past_due}` | Days past due | "15" |
| `{half_emi}` | 50% of EMI amount | "1250" |
| `{half_emi_int}` | 50% of EMI as integer | "1250" |
| `{late_fee}` | Late fee amount | "350" |
| `{days_until_due}` | Days until payment due (predue) | "3" |

## Testing

### Run the test script:
```bash
python test_instructions.py
```

This will:
- List all available agents
- Test instruction loading for each agent
- Validate variable substitution
- Check base vs behavioral instruction separation

### Test with actual calls:
```bash
# Test with AGENT_001
python seed_database.py  # Seed test data
curl -X POST http://localhost:8003/call ... # See example_api_calls.sh
```

## Benefits

1. **Compliance Consistency**: All agents share the same compliance requirements
2. **Easy A/B Testing**: Test different collection strategies by changing agent_id
3. **Rapid Iteration**: Add new agents without modifying code
4. **Clear Separation**: Base (compliance) vs Behavioral (strategy) instructions
5. **Maintainability**: Single source of truth for instructions in JSON

## Troubleshooting

### Agent not found
If an unknown agent_id is provided, the system uses only base instructions (no agent-specific behavior).

### Variable substitution errors
Ensure all required customer_info fields are provided in the API request.

### Instructions not updating
The API server hot-reloads when files change. Check api_server.log for reload confirmations.

## Future Enhancements

1. **Dynamic agent selection**: Choose agent based on customer profile or payment history
2. **Time-based agents**: Different agents for morning/evening calls
3. **Escalation agents**: Progressive agent strategies based on call attempts
4. **Language variants**: Multiple language support per agent
5. **Performance tracking**: Track success rates per agent configuration