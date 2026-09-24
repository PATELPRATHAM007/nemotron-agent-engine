"""
Direct Cloud-to-Drive Downloader for NVIDIA Nemotron 3 Ultra (BF16 ~1.12 TB)
=============================================================================
Run this script inside Google Colab (https://colab.research.google.com).
This downloads the 1.12 TB model directly from Hugging Face servers straight
into your 4TB Google Drive using Google's multi-gigabit datacenter backbone.

0 MB of your local Mac laptop storage is used.
"""

import os
import sys

# 1. Mount your 4TB Google Drive
try:
    from google.colab import drive
    print("Mounting your Google Drive...")
    drive.mount('/content/drive')
except ImportError:
    print("[WARNING] This script is optimized to run inside Google Colab.")

# 2. Enable High-Speed Multi-Threaded HF Transfer (Rust-accelerated)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# -------------------------------------------------------------------------
# PASTE YOUR HUGGING FACE TOKEN HERE (starts with hf_...)
# Get one free at: https://huggingface.co/settings/tokens (Read permission)
# -------------------------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN", "PASTE_YOUR_HF_TOKEN_HERE")

# Target storage directory inside your 4TB Google Drive
TARGET_DIR = "/content/drive/MyDrive/models/nemotron-3-ultra-bf16"
os.makedirs(TARGET_DIR, exist_ok=True)

MODEL_REPO = "nvidia/Nemotron-3-Ultra"

def main():
    if HF_TOKEN == "PASTE_YOUR_HF_TOKEN_HERE" or not HF_TOKEN.startswith("hf_"):
        print("\n[ERROR] Please insert a valid Hugging Face token in the HF_TOKEN variable.")
        print("1. Create a free account at https://huggingface.co")
        print("2. Generate a Read token at https://huggingface.co/settings/tokens")
        print("3. Accept the model license at https://huggingface.co/" + MODEL_REPO)
        return

    print("==================================================================")
    print("🚀 STARTING DIRECT CLOUD-TO-DRIVE DOWNLOAD")
    print(f"📦 Model: {MODEL_REPO} (BF16 ~1.12 TB)")
    print(f"📁 Destination: {TARGET_DIR}")
    print("⚡ Transfer: Rust hf_transfer multi-threaded cloud stream")
    print("==================================================================\n")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Installing huggingface_hub with hf_transfer...")
        os.system("pip install -q 'huggingface_hub[hf_transfer]'")
        from huggingface_hub import snapshot_download

    try:
        downloaded_path = snapshot_download(
            repo_id=MODEL_REPO,
            local_dir=TARGET_DIR,
            token=HF_TOKEN,
            max_workers=16,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onnx"]
        )
        print("\n" + "=" * 66)
        print("✅ DOWNLOAD COMPLETE!")
        print(f"All model shards are safely stored in: {downloaded_path}")
        print("Your Google Cloud VM can now stream directly from this path.")
        print("=" * 66)
    except Exception as e:
        print(f"\n[ERROR] Download encountered an issue: {e}")

if __name__ == "__main__":
    main()
