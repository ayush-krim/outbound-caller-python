# S3 Setup for LiveKit Egress Recording

## Prerequisites
1. AWS Account
2. AWS CLI installed (optional but helpful)

## Step 1: Create S3 Bucket

1. Go to AWS Console → S3
2. Click "Create bucket"
3. Configure:
   - Bucket name: `your-livekit-recordings` (must be globally unique)
   - Region: Choose your preferred region (e.g., `us-east-1`)
   - Block all public access: Keep enabled for security

## Step 2: Create IAM User for LiveKit

1. Go to AWS Console → IAM → Users
2. Click "Add users"
3. User name: `livekit-egress-user`
4. Select "Programmatic access"

## Step 3: Create IAM Policy

Create a new policy with these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-livekit-recordings/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::your-livekit-recordings"
        }
    ]
}
```

## Step 4: Attach Policy to User

1. Attach the policy to `livekit-egress-user`
2. Save the Access Key ID and Secret Access Key

## Step 5: Configure Environment Variables

Add these to your `.env.local` file:

```bash
# S3 Configuration for LiveKit Egress
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=your-livekit-recordings
S3_REGION=us-east-1

# Optional: Use these for the RecordingManager S3 upload feature
USE_S3_STORAGE=true
S3_RECORDING_PREFIX=call-recordings
```

## Step 6: Test S3 Access

Run this command to test:
```bash
aws s3 ls s3://your-livekit-recordings/
```

## CORS Configuration (Optional)

If you need to access recordings from a web browser, add this CORS policy to your bucket:

```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST"],
            "AllowedOrigins": ["*"],
            "ExposeHeaders": []
        }
    ]
}
```

## Security Best Practices

1. Use IAM roles if running on EC2
2. Rotate access keys regularly
3. Enable bucket versioning for recovery
4. Consider enabling bucket encryption
5. Set up lifecycle policies to manage old recordings