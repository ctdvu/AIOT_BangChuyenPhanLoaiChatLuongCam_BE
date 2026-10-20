# Tích hợp AI_handover vào backend và frontend

## Nội dung bàn giao đã phân tích

- `AI_handover/predict.py`: EfficientNet-B0, thay lớp classifier bằng `Linear(1280, 5)`, dùng `eval()`, `torch.no_grad()` và softmax. `load_model()` kiểm tra 5 lớp và thứ tự `class_to_idx`, chọn CPU/CUDA tự động.
- `AI_handover/requirements.txt`: torch 2.5.1, torchvision 0.20.1, Pillow 12.3.0.
- `AI_handover/models/orange_classifier_v3_best.pth`: checkpoint khoảng 48,7 MB, chứa trọng số, thứ tự lớp, grade mapping, cấu hình preprocessing và thông tin huấn luyện. Đã mở bằng `torch.load(..., weights_only=True)`, đối chiếu classifier có kích thước `(5, 1280)`.

Thứ tự đầu ra là `blackspotted_orange`, `cankered_orange`, `fresh_orange`, `green_orange`, `rotten_orange`. Preprocessing: chuyển RGB → Resize(256) → CenterCrop(224) → ToTensor → Normalize với mean `[0.485, 0.456, 0.406]`, std `[0.229, 0.224, 0.225]`. Metadata trong checkpoint khớp với mã bàn giao.

| Lớp AI | Tên tiếng Việt | Grade / khay | Nhãn lưu tương thích |
| --- | --- | --- | --- |
| `fresh_orange` | Cam tươi | 1 | `CAM_DEP` |
| `blackspotted_orange` | Cam đốm đen | 2 | `CAM_KHUYET_TAT` |
| `cankered_orange` | Cam loét vỏ | 2 | `CAM_KHUYET_TAT` |
| `green_orange` | Cam xanh | 3 | `CAM_HONG` |
| `rotten_orange` | Cam thối | 3 | `CAM_HONG` |

Các file bàn giao và checkpoint được giữ nguyên. Backend gọi trực tiếp các hàm của file bàn giao qua đường dẫn tuyệt đối của dự án, nên không phụ thuộc thư mục đang mở terminal.

## Backend đã sửa

| File | Thay đổi và mục đích |
| --- | --- |
| `backend/app/predictor.py` | Bỏ kết quả cố định `CAM_DEP / 0.94`; tải/cached mô hình thật, gọi suy luận gốc, trả lớp thắng và 5 xác suất, kiểm tra grade mapping. Khóa truy cập để tránh tải mô hình đồng thời. |
| `backend/app/constants.py` | Bổ sung 5 lớp, tên tiếng Việt, ánh xạ Grade; đổi tên khay 3 thành “Cam xanh hoặc thối”. Giữ 3 mã nhãn cũ. |
| `backend/app/models.py` | Thêm bảng `prediction_details` liên kết 1–1 với `classifications`, lưu `ai_class` và JSON xác suất. Không thay cấu trúc bảng cũ. |
| `backend/app/schemas.py`, `services/responses.py` | API trả `grade`, `ai_class`, `ai_display_name`, `probabilities`; mở rộng thống kê 5 lớp và schema trạng thái AI. |
| `backend/app/routers/classifications.py` | Ảnh không có nhãn chạy AI trong worker thread, không chặn event loop. Lưu lớp/xác suất trong cùng giao dịch; trả 503 và dọn ảnh khi AI lỗi. Thống kê thêm 5 lớp. |
| `backend/app/device_adapter.py`, `routers/device.py` | Nhận tên lớp AI và mã nhãn cũ; thiết bị có thể gửi ảnh không kèm prediction/score để backend suy luận. Vẫn hỗ trợ thiết bị gửi kết quả có sẵn. |
| `backend/app/main.py` | Thêm `GET /api/model`, cập nhật mô tả/version API. |
| `backend/app/services/images.py` | Sửa đường dẫn xóa ảnh khi `UPLOAD_DIR` được cấu hình riêng; dùng chính thư mục upload thay vì suy ra từ thư mục cha. |
| `backend/requirements.txt`, `requirements-ai.txt` | Đồng bộ Pillow 12.3.0; tách dependencies AI và chọn cặp PyTorch/torchvision theo Python. |
| `backend/.env.example` | Sửa URL MySQL bị lặp phần `charset`; dùng tài khoản mẫu khớp script tạo database. |
| `backend/tests/conftest.py`, `test_api.py`, `test_ai_integration.py` | Test dùng database/upload độc lập; kiểm tra 5 lớp, dữ liệu cũ, xác suất, lỗi AI và checkpoint thật. |

