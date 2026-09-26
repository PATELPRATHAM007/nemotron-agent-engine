#!/usr/bin/env bash
# ==============================================================================
# vLLM High-Performance Serving Script for NVIDIA Nemotron 3 Ultra (550B LatentMoE)
# ==============================================================================
# Serves the model locally on the GCP GPU instance with an OpenAI-compatible API
# endpoint for the Nemotron Agent Engine backend.
#
# Default endpoint: http://localhost:8000/v1
# ==============================================================================

set -euo pipefail

MODEL_DIR="${MODEL_PATH:-/mnt/fast-nvme/nemotron-bf16}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-8}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.95}"
DTYPE="${DTYPE:-bfloat16}"

echo "=================================================================="
echo "🚀 STARTING vLLM OPENAI API SERVER FOR NEMOTRON 3 ULTRA"
echo "=================================================================="
echo "📁 Model Path:               $MODEL_DIR"
echo "🌐 API Endpoint:            http://$HOST:$PORT/v1"
echo "🧵 Tensor Parallel Size:    $TENSOR_PARALLEL_SIZE GPUs"
echo "📏 Max Context Length:      $MAX_MODEL_LEN tokens"
echo "💾 GPU Memory Utilization:  $GPU_MEMORY_UTILIZATION"
echo "🔢 Precision / Dtype:       $DTYPE"
echo "=================================================================="

# 1. Verify model files exist
if [ ! -d "$MODEL_DIR" ] || [ ! -f "$MODEL_DIR/config.json" ]; then
    echo "❌ Error: Model directory $MODEL_DIR is missing or config.json not found."
    echo "   Ensure you have completed streaming from Google Drive via infra/setup_gdrive_rclone.sh!"
    exit 1
fi

# 2. Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    NUM_GPUS=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    echo "✅ Detected $NUM_GPUS NVIDIA GPUs:"
    nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader
    if [ "$NUM_GPUS" -lt "$TENSOR_PARALLEL_SIZE" ]; then
        echo "⚠️ Warning: Detected $NUM_GPUS GPUs but TENSOR_PARALLEL_SIZE is set to $TENSOR_PARALLEL_SIZE."
        echo "   Adjusting TENSOR_PARALLEL_SIZE to $NUM_GPUS."
        TENSOR_PARALLEL_SIZE="$NUM_GPUS"
    fi
else
    echo "❌ Error: nvidia-smi not found. Ensure NVIDIA drivers and CUDA are installed."
    exit 1
fi

# 3. Launch vLLM OpenAI API Server
echo ""
echo "⚡ Launching vLLM Engine..."
exec python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_DIR" \
    --host "$HOST" \
    --port "$PORT" \
    --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --dtype "$DTYPE" \
    --trust-remote-code \
    --enforce-eager \
    --served-model-name "nvidia/Nemotron-3-Ultra"
