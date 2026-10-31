# Hệ Thống Phân Loại Cam Nông Nghiệp Thông Minh (AIoT Orange Sorting System)
### Nền tảng Đám Mây AWS EC2 · Trí Tuệ Nhân Tạo EfficientNet-B0 V3 · Phần Cứng ESP32 Dual-Camera

Dự án phát triển hệ sinh thái **AIoT hoàn chỉnh (End-to-End)** phục vụ phân loại chất lượng nông sản (quả cam) tự động theo thời gian thực. Hệ thống kết hợp cơ cấu chấp hành cơ điện tử tại vườn (**ESP32, Băng chuyền L298N, Cảm biến LM393, 2 Servo phân luồng**) với máy chủ đám mây **AWS EC2 (FastAPI, PyTorch CPU, MySQL 8.0, Nginx)** và giao diện Web Dashboard phân quyền **3 Role (Quản trị viên, Chủ nông trại, Đại lý thu mua)**.

---

## 1. Kiến Trúc Tổng Thể Hệ Thống

```text
       ┌──────────────────────────── NÔNG TRẠI (ON-PREMISE IOT) ────────────────────────────┐
       │                                                                                    │
       │   [Camera 1: Đỉnh] ──(HTTP/JPG)──┐                                                  │
       │                                   ├──> [ESP32 DOIT DevKit V1]                       │
       │   [Camera 2: Hông] ──(HTTP/JPG)──┘      │  Chế độ: WIFI_AP_STA (192.168.4.1)       │
       │                                         │  Stream Multipart 2 ảnh (Zero-Copy)      │
       │   [LM393 Phát Hiện] ────────────────────┤                                          │
       │   [Động Cơ Băng Chuyền L298N] <────────┤                                          │
       │   [Servo 1: Máng 1 (Cam Loại 1)] <──────┤                                          │
       │   [Servo 2: Máng 2 (Cam Loại 2)] <──────┘                                          │
       │   (Đi thẳng: Máng 3 - Cam Hỏng/Xanh)                                               │
       └─────────────────────────────────────────┬──────────────────────────────────────────┘
                                                 │ Internet (HTTP Request + Hardware MAC Binding)
                                                 ▼
       ┌──────────────────────────── AWS EC2 CLOUD INSTANCE ────────────────────────────────┐
       │                                                                                    │
       │   Cổng 80 (HTTP): [ Nginx Reverse Proxy & Frontend SPA ]                           │
       │                   │                                                                │
       │                   ├── /api/  ──> [ FastAPI Backend (Python 3.11) ]                 │
       │                   └── /uploads/ ──┘  │                                             │
       │                                      ├── [ EfficientNet-B0 V3 PyTorch Model ]      │
       │                                      │   (Gộp 2 góc chụp theo Confidence Gap 20%)  │
       │                                      │                                             │
       │                                      └── [ MySQL 8.0 Database Volume ]             │
       └────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tính Năng Nổi Bật

### 2.1. Phân quyền Người Dùng 3 Role Chuyên Biệt
- **👑 Quản trị viên (Admin)**: Quản lý toàn bộ nông trại đối tác, cấp tài khoản cho chủ vườn, cấp mới hoặc đổi mã `device_api_key`, mở khóa/reset địa chỉ MAC phần cứng, gia hạn ngày sử dụng dịch vụ, quản lý tài khoản người dùng và giám sát mô hình AI.
- **🍊 Chủ nông trại (Farm)**: Tra cứu thời hạn thuê bao, sao chép `device_api_key` nạp vào ESP32, xem địa chỉ MAC phần cứng đã khóa, giám sát trạng thái băng chuyền thời gian thực, **xem hình ảnh trực tiếp 2 góc chụp gửi về từ ESP32 theo thời gian thực** kèm phân tích AI tức thì, theo dõi sản lượng và lịch sử của riêng nhà vườn mình.
- **🏬 Đại lý thu mua (Dealer)**: Khảo sát bảng xếp hạng so sánh các nhà vườn, lọc theo sản lượng thương phẩm (Loại 1 + Loại 2), tỉ lệ cam hỏng %, phân bố 5 bệnh học ngoại quan AI, nhãn khuyến nghị thu mua tự động (*Đề xuất nhập*, *Cân nhắc*, *Cảnh báo rủi ro*), **trực tiếp thẩm định cặp ảnh 2 góc chụp thực tế** của từng lô cam để quyết định ký hợp đồng thu mua.

### 2.2. Bảo Mật Thiết Bị Phần Cứng (Hardware MAC Binding)
- ESP32 xác thực với server qua Header `X-Device-Key` và `X-Device-MAC`.
- Server tự động khóa cứng địa chỉ MAC của bo mạch vào nông trại ở lần kết nối đầu tiên.
- Mọi nỗ lực gọi API từ thiết bị lạ dù có mã Key cũng sẽ bị chặn `403 Forbidden` ngay lập tức. Admin có nút **Reset MAC** khi nông trại cần thay thế mạch mới.

### 2.3. Thuật Toán Gộp 2 Góc Chụp Thông Minh (Confidence Gap = 20%)
Mỗi quả cam được quan sát đồng thời từ **Góc trên (Camera 1)** và **Góc ngang (Camera 2)**:
1. **Cùng Grade**: Chọn kết quả có độ tin cậy (`confidence`) cao hơn.
2. **Khác Grade, Chênh lệch độ tin cậy > 20%** (`gap_threshold = 0.20`): Chọn góc chụp có độ tin cậy vượt trội (`high_confidence_override`) để loại trừ góc chụp bị rung mờ hoặc lóa sáng.
3. **Khác Grade, Chênh lệch độ tin cậy ≤ 20%**: Ưu tiên chọn **hạng chất lượng thấp hơn / khuyết tật hơn** (Loại 3 > Loại 2 > Loại 1 — `close_confidence_worse_grade`) nhằm đảm bảo kiểm soát chất lượng nghiêm ngặt, không bỏ sót quả bị nám hoặc thối ở mặt khuất.

### 2.4. Firmware ESP32 Băng Chuyền Khép Kín & Web Nhúng
- **Chế độ Wi-Fi kép `WIFI_AP_STA`**: ESP32 vừa phát Wi-Fi AP (`ESP32-PhanLoaiCam` / IP: `192.168.4.1`) kèm Web cấu hình nhúng (PROGMEM, siêu nhẹ), vừa kết nối Wi-Fi nhà vườn để gọi lên Cloud EC2.
- **Khóa an toàn**: Động cơ luôn dừng khi bật nguồn; chỉ khi bấm [Lưu & Kiểm Tra] thành công thì nút **[▶ BẬT BĂNG CHUYỀN]** mới mở khóa.
- **Tải ảnh Zero-Copy Stream**: Tải lần lượt từng ảnh từ camera IP nội bộ, stream multipart HTTP/1.0 lên EC2 rồi giải phóng RAM ngay, giữ bộ nhớ Heap luôn dư >200 KB.

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
SmartAgriculturalSorting/
├── AI_handover/                        # Mô hình AI bàn giao
│   ├── models/
│   │   └── orange_classifier_v3_best.pth  # Checkpoint EfficientNet-B0 V3
│   └── predict.py                      # Module suy luận hình ảnh
├── backend/                            # FastAPI Backend Service
│   ├── app/
│   │   ├── routers/                    # admin, auth, dealer, farm_portal, hardware_events, cameras
│   │   ├── services/                   # camera_classifications (thuật toán gộp 2 ảnh), images, responses
│   │   ├── config.py                   # Cấu hình Pydantic settings
│   │   ├── constants.py                # Định nghĩa 5 lớp AI và ánh xạ Grade/Máng
│   │   ├── database.py                 # Kết nối MySQL SQLAlchemy
│   │   ├── models.py                   # Model User, Farm, Classification, PredictionDetail...
│   │   ├── predictor.py                # Nạp mô hình PyTorch
│   │   ├── schemas.py                  # Pydantic Schemas cho API
│   │   ├── security.py                 # Xác thực Bearer Token HMAC-SHA256 & Hardware MAC Check
│   │   ├── seed.py                     # Khởi tạo database & nạp sẵn tài khoản demo
│   │   └── main.py                     # Điểm khởi chạy FastAPI & Lifespan retry DB
│   ├── tests/                          # Bộ kiểm thử 50 test cases tự động
│   ├── Dockerfile                      # Container Python 3.11-slim + PyTorch CPU
│   ├── requirements.txt                # Thư viện web backend
│   └── requirements-ai.txt             # Thư viện PyTorch CPU
├── frontend/                           # React SPA Frontend Service
│   ├── src/
│   │   ├── components/                 # AdminDashboard, FarmDashboard, DealerDashboard, AuthBar...
│   │   ├── api.js                      # HTTP Client gọi Backend API
│   │   ├── App.jsx                     # Điều hướng giao diện theo Role người dùng
│   │   └── styles.css                  # Giao diện responsive với 3 theme màu riêng biệt
│   ├── nginx.conf                      # Cấu hình Nginx Reverse Proxy (max body 25M)
│   ├── Dockerfile                      # Multi-stage build Nginx phục vụ SPA
│   └── package.json                    # Dependencies React 18, Vite
├── docker-compose.yml                  # Khởi chạy toàn bộ hệ thống (db, backend, frontend)
├── DEPLOY_EC2.md                       # Hướng dẫn chi tiết triển khai lên AWS EC2
└── README.md                           # Tài liệu tổng quan dự án
```

