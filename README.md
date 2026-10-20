# Orange Sort — Hệ thống phân loại cam bằng AI

## 1. Giới thiệu dự án

Orange Sort là dự án phân loại ngoại quan quả cam bằng AI, kết hợp backend Python và giao diện web. Hệ thống sử dụng hai điện thoại Android làm camera IP để quan sát quả từ phía trên và bên cạnh.

Trong mỗi lượt chụp đôi, backend lấy hai ảnh, phân loại từng góc nhìn và lưu **một lượt lịch sử có đủ hai ảnh**. Kết quả gồm lớp cam, Grade/khay và độ tin cậy của AI.

### Chức năng hiện có

- Kết nối độc lập hai camera HTTP/MJPEG; xem trực tiếp, ngắt, kết nối lại và xoay ảnh từng camera.
- Lưu URL và góc xoay để sử dụng lại sau khi tải lại trang.
- Chụp và phân loại hai camera trong một lượt; thống kê tính một lượt là một quả.
- Trang **Camera & phân loại** hiển thị hai camera và bốn lượt phân loại gần nhất bên dưới.
- Trang **Thống kê & lịch sử** hiển thị số lượng theo loại và lịch sử có phân trang.
- Tải ảnh, dùng webcam máy tính để phân loại, hoặc tự chụp qua webcam khi phát hiện chuyển động.
- Có chế độ mô phỏng để kiểm tra phần mềm khi chưa có camera thật.

**Phạm vi hiện tại:** hai camera IP phân loại khi người dùng bấm nút. API sự kiện phần cứng mới xác nhận đã nhận tín hiệu; chưa tự điều khiển ESP32, cảm biến, băng chuyền hoặc servo. Kết quả AI dựa trên ngoại quan, không kết luận chất lượng ruột quả hoặc mùi.

### Công nghệ sử dụng

| Thành phần | Công nghệ |
| --- | --- |
| Giao diện | React 18, Vite |
| Backend | Python, FastAPI |
| Database | MySQL, SQLAlchemy, PyMySQL |
| Xử lý ảnh | OpenCV, Pillow |
| Mô hình AI | EfficientNet-B0 V3, PyTorch, torchvision |
| Camera | Hai Android có ứng dụng phát video HTTP/MJPEG |

## 2. Cấu trúc thư mục

```text
btl_iot/
├── AI_handover/
│   ├── models/
│   │   └── orange_classifier_v3_best.pth  # Checkpoint AI
│   ├── predict.py                      # Mã suy luận bàn giao
│   └── requirements.txt
├── backend/
│   ├── app/
│   │   ├── routers/                     # API camera, phân loại, thiết bị
│   │   ├── services/                    # Reader camera, lưu ảnh, xử lý lượt
│   │   ├── config.py                    # Đọc cấu hình môi trường
│   │   ├── database.py                  # Kết nối database
│   │   ├── models.py                    # Các bảng dữ liệu
│   │   ├── predictor.py                 # Gọi mô hình AI bàn giao
│   │   ├── schemas.py                   # Cấu trúc request/response
│   │   └── main.py                      # Khởi động FastAPI
│   ├── tests/                          # Kiểm thử backend
│   ├── uploads/                        # Ảnh lưu trên server
│   ├── .env.example                    # Cấu hình backend mẫu
│   ├── create_database.sql             # Tạo database và user MySQL mẫu
│   ├── requirements.txt                # Dependencies backend và OpenCV
│   ├── requirements-ai.txt             # Dependencies AI
│   └── requirements-dev.txt            # Dependencies kiểm thử
├── frontend/
│   ├── public/samples/                 # Ảnh minh họa cho mô phỏng
│   ├── src/
│   │   ├── components/                 # Camera, kết quả, lịch sử, thống kê
│   │   ├── App.jsx                     # Bố cục và điều hướng hai trang
│   │   ├── api.js                      # Gọi backend
│   │   └── styles.css                  # Giao diện
│   ├── tests/                          # Kiểm thử phát hiện chuyển động
│   ├── .env.example                    # Địa chỉ API mẫu
│   ├── package.json
│   └── package-lock.json
├── .gitignore
├── AI_INTEGRATION.md                    # Chi tiết tích hợp mô hình
├── CAMERAS.md                           # Hướng dẫn và API camera
└── README.md
```

`.venv/`, `frontend/node_modules/`, `frontend/dist/`, `.task-temp/` và các tệp `.env` được tạo trên máy chạy, không cần bàn giao qua Git.

## 3. Clone dự án về máy

### Chuẩn bị

- Git.
- Python 3.11, 3.12 hoặc 3.13.
- Node.js và npm.
- MySQL 8.x đang chạy, có tài khoản được phép tạo database và tài khoản ứng dụng.
- Hai điện thoại Android và máy tính cùng Wi-Fi nếu muốn thử camera thật.

