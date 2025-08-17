#!/usr/bin/env python3
"""
Script to find call recordings in S3
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv('.env.local')

def find_recordings(phone_number=None, date=None):
    """Find recordings in S3 bucket"""
    
    # S3 configuration
    s3_bucket = os.getenv('S3_BUCKET_NAME', 'sangram-sandbox-bucket')
    s3_region = os.getenv('S3_REGION', 'us-east-1')
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if not all([aws_access_key, aws_secret_key]):
        print("Error: AWS credentials not found in .env.local")
        return
    
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=s3_region
    )
    
    # Use today's date if not specified
    if date is None:
        date = datetime.now()
    
    # Common prefixes where recordings might be stored
    prefixes = [
        f'egress-recordings/{date.year}/{date.month:02d}/{date.day:02d}/',
        f'call-recordings/{date.year}/{date.month:02d}/{date.day:02d}/',
        f'recordings/{date.year}/{date.month:02d}/{date.day:02d}/',
    ]
    
    found_recordings = []
    
    for prefix in prefixes:
        print(f"\nChecking prefix: {prefix}")
        
        try:
            # Use paginator for large buckets
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=s3_bucket,
                Prefix=prefix
            )
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if key.endswith('.mp4'):
                            # Check if phone number matches (if specified)
                            if phone_number is None or phone_number.replace('+', '') in key:
                                found_recordings.append({
                                    'key': key,
                                    'size': obj['Size'],
                                    'last_modified': obj['LastModified']
                                })
                                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                print(f"  Access denied. Trying alternative method...")
                
                # Try checking specific files if we can't list
                if phone_number:
                    clean_phone = phone_number.replace('+', '')
                    # Try common patterns
                    test_keys = [
                        f'{prefix}outbound-{clean_phone}_{int(datetime.now().timestamp())}.mp4',
                        f'{prefix}room-outbound-{clean_phone}.mp4',
                        f'{prefix}{clean_phone}.mp4',
                    ]
                    
                    for test_key in test_keys:
                        try:
                            response = s3_client.head_object(Bucket=s3_bucket, Key=test_key)
                            found_recordings.append({
                                'key': test_key,
                                'size': response['ContentLength'],
                                'last_modified': response['LastModified']
                            })
                            print(f"  Found: {test_key}")
                        except:
                            pass
            else:
                print(f"  Error: {error_code} - {e.response['Error']['Message']}")
    
    # Display results
    if found_recordings:
        print(f"\n{'='*80}")
        print(f"FOUND {len(found_recordings)} RECORDING(S):")
        print(f"{'='*80}")
        
        for rec in found_recordings:
            print(f"\nFile: {rec['key']}")
            print(f"Size: {rec['size']:,} bytes ({rec['size']/1024/1024:.2f} MB)")
            print(f"Modified: {rec['last_modified']}")
            
            # Generate presigned URL
            try:
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': s3_bucket, 'Key': rec['key']},
                    ExpiresIn=86400  # 24 hours
                )
                print(f"\nPresigned URL (valid 24 hours):")
                print(url)
                
                # Also generate download URL
                download_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': s3_bucket,
                        'Key': rec['key'],
                        'ResponseContentDisposition': f'attachment; filename="{os.path.basename(rec["key"])}"'
                    },
                    ExpiresIn=86400
                )
                print(f"\nDirect download URL:")
                print(download_url)
                
            except Exception as e:
                print(f"Error generating URL: {e}")
            
            print(f"\n{'-'*80}")
    else:
        print(f"\nNo recordings found for date {date.strftime('%Y-%m-%d')}")
        if phone_number:
            print(f"Phone number filter: {phone_number}")


if __name__ == "__main__":
    # Parse command line arguments
    phone = None
    date = None
    
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            date = datetime.strptime(sys.argv[2], '%Y-%m-%d')
        except:
            print(f"Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    print("Call Recording Finder")
    print("=" * 50)
    print(f"Phone: {phone or 'All'}")
    print(f"Date: {(date or datetime.now()).strftime('%Y-%m-%d')}")
    
    find_recordings(phone, date)