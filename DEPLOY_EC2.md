# Hướng Dẫn Triển Khai Hệ Thống Phân Loại Nông Sản Lên AWS EC2

Tài liệu này hướng dẫn chi tiết cách deploy hệ thống Backend AI, Cơ sở dữ liệu MySQL và Web Dashboard 3 Role lên máy chủ đám mây **AWS EC2**, đồng thời hướng dẫn kết nối bo mạch phần cứng **ESP32** từ nhà vườn lên đám mây.

---

## 1. Kiến Trúc Triển Khai Trên AWS EC2

```
                       [ ESP32 tại Nông Trại ]
               (Tự động chụp 2 ảnh & POST HTTP Multipart)
                                  │
                                  ▼ (Internet)
                AWS EC2 Instance (Public IP: x.x.x.x)
 ┌─────────────────────────────────────────────────────────────────┐
 │ Docker Network                                                  │
 │                                                                 │
 │   Cổng 80: [ Nginx Reverse Proxy & Frontend SPA ]              │
 │              │                  │                               │
 │              │ /api/            │ /uploads/                     │
 │              ▼                  ▼                               │
 │   Cổng 8000: [ FastAPI Backend + EfficientNet-B0 AI (CPU) ]     │
 │              │                                                  │
 │              ▼ (Internal SQL port 3306)                         │
 │   [ MySQL 8.0 Database (Persisted Volume) ]                     │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 2. Chuẩn Bị Máy Chủ AWS EC2

### 2.1. Chọn Cấu Hình Instance & Dung Lượng Ổ Cứng
- **Hệ điều hành khuyến nghị**: `Ubuntu 24.04 LTS` hoặc `Ubuntu 22.04 LTS`.
- **Loại Instance**:
  - Tối ưu chi phí & hiệu năng: **`t3.medium`** (2 vCPU, 4GB RAM) hoặc **`c5.large`**.
  - Nếu dùng gói miễn phí **`t2.micro`** hoặc **`t3.small`** (1GB - 2GB RAM): **Bắt buộc** phải tạo Swap File 2GB (xem mục 3.2 bên dưới) để tránh tràn RAM khi PyTorch nạp trọng số mô hình.
- **Dung lượng ổ cứng (Configure Storage)**: Chọn tối thiểu **`20 GiB`** (gp3) thay vì 8 GiB mặc định (Gói AWS Free Tier miễn phí tới **30 GiB**, nếu để 8 GiB sẽ bị báo lỗi `no space left on device` khi giải nén Docker image của MySQL + PyTorch + OpenCV).

### 2.2. Cấu hình Security Group (Inbound Rules)
Vào AWS Console -> EC2 -> Security Groups -> Edit Inbound Rules:

| Type | Port Range | Protocol | Source | Mục đích |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | `22` | TCP | `My IP` (hoặc `0.0.0.0/0`) | Đăng nhập SSH quản trị server |
| **HTTP** | `80` | TCP | `0.0.0.0/0` | Giao diện Web (Nông trại, Đại lý, Admin) |
| **Custom TCP** | `8000` | TCP | `0.0.0.0/0` | ESP32 gọi API trực tiếp & Swagger UI (`/docs`) |
| **HTTPS** (tùy chọn) | `443` | TCP | `0.0.0.0/0` | Nếu cài tên miền và chứng chỉ SSL |

---

## 3. Các Bước Cài Đặt Trên Máy Chủ EC2

### Bước 1: Kết nối SSH vào EC2
```bash
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>
```

### Bước 2: Cập nhật hệ điều hành & Tạo 2GB Swap RAM
```bash
sudo apt update && sudo apt upgrade -y

# Tạo file Swap 2GB chống tràn RAM
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Kiểm tra RAM & Swap
free -h
```

### Bước 3: Cài đặt Docker và Docker Compose
```bash
# Cài Docker bằng script chính thức của Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Cấp quyền cho user ubuntu không cần gõ sudo
sudo usermod -aG docker ubuntu
newgrp docker

# Kiểm tra phiên bản Docker
docker --version
docker compose version
```

### Bước 4: Tải mã nguồn dự án lên máy chủ
Bạn có thể clone từ Git repository của bạn:
```bash
git clone https://github.com/your-username/SmartAgriculturalSorting.git
cd SmartAgriculturalSorting
```
*(Hoặc dùng SCP từ máy tính cá nhân để upload thư mục `SmartAgriculturalSorting` lên EC2).*

### Bước 5: Khởi chạy toàn bộ hệ thống bằng Docker Compose
Chỉ cần chạy 1 lệnh duy nhất:
```bash
docker compose up -d --build
```

Lệnh này sẽ:
1. Kéo image `mysql:8.0` và khởi chạy database an toàn với volume dữ liệu độc lập.
2. Build container `backend` với Python 3.11-slim, cài PyTorch CPU siêu nhẹ và nạp checkpoint mô hình AI `orange_classifier_v3_best.pth`.
3. Tự động chạy cơ chế chờ DB sẵn sàng, tự động khởi tạo bảng (`models.py`) và nạp sẵn 4 tài khoản mẫu (`seed.py`).
4. Build container `frontend` với Vite và phục vụ qua Nginx trên cổng 80.

### Bước 6: Kiểm tra trạng thái hoạt động
```bash
# Xem danh sách các container đang chạy
docker compose ps

