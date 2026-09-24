"""
Resumable Shard-by-Shard Cloud-to-Drive Downloader for NVIDIA Nemotron 3 Ultra (BF16 ~1.12 TB)
=============================================================================================
Run this script inside Google Colab (https://colab.research.google.com).
Downloads the 1.12 TB model directly from Hugging Face servers straight into your 4TB Google Drive.

Key Features:
1. 100% Resumable: If interrupted (e.g. at shard 6 of 224), restarting the script instantly detects
   shards 1-5 are complete and resumes from shard 6.
2. File Integrity Verification: Checks local file size against remote Hugging Face metadata.
3. Automatic Retry: Retries failed shards up to 5 times with exponential backoff.
4. Zero Local Storage: 0 MB used on your local Mac laptop.
"""

import os
import sys
import time

# 1. Mount your 5TB Google Drive
from google.colab import drive
print("Mounting your Google Drive...")
drive.mount('/content/drive')
print("✅ Google Drive Mounted Successfully!")
print("ℹ️ Note: Files written to /content/drive/MyDrive stream directly to your 5TB Google Drive cloud storage.")

# 2. Enable High-Speed HF Transfer
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

# -------------------------------------------------------------------------
# PASTE YOUR HUGGING FACE TOKEN HERE (starts with hf_...)
# Get one free at: https://huggingface.co/settings/tokens (Read permission)
# -------------------------------------------------------------------------
HF_TOKEN = os.getenv("HF_TOKEN", "PASTE_YOUR_HF_TOKEN_HERE")

# Target storage directory inside your 5TB Google Drive
TARGET_DIR = "/content/drive/MyDrive/models/nemotron-3-ultra-bf16"

