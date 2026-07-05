# config.py
"""
One place for plan → credit mappings and operational limits, so signup/webhook
code and worker code never hardcode these in multiple spots.
"""

PLAN_CREDITS = {
    "plan_starter_499": 1000,
    "plan_pro_1999": 10000,
}

TARGET_VMAF_DEFAULT = 94.0
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024   # 2 GB hard cap per input video
DOWNLOAD_TIMEOUT_SECONDS = 60
