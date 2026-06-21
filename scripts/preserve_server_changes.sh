#!/bin/bash

# Server Dirty-Change Preservation Script
# This script helps preserve server changes before deployment

# Configuration
SERVER_USER="hollow"
SERVER_HOST="100.71.60.13"
SERVER_PATH="/path/to/project"  # Update this to actual server path
BACKUP_DIR="./server_backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "=== Server Dirty-Change Preservation ==="
echo "Server: $SERVER_USER@$SERVER_HOST"
echo "Server Path: $SERVER_PATH"
echo "Local Backup: $BACKUP_DIR"
echo ""

# Check server changes
echo "Step 1: Checking server changes..."
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && git status" > "$BACKUP_DIR/server_status.txt"

if grep -q "nothing to commit" "$BACKUP_DIR/server_status.txt"; then
    echo "✓ No dirty changes on server"
    rm "$BACKUP_DIR/server_status.txt"
    exit 0
fi

echo "⚠ Dirty changes detected on server"
echo ""

# Get detailed diff
echo "Step 2: Getting detailed diff..."
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && git diff" > "$BACKUP_DIR/server_diff.txt"
echo "Diff saved to: $BACKUP_DIR/server_diff.txt"
echo ""

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/server_backup_$TIMESTAMP.patch"

echo "Step 3: Creating patch backup..."
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && git diff > /tmp/backup_$TIMESTAMP.patch"
scp "$SERVER_USER@$SERVER_HOST:/tmp/backup_$TIMESTAMP.patch" "$BACKUP_FILE"
ssh "$SERVER_USER@$SERVER_HOST" "rm /tmp/backup_$TIMESTAMP.patch"
echo "Patch saved to: $BACKUP_FILE"
echo ""

# Get list of changed files
echo "Step 4: Getting list of changed files..."
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && git status --short" > "$BACKUP_DIR/changed_files.txt"
echo "Changed files saved to: $BACKUP_DIR/changed_files.txt"
echo ""

# Show summary
echo "=== Summary ==="
echo "Dirty changes found on server"
echo "Backup created: $BACKUP_FILE"
echo "Diff available: $BACKUP_DIR/server_diff.txt"
echo "Changed files: $BACKUP_DIR/changed_files.txt"
echo ""
echo "Next steps:"
echo "1. Review the changes: cat $BACKUP_DIR/server_diff.txt"
echo "2. If changes are legitimate, commit them on server"
echo "3. If changes are accidental, stash them: ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && git stash push -m \"preserved_$TIMESTAMP\"'"
echo "4. After handling, run: git pull on local machine"
echo ""
echo "⚠ DO NOT proceed with deployment until server changes are resolved"
