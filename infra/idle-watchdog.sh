#!/usr/bin/env bash
# ==============================================================================
# GCP Spot VM Idle Watchdog Daemon
# Protects your $300 GCP credit by automatically shutting down the GPU VM
# if no agent tasks or vLLM inference requests are received for 5 minutes (300s).
# ==============================================================================

IDLE_THRESHOLD_SECONDS=300
POLL_INTERVAL=30
IDLE_TIMER=0
LOG_FILE="/var/log/nemotron-watchdog.log"

echo "[$(date)] Starting Nemotron Spot GPU Idle Watchdog Daemon..." | tee -a "$LOG_FILE"

while true; do
    # Check if vLLM or Python worker process is actively generating tokens
    IS_ACTIVE=0

    # 1. Check if GPU compute is active (utilization > 5%)
    if command -v nvidia-smi &> /dev/null; then
        GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -n 1)
        if [ "$GPU_UTIL" -gt 5 ]; then
            IS_ACTIVE=1
        fi
    fi

    # 2. Check if agent mission worker process is running
    if pgrep -f "nemotron_worker" > /dev/null || pgrep -f "celery" > /dev/null; then
        IS_ACTIVE=1
    fi

    if [ "$IS_ACTIVE" -eq 1 ]; then
        IDLE_TIMER=0
    else
        IDLE_TIMER=$((IDLE_TIMER + POLL_INTERVAL))
        echo "[$(date)] Inactive for $IDLE_TIMER / $IDLE_THRESHOLD_SECONDS seconds" >> "$LOG_FILE"

        if [ "$IDLE_TIMER" -ge "$IDLE_THRESHOLD_SECONDS" ]; then
            echo "[$(date)] ⚠️ System idle for 5 minutes! Halting VM to preserve $300 credit..." | tee -a "$LOG_FILE"
            
            # Use gcloud or system poweroff to stop instance
            if command -v gcloud &> /dev/null; then
                ZONE=$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/zone" | awk -F/ '{print $NF}')
                INSTANCE_NAME=$(hostname)
                gcloud compute instances stop "$INSTANCE_NAME" --zone="$ZONE" --quiet
            else
                sudo poweroff
            fi
            exit 0
        fi
    fi

    sleep "$POLL_INTERVAL"
done
