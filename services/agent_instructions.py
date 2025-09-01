"""
Agent Instructions Service
Loads and formats agent instructions from JSON configuration
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class AgentInstructions:
    """Service for managing agent-specific instructions"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the service with configuration file
        
        Args:
            config_path: Path to JSON configuration file
        """
        if config_path is None:
            # Default to config/agent_instructions.json relative to project root
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "agent_instructions.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load JSON configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def format_base_instructions(self, customer_info: Dict[str, Any], skip_greeting: bool = False) -> str:
        """
        Format base compliance instructions with customer information
        
        Args:
            customer_info: Dictionary containing customer details
        
        Returns:
            Formatted base instructions string
        """
        base = self.config.get("base_instructions", {})
        
        # Build the base instructions string
        instructions_parts = []
        
        # Initial greeting (generic for base) - skip if agent will provide its own
        if "greeting" in base and not skip_greeting:
            greeting = base["greeting"].format(**customer_info)
            instructions_parts.append(f"INITIAL GREETING (MUST BE SAID FIRST WHEN CALL CONNECTS):\n\"{greeting}\"\n")
        
        # Critical rules
        if "critical" in base:
            instructions_parts.append(f"CRITICAL: {base['critical']}\n")
        
        # Customer info
        if "customer_info" in base:
            customer_info_str = base["customer_info"].format(**customer_info)
            instructions_parts.append(f"\n{customer_info_str}\n")
        
        # Opt-out compliance
        if "opt_out_compliance" in base:
            opt_out = base["opt_out_compliance"]
            instructions_parts.append("\nOPT-OUT COMPLIANCE:")
            instructions_parts.append(f"- {opt_out['rule']}")
            instructions_parts.append(f"- {opt_out['action']}\n")
        
        # Tool usage rules
        if "tool_usage" in base:
            tools = base["tool_usage"]
            instructions_parts.append("\nTOOL USAGE RULES:")
            for key, value in tools.items():
                instructions_parts.append(f"- {value}")
            instructions_parts.append("")
        
        # Account info responses
        if "account_info_responses" in base:
            account_info = base["account_info_responses"]
            instructions_parts.append("\nACCOUNT INFO RESPONSES:")
            for rule in account_info.get("rules", []):
                instructions_parts.append(f"- {rule}")
            
            if "examples" in account_info:
                instructions_parts.append("- Examples:")
                for example_key, example_value in account_info["examples"].items():
                    instructions_parts.append(f"  {example_value}")
            instructions_parts.append("")
        
        # General rules
        if "general_rules" in base:
            instructions_parts.append(f"\n{base['general_rules']}\n")
        
        # Consequences response
        if "consequences_response" in base:
            consequences = base["consequences_response"]
            instructions_parts.append("\nCONSEQUENCES RESPONSE - When Customer Asks: \"What happens if I don't pay?\"\n")
            
            # Stage 1
            if "stage1" in consequences:
                stage1 = consequences["stage1"]
                instructions_parts.append("STAGE 1 - BRIEF INITIAL RESPONSE (Use this FIRST):")
                response = stage1["response"].format(**customer_info)
                instructions_parts.append(f"{response}\n")
            
            # Stage 2
            if "stage2" in consequences:
                stage2 = consequences["stage2"]
                instructions_parts.append(f"STAGE 2 - DETAILED RESPONSE ({stage2['condition']}):")
                instructions_parts.append("If customer says yes or wants more information, then provide:\n")
                response = stage2["response"].format(**customer_info)
                instructions_parts.append(f"{response}\n")
            
            if "important" in consequences:
                instructions_parts.append(f"IMPORTANT: {consequences['important']}\n")
        
        # Compliance script for fees
        if "compliance_script_fees" in base:
            fees = base["compliance_script_fees"]
            instructions_parts.append("\nCOMPLIANCE SCRIPT - When Customer Asks About Penalties/Late Fees:\n")
            
            for step_key in ["step1", "step2", "step3", "step4", "step5"]:
                if step_key in fees:
                    step = fees[step_key]
                    step_num = step_key.replace("step", "Step ")
                    
                    if "action" in step:
                        instructions_parts.append(f"{step_num}: {step['action']}")
                    elif "title" in step:
                        instructions_parts.append(f"{step_num}: {step['title']}")
                    elif "condition" in step:
                        instructions_parts.append(f"{step_num}: {step['condition']}")
                    
                    if "response" in step:
                        instructions_parts.append(f"\"{step['response']}\"\n")
        
        # Important rules
        if "important_rules" in base:
            instructions_parts.append("\nIMPORTANT RULES:")
            for rule in base["important_rules"]:
                instructions_parts.append(f"- {rule}")
            instructions_parts.append("")
        
        return "\n".join(instructions_parts)
    
    def format_agent_instructions(self, agent_id: str, customer_info: Dict[str, Any]) -> str:
        """
        Format agent-specific behavioral instructions
        
        Args:
            agent_id: The agent identifier
            customer_info: Dictionary containing customer details
        
        Returns:
            Formatted agent instructions string
        """
        agents = self.config.get("agents", {})
        
        # Return empty string if agent not found
        if agent_id not in agents:
            return ""  # No behavioral instructions for unknown agents
        
        agent = agents.get(agent_id, {})
        instructions_parts = []
        
        # Identity
        if "identity" in agent:
            instructions_parts.append(agent["identity"])
            instructions_parts.append("")
        
        # Agent-specific greeting (overrides base greeting)
        if "greeting" in agent:
            greeting = agent["greeting"].format(**customer_info)
            instructions_parts.append(f"INITIAL GREETING (MUST BE SAID FIRST WHEN CALL CONNECTS):\n\"{greeting}\"\n")
        
        # Minimum payment
        if "minimum_payment" in agent:
            min_payment = agent["minimum_payment"].format(**customer_info)
            instructions_parts.append(min_payment)
            instructions_parts.append("")
        
        # Conversation steps
        if "conversation_steps" in agent:
            instructions_parts.append("CONVERSATION STEPS:")
            for i, step in enumerate(agent["conversation_steps"], 1):
                formatted_step = step.format(**customer_info)
                instructions_parts.append(f"{i}. {formatted_step}")
            instructions_parts.append("")
        
        # Negotiation rules
        if "negotiation_rules" in agent:
            negotiation = agent["negotiation_rules"]
            instructions_parts.append("NEGOTIATION RULES:")
            
            # First response
            if "first_response" in negotiation:
                first = negotiation["first_response"]
                instructions_parts.append(f"- FIRST RESPONSE ({first.get('note', '')}): ")
                
                for key, value in first.items():
                    if key != "note":
                        formatted_value = value.format(**customer_info)
                        instructions_parts.append(f"  * If {key.replace('_', ' ')}: \"{formatted_value}\"")
            
            # Subsequent responses
            if "subsequent_responses" in negotiation:
                subsequent = negotiation["subsequent_responses"]
                instructions_parts.append(f"- SUBSEQUENT RESPONSES ({subsequent.get('note', '')}):")
                
                for key, value in subsequent.items():
                    if key != "note":
                        formatted_value = value.format(**customer_info)
                        instructions_parts.append(f"  * If {key.replace('_', ' ')}: \"{formatted_value}\"")
            
            instructions_parts.append("")
        
        # Response style
        if "response_style" in agent:
            instructions_parts.append("RESPONSES MUST BE:")
            for style in agent["response_style"]:
                instructions_parts.append(f"- {style}")
            instructions_parts.append("")
        
        # Empathy guidelines
        if "empathy_guidelines" in agent:
            instructions_parts.append("EMPATHY GUIDELINES:")
            for guideline in agent["empathy_guidelines"]:
                instructions_parts.append(f"- {guideline}")
            instructions_parts.append("")
        
        return "\n".join(instructions_parts)
    
    def get_instructions(self, agent_id: str, customer_info: Dict[str, Any]) -> str:
        """
        Get complete formatted instructions for an agent
        
        Args:
            agent_id: The agent identifier
            customer_info: Dictionary containing customer details including:
                - customer_name: Customer's full name
                - last_4_digits: Last 4 digits of account
                - emi_amount: EMI amount due
                - days_past_due: Number of days past due
                - late_fee: Late fee amount (optional)
                - days_until_due: Days until payment due (for predue agents)
        
        Returns:
            Complete formatted instructions string combining base + agent instructions
        """
        # Ensure all required fields have defaults
        customer_info_with_defaults = {
            "customer_name": "Customer",
            "last_4_digits": "0000",
            "emi_amount": 0,
            "days_past_due": 0,
            "late_fee": 0,
            "days_until_due": 0,
            **customer_info  # Override defaults with provided values
        }
        
        # Calculate derived values - use safe key names for formatting
        half_emi = customer_info_with_defaults["emi_amount"] * 0.5
        customer_info_with_defaults["half_emi"] = half_emi
        customer_info_with_defaults["half_emi_int"] = int(half_emi)
        
        # Check if agent exists and has its own greeting
        skip_base_greeting = False
        if agent_id and agent_id.strip():
            agents = self.config.get("agents", {})
            if agent_id in agents and "greeting" in agents[agent_id]:
                skip_base_greeting = True
        
        # Get base instructions (always included)
        base_instructions = self.format_base_instructions(customer_info_with_defaults, skip_greeting=skip_base_greeting)
        
        # Get agent instructions if agent_id provided and exists
        if agent_id and agent_id.strip():  # Check if agent_id is provided and not empty
            agent_instructions = self.format_agent_instructions(agent_id, customer_info_with_defaults)
            if agent_instructions:  # Only combine if agent instructions exist
                return f"{base_instructions}\n{agent_instructions}"
        
        # Return only base instructions if no agent or unknown agent
        return base_instructions
    
    def list_available_agents(self) -> list:
        """
        Get list of available agent IDs
        
        Returns:
            List of agent IDs configured in the system
        """
        return list(self.config.get("agents", {}).keys())