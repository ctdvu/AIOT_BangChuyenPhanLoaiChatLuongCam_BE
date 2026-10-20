# Hai camera Android qua HTTP/MJPEG

Frontend hiện có là React 18 + Vite; backend là FastAPI + SQLAlchemy. Trang chính bổ sung hai camera IP, giữ phần webcam, tải ảnh, phát hiện chuyển động qua webcam, mô phỏng phân loại, lịch sử và thống kê trong dự án. Không thay đổi `AI_handover`, checkpoint, preprocessing hoặc phần cứng IoT.

## Chạy với hai điện thoại thật

Từ thư mục gốc dự án, cài dependencies vào môi trường hiện có:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Giữ cấu hình database trong `backend/.env` theo README. Backend tự tạo thêm bảng `camera_configurations`; không sửa bảng phân loại cũ. Nếu cần chạy AI, cài thêm `backend/requirements-ai.txt` theo hướng dẫn AI hiện có.

```powershell
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Chạy **một worker**: các reader và khung hình nằm trong bộ nhớ của tiến trình. Không dùng `--workers` lớn hơn 1. Khởi động lại backend sẽ ngắt camera; URL vẫn được giữ trong database. Chỉ chuyển sang `Connected` sau khi nhận và giải mã được ảnh đầu tiên.

Terminal thứ hai:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Mở `http://localhost:5173` trên máy tính.

Thanh điều hướng nằm bên trái với hai trang:

- **Camera & phân loại** (`/#/camera`): hai camera và **4 lượt phân loại mới nhất ngay bên dưới camera**. Mỗi lượt hiển thị ảnh, kết quả từng góc nhìn và kết quả chung. Có liên kết mở toàn bộ lịch sử và mục thu gọn xem chi tiết kết quả mới nhất.
- **Thống kê & lịch sử** (`/#/history`): thống kê tổng số quả và lịch sử đầy đủ có phân trang. Duyệt trang lịch sử cũ không làm thay đổi danh sách kết quả gần đây trên trang camera.

Chuyển trang giữ nguyên URL đang nhập và tác vụ camera hiện tại. Trên điện thoại, mở thanh bên bằng nút menu ở góc trên trái; có thể đóng bằng Esc. Tải lại trang hoặc nút quay lại của trình duyệt vẫn mở đúng trang đã chọn.

1. Kết nối máy tính và hai Android vào cùng Wi-Fi. Tắt chế độ cô lập thiết bị/client isolation của Wi-Fi nếu đang bật.
2. Trên mỗi điện thoại, mở ứng dụng IP Camera hỗ trợ **HTTP/MJPEG**, cấp quyền camera và bật server phát video. Giữ ứng dụng hoạt động; nếu cần, tắt tối ưu pin cho ứng dụng đó.
3. Sao chép **URL luồng video**, không phải trang quản trị, URL RTSP hoặc URL ảnh tĩnh. Ví dụ tài liệu: `http://192.168.1.101:8080/video` và `http://192.168.1.102:8080/video`. Dùng địa chỉ thực tế ứng dụng cung cấp.
4. Nhập URL tương ứng Camera 1 (phía trên), Camera 2 (bên cạnh), nhấn **Kết nối** cho từng camera. URL được lưu khi kết nối; cũng có thể nhấn **Lưu URL** riêng mà không mở luồng.
5. Chờ trạng thái `Connecting` chuyển thành `Connected` và có hình. Mỗi camera có nút ngắt, kết nối lại, chụp ảnh và phóng to riêng. Thoát toàn màn hình bằng Esc hoặc thao tác quay lại của thiết bị.
   Nếu điện thoại đặt dọc nhưng hình nằm ngang, dùng **Xoay trái 90° / Xoay phải 90°** bên dưới video. Mỗi camera lưu góc riêng (0/90/180/270°) trên server và áp dụng ngay cho video, ảnh chụp tiếp theo và ảnh gửi AI. Không cần kết nối lại. Ảnh đã lưu trước đó giữ nguyên. MJPEG thường không cung cấp hướng cầm điện thoại nên cần chọn góc phù hợp bằng các nút này.
