"""
Seed database with test data for voice AI agent testing
Creates all necessary records respecting foreign key constraints
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from database.config import async_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSeeder:
    """Seeds the database with test data in the correct order"""
    
    def __init__(self):
        self.organization_id = None
        self.user_id = None
        self.customer_id = None
        self.campaign_id = None
        self.agent_config_id = None
    
    async def seed_all(self):
        """Run all seed operations in the correct order"""
        try:
            # 1. Create Organization
            await self.create_organization()
            
            # 2. Create User (Agent)
            await self.create_user()
            
            # 3. Create Customer
            await self.create_customer()
            
            # 4. Create Campaign
            await self.create_campaign()
            
            # 5. Create Agent Config (optional)
            await self.create_agent_config()
            
            # 6. Create Interactions
            await self.create_interactions()
            
            logger.info("✅ Database seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            raise
    
    async def create_organization(self):
        """Create organization if it doesn't exist"""
        self.organization_id = "test_org_001"
        
        async with async_session() as session:
            # Check if exists
            result = await session.execute(
                text("SELECT id FROM organizations WHERE id = :id"),
                {"id": self.organization_id}
            )
            if result.fetchone():
                logger.info(f"Organization {self.organization_id} already exists")
                return
            
            # Create organization with all required fields
            await session.execute(text("""
                INSERT INTO organizations (
                    id, name, "legalBusinessName", domain, slug, 
                    industry, size, "primaryEmail", "subscriptionTier", 
                    "isActive", "createdAt", "updatedAt"
                ) VALUES (
                    :id, :name, :legal_name, :domain, :slug,
                    :industry, :size, :email, :tier,
                    true, NOW(), NOW()
                )
            """), {
                "id": self.organization_id,
                "name": "Test Organization",
                "legal_name": "Test Organization LLC",
                "domain": "testorg.com",
                "slug": "test-org",
                "industry": "DEBT_COLLECTION",
                "size": "MEDIUM",
                "email": "admin@testorg.com",
                "tier": "PROFESSIONAL"
            })
            await session.commit()
            logger.info(f"✅ Created organization: {self.organization_id}")
    
    async def create_user(self):
        """Create user (agent) if it doesn't exist"""
        self.user_id = "test_agent_001"
        
        async with async_session() as session:
            # Check if exists
            result = await session.execute(
                text("SELECT id FROM users WHERE id = :id"),
                {"id": self.user_id}
            )
            if result.fetchone():
                logger.info(f"User {self.user_id} already exists")
                return
            
            # Create user with camelCase columns
            await session.execute(text("""
                INSERT INTO users (
                    id, email, password, "firstName", "lastName",
                    status, "organizationId", "createdAt", "updatedAt"
                ) VALUES (
                    :id, :email, :password, :first_name, :last_name,
                    :status, :org_id, NOW(), NOW()
                )
            """), {
                "id": self.user_id,
                "email": "test.agent@testorg.com",
                "password": "$2b$10$YourHashedPasswordHere",  # In real app, this would be properly hashed
                "first_name": "Test",
                "last_name": "Agent",
                "status": "ACTIVE",
                "org_id": self.organization_id
            })
            await session.commit()
            logger.info(f"✅ Created user (agent): {self.user_id}")
    
    async def create_customer(self):
        """Create customer if it doesn't exist"""
        self.customer_id = "test_customer_001"
        
        async with async_session() as session:
            # Check if exists
            result = await session.execute(
                text("SELECT id FROM customers WHERE id = :id"),
                {"id": self.customer_id}
            )
            if result.fetchone():
                logger.info(f"Customer {self.customer_id} already exists")
                return
            
            # Create customer with correct column names
            await session.execute(text("""
                INSERT INTO customers (
                    id, "organizationId", "firstName", "lastName",
                    phone, email, "createdAt", "updatedAt"
                ) VALUES (
                    :id, :org_id, :first_name, :last_name,
                    :phone, :email, NOW(), NOW()
                )
            """), {
                "id": self.customer_id,
                "org_id": self.organization_id,
                "first_name": "Test",
                "last_name": "Customer",
                "phone": "+917827470456",
                "email": "test.customer@example.com"
            })
            await session.commit()
            logger.info(f"✅ Created customer: {self.customer_id}")
            
            # Also create a loan account for this customer
            await self.create_loan_account()
    
    async def create_loan_account(self):
        """Create loan account for the customer"""
        self.loan_account_id = "test_loan_001"
        
        async with async_session() as session:
            # Check if exists
            result = await session.execute(
                text("SELECT id FROM loan_accounts WHERE id = :id"),
                {"id": self.loan_account_id}
            )
            if result.fetchone():
                logger.info(f"Loan account {self.loan_account_id} already exists")
                return
            
            # Create loan account with correct column names
            await session.execute(text("""
                INSERT INTO loan_accounts (
                    id, "customerId", "organizationId", "accountNumber",
                    "productType", status, "originalAmount", "currentBalance",
                    "interestRate", "emiAmount", tenure, "nextDueDate",
                    "createdAt", "updatedAt"
                ) VALUES (
                    :id, :customer_id, :org_id, :account_num,
                    :product_type, :status, :original, :balance,
                    :rate, :emi, :tenure, :due_date,
                    NOW(), NOW()
                )
            """), {
                "id": self.loan_account_id,
                "customer_id": self.customer_id,
                "org_id": self.organization_id,
                "account_num": "LOAN1234567890",
                "product_type": "PERSONAL_LOAN",
                "status": "IN_COLLECTION",
                "original": 50000.00,
                "balance": 47250.00,
                "rate": 8.75,
                "emi": 2500.00,
                "tenure": 24,
                "due_date": datetime.now() - timedelta(days=5)  # Pass datetime not date for timestamp column
            })
            await session.commit()
            logger.info(f"✅ Created loan account: {self.loan_account_id}")
    
    async def create_campaign(self):
        """Create campaign if it doesn't exist"""
        self.campaign_id = "test_campaign_001"
        
        async with async_session() as session:
            # Check if exists
            result = await session.execute(
                text("SELECT id FROM campaigns WHERE id = :id"),
                {"id": self.campaign_id}
            )
            if result.fetchone():
                logger.info(f"Campaign {self.campaign_id} already exists")
                return
            
            # Create campaign with camelCase columns
            await session.execute(text("""
                INSERT INTO campaigns (
                    id, "organizationId", name, status,
                    "createdBy", "createdAt", "updatedAt"
                ) VALUES (
                    :id, :org_id, :name, :status,
                    :created_by, NOW(), NOW()
                )
            """), {
                "id": self.campaign_id,
                "org_id": self.organization_id,
                "name": "Test Voice Campaign",
                "status": "ACTIVE",
                "created_by": self.user_id
            })
            await session.commit()
            logger.info(f"✅ Created campaign: {self.campaign_id}")
    
    async def create_agent_config(self):
        """Create agent config (optional but good to have)"""
        self.agent_config_id = "test_agent_config_001"
        
        async with async_session() as session:
            # Check if exists (table name is agent_configs with underscore)
            try:
                result = await session.execute(
                    text("SELECT id FROM agent_configs WHERE id = :id LIMIT 1"),
                    {"id": self.agent_config_id}
                )
                if result.fetchone():
                    logger.info(f"Agent config {self.agent_config_id} already exists")
                    return
                
                # Create agent config with camelCase columns
                await session.execute(text("""
                    INSERT INTO agent_configs (
                        id, "organizationId", name, personality,
                        "createdBy", "createdAt", "updatedAt"
                    ) VALUES (
                        :id, :org_id, :name, :personality,
                        :created_by, NOW(), NOW()
                    )
                """), {
                    "id": self.agent_config_id,
                    "org_id": self.organization_id,
                    "name": "Test Voice Agent Config",
                    "personality": "professional",
                    "created_by": self.user_id
                })
                await session.commit()
                logger.info(f"✅ Created agent config: {self.agent_config_id}")
            except Exception as e:
                logger.warning(f"Agent config table might not exist: {e}")
                self.agent_config_id = None
    
    async def create_interactions(self):
        """Create test interactions with different statuses"""
        interactions = [
            {
                "id": f"test_interaction_{int(datetime.now().timestamp())}_1",
                "status": "INITIATED",
                "description": "Ready for calling"
            },
            {
                "id": f"test_interaction_{int(datetime.now().timestamp())}_2",
                "status": "INITIATED",
                "description": "Another ready interaction"
            },
            {
                "id": f"test_interaction_{int(datetime.now().timestamp())}_3",
                "status": "COMPLETED",
                "description": "Already completed (for testing)"
            }
        ]
        
        async with async_session() as session:
            for idx, interaction in enumerate(interactions):
                try:
                    # Build the query based on whether agentConfigId exists
                    if self.agent_config_id:
                        query = """
                        INSERT INTO interactions (
                            id, "organizationId", "customerId", "campaignId",
                            "agentId", "agentConfigId", channel, direction,
                            status, "startTime", "createdAt", "updatedAt",
                            notes
                        ) VALUES (
                            :id, :org_id, :customer_id, :campaign_id,
                            :agent_id, :agent_config_id, :channel, :direction,
                            :status, NOW(), NOW(), NOW(),
                            :notes
                        )
                        """
                        params = {
                            "id": interaction["id"],
                            "org_id": self.organization_id,
                            "customer_id": self.customer_id,
                            "campaign_id": self.campaign_id,
                            "agent_id": self.user_id,
                            "agent_config_id": self.agent_config_id,
                            "channel": "VOICE",
                            "direction": "OUTBOUND",
                            "status": interaction["status"],
                            "notes": f"Test interaction: {interaction['description']}"
                        }
                    else:
                        query = """
                        INSERT INTO interactions (
                            id, "organizationId", "customerId", "campaignId",
                            "agentId", channel, direction,
                            status, "startTime", "createdAt", "updatedAt",
                            notes
                        ) VALUES (
                            :id, :org_id, :customer_id, :campaign_id,
                            :agent_id, :channel, :direction,
                            :status, NOW(), NOW(), NOW(),
                            :notes
                        )
                        """
                        params = {
                            "id": interaction["id"],
                            "org_id": self.organization_id,
                            "customer_id": self.customer_id,
                            "campaign_id": self.campaign_id,
                            "agent_id": self.user_id,
                            "channel": "VOICE",
                            "direction": "OUTBOUND",
                            "status": interaction["status"],
                            "notes": f"Test interaction: {interaction['description']}"
                        }
                    
                    await session.execute(text(query), params)
                    await session.commit()
                    
                    if interaction["status"] == "INITIATED":
                        logger.info(f"✅ Created interaction {idx+1}: {interaction['id']} (READY FOR CALLING)")
                    else:
                        logger.info(f"✅ Created interaction {idx+1}: {interaction['id']} (status: {interaction['status']})")
                        
                except Exception as e:
                    logger.error(f"Failed to create interaction {idx+1}: {e}")
    
    async def cleanup(self):
        """Optional: Clean up test data"""
        async with async_session() as session:
            try:
                # Delete in reverse order of creation
                await session.execute(
                    text("DELETE FROM interactions WHERE id LIKE 'test_interaction_%'")
                )
                if self.agent_config_id:
                    await session.execute(
                        text('DELETE FROM agent_configs WHERE id = :id'),
                        {"id": self.agent_config_id}
                    )
                await session.execute(
                    text("DELETE FROM campaigns WHERE id = :id"),
                    {"id": self.campaign_id}
                )
                await session.execute(
                    text("DELETE FROM loan_accounts WHERE id = :id"),
                    {"id": "test_loan_001"}
                )
                await session.execute(
                    text("DELETE FROM customers WHERE id = :id"),
                    {"id": self.customer_id}
                )
                await session.execute(
                    text("DELETE FROM users WHERE id = :id"),
                    {"id": self.user_id}
                )
                await session.execute(
                    text("DELETE FROM organizations WHERE id = :id"),
                    {"id": self.organization_id}
                )
                await session.commit()
                logger.info("✅ Cleanup completed")
            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
                await session.rollback()


