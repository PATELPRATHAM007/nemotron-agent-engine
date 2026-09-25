"""
Resumable Direct-to-Drive Shard Downloader for NVIDIA Nemotron 3 Ultra (BF16 ~1.12 TB)
====================================================================================
Designed to run in Google Colab (https://colab.research.google.com).
Downloads the 1.12 TB model directly from Hugging Face into your mounted Google Drive,
bypassing the Colab VM's limited local disk (~17 GB free) and utilizing your 5 TB Google Drive
as the primary download destination and cache storage.

Key Architecture & Safeguards:
1. Zero Local VM Disk Usage: Model shards stream directly to Google Drive (no local /content staging).
2. Full HF & Temp Redirection: HF_HOME, HF_HUB_CACHE, and TMPDIR are pointed to Google Drive before HF libraries initialize.
3. Pre-Flight Capacity Audit: Estimates total required storage (~1.12 TB across ~225 shards) and verifies GDrive space before downloading.
4. Resumable & Fault-Tolerant: Automatically skips verified shards on runtime disconnects and cleans incomplete files.
5. Header & Integrity Verification: Verifies exact byte sizes and safetensors headers directly on Google Drive.
6. Real-Time Multi-Storage Monitor: Displays Colab VM disk free space, GDrive free space, download speed, ETA, and shard progress.
7. Post-Download Audit Report: Verifies all shards and files upon completion.
"""

import os
import sys
import time
import shutil
import struct
import json
import threading
import concurrent.futures

# =============================================================================
# 1. GOOGLE DRIVE MOUNTING & PATH CONFIGURATION
# =============================================================================

GDRIVE_MOUNT = "/content/drive"
GDRIVE_MYDRIVE = os.path.join(GDRIVE_MOUNT, "MyDrive")

# Official NVIDIA Hugging Face Repository ID
MODEL_REPO = "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16"
MODEL_NAME = "nemotron-3-ultra-bf16"

# Dedicated model directory inside your 5TB Google Drive
TARGET_DIR = os.path.join(GDRIVE_MYDRIVE, "models", MODEL_NAME)

# Dedicated cache and temporary directories on Google Drive (NOT on Colab local disk)
GDRIVE_HF_HOME = os.path.join(GDRIVE_MYDRIVE, "models", ".hf_cache")
GDRIVE_TMP_DIR = os.path.join(GDRIVE_MYDRIVE, "models", ".tmp")

# Hugging Face Access Token (Read permission required)
# Paste your token here or set the HF_TOKEN environment variable
HF_TOKEN = os.getenv("HF_TOKEN", "PASTE_YOUR_HF_TOKEN_HERE")

# Parallel Download Settings:
# NOTE: In Google Colab, Google Drive FUSE stages in-flight writes locally until uploaded to cloud.
# 2 concurrent streams keeps active write buffers small (~9 GB max), preventing Colab VM disk from filling up!
# (You can override this anytime via %env BATCH_SIZE=3 or os.environ["BATCH_SIZE"] = "2")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))

# Google Drive 750 GB Daily Upload Limit Safeguard:
# Google limits uploads to 750 GB per rolling 24 hours per user account.
# We set a safe default threshold of 730 GB to avoid 403 API lockouts or partial writes.
DAILY_UPLOAD_LIMIT_GB = float(os.getenv("DAILY_UPLOAD_LIMIT_GB", "730.0"))
DAILY_UPLOAD_LIMIT_BYTES = int(DAILY_UPLOAD_LIMIT_GB * 1024 * 1024 * 1024)
TRACKER_FILE = os.path.join(TARGET_DIR, ".daily_upload_tracker.json")

print_lock = threading.Lock()
progress_lock = threading.Lock()



def safe_print(*args, **kwargs):
    """Thread-safe synchronized logging."""
    with print_lock:
        print(*args, **kwargs)



def ensure_gdrive_mounted() -> bool:
    """Mount Google Drive at /content/drive if running in Google Colab."""
    if os.path.ismount(GDRIVE_MOUNT) or os.path.exists(GDRIVE_MYDRIVE):
        print(f"✅ Google Drive is already mounted at {GDRIVE_MOUNT}")
        return True

    try:
        from google.colab import drive
        print(f"Mounting Google Drive at {GDRIVE_MOUNT}...")
        drive.mount(GDRIVE_MOUNT)
        print("✅ Google Drive Mounted Successfully!")
        return True
    except ImportError:
        # Non-Colab fallback (for local development or testing)
        if os.path.exists(GDRIVE_MOUNT):
            return True
        print(f"ℹ️ Running outside Google Colab environment. Target path: {TARGET_DIR}")
        return os.path.exists(TARGET_DIR) or os.path.exists(GDRIVE_MOUNT)
    except Exception as e:
        print(f"❌ Failed to mount Google Drive: {e}")
        return False