Mỗi tiến trình backend tải mô hình một lần. Lần tải đầu xảy ra khi kiểm tra `/api/model` hoặc gửi ảnh suy luận; thay checkpoint cần restart backend. Nếu AI chưa sẵn sàng, API lịch sử/thống kê và mô phỏng vẫn hoạt động.

Thiết bị gửi URL ảnh chỉ lưu URL và kết quả đã suy luận, không tự tải URL để chạy mô hình. Endpoint ảnh chấp nhận prediction/score theo cặp; chỉ gửi một trong hai trả 422. Xác suất 5 lớp chỉ có khi backend thực sự chạy mô hình; thiết bị gửi lớp/score sẵn sẽ có lớp chi tiết và `probabilities=null`.

## Frontend đã sửa

| File | Thay đổi và mục đích |
| --- | --- |
| `frontend/src/api.js` | Chỉ gửi label/confidence khi có giá trị; tải ảnh thật không gửi nhãn giả. Thêm gọi trạng thái AI. |
| `frontend/src/App.jsx` | Luồng phân loại AI, trạng thái tải mô hình và thông báo lỗi thao tác riêng; lỗi thao tác không bị polling xóa mất. |
| `frontend/src/components/CameraPanel.jsx` | Tải ảnh JPEG/PNG/WebP, xem ảnh tải lên, chụp webcam và gửi ảnh đến AI. Giữ nút mô phỏng với mô tả rõ độ tin cậy giả. |
| `frontend/src/components/LatestResult.jsx` | Hiển thị lớp cam, Grade/khay, nguồn kết quả và thanh xác suất của 5 lớp, sắp xếp giảm dần. |
| `frontend/src/components/HistoryTable.jsx` | Lịch sử có lớp AI chi tiết và tên nguồn kết quả. |
| `frontend/src/components/Stats.jsx` | Tên khay từ API, thêm thống kê 5 lớp; giải thích vì sao tổng theo lớp có thể nhỏ hơn tổng theo khay. |
| `frontend/src/categories.js`, `samples.js`, `styles.css` | Tập trung tên lớp/nguồn, đồng bộ tên mẫu theo Grade, thêm bố cục cho trạng thái AI/xác suất/thống kê. |

Mô phỏng vẫn gửi ba ảnh minh họa SVG chuyển PNG cùng nhãn và độ tin cậy giả. Không dùng ảnh minh họa để tuyên bố chất lượng mô hình.

## Môi trường và cách chạy

