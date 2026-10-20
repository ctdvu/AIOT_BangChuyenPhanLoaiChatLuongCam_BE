import { useEffect, useRef, useState } from "react";
import { ArrivalDetector, captureRegion } from "../arrivalDetector";

const AUTO_PHASE_NAMES = {
  calibrating: "Đang lấy nền — giữ vùng chụp trống…",
  armed: "Đang chờ quả đi vào vùng chụp",
  "waiting-clear": "Chờ vùng chụp trống để nhận quả tiếp theo",
  busy: "Đang xử lý ảnh…",
  captured: "Đã phát hiện chuyển động — đang chụp…",
};

export default function CameraPanel({ sample, simulating, onSimulate, classifying, onClassify }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const inputRef = useRef(null);
  const previewRef = useRef(null);
  const viewRef = useRef(null);
  const mountedRef = useRef(false);
  const cameraSessionRef = useRef(0);
  const capturingRef = useRef(false);
  const busyRef = useRef(false);
  const captureCallbackRef = useRef(null);
  const autoEnabledRef = useRef(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [openingCamera, setOpeningCamera] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [autoEnabled, setAutoEnabled] = useState(false);
  const [autoPhase, setAutoPhase] = useState("calibrating");
  const [autoCount, setAutoCount] = useState(0);
  const [sensitivity, setSensitivity] = useState("0.12");
  const [baselineVersion, setBaselineVersion] = useState(0);
  const busy = simulating || classifying || capturing;
  busyRef.current = busy;
  autoEnabledRef.current = autoEnabled;

  function stopCamera() {
    cameraSessionRef.current += 1;
    setAutoEnabled(false);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
  }

  async function startCamera() {
    if (openingCamera) return;
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Trình duyệt không hỗ trợ truy cập webcam.");
      return;
    }
    setOpeningCamera(true);
    const session = ++cameraSessionRef.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      if (!mountedRef.current || session !== cameraSessionRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      setCameraOn(true);
    } catch {
      if (mountedRef.current) setCameraError("Không mở được webcam. Hãy cấp quyền camera hoặc dùng ảnh mô phỏng.");
    } finally {
      if (mountedRef.current) setOpeningCamera(false);
    }
  }

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cameraSessionRef.current += 1;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  useEffect(() => {
    if (!autoEnabled || !cameraOn) return undefined;
    const detector = new ArrivalDetector({ threshold: Number(sensitivity) });
    const canvas = document.createElement("canvas");
    canvas.width = 80;
    canvas.height = 60;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const session = cameraSessionRef.current;
    setAutoPhase("calibrating");
    const timer = window.setInterval(() => {
      const video = videoRef.current;
      const view = viewRef.current;
      if (document.hidden || !video?.videoWidth || !video?.videoHeight || !view?.clientWidth) return;
      try {
        const region = captureRegion(video.videoWidth, video.videoHeight, view.clientWidth, view.clientHeight);
        context.drawImage(video, region.x, region.y, region.width, region.height, 0, 0, canvas.width, canvas.height);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        const detection = detector.update(pixels, performance.now(), busyRef.current || capturingRef.current);
        setAutoPhase(detection.phase);
        if (detection.trigger) captureCallbackRef.current({ automatic: true, session });
      } catch {
        setCameraError("Không đọc được khung hình. Chế độ tự động đã tạm dừng; hãy kiểm tra webcam.");
        setAutoEnabled(false);
      }
    }, 120);
    return () => window.clearInterval(timer);
  }, [autoEnabled, cameraOn, sensitivity, baselineVersion]);

  function showPreview(image) {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(image);
    setPreviewUrl(previewRef.current);
  }

  async function uploadImage(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setCameraError("");
    stopCamera();
    showPreview(file);
    await onClassify(file, file.name);
  }

  async function captureImage({ automatic = false, session = cameraSessionRef.current } = {}) {
    if (busyRef.current || capturingRef.current || session !== cameraSessionRef.current) return false;
    setCameraError("");
    const video = videoRef.current;
    if (!video?.videoWidth || !video?.videoHeight) {
      setCameraError("Webcam chưa có khung hình. Hãy thử lại sau một chút.");
      if (automatic) setAutoEnabled(false);
      return false;
    }
    capturingRef.current = true;
    setCapturing(true);
    try {
      const canvas = document.createElement("canvas");
      const view = viewRef.current;
      const region = automatic
        ? captureRegion(video.videoWidth, video.videoHeight, view.clientWidth, view.clientHeight)
        : { x: 0, y: 0, width: video.videoWidth, height: video.videoHeight };
      canvas.width = Math.round(region.width);
      canvas.height = Math.round(region.height);
      canvas.getContext("2d").drawImage(video, region.x, region.y, region.width, region.height,
        0, 0, canvas.width, canvas.height);
      const image = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95));
      if (!image) throw new Error("Không tạo được ảnh từ webcam.");
      if (!mountedRef.current || session !== cameraSessionRef.current) return false;
      if (automatic && !autoEnabledRef.current) return false;
      const succeeded = await onClassify(image, automatic ? "webcam-auto.jpg" : "webcam.jpg");
      if (automatic && mountedRef.current) {
        if (succeeded) setAutoCount((count) => count + 1);
        else {
          setAutoEnabled(false);
          setCameraError("Phân loại AI thất bại. Đã tạm dừng tự động; kiểm tra lỗi phía trên rồi bật lại.");
        }
      }
      return succeeded;
    } catch (captureError) {
      if (mountedRef.current) {
        setCameraError(captureError.message);
        if (automatic) setAutoEnabled(false);
      }
      return false;
    } finally {
      capturingRef.current = false;
      if (mountedRef.current) setCapturing(false);
    }
  }
  captureCallbackRef.current = captureImage;

  return (
    <section className="panel camera-panel" aria-labelledby="camera-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Đầu vào camera</p>
          <h2 id="camera-title">Ảnh cam đầu vào</h2>
        </div>
        <span className={`status-pill ${cameraOn ? "is-live" : ""}`}>
          <span className="status-dot" />
          {cameraOn ? "Webcam đang bật" : previewUrl ? "Ảnh tải lên" : "Chế độ mẫu"}
        </span>
      </div>

      <div className="camera-view" ref={viewRef}>
        <video ref={videoRef} autoPlay playsInline muted hidden={!cameraOn} />
        {!cameraOn && (
          <img src={previewUrl || sample.image} alt={previewUrl ? "Ảnh cam tải lên" : `Ảnh minh họa ${sample.name}`} />
        )}
        <div className="scan-line" aria-hidden="true" />
        <span className="camera-label">CAM 01</span>
        {cameraOn && autoEnabled && <div className="capture-region"><span>Vùng chụp tự động</span></div>}
      </div>

      {cameraError && <p className="inline-error">{cameraError}</p>}

      <div className="camera-actions">
        <button
          className="button button-secondary"
          type="button"
          onClick={cameraOn ? stopCamera : startCamera}
          disabled={openingCamera}
        >
          {openingCamera ? "Đang mở webcam…" : cameraOn ? "Tắt webcam" : "Bật webcam"}
        </button>
        <button
          className="button button-primary"
          type="button"
          onClick={() => inputRef.current.click()}
          disabled={busy}
        >
          {classifying ? "AI đang phân loại…" : "Tải ảnh để phân loại AI"}
        </button>
        {cameraOn && <button className="button button-primary" type="button" onClick={() => captureImage()} disabled={busy || autoEnabled}>Chụp và phân loại AI</button>}
      </div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={uploadImage} />
      <p className="next-sample">AI nhận ảnh JPEG, PNG hoặc WebP và trả về lớp cam, độ tin cậy cùng Grade 1–3.</p>
      <div className="auto-capture-controls">
        <label className="auto-toggle">
          <input type="checkbox" checked={autoEnabled} disabled={!cameraOn || (!autoEnabled && busy)}
            onChange={(event) => { setCameraError(""); setAutoEnabled(event.target.checked); }} />
          Tự động chụp khi có chuyển động
        </label>
        {cameraOn && <div className="auto-settings">
          <label>Độ nhạy
            <select value={sensitivity} disabled={busy} onChange={(event) => setSensitivity(event.target.value)}>
              <option value="0.06">Cao — quả nhỏ</option>
              <option value="0.12">Bình thường</option>
              <option value="0.2">Thấp — giảm nhiễu</option>
            </select>
          </label>
          <button type="button" className="button button-secondary" disabled={!autoEnabled || busy}
            onClick={() => { setCameraError(""); setBaselineVersion((value) => value + 1); }}>Lấy lại nền trống</button>
        </div>}
        {autoEnabled && <p className="auto-status" role="status">
          {busy ? "Đang chụp và phân loại AI…" : AUTO_PHASE_NAMES[autoPhase]}
        </p>}
        <p className="next-sample">Đã tự động phân loại trong phiên: <strong>{autoCount}</strong> quả.</p>
        <p className="next-sample">Bật webcam, để vùng giữa ảnh trống rồi bật tự động. Giữ camera cố định và cho từng quả đi qua, có khoảng trống giữa hai quả. Chế độ này phát hiện thay đổi hình ảnh; vật khác hoặc thay đổi ánh sáng cũng có thể kích hoạt.</p>
      </div>
      <div className="simulation-actions">
        <button className="button button-secondary" type="button" disabled={busy || autoEnabled} onClick={() => {
          setPreviewUrl("");
          onSimulate();
        }}>{simulating ? "Đang gửi…" : "Giả lập quả đi qua"}</button>
      </div>
      <p className="next-sample">
        Mô phỏng lượt tiếp theo: <strong>{sample.name}</strong> · độ tin cậy giả {Math.round(sample.confidence * 100)}%. Ảnh minh họa không chạy qua AI.
      </p>
    </section>
  );
}