---

## 4. Tài Khoản Mặc Định Đã Tạo Sẵn

Sau khi khởi động, hệ thống tự động nạp sẵn 4 tài khoản mẫu để đăng nhập và trải nghiệm ngay:

| Vai trò (Role) | Tên đăng nhập | Mật khẩu | Giao diện & Quyền hạn |
| :--- | :--- | :--- | :--- |
| **👑 Quản trị viên (Admin)** | `admin` | `admin123` | **Theme Tím**: Quản lý nông trại, tạo tài khoản mới, cấp/đổi API Key, mở khóa MAC, gia hạn gói dịch vụ. |
| **🍊 Nông trại 1 (Farm)** | `farm1` | `farm123` | **Theme Cam**: *Nông trại Cam Cao Phong - Hòa Bình*. Lấy API Key, xem live feed 2 ảnh từ ESP32 theo thời gian thực và lịch sử vườn. |
| **🍊 Nông trại 2 (Farm)** | `farm2` | `farm123` | **Theme Cam**: *Nông trại Cam Sành Miền Tây*. Quản lý và theo dõi sản lượng riêng. |
| **🏬 Đại lý (Dealer)** | `dealer1` | `dealer123` | **Theme Xanh Ngọc**: *Đại Lý Thu Mua Nông Sản Toàn Quốc*. Bảng xếp hạng so sánh các vườn, tỉ lệ hỏng %, xem ảnh kiểm định thực tế. |