# Xem log thời gian thực của backend
docker compose logs -f backend
```

Khi thấy dòng:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```
Hệ thống đã sẵn sàng 100%!

---

## 4. Kiểm Tra Trên Trình Duyệt

Mở trình duyệt trên máy tính hoặc điện thoại:
- **Giao diện Web Dashboard**: `http://<EC2_PUBLIC_IP>/`
- **Swagger API Docs**: `http://<EC2_PUBLIC_IP>:8000/docs` hoặc `http://<EC2_PUBLIC_IP>/docs`

### Tài khoản mẫu đã seed sẵn:
| Vai trò (Role) | Username | Password | Quyền hạn |
| :--- | :--- | :--- | :--- |
| **👑 Admin (Quản trị)** | `admin` | `admin123` | Quản lý nông trại, tạo tài khoản mới, cấp/đổi API Key, reset MAC, gia hạn dịch vụ. |
| **🍊 Farm 1 (Nông trại)** | `farm1` | `farm123` | Nông trại Cam Sành Miền Tây: Lấy Key ESP32, xem thời hạn, xem live feed 2 góc và lịch sử. |
| **🍊 Farm 2 (Nông trại)** | `farm2` | `farm123` | Nông trại Cam Vinh: Quản lý thiết bị và theo dõi sản lượng riêng. |
| **🏬 Dealer 1 (Đại lý)** | `dealer1` | `dealer123` | Đại lý Thu mua: Xem bảng so sánh các nông trại, tỉ lệ hỏng %, khuyến nghị nhập và xem ảnh kiểm định. |

*(Trên giao diện Web đã tích hợp sẵn thanh **Đăng nhập nhanh 1-Click** để bạn bấm chuyển đổi qua lại tức thì khi demo thuyết trình).*

---

## 5. Hướng Dẫn Cấu Hình ESP32 Kết Nối Lên EC2

1. **Lấy API Key của Nông trại**:
   - Đăng nhập vào Web với tài khoản nông trại (ví dụ: `farm1`).
   - Tại mục **Xác thực phần cứng ESP32**, bấm nút **📋 Sao chép Key**.

2. **Kết nối vào mạng Wi-Fi cấu hình của ESP32**:
   - Cấp nguồn cho bo mạch ESP32. Động cơ băng tải ban đầu sẽ **dừng** an toàn.
   - Dùng điện thoại hoặc laptop quét Wi-Fi và kết nối vào:
     - **Tên Wi-Fi (SSID)**: `ESP32-PhanLoaiCam`
     - **Mật khẩu**: `12345678`

3. **Mở giao diện Web nhúng cài đặt**:
   - Mở trình duyệt truy cập: `http://192.168.4.1`

4. **Điền thông số kết nối**:
   - **Tên Wi-Fi nhà vườn**: Nhập SSID Wi-Fi tại vườn
   - **Mật khẩu Wi-Fi**: Mật khẩu Wi-Fi tại vườn
   - **Địa chỉ Server EC2**: Nhập Public IP của máy chủ EC2 (ví dụ: `54.254.120.88`)
   - **Cổng Server**: Nhập `8000` (hoặc `80`)
   - **Device API Key**: Dán Key đã sao chép ở Bước 1
   - **IP Camera 1 (Trên)**: URL ảnh từ điện thoại 1 (ví dụ: `http://192.168.1.101:8080/shot.jpg`)
   - **IP Camera 2 (Hông)**: URL ảnh từ điện thoại 2 (ví dụ: `http://192.168.1.102:8080/shot.jpg`)

5. **Lưu & Bật băng chuyền**:
   - Bấm nút **[Lưu & Kiểm tra kết nối Server]**.
   - ESP32 sẽ gọi API `/api/device/verify` lên EC2 kèm địa chỉ MAC phần cứng. Server sẽ tự động xác thực và khóa MAC của bo mạch vào nông trại tương ứng.
   - Khi dòng trạng thái báo `Xác thực thành công!`, nút **[▶ BẬT BĂNG CHUYỀN]** sẽ sáng lên.
   - Bấm nút bật băng chuyền: Động cơ L298N bắt đầu quay đưa cam qua cảm biến LM393.
   - Khi có cam, ESP32 tự chụp 2 ảnh, stream gửi thẳng lên EC2 qua `/api/device/classify-upload`, nhận kết quả Grade 1/2/3 và điều khiển Servo 1 hoặc Servo 2 gạt cam vào đúng máng!

---

## 6. Các Lệnh Quản Trị Hữu Ích Trên EC2

```bash
# Xem log của hệ thống phân loại AI
docker compose logs -f backend

# Khởi động lại dịch vụ khi cập nhật code
docker compose restart backend frontend

# Dừng toàn bộ hệ thống
docker compose down

# Dừng và xóa toàn bộ dữ liệu (nếu muốn cài lại từ đầu)
docker compose down -v
```
