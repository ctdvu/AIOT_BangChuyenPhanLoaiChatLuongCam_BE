FROM python:3.11-slim

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt Python dependencies
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements-ai.txt /app/requirements-ai.txt

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu

# Sao chép mã nguồn backend và mô hình AI
COPY backend /app/backend
COPY AI_handover /app/AI_handover

WORKDIR /app/backend

# Tạo thư mục uploads
RUN mkdir -p /app/backend/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
