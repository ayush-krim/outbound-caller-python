# Call Disposition Guide

## Overview
The call disposition system automatically tracks and categorizes the outcome of each outbound call based on customer responses and call connection status.

## Disposition Types

### Connected Call Dispositions (17 types)

1. **User Claimed Payment with Payment Date** - Customer claims payment was made on a specific date
2. **User Claimed Payment** - Customer claims payment was made but doesn't provide date
3. **User Agrees to Maintain Balance** - Customer agrees to maintain balance for auto-debit
4. **Agree To Pay** - Customer agrees to make payment
5. **General** - Conversation without clear conclusion
6. **Payment Due Reminder** - Agent delivered payment reminder but no further progress
7. **Refused to Pay** - Customer refuses to make payment
8. **RTP - Counselled** - Customer refused but agent attempted to counsel
9. **Human Handoff Requested** - Customer requests human agent
10. **Raise Dispute with Detail** - Customer raises dispute about the bank/account
11. **User Busy Now** - Customer says they're busy/not free
12. **No Response** - Customer didn't respond during call
13. **Customer Hangup** - Customer hung up within 10 seconds
14. **Delay Reason** - Customer explains why payment is delayed
15. **Uncertain Propensity to Pay** - Customer shows uncertainty about repayment
16. **Acceptable Promise To Pay** - Customer makes acceptable payment promise
17. **Unacceptable Promise To Pay** - Customer's payment promise is not acceptable

### Not Connected Dispositions (3 types)

1. **Busy** - Phone line was busy
2. **Failed** - Network issue or call failed
3. **No Answer** - Call rang but customer didn't answer

## How It Works

1. **Real-time Tracking**: The disposition is updated throughout the call as the conversation progresses
2. **Automatic Detection**: Based on keywords, phrases, and conversation patterns
3. **Connection Status**: Tracks whether the call connected or not
4. **Final Disposition**: Determined at call end based on entire conversation

## API Endpoints

### Get All Dispositions
```bash
curl http://localhost:8000/dispositions
```

### Get Call Status with Disposition
```bash
curl http://localhost:8000/calls/{dispatch_id}
```

### Update Call Disposition (Manual Override)
```bash
curl -X POST http://localhost:8000/calls/{dispatch_id}/disposition \
  -H "Content-Type: application/json" \
  -d '"Agree To Pay"'
```

## Integration with Transcript

The disposition is automatically saved with the call transcript:
```json
{
  "disposition": {
    "disposition": "Agree To Pay",
    "connection_status": "CONNECTED",
    "call_duration": 125.5,
    "disposition_history": [...]
  }
}
```

## Disposition Detection Logic

The system analyzes:
- Customer keywords and phrases
- Call duration (e.g., <10 seconds = Customer Hangup)
- Payment-related terms with dates
- Refusal indicators
- Request for human agents
- Dispute keywords
- Busy/availability indicators

## Usage Tips

1. The disposition updates in real-time during the call
2. Check final disposition after call completion
3. Use the API to retrieve disposition for reporting
4. Manual override available if automatic detection is incorrect