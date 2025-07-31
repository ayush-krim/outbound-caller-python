#!/bin/bash

# Usage: ./dispatch_test.sh +917827470456

if [ -z "$1" ]; then
    echo "Usage: $0 <phone_number>"
    exit 1
fi

PHONE_NUMBER=$1

echo "Dispatching call to $PHONE_NUMBER..."

lk dispatch create \
  --new-room \
  --agent-name outbound-caller-local \
  --metadata "{\"phone_number\": \"$PHONE_NUMBER\", \"transfer_to\": \"+1 507 626 9649\"}"