Môi trường hiện tại là Python 3.13.5. Đã cài trong `.venv` của dự án: torch 2.6.0+cpu, torchvision 0.21.0+cpu và Pillow 12.3.0. Phiên bản torch/torchvision khác bàn giao vì cặp 2.5.1/0.20.1 không có wheel Windows cho Python 3.13. `requirements-ai.txt` giữ cặp bàn giao trên Python 3.11/3.12 và chọn cặp mới trên 3.13. Tham khảo [các phiên bản và cặp thư viện PyTorch chính thức](https://docs.pytorch.org/get-started/previous-versions/), [wheel torchvision 0.20.1](https://pypi.org/project/torchvision/0.20.1/), [wheel torch 2.6.0](https://pypi.org/project/torch/2.6.0/).

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
pip install -r backend/requirements-ai.txt --index-url https://download.pytorch.org/whl/cpu
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

Trong terminal khác:

```powershell
Set-Location frontend
npm run dev
```

Thiết lập MySQL/`.env` theo README nếu chưa có. Sau khi restart backend, truy cập `/api/model` hoặc nút “Kiểm tra AI” trên giao diện để kiểm tra tải checkpoint. Bảng bổ sung tự tạo khi khởi động.

## Kiểm chứng

- 17 kiểm thử backend đạt, có kiểm thử suy luận checkpoint thật và so sánh xác suất API với `predict_image()` gốc.
- `npm run build` thành công.
- `pip check` không phát hiện xung đột dependencies.
- Chrome/Playwright: tải ảnh thật qua API, chụp webcam giả lập, mô phỏng và thống kê đạt; không có lỗi JavaScript. Kiểm tra màn hình 390px và sửa lỗi tràn ngang của panel camera. Ảnh chụp giao diện nằm trong `.task-temp/ai-browser-check/`.
- Khởi động ứng dụng với MySQL đang cấu hình trong `backend/.env`: health, model, stats và history đều trả 200; bảng `prediction_details` đã tạo thành công và số bản ghi `classifications` cũ không đổi.
- Kiểm thử dùng ảnh tổng hợp và webcam giả lập để xác nhận luồng phần mềm; không đánh giá độ chính xác trên cam thực tế. Folder bàn giao chưa có bộ ảnh test có nhãn.
- Chưa kiểm chứng phần cứng băng chuyền thật. Hai endpoint sự kiện phần cứng vẫn chỉ xác nhận tín hiệu như trước.

## Bổ sung: tự chụp khi có chuyển động qua webcam

Đã triển khai lựa chọn **Phát hiện chuyển động qua webcam**. Khi bật tự động, trình duyệt lấy nền trống, theo dõi vùng nét đứt giữa video, tự chụp vùng đó và gửi `POST /api/classifications` không kèm nhãn, nên backend chạy mô hình thật và lưu kết quả như luồng tải ảnh. Không thay đổi checkpoint, ánh xạ khay hoặc API phần cứng.

Các file bổ sung/chỉnh sửa:

- `frontend/src/arrivalDetector.js`: bộ so sánh nền, trạng thái lấy nền/chờ vật/chờ vùng trống; quy đổi vùng hiển thị sang tọa độ ảnh gốc để ảnh chụp đúng khung nét đứt trên camera ngang hoặc dọc.
- `frontend/src/components/CameraPanel.jsx`: bật/tắt tự động, khung vùng chụp, độ nhạy, lấy lại nền, đếm kết quả thành công; khóa chụp/gửi đồng thời, dừng khi tắt webcam hoặc AI lỗi.
- `frontend/src/App.jsx`: trả kết quả thành công/thất bại cho panel camera để bộ tự động xử lý lỗi.
- `frontend/src/styles.css`: bố cục khung chụp và điều khiển.
- `frontend/tests/arrivalDetector.test.js`, `frontend/package.json`: thêm `npm test` với 6 kiểm thử chống nhiễu, chụp lặp, khoảng nghỉ, chặn khi đang xử lý, lấy lại nền và tọa độ vùng chụp.
- `README.md`: hướng dẫn sử dụng và giới hạn chế độ tự động.

Thông số mặc định: đọc vùng ảnh 80×60 mỗi 120 ms; trung bình 10 khung hình nền (~1,2 giây); điểm ảnh có chênh lệch RGB trung bình từ 35/255 được tính là thay đổi. Ngưỡng diện tích đổi là 12% (cao: 6%, thấp: 20%). Cần 2 khung liên tiếp vượt ngưỡng để kích hoạt, 4 khung trống liên tiếp và khoảng nghỉ ít nhất 1 giây để sẵn sàng lượt tiếp theo. Không tự lấy vật đang đứng yên làm nền mới.

Đã kiểm tra 6 test frontend và build thành công. Chrome với video tổng hợp xác nhận: nền trống không chụp, chuyển động ngoài khung không chụp, vật vào khung được chụp và lưu bằng AI thật, giữ vật tại chỗ không tạo bản ghi lặp, quả thứ hai tạo kết quả tiếp theo, ảnh chụp đúng vùng, lỗi AI tạm dừng tự động, tắt webcam dừng theo dõi và màn hình 390px không tràn ngang. Ảnh giao diện nằm trong `.task-temp/auto-camera-check/`. Chưa kiểm chứng với webcam/băng chuyền thật.

Để dùng: bật webcam → để vùng trống → bật **Tự động chụp khi có chuyển động** → chờ trạng thái sẵn sàng → đưa từng quả đi qua. Đây là phát hiện thay đổi hình ảnh, nên vật khác hoặc thay đổi ánh sáng cũng có thể kích hoạt. Mỗi lần xử lý một ảnh; cần khoảng trống giữa các quả và chờ AI hoàn tất. Tab bị ẩn sẽ tạm ngừng kiểm tra khung hình.
