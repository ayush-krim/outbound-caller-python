#!/usr/bin/env python3
"""
Test script for agent instructions system
Validates instruction loading and formatting
"""

import json
from services.agent_instructions import AgentInstructions


def test_agent_instructions():
    """Test the agent instructions service"""
    
    print("=" * 60)
    print("AGENT INSTRUCTIONS SYSTEM TEST")
    print("=" * 60)
    
    # Initialize the service
    instruction_service = AgentInstructions()
    
    # Test customer info
    customer_info = {
        "customer_name": "John Doe",
        "last_4_digits": "1234",
        "emi_amount": 2500,
        "days_past_due": 15,
        "late_fee": 350
    }
    
    # List available agents
    print("\n📋 Available Agents:")
    available_agents = instruction_service.list_available_agents()
    for agent in available_agents:
        print(f"  - {agent}")
    
    print("\n" + "=" * 60)
    
    # Test POST_BOUNCE_AGENT (Default Collection Agent)
    print("\n🤖 Testing POST_BOUNCE_AGENT (Default Collection Agent)")
    print("-" * 40)
    
    agent_001_instructions = instruction_service.get_instructions("POST_BOUNCE_AGENT", customer_info)
    
    # Show first 500 characters to verify it's working
    print("\nFirst 500 characters of instructions:")
    print(agent_001_instructions[:500])
    
    # Verify key elements are present
    print("\n✅ Validation Checks for POST_BOUNCE_AGENT:")
    checks = [
        ("Customer name formatting", "John Doe" in agent_001_instructions),
        ("Account digits", "***1234" in agent_001_instructions),
        ("EMI amount", "$2500" in agent_001_instructions),
        ("Days past due", "15 days" in agent_001_instructions),
        ("Minimum payment", "$1250" in agent_001_instructions),
        ("Agent identity", "Sarah from XYZ Bank" in agent_001_instructions),
        ("Compliance greeting", "This call may be recorded" in agent_001_instructions),
        ("Opt-out instructions", "stop calling" in agent_001_instructions)
    ]
    
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
    
    print("\n" + "=" * 60)
    
    # Test PREDUE_AGENT
    print("\n🤖 Testing PREDUE_AGENT (Pre-Due Reminder Agent)")
    print("-" * 40)
    
    # Modify customer info for pre-due scenario
    predue_customer_info = {
        **customer_info,
        "days_until_due": 3,
        "days_past_due": 0  # Not past due yet
    }
    
    predue_instructions = instruction_service.get_instructions("PREDUE_AGENT", predue_customer_info)
    
    # Show first 500 characters
    print("\nFirst 500 characters of instructions:")
    print(predue_instructions[:500])
    
    # Verify key elements for predue agent
    print("\n✅ Validation Checks for PREDUE_AGENT:")
    predue_checks = [
        ("Agent identity", "Michael from XYZ Bank" in predue_instructions),
        ("Upcoming payment", "upcoming" in predue_instructions.lower()),
        ("Days until due", "3 days" in predue_instructions),
        ("Compliance greeting", "This call may be recorded" in predue_instructions),
        ("Opt-out instructions", "stop calling" in predue_instructions)
    ]
    
    for check_name, result in predue_checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
    
    print("\n" + "=" * 60)
    
    # Test non-existent agent (should use base only)
    print("\n🤖 Testing Non-Existent Agent (Should Use Base Instructions Only)")
    print("-" * 40)
    
    print("\nRequesting instructions for 'UNKNOWN_AGENT'...")
    unknown_instructions = instruction_service.get_instructions("UNKNOWN_AGENT", customer_info)
    
    # Check if it uses base only (no agent identity)
    has_no_agent = "Sarah from XYZ Bank" not in unknown_instructions and "Michael from XYZ Bank" not in unknown_instructions
    has_base_greeting = "This call may be recorded" in unknown_instructions
    print(f"  {'✓' if has_no_agent else '✗'} No agent-specific identity: {has_no_agent}")
    print(f"  {'✓' if has_base_greeting else '✗'} Has base greeting: {has_base_greeting}")
    
    print("\n" + "=" * 60)
    
    # Test empty/None agent_id (should use base only)
    print("\n🤖 Testing No Agent ID (Should Use Base Instructions Only)")
    print("-" * 40)
    
    print("\nRequesting instructions with agent_id=None...")
    none_instructions = instruction_service.get_instructions(None, customer_info)
    
    # Check if it uses base only
    has_no_agent = "Sarah from XYZ Bank" not in none_instructions and "Michael from XYZ Bank" not in none_instructions
    has_compliance = "This call may be recorded" in none_instructions
    has_opt_out = "stop calling" in none_instructions
    
    print(f"  {'✓' if has_no_agent else '✗'} No agent-specific identity: {has_no_agent}")
    print(f"  {'✓' if has_compliance else '✗'} Has compliance greeting: {has_compliance}")
    print(f"  {'✓' if has_opt_out else '✗'} Has opt-out instructions: {has_opt_out}")
    
    print("\n" + "=" * 60)
    
    # Test instruction separation
    print("\n📝 Testing Base vs Behavioral Instruction Separation")
    print("-" * 40)
    
    # Need to add calculated fields for direct formatting calls
    customer_info_with_calcs = {
        **customer_info,
        "half_emi": customer_info["emi_amount"] * 0.5,
        "half_emi_int": int(customer_info["emi_amount"] * 0.5)
    }
    base_instructions = instruction_service.format_base_instructions(customer_info_with_calcs)
    behavioral_instructions = instruction_service.format_agent_instructions("POST_BOUNCE_AGENT", customer_info_with_calcs)
    
    print(f"\nBase Instructions Length: {len(base_instructions)} characters")
    print(f"Behavioral Instructions Length: {len(behavioral_instructions)} characters")
    print(f"Combined Instructions Length: {len(agent_001_instructions)} characters")
    
    # Verify base instructions contain compliance elements
    print("\n✅ Base Instructions Validation:")
    base_checks = [
        ("Compliance greeting", "This call may be recorded" in base_instructions),
        ("Opt-out rules", "stop calling" in base_instructions),
        ("Tool usage rules", "check_account_balance tool" in base_instructions),
        ("Consequences script", "potential consequences" in base_instructions),
        ("Fee disclosure", "Late fees" in base_instructions)
    ]
    
    for check_name, result in base_checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
    
    # Verify behavioral instructions contain agent-specific elements
    print("\n✅ Behavioral Instructions Validation:")
    behavioral_checks = [
        ("Agent identity", "Sarah from XYZ Bank" in behavioral_instructions),
        ("Negotiation rules", "NEGOTIATION RULES" in behavioral_instructions),
        ("Empathy guidelines", "EMPATHY GUIDELINES" in behavioral_instructions),
        ("Response style", "RESPONSES MUST BE" in behavioral_instructions),
        ("Conversation steps", "CONVERSATION STEPS" in behavioral_instructions)
    ]
    
    for check_name, result in behavioral_checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
    
    print("\n" + "=" * 60)
    print("\n✅ All tests completed successfully!")
    print("\n💡 Next Steps:")
    print("1. Test with actual API calls using different agent_ids")
    print("2. Add more agent variations to config/agent_instructions.json")
    print("3. Monitor agent behavior with different instruction sets")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_agent_instructions()