Các lệnh bên dưới dùng **Windows PowerShell**. Chạy từ thư mục gốc `btl_iot`, trừ khi có hướng dẫn chuyển thư mục.

Clone repository về thư mục `btl_iot` trên máy:

```powershell
git clone https://github.com/MinhNguyen592005/SmartAgriculturalSorting.git btl_iot
Set-Location btl_iot
```

### Những gì cần chuẩn bị sau khi clone

**Dự án được bàn giao với database trống.** Repository chứa script tạo database và mã định nghĩa bảng; không kèm bản xuất dữ liệu MySQL, lịch sử phân loại, ảnh chụp hoặc cấu hình camera của máy người phát triển. Người clone tạo database mới theo mục 5; backend tự tạo các bảng khi khởi động.

| Thành phần | Cách chuẩn bị trên máy mới |
| --- | --- |
| Cấu hình `.env` | Sao chép từ `.env.example`, chỉnh theo máy mới |
| Database | Tạo bằng script SQL; backend tự tạo các bảng còn thiếu |
| Ảnh lịch sử | Không có sẵn vì `backend/uploads/` đang được Git bỏ qua |
| Mô hình AI | Kiểm tra checkpoint được bàn giao cùng repository hay chưa |
| Thư viện | Cài lại bằng pip và npm, không sao chép `.venv`/`node_modules` |
| Camera | Nhập URL điện thoại trong mạng của máy mới |

## 4. Cài đặt backend và mô hình AI

