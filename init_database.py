#!/usr/bin/env python3
"""
Database Initialization Script
Sets up the PostgreSQL database for voice agent analytics
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import psycopg
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv(dotenv_path=".env.local")

console = Console()


class DatabaseInitializer:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/outbound_calls")
        self.parse_database_url()
        
    def parse_database_url(self):
        """Parse database URL into components"""
        # Simple parsing - could use urllib.parse for more robust parsing
        url = self.database_url.replace("postgresql://", "")
        
        # Handle different URL formats
        if "@" in url:
            auth, host_db = url.split("@", 1)
            if ":" in auth:
                self.user, self.password = auth.split(":", 1)
            else:
                self.user = auth
                self.password = None
        else:
            host_db = url
            self.user = "postgres"
            self.password = None
            
        if "/" in host_db:
            host_port, self.database = host_db.split("/", 1)
        else:
            host_port = host_db
            self.database = "outbound_calls"
            
        if ":" in host_port:
            self.host, self.port = host_port.split(":", 1)
            self.port = int(self.port)
        else:
            self.host = host_port
            self.port = 5432
    
    def check_postgres_running(self) -> bool:
        """Check if PostgreSQL is running"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database="postgres"  # Connect to default database
            )
            conn.close()
            return True
        except:
            return False
    
    def create_database(self):
        """Create the database if it doesn't exist"""
        try:
            # Connect to PostgreSQL server
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database="postgres"  # Connect to default database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database,)
            )
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(f'CREATE DATABASE "{self.database}"')
                console.print(f"[green]✓ Created database: {self.database}[/green]")
            else:
                console.print(f"[yellow]Database '{self.database}' already exists[/yellow]")
                
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating database: {e}[/red]")
            return False
    
    async def run_migrations(self):
        """Run Alembic migrations"""
        try:
            # Check if alembic is available
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Database migrations completed[/green]")
                return True
            else:
                console.print(f"[yellow]Migration output: {result.stdout}[/yellow]")
                if result.stderr:
                    console.print(f"[red]Migration errors: {result.stderr}[/red]")
                return False
                
        except FileNotFoundError:
            console.print("[yellow]Alembic not found, using direct SQL[/yellow]")
            return await self.run_sql_schema()
    
    async def run_sql_schema(self):
        """Run SQL schema directly"""
        schema_file = Path(__file__).parent / "database" / "schema.sql"
        
        if not schema_file.exists():
            console.print("[red]Schema file not found[/red]")
            return False
            
        try:
            # Connect to database using psycopg
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cursor:
                    # Read and execute schema
                    with open(schema_file, 'r') as f:
                        schema_sql = f.read()
                    
                    await cursor.execute(schema_sql)
                    console.print("[green]✓ Database schema created[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating schema: {e}[/red]")
            return False
    
    async def verify_tables(self):
        """Verify that all tables were created"""
        expected_tables = [
            'calls',
            'call_connection_metrics',
            'call_interaction_metrics',
            'call_speech_analytics',
            'call_system_metrics',
            'call_events'
        ]
        
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cursor:
                    # Get list of tables
                    await cursor.execute("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    tables = await cursor.fetchall()
                    
                    table_names = [t[0] for t in tables]
                    
                    console.print("\n[bold]Database Tables:[/bold]")
                    for table in expected_tables:
                        if table in table_names:
                            console.print(f"  [green]✓ {table}[/green]")
                        else:
                            console.print(f"  [red]✗ {table}[/red]")
            
            # Check if all tables exist
            return all(table in table_names for table in expected_tables)
            
        except Exception as e:
            console.print(f"[red]Error verifying tables: {e}[/red]")
            return False
    
    async def test_connection(self):
        """Test database connection and basic operations"""
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as conn:
                async with conn.cursor() as cursor:
                    # Test insert
                    await cursor.execute("""
                        INSERT INTO calls (dispatch_id, room_name, phone_number, status)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (dispatch_id) DO NOTHING
                    """, ("TEST_DISPATCH", "test_room", "+1234567890", "test"))
                    
                    # Test select
                    await cursor.execute(
                        "SELECT COUNT(*) FROM calls WHERE dispatch_id = %s",
                        ("TEST_DISPATCH",)
                    )
                    result = await cursor.fetchone()
                    
                    # Clean up
                    await cursor.execute(
                        "DELETE FROM calls WHERE dispatch_id = %s",
                        ("TEST_DISPATCH",)
                    )
            
            console.print("[green]✓ Database connection test passed[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Connection test failed: {e}[/red]")
            return False


async def main():
    console.print("[bold blue]Voice Agent Database Initialization[/bold blue]\n")
    
    initializer = DatabaseInitializer()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Check PostgreSQL
        task = progress.add_task("Checking PostgreSQL...", total=None)
        if not initializer.check_postgres_running():
            progress.stop()
            console.print("[red]PostgreSQL is not running![/red]")
            console.print("\nTo start PostgreSQL:")
            console.print("  macOS: brew services start postgresql")
            console.print("  Linux: sudo systemctl start postgresql")
            return
        progress.update(task, completed=True)
        
        # Create database
        task = progress.add_task("Creating database...", total=None)
        if not initializer.create_database():
            progress.stop()
            return
        progress.update(task, completed=True)
        
        # Run migrations
        task = progress.add_task("Running migrations...", total=None)
        success = await initializer.run_migrations()
        progress.update(task, completed=True)
        
        if not success:
            progress.stop()
            console.print("\n[yellow]Trying direct SQL schema...[/yellow]")
            success = await initializer.run_sql_schema()
            if not success:
                return
        
        # Verify tables
        task = progress.add_task("Verifying tables...", total=None)
        tables_ok = await initializer.verify_tables()
        progress.update(task, completed=True)
        
        if not tables_ok:
            progress.stop()
            console.print("[red]Some tables are missing![/red]")
            return
        
        # Test connection
        task = progress.add_task("Testing connection...", total=None)
        await initializer.test_connection()
        progress.update(task, completed=True)
    
    console.print("\n[bold green]Database initialization complete![/bold green]")
    console.print(f"\nDatabase URL: {initializer.database_url}")
    console.print("\nYou can now run the agent and analytics will be tracked automatically.")
    console.print("\nTo view analytics, run: python analytics_dashboard.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Initialization cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)