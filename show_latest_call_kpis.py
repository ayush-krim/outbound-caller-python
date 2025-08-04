#!/usr/bin/env python3
"""
Display KPIs from the latest call using SQLAlchemy
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

load_dotenv(".env.local")
console = Console()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_recent_call_kpis():
    """Fetch and display KPIs from the most recent call"""
    
    async with AsyncSessionLocal() as session:
        # Get the most recent call
        result = await session.execute(
            text("""
                SELECT c.*, 
                       cm.room_connection_duration_ms,
                       cm.agent_init_duration_ms,
                       cm.session_creation_duration_ms,
                       cm.sip_dial_duration_ms,
                       cm.dispatch_accepted_at,
                       cm.call_answered_at,
                       cm.participant_joined_at
                FROM calls c
                LEFT JOIN call_connection_metrics cm ON c.id = cm.call_id
                ORDER BY c.created_at DESC
                LIMIT 1
            """)
        )
        call = result.first()
        
        if not call:
            console.print("[red]No calls found in database[/red]")
            return
            
        # Display Call Overview
        console.print(Panel.fit(
            f"[bold blue]Call Analytics Report[/bold blue]\n"
            f"Dispatch ID: {call.dispatch_id}\n"
            f"Phone: {call.phone_number}\n"
            f"Room: {call.room_name}",
            box=box.ROUNDED
        ))
        
        # Connection KPIs
        conn_table = Table(title="📊 Connection KPIs", box=box.ROUNDED)
        conn_table.add_column("Metric", style="cyan")
        conn_table.add_column("Value", style="yellow")
        conn_table.add_column("Target", style="green")
        conn_table.add_column("Status", style="bold")
        
        # Calculate total setup time
        if call.dispatch_accepted_at and call.call_answered_at:
            total_setup = (call.call_answered_at - call.dispatch_accepted_at).total_seconds()
            setup_status = "✅ PASS" if total_setup < 5 else "❌ FAIL"
            conn_table.add_row("Total Setup Time", f"{total_setup:.2f}s", "< 5s", setup_status)
        
        # Individual connection metrics
        room_ms = call.room_connection_duration_ms or 0
        room_status = "✅" if room_ms < 500 else "⚠️"
        conn_table.add_row("Room Connection", f"{room_ms}ms", "< 500ms", room_status)
        
        agent_ms = call.agent_init_duration_ms or 0
        agent_status = "✅" if agent_ms < 200 else "⚠️"
        conn_table.add_row("Agent Init", f"{agent_ms}ms", "< 200ms", agent_status)
        
        session_ms = call.session_creation_duration_ms or 0
        session_status = "✅" if session_ms < 200 else "⚠️"
        conn_table.add_row("Session Creation", f"{session_ms}ms", "< 200ms", session_status)
        
        sip_ms = call.sip_dial_duration_ms or 0
        sip_status = "✅" if sip_ms < 5000 else "⚠️"
        conn_table.add_row("SIP Dial", f"{sip_ms/1000:.1f}s", "< 5s", sip_status)
        
        console.print(conn_table)
        
        # Get interaction metrics
        result = await session.execute(
            text("""
                SELECT * FROM call_interaction_metrics 
                WHERE call_id = :call_id
            """),
            {"call_id": call.id}
        )
        interaction = result.first()
        
        if interaction:
            # Interaction KPIs
            int_table = Table(title="💬 Interaction KPIs", box=box.ROUNDED)
            int_table.add_column("Metric", style="cyan")
            int_table.add_column("Value", style="yellow")
            int_table.add_column("Target", style="green")
            int_table.add_column("Status", style="bold")
            
            # Call duration
            duration = interaction.total_duration_seconds or 0
            int_table.add_row("Call Duration", f"{duration:.1f}s", "-", "📊")
            
            # Response times
            avg_response = interaction.avg_agent_response_time_ms or 0
            response_status = "✅" if avg_response < 800 else "⚠️"
            int_table.add_row("Avg Response Time", f"{avg_response:.0f}ms", "< 800ms", response_status)
            
            # Conversation metrics
            int_table.add_row("Agent Utterances", str(interaction.total_agent_utterances), "-", "📊")
            int_table.add_row("User Utterances", str(interaction.total_user_utterances), "-", "📊")
            
            console.print(int_table)
        
        # Get events
        result = await session.execute(
            text("""
                SELECT event_type, event_timestamp, event_details,
                       EXTRACT(EPOCH FROM (event_timestamp - :call_start)) * 1000 as time_from_start_ms
                FROM call_events 
                WHERE call_id = :call_id
                ORDER BY event_timestamp
            """),
            {"call_id": call.id, "call_start": call.created_at}
        )
        events = result.fetchall()
        
        if events:
            # Events Timeline
            events_table = Table(title="📌 Call Events Timeline", box=box.ROUNDED)
            events_table.add_column("Time", style="cyan")
            events_table.add_column("Event", style="yellow")
            events_table.add_column("Details", style="white")
            
            for event in events:
                time_str = f"+{event.time_from_start_ms/1000:.1f}s" if event.time_from_start_ms else "0s"
                details = str(event.event_details) if event.event_details else "-"
                events_table.add_row(time_str, event.event_type, details)
            
            console.print(events_table)
        
        # Get recording info
        result = await session.execute(
            text("""
                SELECT * FROM call_recordings 
                WHERE call_id = :call_id
            """),
            {"call_id": call.id}
        )
        recording = result.first()
        
        if recording:
            # Recording info
            rec_table = Table(title="🎙️ Call Recording", box=box.ROUNDED)
            rec_table.add_column("Field", style="cyan", width=20)
            rec_table.add_column("Value", style="white")
            
            # Status with color coding
            status_color = {
                "recording": "yellow",
                "completed": "green",
                "failed": "red"
            }.get(recording.status, "white")
            
            rec_table.add_row("Status", f"[{status_color}]{recording.status}[/{status_color}]")
            rec_table.add_row("Egress ID", recording.egress_id[:12] + "...")
            rec_table.add_row("Format", recording.format)
            
            if recording.file_path:
                rec_table.add_row("File Path", recording.file_path)
            
            if recording.duration_seconds:
                minutes = int(recording.duration_seconds // 60)
                seconds = int(recording.duration_seconds % 60)
                rec_table.add_row("Duration", f"{minutes}m {seconds}s")
            
            if recording.file_size:
                # Convert to human readable size
                size_mb = recording.file_size / (1024 * 1024)
                rec_table.add_row("File Size", f"{size_mb:.2f} MB")
            
            if recording.started_at:
                rec_table.add_row("Started At", recording.started_at.strftime("%H:%M:%S"))
            
            if recording.completed_at:
                rec_table.add_row("Completed At", recording.completed_at.strftime("%H:%M:%S"))
            
            console.print(rec_table)
        
        # Overall KPI Summary
        summary_table = Table(title="🎯 KPI Summary", box=box.ROUNDED)
        summary_table.add_column("KPI", style="cyan")
        summary_table.add_column("Target", style="green")
        summary_table.add_column("Actual", style="yellow")
        summary_table.add_column("Result", style="bold")
        
        # Connection KPIs
        if call.dispatch_accepted_at and call.call_answered_at:
            total_setup = (call.call_answered_at - call.dispatch_accepted_at).total_seconds()
            summary_table.add_row(
                "Connection Speed",
                "< 5 seconds",
                f"{total_setup:.2f} seconds",
                "✅ PASS" if total_setup < 5 else "❌ FAIL"
            )
        
        # Response time KPIs
        if interaction:
            if interaction.avg_agent_response_time_ms:
                summary_table.add_row(
                    "Average Response Time",
                    "< 800ms",
                    f"{interaction.avg_agent_response_time_ms:.0f}ms",
                    "✅ PASS" if interaction.avg_agent_response_time_ms < 800 else "❌ FAIL"
                )
        
        # Call outcome
        summary_table.add_row(
            "Call Status",
            "Completed",
            call.status or "In Progress",
            "✅" if call.status in ["completed", "transferred"] else "⏳"
        )
        
        console.print(summary_table)
        
        # Show SQL query to get raw data
        console.print("\n[dim]To see raw data, run:[/dim]")
        console.print(f"[dim]docker exec postgres-outbound psql -U postgres -d outbound_caller -c \"SELECT * FROM calls WHERE dispatch_id = '{call.dispatch_id}';\"[/dim]")


async def main():
    try:
        await get_recent_call_kpis()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())