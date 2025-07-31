#!/usr/bin/env python3
"""
Demo script showing how call tracking works WITHOUT database
Shows what data would be stored during a real call
"""

import asyncio
from datetime import datetime, timezone
import json
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
import time

console = Console()


class MockCallTracker:
    """Mock tracker that shows what would be stored"""
    
    def __init__(self, dispatch_id, room_name, phone_number, transfer_to=None):
        self.dispatch_id = dispatch_id
        self.room_name = room_name  
        self.phone_number = phone_number
        self.transfer_to = transfer_to
        
        # Storage simulation
        self.timestamps = {}
        self.events = []
        self.metrics = {
            "utterances": {"agent": 0, "user": 0},
            "response_times": []
        }
        
        console.print(f"\n[cyan]📞 Call Tracker Created[/cyan]")
        console.print(f"   Dispatch: {dispatch_id}")
        console.print(f"   Phone: {phone_number}")
        console.print(f"   Room: {room_name}\n")
    
    def record_timestamp(self, event_name):
        """Record a timestamp"""
        timestamp = datetime.now(timezone.utc)
        self.timestamps[event_name] = timestamp
        console.print(f"⏱️  [yellow]{event_name}[/yellow] at {timestamp.strftime('%H:%M:%S.%f')[:-3]}")
    
    async def record_event(self, event_type, details=None):
        """Record an event"""
        timestamp = datetime.now(timezone.utc)
        self.events.append({
            "type": event_type,
            "timestamp": timestamp,
            "details": details
        })
        console.print(f"📌 [blue]Event:[/blue] {event_type} {details or ''}")
    
    def track_utterance(self, speaker):
        """Track utterances"""
        self.metrics["utterances"][speaker] += 1
    
    def track_response_time(self, ms):
        """Track response time"""
        self.metrics["response_times"].append(ms)