### 4.1. Tạo môi trường Python

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-ai.txt --index-url https://download.pytorch.org/whl/cpu
```

Nếu dùng Python 3.11 hoặc 3.12, thay `py -3.13` bằng `py -3.11` hoặc `py -3.12`. Nếu không kích hoạt được môi trường, có thể gọi trực tiếp `.\.venv\Scripts\python.exe` thay cho `python` trong các lệnh sau.

Lệnh cài AI trên dùng bản CPU. `requirements-ai.txt` chọn torch/torchvision 2.5.1/0.20.1 cho Python 3.11–3.12 và 2.6.0/0.21.0 cho Python 3.13.

### 4.2. Kiểm tra checkpoint

```powershell
Test-Path AI_handover/models/orange_classifier_v3_best.pth
```

Kết quả cần là `True`. Nếu repository không kèm checkpoint, nhận tệp từ người bàn giao và đặt vào đúng đường dẫn trên. Backend sử dụng lại mã suy luận trong `AI_handover/predict.py`; không cần huấn luyện lại để chạy ứng dụng.

### 4.3. Tạo cấu hình môi trường

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Chỉ sao chép mẫu khi chưa có `.env`, để giữ cấu hình đã chỉnh trên máy đang sử dụng.

## 5. Cài đặt database MySQL

### 5.1. Tạo database và tài khoản

Từ thư mục gốc, chạy bằng tài khoản MySQL có quyền quản trị tương ứng:

```powershell
mysql -u root -p -e "source backend/create_database.sql"
```

Nhập mật khẩu MySQL khi được yêu cầu. Script tạo database `orange_sorting`, tài khoản mẫu `orange_user` với mật khẩu mẫu `orange_password`, và cấp quyền trên database này.

Nếu đã có tài khoản/database riêng, có thể dùng chúng và chỉnh cấu hình kết nối. Script dùng `CREATE USER IF NOT EXISTS`, nên không đổi mật khẩu của tài khoản đã tồn tại.

### 5.2. Cấu hình kết nối

Mở `backend/.env` và đặt thông tin khớp với MySQL trên máy:

```dotenv
DATABASE_URL=mysql+pymysql://orange_user:orange_password@127.0.0.1:3306/orange_sorting?charset=utf8mb4
FRONTEND_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
CAMERA_SIMULATION_ENABLED=false
```

Thay username, password, host, port và tên database nếu cấu hình của bạn khác ví dụ.

### 5.3. Các bảng được tạo tự động

Khi backend khởi động, SQLAlchemy tạo các bảng còn thiếu trong database đã cấu hình:

| Bảng | Nội dung |
| --- | --- |
| `classifications` | Một bản ghi cho mỗi lượt phân loại |
| `prediction_details` | Lớp AI và xác suất của kết quả chung |
| `capture_sessions` | Phiên chụp camera liên kết với lượt phân loại |
| `capture_images` | Ảnh và kết quả riêng của từng camera trong lượt |
| `camera_configurations` | URL đã lưu của hai camera |
| `camera_orientations` | Góc xoay đã lưu của từng camera |

Không cần tự tạo các bảng này trong MySQL Workbench. Việc tạo bảng không tự chèn dữ liệu mẫu hoặc chuyển lịch sử từ máy khác sang. Cơ chế hiện tại không tự sửa cấu trúc cột của bảng đã tồn tại khi nâng cấp schema.

### 5.4. Trạng thái trên máy cài mới

Với database mới, sau khi hoàn thành cài đặt và chạy backend:

- Các bảng đã được tạo nhưng chưa có lượt phân loại; lịch sử trống và thống kê bằng 0.
- Chưa có URL hoặc góc xoay camera đã lưu. Người dùng nhập URL hai điện thoại của mình trên giao diện.
- Thư mục ảnh được backend tạo nếu chưa có; ảnh mới được lưu khi chụp hoặc tải lên.
- Không cần import bản sao dữ liệu từ máy người phát triển. Các lượt phân loại mới sẽ tự ghi vào database trên máy đang chạy.

Script dùng `IF NOT EXISTS` và không xóa dữ liệu trong database đã tồn tại. Nếu máy nhận đã có database `orange_sorting` chứa dữ liệu, cấu hình một database mới trong `DATABASE_URL` để bắt đầu với lịch sử trống.

## 6. Chạy dự án

### Terminal 1 — Backend

Từ thư mục gốc, sau khi đã kích hoạt `.venv`:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Chạy **một worker** để hai camera dùng chung reader và bộ đệm của tiến trình. Khi khởi động lại backend, URL/góc xoay vẫn được lưu nhưng cần kết nối lại camera.

### Terminal 2 — Frontend

Mở PowerShell thứ hai tại thư mục gốc:

```powershell
Set-Location frontend
npm ci
npm run dev
```

`frontend/.env` mặc định dùng:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

### Địa chỉ kiểm tra

| Địa chỉ | Mục đích |
| --- | --- |
| [http://localhost:5173](http://localhost:5173) | Giao diện web |
| [Trang camera](http://localhost:5173/#/camera) | Camera và các kết quả gần đây |
| [Trang thống kê và lịch sử](http://localhost:5173/#/history) | Thống kê và lịch sử đầy đủ |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu API tương tác |
| [http://localhost:8000/api/health](http://localhost:8000/api/health) | Kiểm tra API đang chạy |
| [http://localhost:8000/api/model](http://localhost:8000/api/model) | Kiểm tra tải mô hình AI |

`/api/health` trả `{"status":"ok"}` xác nhận API hoạt động. Để xác nhận AI hoạt động, kiểm tra `/api/model` có `status: "ready"`; lần tải đầu có thể mất vài giây.

## 7. Kết nối hai điện thoại và phân loại

1. Cho máy tính và hai Android kết nối cùng Wi-Fi.
2. Bật server HTTP/MJPEG trong ứng dụng IP Camera trên từng điện thoại.
3. Nhập URL **luồng video** vào hai ô camera, ví dụ `http://192.168.1.101:8080/video` và `http://192.168.1.102:8080/video`. Thay bằng địa chỉ thực tế của từng điện thoại. URL gốc chỉ có `IP:cổng` có thể là trang quản trị, không phải video.
4. Nhấn **Kết nối** cho từng camera, chờ trạng thái `Connected` và có hình. Dùng **Xoay trái/phải 90°** nếu chiều ảnh chưa đúng.
5. Nhấn **Chụp 2 camera và phân loại** để chạy AI trên cả hai ảnh và lưu chung một lượt lịch sử. Hai ảnh có timestamp và được kiểm tra độ mới/độ lệch thời điểm.
6. Xem bốn lượt mới nhất trong **Kết quả gần đây** dưới camera, mỗi lượt một hàng ngang. Bấm vào ảnh để mở ảnh gốc. Ảnh chụp không hiển thị lặp lại dưới từng camera; mở **Thống kê & lịch sử** ở thanh bên trái để xem toàn bộ dữ liệu.

Hai camera dùng chung một nút **Chụp 2 camera và phân loại**: bấm một lần để chụp cả hai, chạy AI và lưu một lượt có hai ảnh. Nút chỉ khả dụng khi cả hai camera đã kết nối và không có thao tác đang xử lý. Lượt chụp đôi chỉ lưu khi cả hai ảnh được phân loại thành công; nếu thiếu một ảnh hoặc AI lỗi, hệ thống báo lỗi và không tạo lượt thiếu dữ liệu.

Kết quả chung lấy dự đoán có Grade cao hơn (chất lượng thấp hơn); cùng Grade thì chọn độ tin cậy cao hơn. Độ tin cậy/xác suất chung thuộc góc được chọn. Cả hai kết quả riêng vẫn được lưu trong lịch sử.

### Các lớp AI

| Lớp AI | Tên tiếng Việt | Grade / khay |
| --- | --- | --- |
| `fresh_orange` | Cam tươi | 1 |
| `blackspotted_orange` | Cam đốm đen | 2 |
| `cankered_orange` | Cam loét vỏ | 2 |
| `green_orange` | Cam xanh | 3 |
| `rotten_orange` | Cam thối | 3 |

