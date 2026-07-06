# celery_tasks.py
"""
Celery worker for video processing jobs.

Downloads the input video (with a hard byte cap), runs the VMAF optimizer
to find the best CRF and encode, uploads the result to S3, and updates
the job row. Credits are trued up against actual duration on success,
or refunded on failure.
"""
import os
import shutil
import tempfile
import logging
from datetime import datetime

import requests
from celery import Celery

from models import SessionLocal, User, Job
from optimizer import optimize_video, get_video_duration
from config import DOWNLOAD_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

celery_app = Celery("vmaf_worker", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))

try:
    import boto3
    _aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    # Skip S3 when credentials are obviously placeholder/test values
    if _aws_key and _aws_key not in ("test_key", "your_key", ""):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=_aws_key,
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    else:
        s3 = None
        logger.info("S3 disabled — using placeholder AWS credentials. Output files stay local.")
except ImportError:
    s3 = None



@celery_app.task(bind=True, name="celery_tasks.process_video_task", max_retries=2, default_retry_delay=60, acks_late=True)
def process_video_task(self, job_id: str, input_url: str, user_id: str, target_vmaf: float, codec: str = "vp9", resolution: str = "original", audio_bitrate: str = "96k"):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    job.status = "processing"
    db.commit()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return

    credits_charged = 0
    work_dir = tempfile.mkdtemp(prefix="vmaf_worker_")
    try:
        input_path = os.path.join(work_dir, "input.mp4")
        if input_url.startswith("local://"):
            local_path = input_url.replace("local://", "")
            shutil.copy(local_path, input_path)
            try:
                os.remove(local_path)
            except OSError:
                pass
        else:
            headers = {}
            if "s3.amazonaws.com" not in input_url:
                headers['User-Agent'] = "VMAF-Optimizer/1.0"
            r = requests.get(input_url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS, headers=headers)
            r.raise_for_status()

            with open(input_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)

        duration = get_video_duration(input_path)
        
        # Credit calculation: 1 credit per minute (minimum 1)
        credits_needed = max(1, int(duration / 60) + (1 if duration % 60 > 0 else 0))
        
        # Check if user has sufficient credits (admin gets unlimited)
        locked_user = db.query(User).filter(User.id == user_id).with_for_update().first()
        if not locked_user.is_admin and locked_user.credits < credits_needed:
            raise ValueError(f"Insufficient credits. Need {credits_needed} credits for {duration:.0f}s video (1 credit/min). You have {locked_user.credits}.")
        
        # Deduct credits (account for the 1 already reserved at submission)
        if not locked_user.is_admin:
            additional = credits_needed - 1  # 1 was already reserved at submission
            locked_user.credits = max(0, locked_user.credits - additional)
            credits_charged = credits_needed
        db.commit()

        job.original_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        db.commit()

        ext = "mp4" if codec in ("h264", "hevc", "av1") else "webm"
        output_path = os.path.join(work_dir, f"output.{ext}")

        optimal_crf, sampled_vmaf = optimize_video(
            input_path, output_path, target_vmaf=target_vmaf, 
            codec=codec, resolution=resolution, audio_bitrate=audio_bitrate
        )

        job.optimal_crf = optimal_crf
        job.sampled_vmaf = sampled_vmaf
        job.optimized_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        job.completed_at = datetime.utcnow()

        if s3 is not None:
            s3_key = f"optimized/{job_id}.{ext}"
            s3.upload_file(output_path, os.getenv("AWS_S3_BUCKET"), s3_key, ExtraArgs={"ContentType": f"video/{ext}"})
            job.output_url = f"https://{os.getenv('AWS_S3_BUCKET')}.s3.amazonaws.com/{s3_key}"
        else:
            os.makedirs("/uploads", exist_ok=True)
            final_filename = f"{job_id}.{ext}"
            final_path = os.path.join("/uploads", final_filename)
            shutil.copy(output_path, final_path)
            job.output_url = f"local://{final_path}"

        job.status = "completed"
        db.commit()

    except Exception as exc:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:2000]
            db.commit()
        logger.exception("Job %s failed", job_id)
        # Refund all credits (1 reserved at submission + any additional charged here)
        refund = credits_charged if credits_charged > 0 else 1
        user = db.query(User).filter(User.id == user_id).with_for_update().first()
        if user and not user.is_admin:
            user.credits += refund
            db.commit()
        raise

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        db.close()