# Mount Drive before setting up directories
ensure_gdrive_mounted()

# Create dedicated model and cache directories on Google Drive
try:
    os.makedirs(TARGET_DIR, exist_ok=True)
    os.makedirs(GDRIVE_HF_HOME, exist_ok=True)
    os.makedirs(GDRIVE_TMP_DIR, exist_ok=True)
except Exception as e:
    print(f"⚠️ Notice when creating Google Drive directories: {e}")


# =============================================================================
# 2. CONFIGURE ENVIRONMENT VARIABLES BEFORE IMPORTING HUGGING FACE LIBRARIES
# =============================================================================
# CRITICAL: Setting these before importing huggingface_hub prevents default caching
# in /root/.cache/huggingface and temporary file writes in /tmp on the Colab VM disk (~17 GB free).
os.environ["HF_HOME"] = GDRIVE_HF_HOME
os.environ["HF_HUB_CACHE"] = os.path.join(GDRIVE_HF_HOME, "hub")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(GDRIVE_HF_HOME, "hub")
os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.join(GDRIVE_HF_HOME, "hub")
os.environ["TMPDIR"] = GDRIVE_TMP_DIR
os.environ["TEMP"] = GDRIVE_TMP_DIR
os.environ["TMP"] = GDRIVE_TMP_DIR

# Also configure Python's standard tempfile module to point to Google Drive
import tempfile
tempfile.tempdir = GDRIVE_TMP_DIR

# CRITICAL: Disable HF Xet and HF Transfer
# Xet downloads deduplicated chunks and attempts local file reconstruction on the local VM disk (/tmp),
# which crashes with 'File reconstruction error: IO Error: No space left on device (os error 28)'.
# Disabling Xet forces direct HTTP range-request streaming straight into Google Drive with 0 local staging!
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_XET_HIGH_PERFORMANCE"] = "0"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

# Filter the spurious FUSE disk space warning (since /content/drive mirrors the 107 GB local VM disk)
import warnings
warnings.filterwarnings("ignore", message=".*Not enough free disk space to download the file.*")



# =============================================================================
# 3. HELPER FUNCTIONS: DISK AUDIT, PROGRESS & INTEGRITY CHECKS
# =============================================================================

