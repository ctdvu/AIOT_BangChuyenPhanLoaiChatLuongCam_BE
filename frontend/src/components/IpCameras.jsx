import { useEffect, useRef, useState } from "react";
import { cameraStreamUrl, classifyCameras, connectCamera,
  disconnectCamera, getCameras, rotateCamera, saveCameraUrl } from "../api";

const INITIAL = [1, 2].map((camera_id) => ({ camera_id, status: "Disconnected", url: "", generation: 0 }));

function CameraCard({ camera, unavailable, simulationEnabled, busy, onAction }) {
  const [url, setUrl] = useState("");
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [streamError, setStreamError] = useState(false);
  const view = useRef(null);
  const id = camera.camera_id;
  const connected = !unavailable && camera.status === "Connected";

  useEffect(() => { if (!dirty) setUrl(camera.url || ""); }, [camera.url, dirty]);
  useEffect(() => { setStreamError(false); }, [camera.generation, camera.status, unavailable]);

  async function act(action, success = "") {
    setError(""); setNotice("");
    try { await action(); setNotice(success); }
    catch (failure) { setError(failure.message); }
  }

  function connect(simulation = false) {
    if (!simulation) {
      try {
        if (!url.trim()) throw new Error("Chưa nhập URL. Sao chép URL video từ ứng dụng IP Camera trên điện thoại.");
        const parsed = new URL(url.trim());
        if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Chỉ hỗ trợ URL HTTP hoặc HTTPS/MJPEG.");
      } catch (failure) {
        setError(failure instanceof TypeError ? "URL sai định dạng. Cần nhập đầy đủ http(s)://IP:cổng/video." : failure.message);
        return;
      }
    }
    act(async () => {
      await onAction(id, () => connectCamera(id, url.trim(), simulation));
      if (!simulation) setDirty(false);
    });
  }

  return <section className="panel ip-camera" aria-labelledby={`ip-camera-${id}`}>
    <div className="section-heading">
      <div><p className="eyebrow">Camera {id}</p><h2 id={`ip-camera-${id}`}>{id === 1 ? "Góc chụp phía trên" : "Góc chụp bên cạnh"}</h2></div>
      <span className={`camera-state state-${unavailable ? "Error" : camera.status}`} role="status">
        {unavailable ? "Không rõ · API mất kết nối" : camera.status}
      </span>
    </div>
    {camera.simulation && <p className="simulation-label">MÔ PHỎNG — hình tổng hợp, không phải camera thật</p>}
    <label className="camera-url" htmlFor={`camera-url-${id}`}>URL video HTTP/MJPEG
      <input id={`camera-url-${id}`} type="url" value={url} spellCheck="false"
        placeholder="Nhập URL video từ điện thoại Android" disabled={busy}
        onChange={(event) => { setDirty(true); setUrl(event.target.value); setNotice(""); }} />
    </label>
    <div className="camera-actions">
      <button type="button" className="button button-primary" disabled={busy || camera.status === "Connecting" || connected} onClick={() => connect()}>Kết nối</button>
      <button type="button" className="button button-secondary" disabled={busy || (!unavailable && camera.status === "Disconnected")} onClick={() => act(() => onAction(id, () => disconnectCamera(id)))}>Ngắt kết nối</button>
      <button type="button" className="button button-secondary" disabled={busy} onClick={() => connect(camera.simulation && !dirty)}>Kết nối lại</button>
      <button type="button" className="button button-secondary" disabled={busy} onClick={() => act(async () => {
        await onAction(id, () => saveCameraUrl(id, url.trim())); setDirty(false);
      }, "Đã lưu URL vào cấu hình server.")}>Lưu URL</button>
    </div>
    <div className="ip-camera-view" ref={view}>
      {connected && !streamError
        ? <img src={cameraStreamUrl(id, camera.generation)} alt={`Video Camera ${id}`} onError={() => setStreamError(true)} />
        : <div className="ip-camera-placeholder"><strong>CAM 0{id}</strong><span>{unavailable ? "Đang chờ backend hoạt động trở lại" : camera.status === "Connecting" ? "Đang mở luồng và chờ khung hình đầu tiên…" : streamError ? "Luồng hiển thị bị gián đoạn. Nhấn Kết nối lại." : "Chưa có video trực tiếp"}</span></div>}
      {camera.simulation && connected && <span className="camera-label">MÔ PHỎNG</span>}
    </div>
    <div className="camera-rotation">
      <span>Chiều ảnh: {camera.rotation || 0}°</span>
      <button type="button" className="button button-secondary" disabled={busy || unavailable} onClick={() => act(() => onAction(id,
        () => rotateCamera(id, ((camera.rotation || 0) + 270) % 360)))}>↶ Xoay trái 90°</button>
      <button type="button" className="button button-secondary" disabled={busy || unavailable} onClick={() => act(() => onAction(id,
        () => rotateCamera(id, ((camera.rotation || 0) + 90) % 360)))}>↷ Xoay phải 90°</button>
    </div>
    <div className="camera-actions">
      <button type="button" className="button button-secondary" disabled={!connected} onClick={() => act(async () => {
        if (!view.current.requestFullscreen) throw new Error("Trình duyệt này chưa hỗ trợ phóng to toàn màn hình.");
        await view.current.requestFullscreen();
      })}>Phóng to</button>
    </div>
    {simulationEnabled && <button type="button" className="simulation-button" disabled={busy} onClick={() => connect(true)}>Mở luồng mô phỏng riêng</button>}
    {(error || camera.error) && <p className="camera-error" role="alert">{error || camera.error}</p>}
    {notice && <p className="camera-notice" role="status">{notice}</p>}
  </section>;
}