### Thử khi chưa có điện thoại

Đặt `CAMERA_SIMULATION_ENABLED=true` trong `backend/.env` rồi khởi động lại backend. Mỗi camera có nút **Mở luồng mô phỏng riêng**; video và ảnh đều gắn nhãn mô phỏng. Có thể thử luồng chụp đôi, AI và lịch sử, không dùng để đánh giá độ chính xác với quả thật.

Phần **Webcam máy tính, tải ảnh và mô phỏng phân loại** nằm dưới các kết quả gần đây. Tự động theo chuyển động chỉ áp dụng cho webcam trình duyệt: bật webcam, để vùng chụp trống rồi bật tự động. Vật khác, rung camera hoặc thay đổi ánh sáng cũng có thể kích hoạt. Nút **Giả lập quả đi qua** dùng ảnh và nhãn minh họa, không chạy AI.

Hướng dẫn camera, whitelist địa chỉ, xem web từ điện thoại và xử lý lỗi chi tiết: [CAMERAS.md](CAMERAS.md).

## 8. Kiểm thử và build

Từ thư mục gốc, trong môi trường `.venv`:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q -p no:cacheprovider
```

Kiểm thử backend dùng database SQLite và thư mục ảnh riêng trong `.task-temp/`, không sử dụng MySQL/ảnh vận hành. Kiểm thử mô hình thật được bỏ qua khi thiếu thư viện AI hoặc checkpoint.

Kiểm thử frontend và tạo bản build:

```powershell
Set-Location frontend
npm test
npm run build
```

## 9. Lỗi thường gặp khi cài trên máy mới

| Hiện tượng | Kiểm tra |
| --- | --- |
| Không tìm thấy lệnh `mysql` | Cài MySQL client và thêm thư mục `bin` vào PATH hoặc gọi đường dẫn đầy đủ |
| `Access denied for user` | Username/password và quyền MySQL có khớp `DATABASE_URL` không; script không đổi mật khẩu user đã tồn tại |
| `Unknown database` | Đã tạo database và điền đúng tên trong `.env` chưa |
| Không kết nối được MySQL | Dịch vụ MySQL đang chạy, đúng host/cổng chưa |
| API chạy nhưng AI chưa sẵn sàng | Đúng `.venv`, đã cài requirements AI và có checkpoint đúng đường dẫn chưa |
| Lịch sử trống sau clone | Đúng với bản bàn giao database trống; chụp và phân loại để tạo các lượt mới |
| Lịch sử có kết quả nhưng thiếu ảnh | Sao chép thêm các tệp tương ứng trong `uploads/` |
| Camera mở trên điện thoại nhưng web báo sai luồng | Dùng URL video HTTP/MJPEG, thường có `/video`, không dùng trang quản trị |
| Camera timeout/từ chối kết nối | Kiểm tra ứng dụng phát video, IP/cổng, Wi-Fi và tường lửa; dùng IP thực tế trên mạng mới |
| Frontend không gọi được API | Kiểm tra backend cổng 8000, `VITE_API_BASE_URL` và `FRONTEND_ORIGINS`; khởi động lại ứng dụng sau khi đổi `.env` |

## 10. Tài liệu liên quan và phần cứng

- [CAMERAS.md](CAMERAS.md): kết nối camera Android, cấu hình, API và kiểm thử camera.
- [AI_INTEGRATION.md](AI_INTEGRATION.md): mô hình bàn giao, preprocessing, ánh xạ lớp và chi tiết tích hợp.
- [backend/.env.example](backend/.env.example): cấu hình backend mẫu.
- [frontend/.env.example](frontend/.env.example): cấu hình frontend mẫu.
- [backend/create_database.sql](backend/create_database.sql): tạo database và tài khoản MySQL mẫu.

Tài liệu API đầy đủ có tại `/docs` khi backend đang chạy. API thiết bị hiện nhận kết quả có sẵn qua `POST /api/device/classifications/json` với `prediction`, `score`, `image_url`; URL ảnh chỉ được lưu, không được tải về chạy AI. `POST /api/device/classifications/image` nhận tệp ảnh, có thể để backend suy luận nếu không gửi prediction/score.

Hai API `POST /api/device/events/fruit-arrived` và `POST /api/device/events/sorting-completed` hiện chỉ xác nhận nhận sự kiện, chưa tạo lệnh điều khiển phần cứng.

Khi đưa dự án lên GitHub, giữ các tệp `.env.example`, script tạo database, requirements và `package-lock.json` trong repository. Giữ thông tin kết nối thực tế trong `.env` riêng của từng máy. Các tệp SQLite thử nghiệm như `test.db` ở thư mục gốc không thay thế database MySQL đang vận hành; nên bỏ chúng khỏi bản mã nguồn bàn giao.
