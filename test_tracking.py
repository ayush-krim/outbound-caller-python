#!/usr/bin/env python3
"""
Test script to demonstrate how call tracking works
Simulates a call and shows what gets stored in the database
"""

import asyncio
import os
from datetime import datetime, timezone
from database.tracker import CallTracker
from database.config import async_session, init_db
from rich.console import Console
from rich.table import Table
from rich import box
import uuid

console = Console()


async def simulate_call():
    """Simulate a complete call flow and show what gets tracked"""
    
    console.print("[bold blue]Call Tracking Simulation[/bold blue]\n")
    
    # Initialize database
    await init_db()
    
    # Create a test call tracker
    dispatch_id = f"TEST_{uuid.uuid4().hex[:8]}"
    room_name = f"test-room-{uuid.uuid4().hex[:8]}"
    phone_number = "+1234567890"
    
    console.print(f"[cyan]Creating call tracker:[/cyan]")
    console.print(f"  Dispatch ID: {dispatch_id}")
    console.print(f"  Room: {room_name}")
    console.print(f"  Phone: {phone_number}\n")
    
    tracker = CallTracker(
        dispatch_id=dispatch_id,
        room_name=room_name,
        phone_number=phone_number,
        transfer_to="+1 507 626 9649",
        agent_name="test-agent"
    )
    
    # Initialize (creates database records)
    await tracker.initialize()
    console.print("[green]✓ Call record created in database[/green]\n")
    
    # Simulate connection phases with realistic timing
    phases = [
        ("dispatch_accepted", 50),
        ("room_connection_start", 100),
        ("room_connection_completed", 234),
        ("agent_init_start", 50),
        ("agent_init_completed", 125),
        ("session_creation_start", 50),
        ("session_creation_completed", 89),
        ("sip_dial_start", 100),
        ("sip_dial_completed", 3456),
        ("call_answered", 50),
        ("participant_joined", 100),
    ]
    
    console.print("[cyan]Simulating connection phases:[/cyan]")
    for phase, delay_ms in phases:
        await asyncio.sleep(delay_ms / 1000)  # Convert to seconds
        tracker.record_timestamp(phase)
        console.print(f"  ✓ {phase}")
    
    # Mark call start
    tracker.record_timestamp("call_start")
    console.print("\n[green]Call connected and started[/green]\n")
    
    # Simulate some call events
    console.print("[cyan]Simulating call events:[/cyan]")
    
    # User speaks first
    await asyncio.sleep(0.5)
    tracker.record_timestamp("user_first_speech")
    console.print("  ✓ User: 'Hello?'")
    
    # Agent responds
    await asyncio.sleep(0.65)  # 650ms response time
    tracker.record_timestamp("agent_first_speech")
    tracker.track_response_time(650)
    tracker.track_utterance("agent")
    console.print("  ✓ Agent: 'Hello, this is your dental office...'")
    
    # Simulate conversation
    for i in range(5):
        await asyncio.sleep(0.2)
        tracker.track_utterance("user")
        await asyncio.sleep(0.3)
        tracker.track_utterance("agent")
        tracker.track_response_time(300 + i * 50)  # Varying response times
    
    console.print("  ✓ Conversation continues...")
    
    # Record a transfer request
    await tracker.record_event("transfer_requested", {"reason": "user_request"})
    console.print("  ✓ Transfer requested")
    
    # End call
    await asyncio.sleep(0.5)
    tracker.record_timestamp("call_end")
    
    # Update metrics
    console.print("\n[cyan]Finalizing call metrics...[/cyan]")
    await tracker.update_connection_metrics()
    await tracker.update_interaction_metrics()
    await tracker.finalize(status="transferred", end_reason="transfer_completed")
    
    console.print("[green]✓ All metrics saved to database[/green]\n")
    
    # Now query and display what was stored
    await display_stored_data(tracker.call_id)


async def display_stored_data(call_id):
    """Query and display what was stored in the database"""
    
    async with async_session() as session:
        # Get call record
        result = await session.execute(
            f"SELECT * FROM calls WHERE id = '{call_id}'"
        )
        call_record = result.first()
        
        # Display call summary
        table = Table(title="Stored Call Record", box=box.ROUNDED)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Call ID", str(call_record.id))
        table.add_row("Dispatch ID", call_record.dispatch_id)
        table.add_row("Phone Number", call_record.phone_number)
        table.add_row("Status", call_record.status)
        table.add_row("End Reason", call_record.end_reason)
        
        console.print(table)
        
        # Get connection metrics
        result = await session.execute(
            f"SELECT * FROM call_connection_metrics WHERE call_id = '{call_id}'"
        )
        conn_metrics = result.first()
        
        # Display connection metrics
        table = Table(title="Connection Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Duration (ms)", style="yellow")
        
        table.add_row("Room Connection", str(conn_metrics.room_connection_duration_ms))
        table.add_row("Agent Init", str(conn_metrics.agent_init_duration_ms))
        table.add_row("Session Creation", str(conn_metrics.session_creation_duration_ms))
        table.add_row("SIP Dial", str(conn_metrics.sip_dial_duration_ms))
        table.add_row("Total Setup Time", str(conn_metrics.total_setup_time_ms))
        
        console.print(table)
        
        # Get interaction metrics
        result = await session.execute(
            f"SELECT * FROM call_interaction_metrics WHERE call_id = '{call_id}'"
        )
        interaction = result.first()
        
        if interaction:
            table = Table(title="Interaction Metrics", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Duration", f"{interaction.total_duration_seconds:.1f}s")
            table.add_row("Agent Utterances", str(interaction.total_agent_utterances))
            table.add_row("User Utterances", str(interaction.total_user_utterances))
            table.add_row("Avg Response Time", f"{interaction.avg_agent_response_time_ms:.0f}ms")
            table.add_row("Time to First Response", f"{interaction.time_to_first_agent_response_ms}ms")
            
            console.print(table)
        
        # Get events
        result = await session.execute(
            f"SELECT * FROM call_events WHERE call_id = '{call_id}' ORDER BY event_timestamp"
        )
        events = result.fetchall()
        
        if events:
            table = Table(title="Call Events", box=box.ROUNDED)
            table.add_column("Event", style="cyan")
            table.add_column("Time from Start (ms)", style="yellow")
            table.add_column("Details", style="white")
            
            for event in events:
                table.add_row(
                    event.event_type,
                    str(event.duration_from_call_start_ms),
                    str(event.event_details)
                )
            
            console.print(table)


async def main():
    """Run the simulation"""
    try:
        await simulate_call()
        
        console.print("\n[bold green]Simulation complete![/bold green]")
        console.print("\nThis demonstrates how the tracking system stores:")
        console.print("  • Connection timing for each phase")
        console.print("  • Call events with timestamps")
        console.print("  • Interaction metrics (utterances, response times)")
        console.print("  • Final call status and outcome")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env.local")
    
    asyncio.run(main())