#!/usr/bin/env bash
# ==============================================================================
# GCP Spot GPU Cluster Provisioner for NVIDIA Nemotron 3 Ultra
# ==============================================================================
# Uses your $300 GCP Credit with 60-91% Spot discounts to launch an 8-GPU node,
# attaches fast local NVMe SSDs, configures firewall rules, and starts the
# idle watchdog daemon to prevent burning credits when idle.
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration (Override via environment variables if desired)
# ------------------------------------------------------------------------------
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}"
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="${GCP_INSTANCE_NAME:-nemotron-spot-node}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-a2-ultragpu-8g}"  # 8x NVIDIA A100 80GB (640 GB VRAM)
ACCELERATOR_TYPE="${GCP_ACCELERATOR:-nvidia-a100-80gb}"
ACCELERATOR_COUNT="${GCP_ACCELERATOR_COUNT:-8}"
BOOT_DISK_SIZE="${GCP_BOOT_DISK_SIZE:-200GB}"
IMAGE_FAMILY="common-cu121-debian-11"
IMAGE_PROJECT="deeplearning-platform-release"

echo "=================================================================="
echo "⚡ GCP SPOT GPU CLUSTER LAUNCHER: NEMOTRON 3 ULTRA"
echo "=================================================================="
echo "Project ID:      $PROJECT_ID"
echo "Zone:            $ZONE"
echo "Instance:        $INSTANCE_NAME"
echo "Machine Type:    $MACHINE_TYPE"
echo "GPUs:            $ACCELERATOR_COUNT x $ACCELERATOR_TYPE"
echo "Pricing Model:   SPOT (Max Credit Longevity - saves up to 90%)"
echo "=================================================================="

# 1. Verify Project ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP Project ID is not set. Run: gcloud config set project <YOUR_PROJECT_ID>"
    exit 1
fi

# 2. Ensure Google Compute Engine API is enabled
echo "[1/4] Ensuring Compute Engine API is enabled..."
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"

# 3. Create Firewall Rule for vLLM API (Port 8000)
echo "[2/4] Configuring Firewall Rule for port 8000..."
if ! gcloud compute firewall-rules describe allow-vllm-8000 --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute firewall-rules create allow-vllm-8000 \
        --project="$PROJECT_ID" \
        --direction=INGRESS \
        --priority=1000 \
        --network=default \
        --action=ALLOW \
        --rules=tcp:8000 \
        --source-ranges=0.0.0.0/0 \
        --target-tags=vllm-server
    echo "✅ Firewall rule 'allow-vllm-8000' created."
else
    echo "✅ Firewall rule 'allow-vllm-8000' already exists."
fi

# 4. Provision Spot GPU Instance
echo "[3/4] Provisioning Spot GPU Instance on Google Cloud..."
gcloud compute instances create "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --accelerator="type=$ACCELERATOR_TYPE,count=$ACCELERATOR_COUNT" \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --boot-disk-size="$BOOT_DISK_SIZE" \
    --boot-disk-type="pd-balanced" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --maintenance-policy=TERMINATE \
    --tags=vllm-server \
    --local-ssd=interface=NVME \
    --local-ssd=interface=NVME \
    --local-ssd=interface=NVME \
    --local-ssd=interface=NVME \
    --metadata="install-nvidia-driver=True"

# 5. Retrieve External IP
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=================================================================="
echo "🎉 SPOT GPU INSTANCE LAUNCHED SUCCESSFULLY!"
echo "=================================================================="
echo "🖥️ Instance Name:  $INSTANCE_NAME"
echo "🌐 External IP:    $EXTERNAL_IP"
echo "🔗 vLLM Endpoint:  http://$EXTERNAL_IP:8000/v1"
echo ""
echo "👉 Step 1: Connect to your instance:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo ""
echo "👉 Step 2: Stream 1.12 TB model from Google Drive to local NVMe:"
echo "   bash infra/setup_gdrive_rclone.sh"
echo ""
echo "👉 Step 3: Start the Idle Watchdog (preserves your $300 credit):"
echo "   nohup bash infra/idle-watchdog.sh > /dev/null 2>&1 &"
echo ""
echo "👉 Step 4: Launch vLLM Serving Engine:"
echo "   bash infra/start_vllm_nemotron.sh"
echo ""
echo "👉 Step 5: In your local nemotron-agent-engine .env, set:"
echo "   NEMOTRON_API_BASE=http://$EXTERNAL_IP:8000/v1"
echo "=================================================================="
