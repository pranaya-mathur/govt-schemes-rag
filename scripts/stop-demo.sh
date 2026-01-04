#!/bin/bash
# Stop Demo Environment - Graceful shutdown to minimize costs
# This script stops both EC2 instances after demo/interview

set -e

echo "=========================================="
echo "Stopping Yojana-AI Demo Environment"
echo "=========================================="
echo ""

# ============================================
# CONFIGURATION - UPDATE WITH YOUR VALUES
# ============================================
JENKINS_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"  # TODO: Replace with your Jenkins instance ID
APP_INSTANCE_ID="i-XXXXXXXXXXXXXXXXX"      # TODO: Replace with your App instance ID
REGION="us-east-1"                         # TODO: Update if using different region

echo "Configuration:"
echo "  Jenkins Instance: $JENKINS_INSTANCE_ID"
echo "  App Instance:     $APP_INSTANCE_ID"
echo "  Region:           $REGION"
echo ""

# Confirm before stopping
read -p "Are you sure you want to stop the demo environment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Stopping EC2 instances..."
aws ec2 stop-instances \
    --instance-ids $JENKINS_INSTANCE_ID $APP_INSTANCE_ID \
    --region $REGION \
    --output table

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Environment Stopped Successfully"
    echo "=========================================="
    echo ""
    echo "Status:"
    echo "  ⏸️  Both instances are now stopping"
    echo "  💰 Monthly costs reduced to near-zero"
    echo "  💾 All data persisted in EBS volumes"
    echo ""
    echo "To restart:"
    echo "  ./scripts/start-demo.sh"
    echo ""
    echo "Cost Impact:"
    echo "  Running:  ~$0.02/hour (both instances)"
    echo "  Stopped:  ~$0.10/month (EBS storage only)"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "❌ ERROR: Failed to stop instances"
    echo "Please check:"
    echo "  - AWS credentials configured"
    echo "  - Instance IDs are correct"
    echo "  - You have permissions to stop instances"
    exit 1
fi