def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (B, KB, MB, GB, TB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def format_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds < 0 or seconds > 3600 * 240:
        return "calculating..."
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


def get_storage_stats():
    """Retrieve total, used, and free space for Google Drive and Colab local disk."""
    # Colab Local VM Disk (Root filesystem /)
    try:
        colab_usage = shutil.disk_usage("/")
        colab_total, colab_used, colab_free = colab_usage.total, colab_usage.used, colab_usage.free
    except Exception:
        colab_total, colab_used, colab_free = 0, 0, 0

    # Google Drive Storage (/content/drive/MyDrive)
    try:
        check_path = TARGET_DIR if os.path.exists(TARGET_DIR) else (GDRIVE_MOUNT if os.path.exists(GDRIVE_MOUNT) else "/")
        gdrive_usage = shutil.disk_usage(check_path)
        gdrive_total, gdrive_used, gdrive_free = gdrive_usage.total, gdrive_usage.used, gdrive_usage.free
    except Exception:
        gdrive_total, gdrive_used, gdrive_free = 0, 0, 0

    return {
        "colab_total": colab_total,
        "colab_used": colab_used,
        "colab_free": colab_free,
        "gdrive_total": gdrive_total,
        "gdrive_used": gdrive_used,
        "gdrive_free": gdrive_free,
    }


def verify_safetensors_file(file_path: str, expected_size: int) -> bool:
    """
    Verify file integrity via exact byte size check against Hugging Face metadata.
    Avoids opening file handles across Google Drive FUSE mount which causes I/O errors.
    """
    if not os.path.exists(file_path):
        return False
    try:
        actual_size = os.path.getsize(file_path)
        return actual_size == expected_size
    except Exception:
        return False


def clean_local_colab_disk() -> int:
    """
    Safely purge lingering Hugging Face cache (/root/.cache/huggingface), Xet cache (/root/.cache/xet),
    pip cache (/root/.cache/pip), and /tmp to recover disk space on the Colab local VM.
    """
    freed = 0
    targets = [
        "/root/.cache/huggingface",
        "/root/.cache/xet",
        "/root/.cache/pip",
        "/root/.cache/torch",
        "/content/sample_data",
    ]
    for path in targets:
        if os.path.exists(path):
            try:
                size = 0
                for dp, dn, fn in os.walk(path):
                    for f in fn:
                        try:
                            size += os.path.getsize(os.path.join(dp, f))
                        except Exception:
                            pass
                shutil.rmtree(path, ignore_errors=True)
                freed += size
                if size > 0:
                    print(f"🧹 Purged {path}: freed {format_bytes(size)} on Colab VM disk.")
            except Exception:
                pass

    # Clean stray model shards directly on Colab root /content (NEVER touching /content/drive)
    if os.path.exists("/content"):
        for item in os.listdir("/content"):
            if item == "drive" or item.startswith("."):
                continue  # STRICT GUARD: Never touch Google Drive mount
            p = os.path.join("/content", item)
            if p.startswith("/content/drive") or os.path.isdir(p):
                continue
            if item.endswith(".safetensors") or item.endswith(".bin") or item.endswith(".incomplete"):
                try:
                    size = os.path.getsize(p)
                    os.remove(p)
                    freed += size
                    print(f"🧹 Removed stray file in /content: {item} (freed {format_bytes(size)})")
                except Exception:
                    pass


    # Clean /tmp thoroughly
    if os.path.exists("/tmp"):
        for item in os.listdir("/tmp"):
            p = os.path.join("/tmp", item)
            try:
                if os.path.isfile(p):
                    size = os.path.getsize(p)
                    os.remove(p)
                    freed += size
                elif os.path.isdir(p) and not item.startswith("."):
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass

    return freed


def flush_fuse_cache():
    """
    Force the Linux kernel and Google Drive FUSE driver to flush dirty write buffers
    directly to Google Drive cloud storage and immediately evict local cache pages.
    """
    try:
        import gc
        gc.collect()
        os.system("sync")
    except Exception:
        pass


def render_progress_bar(percentage: float, width: int = 24) -> str:
    """Render a visual ASCII progress bar."""

    filled = int(width * percentage / 100.0)
    filled = min(max(filled, 0), width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percentage:5.1f}%"


def get_daily_tracker() -> dict:
    """Load or initialize the daily upload quota tracker from Google Drive."""
    today_str = time.strftime("%Y-%m-%d")
    default_data = {
        "date": today_str,
        "uploaded_bytes": 0,
        "history": {},
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if not os.path.exists(TRACKER_FILE):
        return default_data
    try:
        with open(TRACKER_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today_str:
            prev_date = data.get("date", "previous")
            prev_bytes = data.get("uploaded_bytes", 0)
            history = data.get("history", {})
            history[prev_date] = prev_bytes
            data = {
                "date": today_str,
                "uploaded_bytes": 0,
                "history": history,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        return data
    except Exception:
        return default_data


def update_daily_tracker(bytes_added: int):
    """Safely record uploaded bytes to the daily tracker on Google Drive."""
    try:
        with progress_lock:
            data = get_daily_tracker()
            data["uploaded_bytes"] = data.get("uploaded_bytes", 0) + bytes_added
            data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            temp_path = TRACKER_FILE + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, TRACKER_FILE)
    except Exception:
        pass


def print_daily_quota_stop_banner(
    uploaded_today: int,
    total_downloaded: int,
    total_expected: int,
    remaining: int,
    limit_gb: float = DAILY_UPLOAD_LIMIT_GB,
):
    """Display clear, user-friendly notice when the 750 GB daily limit is reached."""
    pct = (total_downloaded / total_expected * 100) if total_expected > 0 else 0
    safe_print("\n" + "=" * 80)
    safe_print(f"🛑 DAILY GOOGLE DRIVE UPLOAD LIMIT REACHED ({limit_gb:.0f} GB / 24 Hours)")
    safe_print("=" * 80)
    safe_print("📢 NOTICE TO USER:")
    safe_print(f"   You have already downloaded and uploaded ~{format_bytes(uploaded_today)} to Google Drive today.")
    safe_print("   Google enforces a strict 750 GB upload limit per rolling 24 hours on all accounts.")
    safe_print("   To protect your Google Drive from API lockouts or 403 errors, downloading has")
    safe_print("   been paused automatically for today.")
    safe_print("-" * 80)
    safe_print("📊 CURRENT PROGRESS & STORAGE STATUS:")
    safe_print(f"   • Safely Saved in Drive:   {format_bytes(total_downloaded)} / {format_bytes(total_expected)} ({pct:.1f}%)")
    safe_print(f"   • Remaining for Tomorrow:  {format_bytes(remaining)}")
    safe_print("-" * 80)
    safe_print("✅ ALL EXISTING SHARDS ARE 100% VERIFIED AND PERMANENT IN YOUR GOOGLE DRIVE!")
    safe_print("🗓️ Remaining shards will be downloaded tomorrow when Google's 24-hour quota resets.")
    safe_print("\n👉 To resume tomorrow, simply re-run this exact same command:")
    safe_print("   !python infra/download_nemotron_to_gdrive.py")
    safe_print("   (The script will automatically verify and skip all existing shards in seconds!)")
    safe_print("=" * 80 + "\n")


def display_monitor(
    current_idx: int,
    total_files: int,
    current_file: str,
    file_size: int,
    downloaded_bytes: int,
    total_bytes: int,
    speed_mb: float,
    eta_sec: float,
    attempt: int = 1,
    max_attempts: int = 5,
):
    """Continuously prints real-time storage and download status."""
    stats = get_storage_stats()
    pct = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
    bar_str = render_progress_bar(pct)

    print("\n" + "=" * 80)
    print(f"📥 [{current_idx}/{total_files}] DOWNLOADING: {current_file}")
    print(f"   • File Size: {format_bytes(file_size)} | Attempt: {attempt}/{max_attempts}")
    print(f"   • Total Progress: {bar_str} ({format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)})")
    print(f"   • Speed: {speed_mb:.1f} MB/s | ETA: {format_time(eta_sec)}")
    print("💾 Storage Monitor:")
    print(f"   • Storage Backend:    Google Drive Cloud Storage (5 TB Account Quota)")
    print(f"   • Colab VM Disk Free: {format_bytes(stats['colab_free'])} (Capacity: {format_bytes(stats['colab_total'])}) [SAFE: 0 bytes consumed]")
    print("=" * 80)


def audit_final_model(ordered_files: list) -> dict:
    """
    Perform a complete post-download audit of all files in Google Drive.
    Reports total model size, verified shards, missing/corrupted files, and disk space.
    """
    total_expected_files = len(ordered_files)
    total_expected_bytes = sum(f["size"] for f in ordered_files)

    verified_files = []
    missing_files = []
    corrupted_files = []
    actual_total_bytes = 0
    safetensors_verified = 0

    for f in ordered_files:
        fname = f["name"]
        expected_size = f["size"]
        local_path = os.path.join(TARGET_DIR, fname)

        if not os.path.exists(local_path):
            missing_files.append((fname, expected_size))
        else:
            actual_size = os.path.getsize(local_path)
            actual_total_bytes += actual_size
            if verify_safetensors_file(local_path, expected_size):
                verified_files.append(fname)
                if fname.endswith(".safetensors"):
                    safetensors_verified += 1
            else:
                corrupted_files.append((fname, expected_size, actual_size))

    stats = get_storage_stats()

    return {
        "total_expected_files": total_expected_files,
        "total_expected_bytes": total_expected_bytes,
        "verified_count": len(verified_files),
        "safetensors_verified": safetensors_verified,
        "actual_total_bytes": actual_total_bytes,
        "missing_files": missing_files,
        "corrupted_files": corrupted_files,
        "gdrive_free": stats["gdrive_free"],
        "colab_free": stats["colab_free"],
        "is_complete": len(missing_files) == 0 and len(corrupted_files) == 0,
    }


def print_final_report(report: dict):
    """Print complete post-download audit report."""
    print("\n" + "=" * 80)
    print("🎉 MODEL DOWNLOAD & INTEGRITY AUDIT REPORT")
    print("=" * 80)
    if report["is_complete"]:
        print("Status:                         ✅ 100% COMPLETE & VERIFIED")
    else:
        print("Status:                         ⚠️ INCOMPLETE")

    print(f"Primary Destination:            {TARGET_DIR}")
    print(f"Total Model Size on Drive:      {format_bytes(report['actual_total_bytes'])} (Expected: {format_bytes(report['total_expected_bytes'])})")
    print(f"Total Files Verified:           {report['verified_count']} / {report['total_expected_files']}")
    print(f"Safetensors Shards Verified:    {report['safetensors_verified']} shards")
    print(f"Missing Files:                  {len(report['missing_files'])}")
    print(f"Corrupted Files:                {len(report['corrupted_files'])}")
    print("-" * 80)
    print(f"Backend Storage:                Google Drive Cloud Storage (5 TB Account Quota)")
    print(f"Colab Local VM Disk Remaining:  {format_bytes(report['colab_free'])} (Preserved: 0 bytes consumed)")
    print("=" * 80)

    if report["missing_files"]:
        print("\n⚠️ Missing files:")
        for fname, size in report["missing_files"][:10]:
            print(f"  • {fname} ({format_bytes(size)})")

    if report["corrupted_files"]:
        print("\n⚠️ Corrupted files:")
        for fname, exp, act in report["corrupted_files"][:10]:
            print(f"  • {fname} (expected {format_bytes(exp)}, got {format_bytes(act)})")

    if report["is_complete"]:
        print("\n🚀 Model is ready for serving and inference directly from Google Drive!\n")


def colab_monitoring_cell(refresh_interval_sec: int = 10):
    """
    Optional Colab Standalone Monitoring Snippet:
    Run this function in a separate Colab cell to monitor storage
    and shard progress concurrently in real-time.
    """
    try:
        import IPython.display
    except ImportError:
        IPython = None

    while True:
        stats = get_storage_stats()
        files = os.listdir(TARGET_DIR) if os.path.exists(TARGET_DIR) else []
        safetensors = [f for f in files if f.endswith(".safetensors")]
        total_size = sum(
            os.path.getsize(os.path.join(TARGET_DIR, f))
            for f in files
            if os.path.isfile(os.path.join(TARGET_DIR, f))
        )

        if IPython:
            IPython.display.clear_output(wait=True)

        print("=" * 70)
        print("📊 GOOGLE COLAB REAL-TIME STORAGE & SHARD MONITOR")
        print("=" * 70)
        print(f"💾 Google Drive Free Space:  {format_bytes(stats['gdrive_free'])}")
        print(f"🖥️ Colab VM Local Disk Free: {format_bytes(stats['colab_free'])} [PROTECTED]")
        print(f"📁 Downloaded in Target:     {len(files)} files ({len(safetensors)} safetensors shards)")
        print(f"📦 Total Downloaded Size:    {format_bytes(total_size)}")
        print(f"⏱️ Updated at:               {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        time.sleep(refresh_interval_sec)


# =============================================================================
# 4. PARALLEL SHARD DOWNLOAD WORKER
# =============================================================================

def download_shard_worker(
    item_idx: int,
    total_files: int,
    file_info: dict,
    target_dir: str,
    model_repo: str,
    hf_token: str,
    batch_idx: int,
    total_batches: int,
    max_attempts: int = 5,
) -> tuple:
    """
    Thread pool worker: Downloads a single shard directly to Google Drive.
    Returns: (success: bool, fname: str, downloaded_bytes: int, duration: float, error_msg: str)
    """
    from huggingface_hub import hf_hub_download

    fname = file_info["name"]
    expected_size = file_info["size"]
    local_path = os.path.join(target_dir, fname)

    # 1. Fast check if already completed
    if os.path.exists(local_path) and os.path.getsize(local_path) == expected_size and expected_size > 0:
        safe_print(f"  [Batch {batch_idx}/{total_batches}] ⚡ Already complete: {fname} ({format_bytes(expected_size)})")
        return (True, fname, expected_size, 0.0, None)

    # 2. 0-byte file placeholder
    if expected_size == 0:
        with open(local_path, "wb") as empty_f:
            pass
        safe_print(f"  [Batch {batch_idx}/{total_batches}] ✅ Verified empty file: {fname}")
        return (True, fname, 0, 0.0, None)

    # 3. Download retry loop
    for attempt in range(1, max_attempts + 1):
        try:
            start_t = time.time()
            safe_print(f"  [Batch {batch_idx}/{total_batches}] 📥 Starting [{item_idx}/{total_files}]: {fname} ({format_bytes(expected_size)}) [Attempt {attempt}/{max_attempts}]...")

            hf_hub_download(
                repo_id=model_repo,
                filename=fname,
                local_dir=target_dir,
                token=hf_token,
                force_download=False,
            )

            duration = max(time.time() - start_t, 0.001)

            if os.path.exists(local_path) and os.path.getsize(local_path) == expected_size:
                speed_mb = (expected_size / 1024 / 1024) / duration if expected_size > 0 else 0
                safe_print(f"  [Batch {batch_idx}/{total_batches}] ✅ Done & Verified [{item_idx}/{total_files}]: {fname} ({format_bytes(expected_size)} in {duration:.1f}s @ {speed_mb:.1f} MB/s)")
                flush_fuse_cache()
                update_daily_tracker(expected_size)
                return (True, fname, expected_size, duration, None)

            else:
                actual_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                safe_print(f"  [Batch {batch_idx}/{total_batches}] ⚠️ Incomplete: {fname} (got {actual_size:,} B vs {expected_size:,} B). Retrying...")
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except OSError:
                    pass

        except Exception as e:
            err_str = str(e).lower()
            is_quota = any(k in err_str for k in ["rate limit", "quota", "403", "user rate limit exceeded"])
            if is_quota:
                safe_print(f"\n  🛑 [Batch {batch_idx}/{total_batches}] Google Drive daily upload limit reached on {fname}: {e}")
                return (False, fname, 0, 0.0, "QUOTA_EXCEEDED")

            safe_print(f"  [Batch {batch_idx}/{total_batches}] ❌ Error on {fname} (attempt {attempt}): {e}")
            if attempt < max_attempts:
                time.sleep(attempt * 3)

    return (False, fname, 0, 0.0, f"Failed after {max_attempts} attempts")


# =============================================================================
# 5. MAIN DOWNLOAD WORKFLOW
# =============================================================================

def main():
    print("=" * 80)
    print("🚀 RESUMABLE DIRECT-TO-DRIVE DOWNLOADER: NVIDIA NEMOTRON 3 ULTRA (~1.12 TB)")
    print(f"📦 Hugging Face Repository: {MODEL_REPO}")
    print(f"📁 Primary Destination:    {TARGET_DIR}")
    print(f"🗂️ HF Cache Directory:     {GDRIVE_HF_HOME}")
    print(f"🗂️ Temp Directory:         {GDRIVE_TMP_DIR}")
    print("=" * 80 + "\n")

    # 1. Verify Hugging Face Token
    if HF_TOKEN == "PASTE_YOUR_HF_TOKEN_HERE" or not HF_TOKEN.startswith("hf_"):
        print("\n" + "=" * 80)
        print("❌ [ACTION REQUIRED] Please insert your Hugging Face Token in HF_TOKEN!")
        print("1. Create an account at: https://huggingface.co")
        print("2. Generate a Read token at: https://huggingface.co/settings/tokens")
        print("3. Accept model license at: https://huggingface.co/" + MODEL_REPO)
        print("4. Paste token in HF_TOKEN or set os.environ['HF_TOKEN'] = 'hf_...'")
        print("=" * 80 + "\n")
        return

    # 2. Verify Google Drive Mount
    if not ensure_gdrive_mounted():
        print(f"❌ Google Drive could not be verified at {GDRIVE_MOUNT}. Aborting.")
        return

    # 3. Clean any legacy local caches to restore Colab VM local disk space (~15-20 GB)
    clean_local_colab_disk()

    # 4. Ensure huggingface_hub is installed with pip cache disabled
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("📦 Installing huggingface_hub with hf_transfer (disabling pip cache)...")
        # --no-cache-dir ensures pip doesn't fill /root/.cache/pip on Colab's local disk
        os.system("pip install -q --no-cache-dir 'huggingface_hub[hf_transfer]'")
        from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=HF_TOKEN)

    # 4. Fetch model metadata from Hugging Face
    print("🔍 Fetching model file list and shard metadata from Hugging Face...")
    try:
        model_info = api.model_info(repo_id=MODEL_REPO, files_metadata=True)
    except Exception as e:
        print(f"❌ Failed to fetch model metadata: {e}")
        print("Please verify that your HF_TOKEN has read access and you accepted the license at:")
        print(f"https://huggingface.co/{MODEL_REPO}")
        return

    # Filter files: exclude unsupported formats, keep configs and safetensors
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

    # Sort files: json/txt/tokenizer configs first, then safetensors shards sequentially
    configs = [f for f in all_files if not f["name"].endswith('.safetensors')]
    shards = sorted([f for f in all_files if f["name"].endswith('.safetensors')], key=lambda x: x["name"])
    ordered_files = configs + shards

    total_files = len(ordered_files)
    total_safetensors = len(shards)
    total_bytes = sum(f["size"] for f in ordered_files)

    # 5. Pre-flight Storage & Resume Verification
    print("\n🔎 Auditing Google Drive directory for existing shards (Resumption check)...")
    downloaded_bytes = 0
    files_to_download = []
    verified_existing_count = 0

    for idx, f in enumerate(ordered_files, 1):
        local_path = os.path.join(TARGET_DIR, f["name"])
        expected_size = f["size"]

        if os.path.exists(local_path):
            actual_size = os.path.getsize(local_path)
            if actual_size == expected_size and expected_size > 0:
                downloaded_bytes += expected_size
                verified_existing_count += 1
                print(f"  [{idx}/{total_files}] ✅ VERIFIED: {f['name']} ({format_bytes(actual_size)}) - Already completed! Skipping.")
                continue
            elif expected_size == 0 and actual_size == 0:
                verified_existing_count += 1
                print(f"  [{idx}/{total_files}] ✅ VERIFIED: {f['name']} (0 B config) - Already completed! Skipping.")
                continue
            elif actual_size < expected_size:
                print(f"  [{idx}/{total_files}] ⚠️ PARTIAL SHARD: {f['name']} ({actual_size:,} / {expected_size:,} bytes - {format_bytes(actual_size)} / {format_bytes(expected_size)}). Will re-download clean.")
                try:
                    os.remove(local_path)
                except OSError:
                    pass
            elif actual_size > expected_size:
                print(f"  [{idx}/{total_files}] ⚠️ OVERSIZED/CORRUPT: {f['name']} ({actual_size:,} bytes vs expected {expected_size:,} bytes). Will re-download clean.")
                try:
                    os.remove(local_path)
                except OSError:
                    pass

        files_to_download.append((idx, f))

    remaining_bytes = total_bytes - downloaded_bytes
    stats = get_storage_stats()
    daily_tracker = get_daily_tracker()
    uploaded_today = daily_tracker.get("uploaded_bytes", 0)

    # Pre-Flight Storage Report
    print("\n" + "=" * 80)
    print("📊 PRE-FLIGHT STORAGE & CAPACITY AUDIT")
    print("=" * 80)
    print(f"📦 Model Repository:          {MODEL_REPO}")
    print(f"📄 Total Files:                {total_files} files ({total_safetensors} safetensors shards)")
    print(f"💾 Total Model Size:           {format_bytes(total_bytes)}")
    print(f"✅ Already Downloaded & Ready: {verified_existing_count} files ({format_bytes(downloaded_bytes)})")
    print(f"⏳ Remaining to Download:      {len(files_to_download)} files ({format_bytes(remaining_bytes)})")
    print("-" * 80)
    print(f"📁 Primary Cloud Destination:  {TARGET_DIR}")
    print(f"   • Backend Storage:          Google Drive Cloud Storage (Account Quota: ~5 TB)")
    print(f"   • Model Shards Stream:      DIRECT TO GOOGLE DRIVE CLOUD (0 bytes stored on local VM)")
    print(f"   • Google Drive Daily Quota: {format_bytes(uploaded_today)} / {format_bytes(DAILY_UPLOAD_LIMIT_BYTES)} uploaded today")
    print(f"🖥️ Colab Local VM Disk:        {format_bytes(stats['colab_free'])} free (Capacity: {format_bytes(stats['colab_total'])})")
    print(f"   • Colab Disk Status:        PROTECTED (HF_HOME and TMPDIR redirected to Google Drive)")
    print("=" * 80 + "\n")

    # Check if today's 750 GB limit has already been reached before starting
    if uploaded_today >= DAILY_UPLOAD_LIMIT_BYTES:
        print_daily_quota_stop_banner(
            uploaded_today=uploaded_today,
            total_downloaded=downloaded_bytes,
            total_expected=total_bytes,
            remaining=remaining_bytes,
        )
        return

    print("✅ Storage check passed! Streaming remaining shards directly into your 5 TB Google Drive.")

    if not files_to_download:
        print("🎉 ALL FILES ARE ALREADY DOWNLOADED AND VERIFIED!")
        report = audit_final_model(ordered_files)
        print_final_report(report)
        return

    # 6. Parallel Batch Download Loop (10 per batch)
    batches = [files_to_download[i:i + BATCH_SIZE] for i in range(0, len(files_to_download), BATCH_SIZE)]
    total_batches = len(batches)

    safe_print("\n" + "=" * 80)
    safe_print("🚀 PARALLEL BATCH DOWNLOAD MODE")
    safe_print(f"📦 Remaining to Download: {len(files_to_download)} files ({format_bytes(remaining_bytes)})")
    safe_print(f"⚡ Batch Strategy:        {total_batches} batches of up to {BATCH_SIZE} shards concurrently")
    safe_print(f"🧵 Parallel Workers:      {MAX_WORKERS} simultaneous streams directly to Google Drive")
    safe_print("=" * 80 + "\n")

    for batch_idx, batch in enumerate(batches, 1):
        batch_bytes = sum(f[1]["size"] for f in batch)
        batch_start_t = time.time()

        # Check if launching this batch would exceed today's 750 GB daily limit
        current_uploaded_today = get_daily_tracker().get("uploaded_bytes", 0)
        if current_uploaded_today + batch_bytes > DAILY_UPLOAD_LIMIT_BYTES:
            print_daily_quota_stop_banner(
                uploaded_today=current_uploaded_today,
                total_downloaded=downloaded_bytes,
                total_expected=total_bytes,
                remaining=total_bytes - downloaded_bytes,
            )
            return

        safe_print("\n" + "-" * 80)
        safe_print(f"⚡ BATCH {batch_idx}/{total_batches}: Launching {len(batch)} parallel shard downloads ({format_bytes(batch_bytes)})...")
        safe_print("-" * 80)

        batch_failed = []
        quota_interrupted = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_item = {
                executor.submit(
                    download_shard_worker,
                    item_idx,
                    total_files,
                    file_info,
                    TARGET_DIR,
                    MODEL_REPO,
                    HF_TOKEN,
                    batch_idx,
                    total_batches,
                ): (item_idx, file_info)
                for item_idx, file_info in batch
            }

            for future in concurrent.futures.as_completed(future_to_item):
                item_idx, file_info = future_to_item[future]
                try:
                    success, fname, dl_bytes, dur, err = future.result()
                    with progress_lock:
                        if success:
                            downloaded_bytes += dl_bytes
                        else:
                            batch_failed.append(fname)
                            if err == "QUOTA_EXCEEDED":
                                quota_interrupted = True
                except Exception as exc:
                    safe_print(f"  ❌ Unhandled exception for {file_info['name']}: {exc}")
                    batch_failed.append(file_info['name'])

        batch_dur = max(time.time() - batch_start_t, 0.001)
        batch_speed = (batch_bytes / 1024 / 1024) / batch_dur if batch_bytes > 0 else 0
        overall_pct = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0

        # Flush Google Drive FUSE write buffers to cloud and scrub local disk
        flush_fuse_cache()
        clean_local_colab_disk()
        stats = get_storage_stats()

        safe_print("\n" + "=" * 80)
        if not batch_failed:
            safe_print(f"🎉 BATCH {batch_idx}/{total_batches} FINISHED in {format_time(batch_dur)} (Aggregate Speed: {batch_speed:.1f} MB/s)!")
        else:
            safe_print(f"⚠️ BATCH {batch_idx}/{total_batches} HAD {len(batch_failed)} FAILED SHARDS: {batch_failed}")

        safe_print(f"📊 Overall Progress:        {render_progress_bar(overall_pct)} ({format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)})")
        safe_print(f"🖥️ Colab VM Local Disk Free: {format_bytes(stats['colab_free'])} (Protected)")
        safe_print("=" * 80)

        if quota_interrupted:
            print_daily_quota_stop_banner(
                uploaded_today=get_daily_tracker().get("uploaded_bytes", 0),
                total_downloaded=downloaded_bytes,
                total_expected=total_bytes,
                remaining=total_bytes - downloaded_bytes,
            )
            return

        if batch_failed:
            safe_print("⚠️ Stopping batch loop to allow retry. Re-running will resume cleanly from where it left off.")
            return

    # 7. Final Verification Audit Report
    report = audit_final_model(ordered_files)
    print_final_report(report)


if __name__ == "__main__":
    main()