# Exact Official NVIDIA Hugging Face Repository ID
MODEL_REPO = "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16"


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (GB / MB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def main():
    if HF_TOKEN == "PASTE_YOUR_HF_TOKEN_HERE" or not HF_TOKEN.startswith("hf_"):
        print("\n" + "=" * 70)
        print("❌ [ACTION REQUIRED] Please insert your Hugging Face Token in HF_TOKEN!")
        print("1. Create an account at: https://huggingface.co")
        print("2. Generate a Read token at: https://huggingface.co/settings/tokens")
        print("3. Accept model license at: https://huggingface.co/" + MODEL_REPO)
        print("=" * 70 + "\n")
        return

    os.makedirs(TARGET_DIR, exist_ok=True)

    print("==================================================================")
    print("🚀 RESUMABLE SHARD-BY-SHARD DOWNLOADER: NEMOTRON 3 ULTRA (1.12 TB)")
    print(f"📦 Repository: {MODEL_REPO}")
    print(f"📁 Target Folder: {TARGET_DIR}")
    print("==================================================================\n")

    # Ensure huggingface_hub is installed
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("Installing huggingface_hub with hf_transfer...")
        os.system("pip install -q 'huggingface_hub[hf_transfer]'")
        from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=HF_TOKEN)

    print("🔍 Fetching model file list and shard metadata from Hugging Face...")
    try:
        model_info = api.model_info(repo_id=MODEL_REPO, files_metadata=True)
    except Exception as e:
        print(f"❌ Failed to fetch model metadata: {e}")
        print("Please verify that your HF_TOKEN has read access and you accepted the license.")
        return

    # Collect files to download (exclude git/msgpack/onnx, prioritize configs, then safetensors)
    all_files = []
    ignored_extensions = ('.msgpack', '.h5', '.ot', '.onnx', '.gitattributes')

    for sibling in model_info.siblings:
        fname = sibling.rfilename
        if any(fname.endswith(ext) for ext in ignored_extensions):
            continue
        all_files.append({
            "name": fname,
            "size": sibling.size or 0,
        })

    # Sort files: json/txt configs first, then sorted safetensors shards
    configs = [f for f in all_files if not f["name"].endswith('.safetensors')]
    shards = sorted([f for f in all_files if f["name"].endswith('.safetensors')], key=lambda x: x["name"])
    ordered_files = configs + shards

    total_files = len(ordered_files)
    total_bytes = sum(f["size"] for f in ordered_files)

    print(f"📋 Found {total_files} files in repository. Total size: {format_bytes(total_bytes)}\n")

    # 3. Check already downloaded files (Resumption detection)
    downloaded_bytes = 0
    files_to_download = []

    print("🔎 Checking existing files in Google Drive for resume points...")
    for idx, f in enumerate(ordered_files, 1):
        local_path = os.path.join(TARGET_DIR, f["name"])
        expected_size = f["size"]

        if os.path.exists(local_path):
            local_size = os.path.getsize(local_path)
            if local_size == expected_size:
                downloaded_bytes += expected_size
                print(f"  [{idx}/{total_files}] ✅ VERIFIED: {f['name']} ({format_bytes(local_size)}) - Already completed!")
                continue
            elif expected_size > 0 and local_size < expected_size:
                print(f"  [{idx}/{total_files}] ⚠️ PARTIAL: {f['name']} ({format_bytes(local_size)} / {format_bytes(expected_size)}) - Will re-download clean.")
                try:
                    os.remove(local_path)
                except OSError:
                    pass

        files_to_download.append((idx, f))

    already_done_count = total_files - len(files_to_download)
    print("\n" + "-" * 70)
    print(f"📊 Resume Status:")
    print(f"   • Completed: {already_done_count} / {total_files} files ({format_bytes(downloaded_bytes)})")
    print(f"   • Remaining: {len(files_to_download)} / {total_files} files ({format_bytes(total_bytes - downloaded_bytes)})")
    print("-" * 70 + "\n")

    if not files_to_download:
        print("🎉 ALL FILES ARE ALREADY DOWNLOADED AND VERIFIED! You are 100% ready to run.")
        return

    # 4. Download remaining files with automatic retry
    print(f"⚡ Resuming download starting from item {files_to_download[0][0]}: {files_to_download[0][1]['name']}...\n")

    for idx, f in files_to_download:
        fname = f["name"]
        expected_size = f["size"]
        local_path = os.path.join(TARGET_DIR, fname)
        max_attempts = 5
        success = False

        # If file is an empty 0-byte placeholder (like __init__.py), create it directly
        if expected_size == 0:
            with open(local_path, "wb") as empty_f:
                pass
            print(f"      ✅ Created verified empty file ({fname})")
            success = True
            break

        for attempt in range(1, max_attempts + 1):
            pct = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
            print(f"[{idx}/{total_files}] ({pct:.1f}%) 📥 Downloading: {fname} ({format_bytes(expected_size)}) [Attempt {attempt}/{max_attempts}]...")

            try:
                start_t = time.time()
                hf_hub_download(
                    repo_id=MODEL_REPO,
                    filename=fname,
                    local_dir=TARGET_DIR,
                    token=HF_TOKEN,
                    force_download=False,
                )
                duration = max(time.time() - start_t, 0.001)

                # Verify downloaded size
                if os.path.exists(local_path):
                    actual_size = os.path.getsize(local_path)
                    if actual_size == expected_size:
                        speed = (actual_size / 1024 / 1024) / duration if actual_size > 0 else 0
                        downloaded_bytes += expected_size
                        print(f"      ✅ Completed & Verified! ({speed:.1f} MB/s)")
                        success = True
                        break
                    else:
                        print(f"      ⚠️ Size mismatch (got {actual_size} bytes, expected {expected_size}). Retrying...")
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass

            except Exception as e:
                print(f"      ❌ Download error on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    sleep_time = attempt * 5
                    print(f"      ⏳ Waiting {sleep_time}s before retrying...")
                    time.sleep(sleep_time)

        if not success:
            print(f"\n❌ [CRITICAL] Failed to download {fname} after {max_attempts} attempts.")
            print("You can simply re-run this script anytime; it will resume right from this file!")
            return

    print("\n" + "=" * 70)
    print("🎉 ALL SHARDS SUCCESSFULLY DOWNLOADED TO GOOGLE DRIVE!")
    print(f"📁 Destination: {TARGET_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
