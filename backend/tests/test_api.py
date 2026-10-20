def test_empty_state(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/classifications/latest").status_code == 404
    history = client.get("/api/classifications").json()
    assert history == {"items": [], "total": 0, "page": 1, "page_size": 10, "total_pages": 0}
    stats = client.get("/api/stats").json()
    assert stats["total"] == 0
    assert [item["count"] for item in stats["by_category"]] == [0, 0, 0]


def test_create_with_simulated_result_and_read_back(client, image_bytes):
    response = client.post(
        "/api/classifications",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
        data={"label": "CAM_KHUYET_TAT", "confidence": "0.87", "source": "simulation"},
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["label"] == "CAM_KHUYET_TAT"
    assert created["tray"] == 2
    assert created["confidence"] == 0.87
    assert created["image_url"].startswith("http://testserver/uploads/")
    assert client.get(created["image_url"]).status_code == 200

    assert client.get("/api/classifications/latest").json()["id"] == created["id"]
    assert client.get("/api/classifications?page=1&page_size=5").json()["total"] == 1
    assert client.get("/api/stats").json()["total"] == 1


def test_predict_when_label_is_missing(client, image_bytes, monkeypatch):
    probabilities = {"blackspotted_orange": 0.01, "cankered_orange": 0.01,
                     "fresh_orange": 0.94, "green_orange": 0.02, "rotten_orange": 0.02}
    monkeypatch.setattr("app.routers.classifications.predict", lambda path: {
        "label": "CAM_DEP", "confidence": 0.94, "ai_class": "fresh_orange",
        "probabilities": probabilities,
    })
    response = client.post(
        "/api/classifications",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["label"] == "CAM_DEP"
    assert body["confidence"] == 0.94
    assert body["source"] == "model"
    assert body["grade"] == 1
    assert body["ai_class"] == "fresh_orange"
    assert body["probabilities"] == probabilities
    assert client.get("/api/classifications/latest").json() == body
    assert client.get("/api/classifications").json()["items"] == [body]


def test_validation(client, image_bytes):
    bad_label = client.post(
        "/api/classifications",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
        data={"label": "SAI_NHAN", "confidence": "0.5"},
    )
    assert bad_label.status_code == 422

    bad_confidence = client.post(
        "/api/classifications",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
        data={"label": "CAM_DEP", "confidence": "1.2"},
    )
    assert bad_confidence.status_code == 422

    bad_image = client.post(
        "/api/classifications",
        files={"image": ("fake.jpg", b"not an image", "image/jpeg")},
        data={"label": "CAM_DEP", "confidence": "0.9"},
    )
    assert bad_image.status_code == 422


def test_device_endpoints(client, image_bytes):
    json_response = client.post(
        "/api/device/classifications/json",
        json={
            "prediction": "CAM_HONG",
            "score": 0.96,
            "image_url": "https://camera.example/orange-01.jpg",
        },
    )
    assert json_response.status_code == 201
    assert json_response.json()["tray"] == 3
    assert json_response.json()["source"] == "device"

    image_response = client.post(
        "/api/device/classifications/image",
        files={"image": ("orange.jpg", image_bytes, "image/jpeg")},
        data={"prediction": "CAM_DEP", "score": "0.91"},
    )
    assert image_response.status_code == 201
    assert image_response.json()["tray"] == 1

    assert client.post("/api/device/events/fruit-arrived").status_code == 202
    assert client.post("/api/device/events/sorting-completed").status_code == 202