6. Nhấn **Chụp 2 camera và phân loại**. Backend lấy hai ảnh trong cùng phiên, chạy mô hình hiện có trên từng ảnh rồi lưu **một lượt lịch sử có đủ hai ảnh**, kết quả từng camera, timestamp, góc xoay và kết quả chung. Thống kê chỉ tăng **1 quả**. Ảnh được hiển thị trong **Kết quả gần đây**, mỗi lượt một hàng ngang, không lặp lại dưới từng camera. Bấm ảnh để mở ảnh gốc; hai ảnh cũng nằm chung một lượt trong lịch sử đầy đủ.
7. Giao diện hai camera dùng **một nút chụp chung**, không cần bấm chụp riêng từng camera. Nút chỉ bật khi cả hai camera đã kết nối và không có thao tác đang xử lý. Webcam/tải ảnh vẫn dùng API phân loại cũ. Với lượt hai ảnh, kết quả chung lấy dự đoán có Grade cao hơn (chất lượng thấp hơn); cùng Grade thì chọn dự đoán có độ tin cậy cao hơn. Xác suất/độ tin cậy chung thuộc góc được chọn, không phải xác suất tổng hợp của mô hình hai đầu vào. Giao diện hiển thị rõ quy tắc và giữ đầy đủ kết quả riêng của hai góc nhìn.
8. Tải lại trang để xác nhận URL được giữ. Thử ngắt Camera 1: Camera 2 phải vẫn phát và chụp được. Sau đó kết nối lại Camera 1.

Nếu xem web từ điện thoại: chạy Vite với `npm run dev -- --host 0.0.0.0`; đặt `VITE_API_BASE_URL` trong `frontend/.env` thành `http://IP_MAY_TINH:8000`, thêm origin web tương ứng vào `FRONTEND_ORIGINS` của backend rồi khởi động lại cả hai. Mở quyền tường lửa cho các cổng cần dùng trên mạng riêng.

## Trạng thái và xử lý lỗi

| Hiện tượng | Việc cần kiểm tra |
| --- | --- |
| Chưa nhập URL / URL sai định dạng | Nhập đủ `http(s)://IP:cổng/đường-dẫn-video`. Không dùng URL có tài khoản hoặc `#fragment`. |
| Connecting | Backend đang mở HTTP và chờ JPEG đầu tiên; chưa xác nhận camera đã hoạt động. |
| Hết thời gian phản hồi | Server trên điện thoại đã bật chưa; đúng IP/cổng chưa; máy tính và điện thoại có thấy nhau qua Wi-Fi không; tường lửa/router có chặn không. Không thể suy ra chính xác nguyên nhân chỉ từ timeout. |
| Từ chối kết nối | Kiểm tra cổng và ứng dụng camera server. Một số hệ điều hành có thể trả timeout cho cổng đóng. |
| HTTP 401/403 | Camera đang yêu cầu xác thực/quyền truy cập. Phiên bản này không nhận tài khoản trong URL. |
| HTTP 404 / URL không phải MJPEG | Dùng đúng đường dẫn video do ứng dụng cung cấp, không dùng trang quản trị. |
| Camera trả chuyển hướng | Nhập URL MJPEG đích trực tiếp; backend không đi theo redirect. |
| Không có khung hình mới / camera đóng luồng | Bật lại ứng dụng, kiểm tra Wi-Fi, nhấn Kết nối lại. Không tự chụp lại ảnh cũ. |
| Luồng hiển thị gián đoạn | Nhấn Kết nối lại để mở lại viewer. Các viewer không mở thêm kết nối tới điện thoại. |
| API mất kết nối | Kiểm tra FastAPI và cấu hình API/CORS; giao diện ẩn video và hiển thị trạng thái chưa xác định đến khi lấy lại trạng thái thật. |
| AI chưa sẵn sàng | Kiểm tra dependencies/checkpoint theo `AI_INTEGRATION.md`; xem thông báo AI phía trên. Ảnh chụp camera vẫn lưu riêng trong uploads. |