async def simulate_call_flow():
    """Simulate a complete call flow"""
    
    console.print(Panel.fit(
        "[bold blue]Voice Agent Call Tracking Demo[/bold blue]\n"
        "This shows what data gets tracked during a real call",
        box=box.ROUNDED
    ))
    
    # Phase 1: Call Setup
    console.print("\n[bold magenta]Phase 1: Call Dispatch & Setup[/bold magenta]")
    
    tracker = MockCallTracker(
        dispatch_id="AD_Demo123456",
        room_name="room-demo-xyz",
        phone_number="+917827470456",
        transfer_to="+1 507 626 9649"
    )
    
    # Simulate connection phases
    setup_phases = [
        ("dispatch_accepted", "Agent picks up the job", 50),
        ("room_connection_start", "Connecting to LiveKit room", 100),
        ("room_connection_completed", "Connected to room ✓", 234),
        ("agent_init_start", "Initializing AI agent", 50),
        ("agent_init_completed", "Agent ready ✓", 125),
        ("session_creation_start", "Creating AI session", 50),
        ("session_creation_completed", "Session ready ✓", 89),
        ("sip_dial_start", "Dialing phone number...", 100),
        ("sip_dial_completed", "Phone answered! ✓", 3456),
        ("participant_joined", "User joined room", 100),
    ]
    
    total_setup_time = 0
    for phase, description, delay_ms in setup_phases:
        console.print(f"\n→ {description}")
        await asyncio.sleep(delay_ms / 1000)
        tracker.record_timestamp(phase)
        total_setup_time += delay_ms
    
    console.print(f"\n[green]✅ Total setup time: {total_setup_time/1000:.2f} seconds[/green]")
    
    # Phase 2: Call Conversation
    console.print("\n[bold magenta]Phase 2: Call Conversation[/bold magenta]\n")
    
    tracker.record_timestamp("call_start")
    await tracker.record_event("call_started", {"setup_time_ms": total_setup_time})
    
    # Simulate conversation
    conversation = [
        ("user", "Hello?", None),
        ("agent", "Hello! This is your dental office calling about your appointment next Tuesday at 3pm.", 650),
        ("user", "Oh yes, I remember that appointment.", 1200),
        ("agent", "Great! I'm calling to confirm if you'll be able to make it?", 450),
        ("user", "Actually, can I reschedule? Something came up.", 2100),
        ("agent", "Of course! Let me check our availability. When would work better for you?", 380),
        ("user", "How about Thursday afternoon?", 1800),
        ("agent", "Let me check... We have openings at 2pm and 4pm on Thursday.", 520),
        ("user", "4pm works perfectly.", 1500),
        ("agent", "Excellent! I've rescheduled your appointment to Thursday at 4pm.", 420),
        ("user", "Thank you! Oh, can I speak to someone about insurance?", 2200),
        ("agent", "Certainly! I'll transfer you to our billing department right away.", 350),
    ]
    
    for speaker, text, response_time_ms in conversation:
        console.print(f"\n💬 [{'green' if speaker == 'agent' else 'cyan'}]{speaker.upper()}:[/] {text}")
        
        tracker.track_utterance(speaker)
        
        if response_time_ms:
            tracker.track_response_time(response_time_ms)
            await asyncio.sleep(response_time_ms / 1000)
        else:
            await asyncio.sleep(0.5)
        
        # First utterance timestamps
        if speaker == "user" and "user_first_speech" not in tracker.timestamps:
            tracker.record_timestamp("user_first_speech")
        elif speaker == "agent" and "agent_first_speech" not in tracker.timestamps:
            tracker.record_timestamp("agent_first_speech")
    
    # Transfer event
    await tracker.record_event("transfer_requested", {"reason": "billing_inquiry"})
    await asyncio.sleep(1)
    await tracker.record_event("transfer_completed", {"transfer_to": "+1 507 626 9649"})
    
    tracker.record_timestamp("call_end")
    
    # Phase 3: Show what would be stored
    console.print("\n[bold magenta]Phase 3: Data Storage Summary[/bold magenta]\n")
    
    # Connection Metrics Table
    conn_table = Table(title="📊 Connection Metrics (Stored in DB)", box=box.ROUNDED)
    conn_table.add_column("Metric", style="cyan")
    conn_table.add_column("Value", style="yellow")
    conn_table.add_column("Target", style="green")
    
    # Calculate durations
    room_conn_ms = (tracker.timestamps["room_connection_completed"] - tracker.timestamps["room_connection_start"]).total_seconds() * 1000
    agent_init_ms = (tracker.timestamps["agent_init_completed"] - tracker.timestamps["agent_init_start"]).total_seconds() * 1000
    session_ms = (tracker.timestamps["session_creation_completed"] - tracker.timestamps["session_creation_start"]).total_seconds() * 1000
    sip_dial_ms = (tracker.timestamps["sip_dial_completed"] - tracker.timestamps["sip_dial_start"]).total_seconds() * 1000
    
    conn_table.add_row("Room Connection", f"{room_conn_ms:.0f}ms", "< 500ms")
    conn_table.add_row("Agent Init", f"{agent_init_ms:.0f}ms", "< 200ms")  
    conn_table.add_row("Session Creation", f"{session_ms:.0f}ms", "< 200ms")
    conn_table.add_row("SIP Dial", f"{sip_dial_ms/1000:.1f}s", "< 5s")
    conn_table.add_row("Total Setup", f"{total_setup_time/1000:.1f}s", "< 5s ✓")
    
    console.print(conn_table)
    
    # Interaction Metrics Table
    interaction_table = Table(title="💬 Interaction Metrics (Stored in DB)", box=box.ROUNDED)
    interaction_table.add_column("Metric", style="cyan")
    interaction_table.add_column("Value", style="yellow")
    
    call_duration = (tracker.timestamps["call_end"] - tracker.timestamps["call_start"]).total_seconds()
    avg_response = sum(tracker.metrics["response_times"]) / len(tracker.metrics["response_times"])
    time_to_first = (tracker.timestamps["agent_first_speech"] - tracker.timestamps["call_start"]).total_seconds() * 1000
    
    interaction_table.add_row("Call Duration", f"{call_duration:.1f}s")
    interaction_table.add_row("Agent Utterances", str(tracker.metrics["utterances"]["agent"]))
    interaction_table.add_row("User Utterances", str(tracker.metrics["utterances"]["user"]))
    interaction_table.add_row("Avg Response Time", f"{avg_response:.0f}ms")
    interaction_table.add_row("Time to First Response", f"{time_to_first:.0f}ms")
    
    console.print(interaction_table)
    
    # Events Table
    events_table = Table(title="📌 Call Events (Stored in DB)", box=box.ROUNDED)
    events_table.add_column("Event", style="cyan")
    events_table.add_column("Details", style="yellow")
    
    for event in tracker.events:
        events_table.add_row(
            event["type"],
            json.dumps(event["details"]) if event["details"] else "-"
        )
    
    console.print(events_table)
    
    # SQL Preview
    console.print("\n[bold]🗄️  SQL that would be executed:[/bold]")
    console.print(Panel(f"""
-- Insert call record
INSERT INTO calls (dispatch_id, room_name, phone_number, status, transfer_to_number)
VALUES ('{tracker.dispatch_id}', '{tracker.room_name}', '{tracker.phone_number}', 'transferred', '{tracker.transfer_to}');

-- Insert connection metrics  
INSERT INTO call_connection_metrics (call_id, total_setup_time_ms, room_connection_duration_ms, ...)
VALUES ('...', {total_setup_time}, {room_conn_ms:.0f}, ...);

-- Insert interaction metrics
INSERT INTO call_interaction_metrics (call_id, total_duration_seconds, total_agent_utterances, ...)  
VALUES ('...', {call_duration:.1f}, {tracker.metrics["utterances"]["agent"]}, ...);

-- Insert events
INSERT INTO call_events (call_id, event_type, event_timestamp, event_details)
VALUES ('...', 'transfer_requested', '...', '{{"reason": "billing_inquiry"}}');
    """, box=box.ROUNDED))


async def main():
    """Run the demo"""
    try:
        await simulate_call_flow()
        
        console.print("\n[bold green]✅ Demo Complete![/bold green]")
        console.print("\nIn a real call, all this data is automatically stored in PostgreSQL")
        console.print("for analytics, performance monitoring, and optimization.\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())