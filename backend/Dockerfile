FROM python:3.11-slim

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt Python dependencies + PyTorch CPU và xóa ngay các file test/header nặng không cần thiết trong cùng 1 layer
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements-ai.txt /app/requirements-ai.txt

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /usr/local/lib/python3.11/site-packages/torch/test \
           /usr/local/lib/python3.11/site-packages/torch/include \
           /usr/local/lib/python3.11/site-packages/torch/bin/test* \
           /root/.cache && \
    find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} +

# Sao chép mã nguồn backend và mô hình AI
COPY backend /app/backend
COPY AI_handover /app/AI_handover

WORKDIR /app/backend

# Tạo thư mục uploads
RUN mkdir -p /app/backend/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