## Cấu hình và bảo vệ URL

Tham khảo các biến trong `backend/.env.example`:

```dotenv
CAMERA_ALLOWED_HOSTS=[]
CAMERA_SIMULATION_ENABLED=false
CAMERA_CONNECT_TIMEOUT=5
CAMERA_READ_TIMEOUT=3
CAMERA_FRAME_MAX_AGE=2
CAMERA_PAIR_MAX_SKEW=0.25
```

Mặc định cho phép các dải LAN IPv4 `10/8`, `172.16/12`, `192.168/16` và IPv6 ULA `fc00::/7`. Hostname được kiểm tra toàn bộ IP phân giải được; kết nối được ghim vào IP đã kiểm tra. Các địa chỉ ngoài LAN chỉ được phép khi hostname/IP nằm chính xác trong danh sách JSON `CAMERA_ALLOWED_HOSTS`. Link-local (bao gồm địa chỉ metadata), multicast, unspecified và IPv4-mapped IPv6 luôn bị chặn. Loopback chỉ được dùng khi cho phép rõ ràng, ví dụ `CAMERA_ALLOWED_HOSTS=["127.0.0.1"]` cho server MJPEG kiểm thử.

Backend kiểm soát HTTP/HTTPS bằng thư viện chuẩn Python, không dùng proxy môi trường và không đi theo redirect. Dữ liệu JPEG được [OpenCV `imdecode`/`imencode`](https://docs.opencv.org/4.x/d4/da8/group__imgcodecs.html) giải mã, kiểm tra và mã hóa lại. Đây là lựa chọn có chủ ý thay cho việc đưa URL tùy ý thẳng vào `VideoCapture`/FFmpeg, để có thể kiểm soát DNS và chuyển hướng. HTTPS kiểm tra chứng chỉ thông thường.

Mỗi camera chỉ có một reader thread. Các viewer dùng chung khung hình JPEG bất biến trong bộ nhớ. Truy cập buffer có khóa; khi ngắt/kết nối lại, reader cũ phải dừng trước khi reader mới chạy, socket và response được đóng. Không có tiến trình camera mới cho mỗi request xem video. Lỗi một reader chỉ cập nhật camera tương ứng. Kết nối lại là thao tác chủ động bằng nút trên giao diện.

Mỗi camera giữ tối đa 30 khung hình. Chụp riêng dùng ảnh mới nhất còn trong giới hạn tuổi. Chụp đôi chọn hai ảnh gần thời điểm nhận nhau, chờ tối đa `CAMERA_FRAME_MAX_AGE` để có cặp trong giới hạn `CAMERA_PAIR_MAX_SKEW`; nếu thiếu ảnh, ảnh cũ hoặc lệch quá nhiều, API trả lỗi và không lưu cặp không đầy đủ. Timestamp UTC là **thời điểm backend nhận/giải mã khung hình**, không phải timestamp màn trập của điện thoại. HTTP/MJPEG không bảo đảm hai máy chụp đồng bộ vật lý.

Ảnh lưu tại `UPLOAD_DIR` hiện có, tên `camera-ID-SESSION.jpg`. Hệ thống chưa tự xóa ảnh cũ; dọn thư mục theo nhu cầu dung lượng. Cấu hình URL được lưu phía backend; URL không được hardcode trên giao diện. Lưu URL chỉ kiểm tra định dạng, còn quyền địa chỉ và khả năng nhận video được xác minh khi kết nối.

## API

| Endpoint | Nội dung |
| --- | --- |
| `POST /api/cameras/connect` | JSON `{"camera_id":1,"url":"http://IP:PORT/video"}`; trả 202, trạng thái thực tế tiếp tục cập nhật qua polling. Gọi lại để reconnect. |
| `POST /api/cameras/disconnect` | JSON `{"camera_id":1}`. |
| `GET /api/cameras/status` | Trả `cameras` gồm URL, trạng thái, lỗi, timestamp, tuổi ảnh, generation, cờ simulation; và `simulation_enabled`. |
| `PUT /api/cameras/{camera_id}/config` | JSON `{"url":"http://IP:PORT/video"}` để lưu URL mà không mở camera. |
| `PUT /api/cameras/{camera_id}/rotation` | JSON `{"rotation":90}`; nhận 0/90/180/270 độ theo chiều kim đồng hồ, lưu riêng từng camera. |
| `GET /api/cameras/{camera_id}/stream` | MJPEG chỉ khi camera đã nhận ảnh; lỗi 409 khi chưa kết nối. |
| `POST /api/cameras/{camera_id}/capture` | Chụp một camera. |
| `POST /api/cameras/capture` | Chụp cả hai; cùng `session_id`, timestamp riêng từng ảnh, trả `skew_ms`. |

Camera ID chỉ là 1 hoặc 2. Response chụp ảnh gồm `images` với `camera_id`, `timestamp`, `image_url`, `simulation`. `image_url` là đường dẫn tương đối trên backend, không phải địa chỉ IP điện thoại.

### Phân loại và lưu lượt camera

- `POST /api/cameras/classify`: chụp, phân loại cả hai camera và lưu một lượt. Trả HTTP 201 với `capture` và `classification`.
- `POST /api/cameras/{camera_id}/classify`: chụp, phân loại và lưu lượt một camera.
- Lượt trả thêm `capture_session_id`, `capture_skew_ms`, `aggregation_policy` và `images`. Mỗi ảnh có ID camera, URL ảnh, timestamp UTC, góc xoay, cờ mô phỏng, lớp AI, Grade, độ tin cậy và đủ 5 xác suất.
- `/api/classifications`, `/api/classifications/latest` trả cùng cấu trúc mở rộng. Bản ghi cũ có `images=[]`, vẫn hiển thị ảnh cũ như trước. Phân trang, tổng lượt và thống kê đều tính theo bản ghi lượt, không đếm mỗi ảnh thành một quả riêng.
- Hai bảng mới `capture_sessions` và `capture_images` liên kết với một bản ghi `classifications`, tự tạo khi khởi động. Không cần thay cấu trúc các bảng lịch sử cũ.
- Chỉ commit khi cả hai ảnh đã suy luận thành công. Nếu một camera thiếu ảnh hoặc một lần suy luận thất bại, API báo lỗi, không tạo lượt thiếu ảnh và dọn các tệp của lượt thất bại. Không tự ghép các bản ghi cũ thành lượt vì chúng thiếu thông tin xác nhận cùng phiên chụp.

## Mô phỏng và kiểm thử

Không có hai Android thật trong môi trường phát triển này. Để bật luồng tổng hợp riêng, đặt `CAMERA_SIMULATION_ENABLED=true` và khởi động lại backend. Trên mỗi panel sẽ có **Mở luồng mô phỏng riêng**. Luồng và ảnh đều gắn nhãn **MÔ PHỎNG**, có cờ `simulation=true`; không thay đổi URL camera thật đã lưu. Tắt lại biến này sau khi kiểm tra. API mô phỏng: `POST /api/cameras/connect` với JSON `{"camera_id":1,"simulation":true}`.

Kiểm thử tự động dùng thêm server HTTP/MJPEG giả lập qua socket thật, database và uploads riêng; không truy cập điện thoại thật:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q -p no:cacheprovider
Set-Location frontend
npm test
npm run build
```

Bao phủ: hai reader HTTP riêng, chụp đơn/đôi, ngắt và reconnect, camera đóng luồng không ảnh hưởng camera còn lại, timeout, từ chối kết nối, ngăn redirect, whitelist và DNS nhiều IP, URL sai, ảnh cũ/lệch thời gian, trạng thái mô phỏng và lưu cấu hình. Các kiểm thử AI cũ tiếp tục chạy. Kiểm tra Chrome riêng xác nhận hai viewer cùng lúc, ảnh chụp, AI hiện có, toàn màn hình, tải lại cấu hình, mất/phục hồi API và bố cục 390px.

Kết quả kiểm tra trong môi trường phát triển: **44 kiểm thử backend**, **6 kiểm thử frontend** đạt; `npm run build` thành công. Kiểm thử lượt hai ảnh xác nhận chạy AI hai lần, lưu một lượt và hai ảnh, thống kê tăng một, giữ đúng kết quả/timestamp/góc xoay của từng camera, phân trang cùng bản ghi cũ, dọn toàn bộ lượt khi AI ảnh thứ hai hoặc giao dịch DB thất bại. Kiểm thử xoay xác nhận chiều pixel, kích thước ảnh chụp, video dùng chung chiều, giữ tuổi khung hình, góc riêng từng camera và khôi phục sau khi khởi động lại. Chrome xác nhận chạy AI thật trên hai ảnh mô phỏng, một dòng lịch sử có hai ảnh sau tải lại trang, desktop/mobile và không có lỗi JavaScript. Đây là kiểm chứng phần mềm với luồng/ảnh mô phỏng; vẫn cần làm các bước kiểm tra bằng hai điện thoại thật ở phần đầu tài liệu.

## File đã tạo/chỉnh sửa

- Tạo `backend/app/services/cameras.py`: quản lý reader, kiểm soát URL/HTTP, OpenCV, buffer, độ mới và ghép cặp ảnh.
- Tạo `backend/app/services/camera_classifications.py`: suy luận từng góc nhìn, chọn kết quả chung và lưu nguyên lượt trong một giao dịch.
- Tạo `backend/app/routers/cameras.py`: API camera và lưu ảnh.
- Tạo `backend/tests/test_cameras.py`: kiểm thử camera với HTTP/MJPEG giả lập.
- Sửa `backend/app/config.py`, `backend/app/models.py`, `backend/app/main.py`: cấu hình, bảng URL và vòng đời reader.
- Góc xoay được lưu trong bảng mới `camera_orientations`, tự tạo khi khởi động; không thay đổi cấu trúc bảng URL hiện có.
- Sửa `backend/requirements.txt`, `backend/.env.example`: OpenCV và biến môi trường camera.
- Tạo `frontend/src/components/IpCameras.jsx`: hai panel camera, polling, xem/chụp/phân loại ảnh, trạng thái/lỗi, mô phỏng.
- Tạo `frontend/src/components/ClassificationImages.jsx`; sửa `HistoryTable.jsx`, `LatestResult.jsx`, `Stats.jsx`: hiển thị hai ảnh và kết quả mỗi góc trên cùng lượt, thống kê theo lượt.
- Tạo `frontend/src/components/RecentResults.jsx`; sửa `App.jsx` và `styles.css`: hai trang với điều hướng bên trái, 4 kết quả mới nhất dưới camera, menu thu gọn trên điện thoại và giữ trạng thái camera khi đổi trang.
- Sửa `backend/app/schemas.py`, `backend/app/services/responses.py`: dữ liệu lượt có danh sách ảnh, giữ tương thích dữ liệu cũ.
- Sửa `frontend/src/api.js`, `frontend/src/App.jsx`, `frontend/src/styles.css`: API client, bố cục và giao diện đáp ứng.
- Tạo `CAMERAS.md`, bổ sung liên kết trong `README.md`.

Artifact kiểm tra tạm ở `.task-temp/two-camera-check/`; các tệp build trong `frontend/dist/` được tạo lại bằng Vite.