export default function IpCameras({ onClassified, classifying, simulating }) {
  const [cameras, setCameras] = useState(INITIAL);
  const [simulationEnabled, setSimulationEnabled] = useState(false);
  const [unavailable, setUnavailable] = useState(true);
  const [backendError, setBackendError] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState({});
  const [session, setSession] = useState(null);
  const busyRef = useRef(new Set());
  const version = useRef(0);

  useEffect(() => {
    let active = true;
    let timer;
    async function poll() {
      const started = version.current;
      try {
        const result = await getCameras();
        if (active && started === version.current) {
          setCameras(result.cameras); setSimulationEnabled(result.simulation_enabled);
          setUnavailable(false); setBackendError("");
        }
      } catch (failure) {
        if (active && started === version.current) { setUnavailable(true); setBackendError(failure.message); }
      } finally { if (active) timer = window.setTimeout(poll, 1000); }
    }
    poll();
    return () => { active = false; window.clearTimeout(timer); };
  }, []);

  async function withBusy(ids, operation) {
    if (ids.some((id) => busyRef.current.has(id))) throw new Error("Camera đang xử lý thao tác trước. Hãy chờ hoàn tất.");
    ids.forEach((id) => busyRef.current.add(id));
    setBusy(Object.fromEntries([...busyRef.current].map((id) => [id, true])));
    try { return await operation(); }
    finally {
      ids.forEach((id) => busyRef.current.delete(id));
      setBusy(Object.fromEntries([...busyRef.current].map((id) => [id, true])));
    }
  }

  async function action(id, operation, update = true) {
    return withBusy([id], async () => {
      version.current += 1;
      const result = await operation();
      version.current += 1;
      if (update) setCameras((previous) => previous.map((camera) => camera.camera_id === id ? { ...camera, ...result } : camera));
      return result;
    });
  }

  async function captureBoth() {
    return withBusy([1, 2], async () => {
      const response = await classifyCameras();
      const result = response.capture;
      setSession({ ...result, classification: response.classification });
      await onClassified(response.classification);
      return result;
    });
  }

  return <section className="camera-management" aria-labelledby="camera-management-title">
    <div className="section-heading camera-management-heading">
      <div><p className="eyebrow">Hai góc nhìn · một phiên chụp</p><h2 id="camera-management-title">Quản lý Camera Android</h2></div>
    </div>
    <p className="camera-help">Bật phát HTTP/MJPEG trên hai điện thoại cùng Wi-Fi với máy tính. Nhập URL video rồi kết nối từng camera. Nhấn Esc để thoát phóng to.</p>
    <p className="camera-help">Bấm một lần vào Chụp 2 camera và phân loại để chụp cả hai góc nhìn, phân loại và lưu chung một lượt trong lịch sử. Cần kết nối đủ hai camera trước khi chụp.</p>
    {backendError && <p className="camera-error" role="alert">{backendError}</p>}
    <div className="ip-camera-grid">{cameras.map((camera) => <CameraCard key={camera.camera_id} camera={camera}
      unavailable={unavailable} simulationEnabled={simulationEnabled}
      busy={Boolean(busy[camera.camera_id]) || classifying || simulating}
      onAction={action} />)}</div>
    <div className="camera-shared-actions">
      <button type="button" className="button button-primary" disabled={unavailable || classifying || simulating || Object.values(busy).some(Boolean) || cameras.some((camera) => camera.status !== "Connected")} onClick={async () => {
        setError("");
        try { await captureBoth(); } catch (failure) { setError(failure.message); }
      }}>{busy[1] && busy[2] ? "Đang chụp và phân loại…" : "Chụp 2 camera và phân loại"}</button>
    </div>
    {error && <p className="camera-error" role="alert">{error}</p>}
    {session?.classification && <p className="camera-notice" role="status">Đã phân loại và lưu lượt #{session.classification.id} · {session.images.length} ảnh · {session.classification.display_name}{session.images.length === 2 ? ` · chênh lệch thời điểm nhận ${session.skew_ms} ms` : ""}.</p>}
  </section>;
}