*(Người dùng bên ngoài cũng có thể tự đăng ký tài khoản Đại lý mới tại màn hình đăng nhập).*

---

## 5. Hướng Dẫn Cài Đặt & Chạy Thử Nghiệm

### Cách 1: Triển Khai Nhanh Bằng Docker Compose (Khuyến nghị cho AWS EC2)
Chỉ cần máy chủ đã cài đặt Docker và Docker Compose:

```bash
# 1. Clone repository
git clone https://github.com/MinhNguyen592005/SmartAgriculturalSorting.git
cd SmartAgriculturalSorting

# 2. Khởi chạy toàn bộ hệ thống
docker compose up -d --build
```

Hệ thống sẽ tự động khởi tạo MySQL 8.0, build container Backend (FastAPI + AI CPU), nạp tài khoản mẫu và build Frontend Nginx trên cổng 80.
- Xem chi tiết từng bước cấu hình máy ảo EC2, mở Security Group và tạo Swap RAM tại: [DEPLOY_EC2.md](DEPLOY_EC2.md).

---

### Cách 2: Chạy Thủ Công Trên Máy Cá Nhân (Local Development)

#### Bước 1: Khởi tạo môi trường Backend Python
```powershell
# Từ thư mục gốc SmartAgriculturalSorting:
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện backend và PyTorch CPU
pip install -r backend/requirements.txt
pip install -r backend/requirements-ai.txt --index-url https://download.pytorch.org/whl/cpu
```

#### Bước 2: Chuẩn bị Cơ sở dữ liệu MySQL
Tạo database `orange_sorting` và user mẫu bằng MySQL:
```powershell
mysql -u root -p -e "source backend/create_database.sql"
```
*(Nếu dùng thông tin kết nối khác, chỉnh sửa biến `DATABASE_URL` trong file `backend/app/config.py` hoặc tạo file `backend/.env`).*

