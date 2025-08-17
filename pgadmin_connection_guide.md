# pgAdmin 4 Connection Guide for Krim AI Database

## Step 1: Open pgAdmin 4

## Step 2: Create New Server Connection
1. In the left panel, you should see "Servers"
2. Right-click on "Servers"
3. Select "Register" → "Server..."

## Step 3: Fill in the Details

### In the "General" tab:
- **Name**: `Krim AI Platform` (this is just a display name, can be anything)

### In the "Connection" tab:
Fill in these EXACT values:
- **Host name/address**: `localhost`
- **Port**: `5432`
- **Maintenance database**: `krim_ai_platform`
- **Username**: `krim_ai`
- **Password**: `dev_password_change_in_production`
- ✅ Check "Save password?"

### Click "Save"

## Step 4: Navigate to the Database
Once connected, expand the tree:
```
Servers
└── Krim AI Platform (or whatever name you gave)
    └── Databases (1)
        └── krim_ai_platform
            └── Schemas (1)
                └── public
                    └── Tables (90+)
                        └── interactions
                        └── customers
                        └── loan_accounts
                        └── ... (many more tables)
```

## Common Issues and Solutions

### Issue 1: "Unable to connect to server"
```bash
# Check if PostgreSQL is running
pg_ctl status

# If not running, start it:
pg_ctl start
```

### Issue 2: "FATAL: password authentication failed"
Make sure you're using:
- Username: `krim_ai` (NOT postgres)
- Password: `dev_password_change_in_production`

### Issue 3: "Database 'krim_ai_platform' does not exist"
The database name is case-sensitive. Use exactly: `krim_ai_platform`

### Issue 4: Can't see any databases after connecting
- Make sure you're connecting with username `krim_ai`
- The user might not have permissions. Try this in terminal:
```bash
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE krim_ai_platform TO krim_ai;"
```

## Quick Test Query
Once connected, open Query Tool (Tools → Query Tool) and run:
```sql
SELECT COUNT(*) FROM interactions;
```

This should return a count of interactions in the database.

## Alternative: Direct Connection String
If you're still having issues, in pgAdmin you can also:
1. Right-click "Servers" → "Register" → "Server..."
2. Go to "Connection" tab
3. At the bottom, there's an "Advanced" section
4. In "DB restriction", enter: `krim_ai_platform`

This forces pgAdmin to only show this specific database.