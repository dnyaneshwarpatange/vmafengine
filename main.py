# main.py
"""
FastAPI backend for the VMAF Video Optimization API.

Handles auth (hashed API keys shown once at signup), job submission with
SSRF-safe URL validation and row-locked credit reservation, job status
polling, Razorpay subscription creation, and webhook processing with
signature verification and idempotency.
"""
import os
import hashlib
import secrets
import ipaddress
import socket
import json as jsonlib
import hmac
from urllib.parse import urlparse
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

import razorpay
from fastapi import FastAPI, Header, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import time
import redis
from sqlalchemy.orm import Session

from models import User, Job, WebhookEvent, init_db, get_db
from config import PLAN_CREDITS, TARGET_VMAF_DEFAULT

app = FastAPI(title="VMAF Video Optimization API")

# Allow requests from any origin (Frontend decoupling)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


# Lazy-initialized so the API can start even with placeholder Razorpay
# credentials (useful for local testing of non-payment endpoints).
_razorpay_client = None

def get_razorpay_client():
    global _razorpay_client
    if _razorpay_client is None:
        _razorpay_client = razorpay.Client(
            auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        )
    return _razorpay_client


SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("JWT_SECRET_KEY", secrets.token_hex(32)))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    if not hashed_password: return False
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    # Admin Seeder
    admin_email = "admin@vmaf.local"
    if not db.query(User).filter(User.email == admin_email).first():
        admin = User(
            email=admin_email,
            hashed_password=get_password_hash("admin"),
            credits=999999,
            is_admin=True,
            api_key_hash=None
        )
        db.add(admin)
        db.commit()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: authenticate the caller via JWT Bearer token."""
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user


def assert_url_is_safe(url: str):
    """SSRF guard: the worker fetches whatever URL is submitted here, so an
    unchecked URL lets a caller point the server at internal services or
    cloud metadata endpoints (e.g. 169.254.169.254)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="input_url must be http or https")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="input_url is missing a host")
    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="input_url host could not be resolved")
    for family, _, _, _, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise HTTPException(status_code=400, detail="input_url resolves to a disallowed address")


# ---------- Job submission & status ----------

class OptimizeRequest(BaseModel):
    input_url: str
    target_vmaf: float = TARGET_VMAF_DEFAULT
    codec: str = "vp9"
    resolution: str = "original"
    audio_bitrate: str = "96k"


