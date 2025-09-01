#!/bin/bash

# API Test Script for Multi-Agent System
# Tests different agent configurations with curl commands

# Configuration
API_URL="http://localhost:8003"
API_KEY="admin-api-key-12345"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "    MULTI-AGENT API TEST SUITE"
echo "========================================"
echo ""

# Function to make API call and display result
make_call() {
    local test_name="$1"
    local agent_id="$2"
    local description="$3"
    
    echo -e "${BLUE}Test: ${test_name}${NC}"
    echo -e "${YELLOW}Agent ID: ${agent_id}${NC}"
    echo "$description"
    echo ""
    
    # Build JSON payload
    if [ "$agent_id" == "NONE" ]; then
        # Test missing agent_id (should fail)
        payload='{
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
    else
        payload="{
            \"customer_id\": \"test_customer_001\",
            \"organization_id\": \"test_org_001\",
            \"campaign_id\": \"test_campaign_001\",
            \"agent_id\": \"$agent_id\",
            \"phone_number\": \"+917827470456\",
            \"from_number\": \"+15076269649\",
            \"customer_info\": {
                \"customer_name\": \"Test Customer\",
                \"last_4_digits\": \"1234\",
                \"emi_amount\": 2500,
                \"emi_due_date\": \"2025-08-02\",
                \"late_fee\": 350
            }
        }"
    fi
    
    echo "Request:"
    echo "$payload" | jq '.' 2>/dev/null || echo "$payload"
    echo ""
    
    echo "Response:"
    response=$(curl -s -X POST "$API_URL/call" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$payload")
    
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Check if successful
    if echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}✅ Test passed${NC}"
    else
        echo -e "${RED}❌ Test failed${NC}"
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Test 1: Missing agent_id (should fail with helpful error)
echo -e "${RED}=== TEST 1: Missing Agent ID (Should Fail) ===${NC}"
make_call \
    "Missing Agent ID" \
    "NONE" \
    "This should fail with an error message telling user to provide agent_id"

# Wait a moment
sleep 2

# Test 2: Base instructions only
echo -e "${GREEN}=== TEST 2: Base Instructions Only ===${NC}"
make_call \
    "Base Instructions" \
    "BASE" \
    "Uses only compliance and base instructions without agent-specific behavior"

# Wait before next call
sleep 2

# Test 3: Collection Agent (AGENT_001)
echo -e "${GREEN}=== TEST 3: Collection Agent Sarah ===${NC}"
make_call \
    "AGENT_001 - Sarah" \
    "AGENT_001" \
    "Sarah from XYZ Bank - Professional collection agent with 50% minimum payment strategy"

# Wait before next call
sleep 2

# Test 4: Pre-due Reminder Agent
echo -e "${GREEN}=== TEST 4: Pre-Due Reminder Agent Michael ===${NC}"
# Modify the date for pre-due scenario
payload_predue='{
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

echo -e "${BLUE}Test: Pre-Due Agent${NC}"
echo -e "${YELLOW}Agent ID: PREDUE_AGENT${NC}"
echo "Michael from XYZ Bank - Friendly reminder for upcoming payment"
echo ""
echo "Request:"
echo "$payload_predue" | jq '.'
echo ""
echo "Response:"
response=$(curl -s -X POST "$API_URL/call" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$payload_predue")

echo "$response" | jq '.' 2>/dev/null || echo "$response"

if echo "$response" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ Test passed${NC}"
else
    echo -e "${RED}❌ Test failed${NC}"
fi

echo ""
echo "----------------------------------------"
echo ""

# Wait before next call
sleep 2

# Test 5: Unknown Agent (should use base instructions)
echo -e "${YELLOW}=== TEST 5: Unknown Agent ===${NC}"
make_call \
    "Unknown Agent" \
    "UNKNOWN_AGENT_XYZ" \
    "Unknown agent ID - should default to base instructions only"

# Test 6: Empty string agent_id (should fail)
echo -e "${RED}=== TEST 6: Empty Agent ID (Should Fail) ===${NC}"
make_call \
    "Empty Agent ID" \
    "" \
    "Empty string for agent_id - should fail with error message"

echo ""
echo "========================================"
echo "         TEST SUMMARY"
echo "========================================"
echo ""
echo -e "${GREEN}Expected Results:${NC}"
echo "1. Missing agent_id: ❌ Should fail with error"
echo "2. BASE: ✅ Should work with base instructions only"
echo "3. AGENT_001: ✅ Should work with Sarah's instructions"
echo "4. PREDUE_AGENT: ✅ Should work with Michael's instructions"
echo "5. Unknown agent: ✅ Should work with base instructions (with warning)"
echo "6. Empty agent_id: ❌ Should fail with error"
echo ""
echo "========================================"
echo ""
echo -e "${BLUE}Quick Reference - Agent IDs:${NC}"
echo "• BASE         - Base instructions only (compliance-focused)"
echo "• AGENT_001    - Sarah, collection agent"
echo "• PREDUE_AGENT - Michael, pre-due reminder"
echo "• (unknown)    - Falls back to base instructions"
echo ""
echo "========================================"
echo ""
echo -e "${YELLOW}Example CURL Commands:${NC}"
echo ""
echo "# Base instructions only:"
echo 'curl -X POST http://localhost:8003/call \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "X-API-Key: admin-api-key-12345" \'
echo '  -d '"'"'{"agent_id": "BASE", "customer_id": "test_customer_001", ...}'"'"
echo ""
echo "# Specific agent:"
echo 'curl -X POST http://localhost:8003/call \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "X-API-Key: admin-api-key-12345" \'
echo '  -d '"'"'{"agent_id": "AGENT_001", "customer_id": "test_customer_001", ...}'"'"
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Note: Install 'jq' for better JSON formatting:${NC}"
    echo "  brew install jq  # macOS"
    echo "  apt-get install jq  # Ubuntu/Debian"
    echo ""
fi