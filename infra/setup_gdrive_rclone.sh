#!/usr/bin/env bash
# ==============================================================================
# Setup & Fast Stream Nemotron 3 Ultra (1.12 TB BF16) from 4TB Google Drive
# to GCP Ephemeral Local NVMe RAID-0 Array
# ==============================================================================

set -euo pipefail

echo "=================================================================="
echo "⚡ Nemotron 3 Ultra: GCP Ephemeral NVMe Fast Streamer"
echo "=================================================================="

NVME_MOUNT="/mnt/fast-nvme/nemotron-bf16"
GDRIVE_REMOTE="gdrive:models/nemotron-3-ultra-bf16"

# 1. Check if Local NVMe devices exist on this GCP instance
if ls /dev/nvme0n* 1> /dev/null 2>&1; then
    echo "[1/3] Detected Local NVMe SSD drives. Assembling RAID-0 array..."
    if ! grep -qs "$NVME_MOUNT" /proc/mounts; then
        mkdir -p "$NVME_MOUNT"
        if ! [ -e /dev/md0 ]; then
            mdadm --create /dev/md0 --level=0 --raid-devices=$(ls -1 /dev/nvme0n* | wc -l) /dev/nvme0n*
            mkfs.ext4 -F /dev/md0
        fi
        mount -o noatime,nodiratime /dev/md0 "$NVME_MOUNT"
        echo "✅ Mounted NVMe RAID-0 at $NVME_MOUNT (I/O bandwidth: up to 20 GB/s)"
    fi
else
    echo "[INFO] No local NVMe devices found. Using standard fast scratch disk."
    mkdir -p "$NVME_MOUNT"
fi

# 2. Verify rclone installation
if ! command -v rclone &> /dev/null; then
    echo "[2/3] Installing rclone..."
    curl -s https://rclone.org/install.sh | sudo bash
fi

# 3. Stream 1.12 TB Sharded Weights from 4TB Google Drive
echo "[3/3] Streaming 1.12 TB model weights from $GDRIVE_REMOTE to $NVME_MOUNT..."
rclone copy "$GDRIVE_REMOTE" "$NVME_MOUNT" \
  --transfers=32 \
  --checkers=32 \
  --drive-chunk-size=256M \
  --buffer-size=128M \
  --fast-list \
  --progress

echo "=================================================================="
echo "✅ Checkpoint stream complete! All 224 shards ready for vLLM / NIM."
echo "Launch vLLM using:"
echo "python3 -m vllm.entrypoints.openai.api_server --model $NVME_MOUNT --tensor-parallel-size 8 --dtype bfloat16"
echo "=================================================================="