@app.post("/v1/optimize")
async def optimize_video_endpoint(
    request: OptimizeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_url_is_safe(request.input_url)

    # Reserve 1 credit under a row lock so concurrent submissions can't all
    # pass the credits-available check before any of them is actually charged.
    locked_user = db.query(User).filter(User.id == user.id).with_for_update().one()
    if locked_user.credits < 1:
        db.rollback()
        raise HTTPException(status_code=402, detail="Insufficient credits. Please subscribe.")
    locked_user.credits -= 1
    db.commit()

    new_job = Job(
        user_id=user.id, 
        input_url=request.input_url, 
        status="pending", 
        target_vmaf=request.target_vmaf,
        codec=request.codec,
        resolution=request.resolution,
        audio_bitrate=request.audio_bitrate
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    from celery_tasks import process_video_task
    process_video_task.delay(str(new_job.id), request.input_url, str(user.id), request.target_vmaf, request.codec, request.resolution, request.audio_bitrate)

    return {"job_id": str(new_job.id), "status": "pending",
            "message": "Video is being processed. Check status via /v1/status/{job_id}"}


@app.post("/v1/optimize/free")
async def optimize_free(
    request: Request,
    file: UploadFile = File(...),
    target_vmaf: float = Form(TARGET_VMAF_DEFAULT),
    codec: str = Form("vp9"),
    resolution: str = Form("original"),
    audio_bitrate: str = Form("96k"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Free tier endpoint: max 5 videos per user, local file upload."""
    
    # Track usage on the user directly (simplest way: count their jobs)
    # or keep the Redis rate limiter but keyed by User ID to prevent abuse.
    rate_limit_key = f"rate_limit:user:{user.id}"
    current_count = redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= 5:
        raise HTTPException(status_code=429, detail="Free tier limit reached (5 videos total). Please subscribe for unlimited access.")

    os.makedirs("/uploads", exist_ok=True)
    temp_file_path = f"/uploads/free_{secrets.token_hex(8)}_{file.filename}"
    
    with open(temp_file_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            buffer.write(chunk)

    if current_count is None and not user.is_admin:
        redis_client.set(rate_limit_key, 1) # Lifetime limit of 5 for free users
    elif not user.is_admin:
        redis_client.incr(rate_limit_key)

    local_url = f"local://{temp_file_path}"
    
    new_job = Job(
        user_id=user.id, 
        input_url=local_url, 
        status="pending", 
        target_vmaf=target_vmaf,
        codec=codec,
        resolution=resolution,
        audio_bitrate=audio_bitrate
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    from celery_tasks import process_video_task
    process_video_task.delay(str(new_job.id), local_url, str(user.id), target_vmaf, codec, resolution, audio_bitrate)

    return {"job_id": str(new_job.id), "status": "pending",
            "message": "Free video processing started."}


@app.get("/v1/download/{job_id}", response_model=None)
async def download_file(job_id: str, token: str = None, db: Session = Depends(get_db)):
    """Download endpoint authenticates via ?token= query param.
    Query param is needed because <a href> links can't send Authorization headers."""
    user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
        except jwt.PyJWTError:
            pass
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Pass ?token=YOUR_JWT")
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    if not job.output_url or not job.output_url.startswith("local://"):
        raise HTTPException(status_code=400, detail="File is not stored locally")
        
    file_path = job.output_url.replace("local://", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "mp4"
    media_type = "video/webm" if ext == "webm" else "video/mp4"
    download_name = f"vmaf_{job.resolution}_{job.codec}_{os.path.basename(file_path)}"
    
    return FileResponse(path=file_path, filename=download_name, media_type=media_type)


@app.get("/v1/status/{job_id}")
async def get_status(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job.id),
        "status": job.status,
        "original_size_mb": job.original_size_mb,
        "optimized_size_mb": job.optimized_size_mb,
        "target_vmaf": job.target_vmaf,
        "codec": job.codec,
        "resolution": job.resolution,
        "audio_bitrate": job.audio_bitrate,
        "sampled_vmaf": job.sampled_vmaf,
        "output_url": job.output_url,
        "error_message": job.error_message
    }


@app.get("/v1/users/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "credits": user.credits,
        "is_active": user.is_active,
        # For the dashboard, we return a mock API key since we only store the hash
        # In a real app, users generate keys on demand and only see them once.
        "api_key_placeholder": "vmaf_live_..." 
    }


@app.get("/v1/jobs")
async def get_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(50).all()
    return [{
        "job_id": str(j.id),
        "status": j.status,
        "target_vmaf": j.target_vmaf,
        "codec": j.codec,
        "resolution": j.resolution,
        "audio_bitrate": j.audio_bitrate,
        "sampled_vmaf": j.sampled_vmaf,
        "original_size_mb": j.original_size_mb,
        "optimized_size_mb": j.optimized_size_mb,
        "created_at": j.created_at.isoformat() if j.created_at else None
    } for j in jobs]


# ---------- Authentication ----------

class RegisterRequest(BaseModel):
    email: str
    password: str

@app.post("/v1/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    razorpay_customer = get_razorpay_client().customer.create({
        "name": request.email.split("@")[0],
        "email": request.email,
        "contact": "9999999999",
    })

    new_user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        razorpay_customer_id=razorpay_customer["id"],
        credits=5,  # Give 5 free credits on signup!
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/v1/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


class GoogleAuthRequest(BaseModel):
    token: str

@app.post("/v1/auth/google")
async def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        import requests
        resp = requests.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={request.token}")
        if resp.status_code != 200:
            raise ValueError(f"Invalid access token: {resp.text}")
        idinfo = resp.json()
        
        email = idinfo.get("email")
        google_id = idinfo.get("sub")
        
        if not email:
            raise ValueError("No email provided by Google")
        
        user = db.query(User).filter((User.email == email) | (User.google_id == google_id)).first()
        
        if not user:
            # Create a new user for Google Sign-In
            razorpay_customer = get_razorpay_client().customer.create({
                "name": email.split("@")[0],
                "email": email,
                "contact": "9999999999",
            })
            user = User(
                email=email,
                google_id=google_id,
                razorpay_customer_id=razorpay_customer["id"],
                credits=5,  # 5 free credits
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif not user.google_id:
            # Link existing email account to Google ID
            user.google_id = google_id
            db.commit()
            
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError as e:
        print(f"Google token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")


class SubscribeRequest(BaseModel):
    email: str
    plan_id: str


@app.post("/v1/payments/subscribe")
async def create_subscription(request: SubscribeRequest, db: Session = Depends(get_db)):
    if request.plan_id not in PLAN_CREDITS:
        raise HTTPException(status_code=400, detail="Unknown plan_id")

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # We use order.create instead of subscription.create so the user doesn't have to manually create Plans in Razorpay
    amount = 49900 if request.plan_id == 'plan_starter_499' else 199900
    try:
        order = get_razorpay_client().order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"rcpt_{secrets.token_hex(8)}"
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Razorpay Order Error: {str(e)}")

    # We skip saving subscription_id, we'll just give them credits instantly for testing
    user.credits += PLAN_CREDITS[request.plan_id]
    db.commit()

    return {"order_id": order["id"], "amount": amount, "message": "Credits added successfully!"}


# ---------- Razorpay webhook ----------

@app.post("/v1/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    expected_signature = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = request.headers.get("X-Razorpay-Event-Id")
    body = jsonlib.loads(raw_body)
    event = body["event"]

    # Idempotency: Razorpay retries undelivered webhooks with backoff for 24h.
    if event_id and db.query(WebhookEvent).filter(WebhookEvent.razorpay_event_id == event_id).first():
        return {"status": "ok", "note": "duplicate event ignored"}

    if event in ("subscription.activated", "subscription.charged"):
        subscription_id = body["payload"]["subscription"]["entity"]["id"]
        plan_id = body["payload"]["subscription"]["entity"]["plan_id"]
        user = db.query(User).filter(User.razorpay_subscription_id == subscription_id).first()
        if user and plan_id in PLAN_CREDITS:
            user.credits += PLAN_CREDITS[plan_id]

    if event_id:
        db.add(WebhookEvent(razorpay_event_id=event_id, event_type=event))
    db.commit()

    return {"status": "ok"}


# ---------- SPA Fallback ----------
# Serve React static assets
os.makedirs("frontend/dist", exist_ok=True)
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Catch-all route to serve the React app (must be last)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if os.path.exists("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    return {"error": "React frontend not built yet. Run 'npm run build' inside frontend/."}