async def main():
    """Main function to run seeding"""
    import sys
    
    seeder = DatabaseSeeder()
    
    print("\n🌱 DATABASE SEEDER FOR VOICE AI AGENT 🌱")
    print("="*50)
    print("\nThis will create test data for:")
    print("- Organization: test_org_001")
    print("- User (Agent): test_agent_001")
    print("- Customer: test_customer_001")
    print("- Campaign: test_campaign_001")
    print("- Loan Account: test_loan_001")
    print("- Interactions: 3 test interactions (2 INITIATED, 1 COMPLETED)")
    print("\n" + "="*50)
    
    # Check for command line argument
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        # Default to seeding
        choice = "1"
        print("\n🚀 Auto-seeding database (no argument provided)...")
    
    if choice == "1" or choice == "seed":
        print("\n🚀 Starting database seeding...")
        await seeder.seed_all()
        
        print("\n✅ SEEDING COMPLETE!")
        print("\n📞 You can now make test calls with:")
        print("""
curl -X POST http://localhost:8000/call \\
  -H "Content-Type: application/json" \\
  -d '{
    "customer_id": "test_customer_001",
    "organization_id": "test_org_001",
    "campaign_id": "test_campaign_001",
    "agent_id": "test_agent_001",
    "phone_number": "+917827470456",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test Customer",
      "last_4_digits": "1234",
      "emi_amount": 2500,
      "emi_due_date": "2025-08-02"
    }
  }'
        """)
        
    elif choice == "2" or choice == "cleanup":
        print("\n🧹 Cleaning up test data...")
        await seeder.cleanup()
        
    else:
        print("\n❌ Invalid choice. Use '1' or 'seed' to seed, '2' or 'cleanup' to clean up.")
        print("Usage: python seed_database.py [seed|cleanup]")


if __name__ == "__main__":
    import os
    # Ensure we use the correct database URL
    os.environ["DATABASE_URL"] = "postgresql://krim_ai:dev_password_change_in_production@localhost:5432/krim_ai_platform"
    
    asyncio.run(main())