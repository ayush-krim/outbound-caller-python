#!/usr/bin/env python3
"""
Voice Agent Analytics Dashboard
Displays real-time and historical call analytics from the database
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncpg
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box
import argparse

# Load environment variables
load_dotenv(dotenv_path=".env.local")

console = Console()


class AnalyticsDashboard:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
    
    async def connect(self):
        """Connect to the database"""
        self.conn = await asyncpg.connect(self.database_url)
    
    async def disconnect(self):
        """Disconnect from the database"""
        if self.conn:
            await self.conn.close()
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall summary statistics"""
        query = """
        SELECT 
            COUNT(*) as total_calls,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_calls,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_calls,
            COUNT(CASE WHEN status = 'voicemail' THEN 1 END) as voicemail_calls,
            COUNT(CASE WHEN status = 'transferred' THEN 1 END) as transferred_calls,
            ROUND(COUNT(CASE WHEN status = 'completed' THEN 1 END)::FLOAT / 
                  NULLIF(COUNT(*), 0) * 100, 2) as success_rate
        FROM calls
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        """
        return await self.conn.fetchrow(query)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        query = """
        SELECT 
            ROUND(AVG(ccm.total_setup_time_ms) / 1000.0, 2) as avg_setup_seconds,
            ROUND(MIN(ccm.total_setup_time_ms) / 1000.0, 2) as min_setup_seconds,
            ROUND(MAX(ccm.total_setup_time_ms) / 1000.0, 2) as max_setup_seconds,
            ROUND(AVG(cim.total_duration_seconds), 2) as avg_call_duration,
            ROUND(AVG(cim.avg_agent_response_time_ms), 0) as avg_response_time_ms,
            ROUND(AVG(cim.time_to_first_agent_response_ms) / 1000.0, 2) as avg_time_to_first_response
        FROM calls c
        LEFT JOIN call_connection_metrics ccm ON c.id = ccm.call_id
        LEFT JOIN call_interaction_metrics cim ON c.id = cim.call_id
        WHERE c.created_at >= NOW() - INTERVAL '24 hours'
        """
        return await self.conn.fetchrow(query)
    
    async def get_recent_calls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent call details"""
        query = """
        SELECT 
            c.dispatch_id,
            c.phone_number,
            c.status,
            c.created_at,
            ccm.total_setup_time_ms / 1000.0 as setup_seconds,
            cim.total_duration_seconds as duration_seconds,
            cim.avg_agent_response_time_ms as response_time_ms
        FROM calls c
        LEFT JOIN call_connection_metrics ccm ON c.id = ccm.call_id
        LEFT JOIN call_interaction_metrics cim ON c.id = cim.call_id
        ORDER BY c.created_at DESC
        LIMIT $1
        """
        return await self.conn.fetch(query, limit)
    
    async def get_hourly_stats(self) -> List[Dict[str, Any]]:
        """Get hourly statistics for the last 24 hours"""
        query = """
        SELECT 
            DATE_TRUNC('hour', created_at) as hour,
            COUNT(*) as total_calls,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_calls,
            ROUND(AVG(CASE WHEN ccm.total_setup_time_ms IS NOT NULL 
                      THEN ccm.total_setup_time_ms / 1000.0 END), 2) as avg_setup_seconds
        FROM calls c
        LEFT JOIN call_connection_metrics ccm ON c.id = ccm.call_id
        WHERE c.created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC
        """
        return await self.conn.fetch(query)
    
    def create_summary_table(self, stats: Dict[str, Any]) -> Table:
        """Create summary statistics table"""
        table = Table(title="24-Hour Call Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Calls", str(stats['total_calls']))
        table.add_row("Completed", f"{stats['completed_calls']} ({stats['success_rate']}%)")
        table.add_row("Failed", str(stats['failed_calls']))
        table.add_row("Voicemail", str(stats['voicemail_calls']))
        table.add_row("Transferred", str(stats['transferred_calls']))
        
        return table
    
    def create_performance_table(self, metrics: Dict[str, Any]) -> Table:
        """Create performance metrics table"""
        table = Table(title="Performance Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Target", style="green")
        
        # Setup time
        setup_color = "green" if metrics['avg_setup_seconds'] and metrics['avg_setup_seconds'] < 5 else "red"
        table.add_row(
            "Avg Setup Time",
            f"[{setup_color}]{metrics['avg_setup_seconds']}s[/{setup_color}]",
            "< 5s"
        )
        
        # Response time
        response_color = "green" if metrics['avg_response_time_ms'] and metrics['avg_response_time_ms'] < 800 else "red"
        table.add_row(
            "Avg Response Time",
            f"[{response_color}]{metrics['avg_response_time_ms']}ms[/{response_color}]",
            "< 800ms"
        )
        
        # Time to first response
        first_response_color = "green" if metrics['avg_time_to_first_response'] and metrics['avg_time_to_first_response'] < 1 else "red"
        table.add_row(
            "Time to First Response",
            f"[{first_response_color}]{metrics['avg_time_to_first_response']}s[/{first_response_color}]",
            "< 1s"
        )
        
        table.add_row("Avg Call Duration", f"{metrics['avg_call_duration']}s", "-")
        
        return table
    
    def create_recent_calls_table(self, calls: List[Dict[str, Any]]) -> Table:
        """Create recent calls table"""
        table = Table(title="Recent Calls", box=box.ROUNDED)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Phone", style="white")
        table.add_column("Status", style="white")
        table.add_column("Setup", style="yellow")
        table.add_column("Duration", style="yellow")
        table.add_column("Response", style="yellow")
        
        for call in calls:
            status_color = {
                'completed': 'green',
                'failed': 'red',
                'voicemail': 'yellow',
                'transferred': 'blue'
            }.get(call['status'], 'white')
            
            table.add_row(
                call['created_at'].strftime("%H:%M:%S"),
                call['phone_number'][-4:],  # Last 4 digits
                f"[{status_color}]{call['status']}[/{status_color}]",
                f"{call['setup_seconds']:.1f}s" if call['setup_seconds'] else "-",
                f"{call['duration_seconds']:.0f}s" if call['duration_seconds'] else "-",
                f"{call['response_time_ms']:.0f}ms" if call['response_time_ms'] else "-"
            )
        
        return table
    
    async def display_dashboard(self, refresh_interval: int = 5):
        """Display the live dashboard"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        with Live(layout, refresh_per_second=1, screen=True) as live:
            while True:
                try:
                    # Fetch data
                    stats = await self.get_summary_stats()
                    metrics = await self.get_performance_metrics()
                    recent_calls = await self.get_recent_calls()
                    
                    # Update header
                    layout["header"].update(
                        Panel(
                            f"[bold blue]Voice Agent Analytics Dashboard[/bold blue]\n"
                            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            box=box.ROUNDED
                        )
                    )
                    
                    # Update left panel
                    layout["left"].split_column(
                        Layout(self.create_summary_table(dict(stats))),
                        Layout(self.create_performance_table(dict(metrics)))
                    )
                    
                    # Update right panel
                    layout["right"].update(self.create_recent_calls_table(recent_calls))
                    
                    # Update footer
                    layout["footer"].update(
                        Panel(
                            "[dim]Press Ctrl+C to exit | Refreshing every 5 seconds[/dim]",
                            box=box.ROUNDED
                        )
                    )
                    
                    await asyncio.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(refresh_interval)


async def main():
    parser = argparse.ArgumentParser(description="Voice Agent Analytics Dashboard")
    parser.add_argument(
        "--mode", 
        choices=["live", "summary"], 
        default="live",
        help="Dashboard mode: live (real-time updates) or summary (one-time report)"
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=5,
        help="Refresh interval in seconds for live mode"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        console.print("[red]Error: DATABASE_URL not found in environment[/red]")
        return
    
    # Create dashboard
    dashboard = AnalyticsDashboard(database_url)
    
    try:
        await dashboard.connect()
        console.print("[green]Connected to database[/green]")
        
        if args.mode == "live":
            await dashboard.display_dashboard(args.refresh)
        else:
            # One-time summary
            stats = await dashboard.get_summary_stats()
            metrics = await dashboard.get_performance_metrics()
            recent_calls = await dashboard.get_recent_calls(5)
            
            console.print(dashboard.create_summary_table(dict(stats)))
            console.print()
            console.print(dashboard.create_performance_table(dict(metrics)))
            console.print()
            console.print(dashboard.create_recent_calls_table(recent_calls))
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        await dashboard.disconnect()


if __name__ == "__main__":
    asyncio.run(main())