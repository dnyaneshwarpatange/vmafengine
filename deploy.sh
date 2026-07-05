#!/bin/bash
set -e

echo "============================================="
echo " VMAF Engine - Enterprise 1-Click Deployment "
echo "============================================="

# 1. System Updates
echo "[1/4] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Install Docker & Docker Compose
echo "[2/4] Installing Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    sudo apt-get install docker-compose-plugin -y || \
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 3. Create .env if it doesn't exist
echo "[3/4] Checking environment configuration..."
if [ ! -f .env ]; then
    echo "Creating a template .env file..."
    cat <<EOF > .env
# Database & Redis
POSTGRES_USER=vmaf_user
POSTGRES_PASSWORD=vmaf_pass
POSTGRES_DB=vmaf
DATABASE_URL=postgresql://vmaf_user:vmaf_pass@db:5432/vmaf
REDIS_URL=redis://redis:6379/0

# Security (Change in production!)
JWT_SECRET_KEY=$(openssl rand -hex 32)
VITE_API_URL=http://YOUR_SERVER_IP:8000

# Razorpay (Get these from https://dashboard.razorpay.com/app/keys)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Optional: AWS S3 Configuration (Leave blank to use local VPS storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=
AWS_S3_BUCKET=
EOF
    echo -e "\e[31m[ACTION REQUIRED]\e[0m I created a .env file. Please edit it with your Razorpay keys and Server IP: 'nano .env'"
    exit 0
fi

# 4. Build and Start the Cluster
echo "[4/4] Building and launching the VMAF Enterprise cluster..."
mkdir -p uploads  # Ensure local storage directory exists
docker-compose up -d --build

echo "============================================="
echo " Deployment Complete!                        "
echo " The frontend is running on port 8000.       "
echo " Ensure your firewall allows port 8000.      "
echo "============================================="
