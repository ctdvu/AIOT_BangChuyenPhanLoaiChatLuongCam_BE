import io
from PIL import Image
from app.services.camera_classifications import select_final_prediction


def prediction_sample(ai_class: str, label: str, confidence: float):
    return {
        "ai_class": ai_class,
        "label": label,
        "confidence": confidence,
        "probabilities": {ai_class: confidence},
    }


def make_jpeg_bytes(color=(255, 140, 0)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_select_final_prediction_single_view():
    p1 = prediction_sample("fresh_orange", "CAM_DEP", 0.95)
    selected, policy = select_final_prediction([p1], gap_threshold=0.20)
    assert selected == p1
    assert policy == "single_view"


def test_select_final_prediction_same_grade():
    p1 = prediction_sample("cankered_orange", "CAM_KHUYET_TAT", 0.85)
    p2 = prediction_sample("blackspotted_orange", "CAM_KHUYET_TAT", 0.70)
    selected, policy = select_final_prediction([p1, p2], gap_threshold=0.20)
    assert selected == p1
    assert policy == "same_grade_max_conf"


def test_select_final_prediction_high_confidence_override():
    # Chênh lệch độ tin cậy NHIỀU (> 20%): 0.94 vs 0.60 (diff = 0.34 > 0.20)
    p1 = prediction_sample("fresh_orange", "CAM_DEP", 0.94)
    p2 = prediction_sample("blackspotted_orange", "CAM_KHUYET_TAT", 0.60)
    selected, policy = select_final_prediction([p1, p2], gap_threshold=0.20)
    assert selected == p1
    assert policy == "high_confidence_override"


def test_select_final_prediction_close_confidence_worse_grade():
    # Chênh lệch độ tin cậy ÍT (<= 20%): 0.88 vs 0.82 (diff = 0.06 <= 0.20)
    p1 = prediction_sample("fresh_orange", "CAM_DEP", 0.88)
    p2 = prediction_sample("cankered_orange", "CAM_KHUYET_TAT", 0.82)
    selected, policy = select_final_prediction([p1, p2], gap_threshold=0.20)
    assert selected == p2
    assert policy == "close_confidence_worse_grade"


def test_full_end_to_end_all_apis(client, monkeypatch):
    # Giả lập kết quả AI cho test upload 2 ảnh từ ESP32
    calls = []

    def fake_predict(_path):
        idx = len(calls)
        calls.append(idx)
        if idx % 2 == 0:
            return {
                "ai_class": "fresh_orange",
                "label": "CAM_DEP",
                "grade": 1,
                "confidence": 0.89,
                "probabilities": {"fresh_orange": 0.89},
            }
        return {
            "ai_class": "cankered_orange",
            "label": "CAM_KHUYET_TAT",
            "grade": 2,
            "confidence": 0.81,
            "probabilities": {"cankered_orange": 0.81},
        }

    monkeypatch.setattr("app.services.camera_classifications.predict", fake_predict)

    # 1. Kiểm tra đăng nhập sai mật khẩu -> 401
    bad_login = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad_login.status_code == 401

    # 2. Login Admin & kiểm tra /api/auth/me
    login_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200
    admin_token = login_admin.json()["access_token"]
    assert login_admin.json()["user"]["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    me_admin = client.get("/api/auth/me", headers=admin_headers)
    assert me_admin.status_code == 200
    assert me_admin.json()["user"]["username"] == "admin"

    # 3. Admin tạo nông trại mới (POST /api/admin/farms)
    create_farm_res = client.post(
        "/api/admin/farms",
        headers=admin_headers,
        json={
            "username": "farm_vinhlong",
            "password": "farmpassword",
            "full_name": "Trần Văn Cam",
            "farm_name": "Nông trại Cam Sành Vĩnh Long",
            "location": "Tam Bình, Vĩnh Long",
            "contact_phone": "0988777666",
            "description": "Cam sành chuẩn VietGAP",
            "service_plan": "Gói Cao Cấp",
            "subscription_days": 90,
        },
    )
    assert create_farm_res.status_code == 201
    created_farm = create_farm_res.json()
    new_farm_id = created_farm["id"]
    assert created_farm["name"] == "Nông trại Cam Sành Vĩnh Long"
    assert created_farm["days_remaining"] >= 89

    # 4. Admin gia hạn thêm 30 ngày (PUT /api/admin/farms/{id})
    update_farm_res = client.put(
        f"/api/admin/farms/{new_farm_id}",
        headers=admin_headers,
        json={"extend_days": 30, "service_plan": "Gói Doanh Nghiệp"},
    )
    assert update_farm_res.status_code == 200
    assert update_farm_res.json()["service_plan"] == "Gói Doanh Nghiệp"
    assert update_farm_res.json()["days_remaining"] >= 119

    # 5. Login tài khoản Nông trại vừa tạo & kiểm tra /api/farm/me (GET & PUT)
    login_new_farm = client.post(
        "/api/auth/login", json={"username": "farm_vinhlong", "password": "farmpassword"}
    )
    assert login_new_farm.status_code == 200
    farm_token = login_new_farm.json()["access_token"]
    farm_headers = {"Authorization": f"Bearer {farm_token}"}

    # Nông trại không được gọi API của Admin -> 403
    forbidden_res = client.get("/api/admin/users", headers=farm_headers)
    assert forbidden_res.status_code == 403

    my_farm_get = client.get("/api/farm/me", headers=farm_headers)
    assert my_farm_get.status_code == 200
    api_key = my_farm_get.json()["device_api_key"]

    my_farm_put = client.put(
        "/api/farm/me",
        headers=farm_headers,
        json={
            "location": "Huyện Trà Ôn, Vĩnh Long",
            "contact_phone": "0909111222",
            "cam1_rotation": 90,
            "cam2_rotation": 180,
        },
    )
    assert my_farm_put.status_code == 200
    assert my_farm_put.json()["cam1_rotation"] == 90
    assert my_farm_put.json()["cam2_rotation"] == 180

    # 6. ESP32 gọi /api/device/verify -> Khóa chặt địa chỉ MAC phần cứng
    esp_mac = "AA:BB:CC:DD:EE:01"
    verify_ok = client.post(
        "/api/device/verify",
        headers={"X-Device-Key": api_key, "X-Device-MAC": esp_mac},
    )
    assert verify_ok.status_code == 200
    assert verify_ok.json()["status"] == "verified"
    assert verify_ok.json()["bound_mac_address"] == esp_mac

    # Thiết bị lạ dùng trộm API Key nhưng khác MAC -> bị chặn 403 Forbidden
    verify_spoof = client.post(
        "/api/device/verify",
        headers={"X-Device-Key": api_key, "X-Device-MAC": "FF:FF:FF:00:00:99"},
    )
    assert verify_spoof.status_code == 403

    # 7. Admin Reset MAC -> Mở khóa cho phép đổi mạch ESP32 mới
    reset_mac_res = client.post(f"/api/admin/farms/{new_farm_id}/reset-mac", headers=admin_headers)
    assert reset_mac_res.status_code == 200
    assert reset_mac_res.json()["bound_mac_address"] is None

    # Khóa lại với MAC chính thức
    esp_headers = {"X-Device-Key": api_key, "X-Device-MAC": esp_mac}
    assert client.post("/api/device/verify", headers=esp_headers).status_code == 200

    # 8. ESP32 gửi Heartbeat (POST /api/device/events/heartbeat)
    hb_res = client.post(
        "/api/device/events/heartbeat",
        headers=esp_headers,
        json={"device_id": "esp32-conveyor", "conveyor_state": "running"},
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["online"] is True
    assert hb_res.json()["conveyor_state"] == "running"

    # 9. ESP32 chụp và POST trực tiếp 2 ảnh lên /api/device/classify-upload
    img1 = make_jpeg_bytes((255, 165, 0))
    img2 = make_jpeg_bytes((200, 120, 20))
    upload_res = client.post(
        "/api/device/classify-upload",
        headers=esp_headers,
        files={
            "image_1": ("cam1.jpg", img1, "image/jpeg"),
            "image_2": ("cam2.jpg", img2, "image/jpeg"),
        },
    )
    assert upload_res.status_code == 201
    up_data = upload_res.json()
    assert up_data["status"] == "classified"
    assert up_data["farm_id"] == new_farm_id
    # Chênh lệch 0.89 vs 0.81 = 0.08 (<= 0.20) -> Lấy loại khuyết tật hơn (Grade 2, Tray 2)
    assert up_data["grade"] == 2
    assert up_data["tray"] == 2
    assert up_data["aggregation_policy"] == "close_confidence_worse_grade"
    assert len(up_data["classification"]["images"]) == 2
    cls_id = up_data["classification_id"]

    # 10. ESP32 báo cáo đã gạt cam xong (/api/device/events/sorting-completed)
    done_res = client.post(
        "/api/device/events/sorting-completed",
        headers=esp_headers,
        json={"device_id": "esp32-conveyor", "grade": 2, "tray": 2, "classification_id": cls_id},
    )
    assert done_res.status_code == 202
    assert done_res.json()["sorted_count"] >= 1

    # 11. Chủ nông trại xem kết quả mới nhất, lịch sử và thống kê của vườn mình
    latest_farm = client.get("/api/classifications/latest", headers=farm_headers)
    assert latest_farm.status_code == 200
    assert latest_farm.json()["id"] == cls_id
    assert latest_farm.json()["farm_id"] == new_farm_id

    stats_farm = client.get("/api/stats", headers=farm_headers)
    assert stats_farm.status_code == 200
    assert stats_farm.json()["total"] == 1

    hist_farm = client.get("/api/classifications?page=1&page_size=8", headers=farm_headers)
    assert hist_farm.status_code == 200
    assert hist_farm.json()["total"] == 1

    # 12. Đại lý thu mua đăng ký / đăng nhập và khảo sát nông trại
    reg_dealer = client.post(
        "/api/auth/register-dealer",
        json={
            "username": "dealer_audit",
            "password": "password123",
            "full_name": "Đại Lý Kiểm Định",
            "phone": "0911222333",
        },
    )
    assert reg_dealer.status_code == 201
    dealer_token = reg_dealer.json()["access_token"]
    dealer_headers = {"Authorization": f"Bearer {dealer_token}"}

    dealer_list = client.get("/api/dealer/farms?days=30", headers=dealer_headers)
    assert dealer_list.status_code == 200
    target_stat = next(f for f in dealer_list.json() if f["farm_id"] == new_farm_id)
    assert target_stat["total_fruits"] == 1
    assert target_stat["grade_2_count"] == 1
    assert target_stat["marketable_count"] == 1

    dealer_detail = client.get(f"/api/dealer/farms/{new_farm_id}?days=30", headers=dealer_headers)
    assert dealer_detail.status_code == 200
    detail_json = dealer_detail.json()
    assert detail_json["farm"]["id"] == new_farm_id
    assert len(detail_json["recent_classifications"]) == 1
    assert len(detail_json["recent_classifications"][0]["images"]) == 2