#### Bước 3: Khởi chạy Backend
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```
- Swagger API tương tác: [http://localhost:8000/docs](http://localhost:8000/docs)
- Kiểm tra trạng thái AI: [http://localhost:8000/api/model](http://localhost:8000/api/model)

#### Bước 4: Khởi chạy Frontend React
Mở một cửa sổ Terminal mới:
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
- Truy cập giao diện web tại: [http://localhost:5173](http://localhost:5173)

---

## 6. Hướng Dẫn Kết Nối Phần Cứng ESP32 Lên Hệ Thống

1. **Lấy API Key**: Đăng nhập tài khoản Nông trại (ví dụ `farm1` / `farm123`), vào tab **Khóa ESP32 & Gói Dịch Vụ**, bấm **📋 Sao chép**.
2. **Cấp nguồn cho bo mạch ESP32**: Băng chuyền ban đầu sẽ **dừng** an toàn.
3. **Kết nối Wi-Fi cấu hình**:
   - Dùng điện thoại kết nối Wi-Fi: `ESP32-PhanLoaiCam` (Mật khẩu: `12345678`).
   - Mở trình duyệt vào địa chỉ: `http://192.168.4.1`.
4. **Nhập thông số**:
   - Wi-Fi nhà vườn: SSID & Mật khẩu.
   - Địa chỉ Server: IP máy chủ EC2 hoặc IP LAN của máy chạy backend.
   - Cổng Port: `8000` (hoặc `80`).
   - API Key: Dán mã Key đã sao chép ở Bước 1.
   - Camera 1 (Đỉnh) & Camera 2 (Hông): URL ảnh tĩnh (VD: `http://192.168.1.101:8080/shot.jpg`).
5. **Vận hành**:
   - Bấm **[💾 Lưu & Kiểm Tra Kết Nối]**. Sau khi xác thực hợp lệ, bấm **[▶ BẬT BĂNG CHUYỀN]**.
   - Băng chuyền chuyển động đưa cam qua cảm biến LM393 $\rightarrow$ ESP32 tự dừng, chụp 2 ảnh, stream lên EC2, nhận kết quả và gạt Servo vào đúng máng phân loại!

---

## 7. Phân Loại Chất Lượng & Cơ Cấu Chấp Hành

| Lớp Dự Đoán AI | Nhận Diện Bệnh Học | Hạng Chất Lượng | Cơ Cấu Chấp Hành (Servo & Máng) |
| :--- | :--- | :---: | :--- |
| `fresh_orange` | Quả tròn đều, vỏ sáng mịn, tươi ngon | **Loại 1** (Grade 1) | **Servo 1** quay 60° gạt vào **Máng 1** (Cam xuất khẩu) |
| `blackspotted_orange` | Bệnh đốm đen (*Guignardia citricarpa*) | **Loại 2** (Grade 2) | **Servo 2** quay 60° gạt vào **Máng 2** (Cam thương phẩm chợ/chế biến) |
| `cankered_orange` | Bệnh loét sẹo (*Xanthomonas axonopodis*) | **Loại 2** (Grade 2) | **Servo 2** quay 60° gạt vào **Máng 2** (Cam thương phẩm chợ/chế biến) |
| `green_orange` | Quả còn xanh non, chưa chín | **Loại 3** (Grade 3) | **Giữ nguyên 2 Servo (0°)**, chạy thẳng vào **Máng 3** (Phế phẩm / Ủ chín) |
| `rotten_orange` | Quả thối rữa, nấm mốc hỏng | **Loại 3** (Grade 3) | **Giữ nguyên 2 Servo (0°)**, chạy thẳng vào **Máng 3** (Phế phẩm / Thải bỏ) |

---

## 8. Kiểm Thử Hệ Thống (Automated Testing)

Toàn bộ hệ thống được bảo vệ bởi bộ kiểm thử tự động toàn diện:

```powershell
# Chạy bộ test backend (50 test cases bao gồm Auth, Hardware, Roles, AI):
.\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
# Kết quả: 50 passed in ~20s

# Chạy kiểm thử frontend:
cd frontend
npm.cmd test -- --run
npm.cmd run build
```

---

## 9. Giấy Phép & Tác Giả

Dự án Bài tập lớn / Đồ án Hệ thống Nhúng và IoT — Phân loại Nông sản Thông minh bằng AIoT.
Mọi thắc mắc kỹ thuật vui lòng tham khảo thêm tài liệu [DEPLOY_EC2.md](DEPLOY_EC2.md) hoặc mã nguồn trong thư mục `backend/app/routers/`.
