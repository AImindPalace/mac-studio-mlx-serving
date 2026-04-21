#!/usr/bin/env bash
# Fast Mac <- Spark transfer of merged BF16 model.
# Uses tar stream over SSH with AES-GCM (hw accel on Apple Silicon).
# See docs/ethernet-transfer-gotcha.md for background.

set -euo pipefail

SPARK_HOST="${1:?usage: transfer_from_spark.sh <user@spark> [remote_dir] [local_dir]}"
REMOTE_DIR="${2:-~/models/Jarvis_27B_trading}"
LOCAL_DIR="${3:-$HOME/jarvis/merged}"

echo "Turning off WiFi to force ethernet-only route..."
networksetup -setairportpower en1 off

echo "Creating local dir: $LOCAL_DIR"
mkdir -p "$LOCAL_DIR"

echo "Streaming $SPARK_HOST:$REMOTE_DIR -> $LOCAL_DIR"
ssh -c aes256-gcm@openssh.com -o Compression=no "$SPARK_HOST" \
  "cd $(dirname $REMOTE_DIR) && tar cf - $(basename $REMOTE_DIR)" \
  | tar xf - -C "$LOCAL_DIR" --strip-components=1

echo "Transfer complete. Files:"
ls -la "$LOCAL_DIR" | head -20

echo
echo "To re-enable WiFi: networksetup -setairportpower en1 on"
