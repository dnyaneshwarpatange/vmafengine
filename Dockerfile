# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN rm -f package-lock.json
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Build the FastAPI backend
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Copy the built React app from the frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
