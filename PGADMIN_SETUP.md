# Connecting to Krim AI Database with pgAdmin 4

## Database Connection Details
```
Host: localhost
Port: 5432
Database: krim_ai_platform
Username: krim_ai
Password: dev_password_change_in_production
```

## Steps to Connect in pgAdmin 4

### 1. Install pgAdmin 4 (if not already installed)
- Download from: https://www.pgadmin.org/download/
- For macOS: Download the .dmg file and install

### 2. Open pgAdmin 4 and Create New Server Connection

1. **Right-click on "Servers"** in the left panel
2. Select **"Register" → "Server..."**

### 3. Configure Connection

#### General Tab:
- **Name**: Krim AI Platform (or any name you prefer)

#### Connection Tab:
- **Host name/address**: `localhost`
- **Port**: `5432`
- **Maintenance database**: `krim_ai_platform`
- **Username**: `krim_ai`
- **Password**: `dev_password_change_in_production`
- **Save password?**: Check this box if you want to save the password

### 4. Optional Settings

#### SSL Tab (if needed):
- **SSL mode**: Prefer (or Disable for local development)

#### Advanced Tab:
- Leave default values unless you have specific requirements

### 5. Click "Save" to connect

## Viewing the Data

Once connected, navigate to:
```
Servers 
  → Krim AI Platform (your server name)
    → Databases
      → krim_ai_platform
        → Schemas
          → public
            → Tables
```

### Key Tables to Explore:
- **interactions** - Contains all call data and dispositions
- **customers** - Customer information
- **loan_accounts** - Loan details with EMI information
- **organizations** - Organization data
- **users** - Agent/user information
- **campaigns** - Campaign information
- **agent_configs** - Agent configuration

### To View Interaction Data:
1. Right-click on the **interactions** table
2. Select **"View/Edit Data" → "All Rows"**
3. Or use the Query Tool to run custom queries

## Useful Queries for pgAdmin Query Tool

### View all test interactions:
```sql
SELECT * FROM interactions 
WHERE "customerId" = 'test_customer_001'
ORDER BY "createdAt" DESC;
```

### View interactions with dispositions:
```sql
SELECT 
    id,
    status,
    outcome,
    "callDisposition"->>'disposition' as disposition,
    "callDisposition"->>'connection_status' as connection,
    "paymentDiscussed",
    "paymentAmount",
    duration
FROM interactions 
WHERE "callDisposition" IS NOT NULL
ORDER BY "updatedAt" DESC;
```

### View customer with loan details:
```sql
SELECT 
    c.id,
    c."firstName",
    c."lastName",
    c.phone,
    la."accountNumber",
    la."emiAmount",
    la."nextDueDate",
    la."currentBalance"
FROM customers c
LEFT JOIN loan_accounts la ON c.id = la."customerId"
WHERE c.id = 'test_customer_001';
```

## Troubleshooting

### Connection Refused Error:
- Ensure PostgreSQL is running: `pg_ctl status`
- Check if it's listening on port 5432: `lsof -i :5432`

### Authentication Failed:
- Verify the password is correct
- Check pg_hba.conf allows connections from localhost

### Database Not Found:
- Ensure you're connecting to `krim_ai_platform` not `postgres`

## Visual Features in pgAdmin

1. **Table Data Grid**: View and edit data directly
2. **Query Tool**: Write and execute SQL queries
3. **ERD Tool**: View database relationships
4. **Statistics**: Monitor query performance
5. **Dashboard**: Real-time server metrics

## Tips
- Use the filter feature in data view to find specific records
- Save frequently used queries as "Macros"
- Use the explain plan feature to optimize queries
- Export query results to CSV/JSON for analysis