#!/bin/bash

# Comprehensive Multi-Agent Testing Script
# Tests all scenarios for the multi-agent instruction system

# Configuration
API_URL="http://localhost:8003"
API_KEY="admin-api-key-12345"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "     MULTI-AGENT SYSTEM - COMPREHENSIVE TEST"
echo "================================================"
echo ""

# Test counter
test_num=0
passed=0
failed=0

# Function to run a test
run_test() {
    local test_name="$1"
    local payload="$2"
    local expected_result="$3"  # "success" or "fail"
    local description="$4"
    
    test_num=$((test_num + 1))
    
    echo -e "${BLUE}TEST $test_num: $test_name${NC}"
    echo "$description"
    echo ""
    echo "Request payload:"
    echo "$payload" | jq '.' 2>/dev/null || echo "$payload"
    echo ""
    
    # Make the API call
    response=$(curl -s -X POST "$API_URL/call" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$payload" 2>/dev/null)
    
    echo "Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Check result
    if [ "$expected_result" = "success" ]; then
        if echo "$response" | grep -q '"success":true'; then
            echo -e "${GREEN}✅ PASSED: Call initiated successfully${NC}"
            passed=$((passed + 1))
        else
            echo -e "${RED}❌ FAILED: Expected success but got error${NC}"
            failed=$((failed + 1))
        fi
    else
        if echo "$response" | grep -q '"success":true'; then
            echo -e "${RED}❌ FAILED: Expected error but got success${NC}"
            failed=$((failed + 1))
        else
            echo -e "${GREEN}✅ PASSED: Correctly returned error${NC}"
            passed=$((passed + 1))
        fi
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
    
    # Small delay between tests
    sleep 1
}

# ========================================
# TEST 1: Missing agent_id (should fail)
# ========================================
echo -e "${YELLOW}=== SCENARIO: Missing agent_id ===${NC}"
run_test \
    "Missing agent_id field" \
    '{
        "customer_id": "test_customer_001",
        "organization_id": "test_org_001",
        "campaign_id": "test_campaign_001",
        "phone_number": "+917827470456",
        "from_number": "+15076269649",
        "customer_info": {
            "customer_name": "John Doe",
            "last_4_digits": "1234",
            "emi_amount": 2500,
            "emi_due_date": "2025-08-02"
        }
    }' \
    "fail" \
    "Should fail with validation error - agent_id is required"

# ========================================
# TEST 2: Empty agent_id (should fail)
# ========================================
echo -e "${YELLOW}=== SCENARIO: Empty agent_id ===${NC}"
run_test \
    "Empty agent_id string" \
    '{
        "agent_id": "",
        "customer_id": "test_customer_001",
        "organization_id": "test_org_001",
        "campaign_id": "test_campaign_001",
        "phone_number": "+917827470456",
        "from_number": "+15076269649",
        "customer_info": {
            "customer_name": "John Doe",
            "last_4_digits": "1234",
            "emi_amount": 2500,
            "emi_due_date": "2025-08-02"
        }
    }' \
    "fail" \
    "Should fail - empty string is not a valid agent_id"

# ========================================
# TEST 3: Invalid agent_id (should fail)
# ========================================
echo -e "${YELLOW}=== SCENARIO: Invalid agent_id ===${NC}"
run_test \
    "Unknown agent_id" \
    '{
        "agent_id": "UNKNOWN_AGENT_XYZ",
        "customer_id": "test_customer_001",
        "organization_id": "test_org_001",
        "campaign_id": "test_campaign_001",
        "phone_number": "+917827470456",
        "from_number": "+15076269649",
        "customer_info": {
            "customer_name": "John Doe",
            "last_4_digits": "1234",
            "emi_amount": 2500,
            "emi_due_date": "2025-08-02"
        }
    }' \
    "fail" \
    "Should fail with error listing available agents"

# ========================================
# TEST 4: Valid POST_BOUNCE_AGENT (should succeed)
# ========================================
echo -e "${GREEN}=== SCENARIO: Valid Agent - POST_BOUNCE_AGENT ===${NC}"
run_test \
    "POST_BOUNCE_AGENT - Sarah" \
    '{
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
    }' \
    "success" \
    "Should succeed - Sarah from XYZ Bank, collection agent"

# ========================================
# TEST 5: Valid PREDUE_AGENT (should succeed)
# ========================================
echo -e "${GREEN}=== SCENARIO: Valid Agent - PREDUE_AGENT ===${NC}"
run_test \
    "PREDUE_AGENT - Michael" \
    '{
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
    }' \
    "success" \
    "Should succeed - Michael from XYZ Bank, pre-due reminder"

# ========================================
# TEST 6: Case sensitivity check
# ========================================
echo -e "${YELLOW}=== SCENARIO: Case Sensitivity ===${NC}"
run_test \
    "Lowercase agent_id" \
    '{
        "agent_id": "post_bounce_agent",
        "customer_id": "test_customer_001",
        "organization_id": "test_org_001",
        "campaign_id": "test_campaign_001",
        "phone_number": "+917827470456",
        "from_number": "+15076269649",
        "customer_info": {
            "customer_name": "Test User",
            "last_4_digits": "9999",
            "emi_amount": 1500
        }
    }' \
    "fail" \
    "Should fail - agent_id is case sensitive"

# ========================================
# SUMMARY
# ========================================
echo ""
echo "================================================"
echo "              TEST SUMMARY"
echo "================================================"
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"
echo -e "Total:  $test_num"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
fi

echo ""
echo "================================================"
echo "         AVAILABLE AGENTS REFERENCE"
echo "================================================"
echo ""
echo "Current agents configured in the system:"
echo "1. POST_BOUNCE_AGENT - Sarah, post-bounce collection"
echo "   • Identity: Sarah from XYZ Bank"
echo "   • Strategy: 50% minimum payment, 2-day timeline"
echo "   • Tone: Professional, empathetic but firm"
echo ""
echo "2. PREDUE_AGENT - Michael, pre-due reminder"
echo "   • Identity: Michael from XYZ Bank"  
echo "   • Strategy: Payment scheduling, prevention"
echo "   • Tone: Friendly, proactive, helpful"
echo ""
echo "================================================"
echo ""

# Show example curl commands
echo "📝 EXAMPLE CURL COMMANDS:"
echo ""
echo "# Test with POST_BOUNCE_AGENT:"
cat << 'EOF'
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
      "emi_due_date": "2025-08-02"
    }
  }'
EOF

echo ""
echo "# Test with PREDUE_AGENT:"
cat << 'EOF'
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
EOF

echo ""
echo "================================================"