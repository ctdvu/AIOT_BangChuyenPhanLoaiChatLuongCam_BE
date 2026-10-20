import { useCallback, useEffect, useRef, useState } from "react";

import { createClassification, getHistory, getLatest, getModelStatus, getStats } from "./api";
import CameraPanel from "./components/CameraPanel";
import IpCameras from "./components/IpCameras";
import HistoryTable from "./components/HistoryTable";
import LatestResult from "./components/LatestResult";
import RecentResults from "./components/RecentResults";
import Stats from "./components/Stats";
import { sampleToPng, SIMULATION_SAMPLES } from "./samples";

const PAGE_SIZE = 8;
const RECENT_LIMIT = 4;
const viewFromHash = () => window.location.hash === "#/history" ? "history" : "camera";

export default function App() {
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState(null);
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [view, setView] = useState(viewFromHash);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const sidebarRef = useRef(null);
  const menuButtonRef = useRef(null);
  const refreshVersion = useRef(0);
  const [page, setPage] = useState(1);
  const [sampleIndex, setSampleIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [classifying, setClassifying] = useState(false);
  const [modelStatus, setModelStatus] = useState(null);

  async function refreshModel() {
    try {
      setModelStatus(await getModelStatus());
    } catch (modelError) {
      setModelStatus({ status: "unavailable", detail: modelError.message });
    }
  }

  useEffect(() => { refreshModel(); }, []);

  useEffect(() => {
    const changeView = () => { setView(viewFromHash()); setSidebarOpen(false); };
    window.addEventListener("hashchange", changeView);
    return () => window.removeEventListener("hashchange", changeView);
  }, []);

  useEffect(() => {
    document.title = `${view === "camera" ? "Camera và phân loại" : "Thống kê và lịch sử"} | Orange Sort`;
    window.scrollTo({ top: 0 });
  }, [view]);

  useEffect(() => {
    if (!sidebarOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebarRef.current?.querySelector('[aria-current="page"]')?.focus();
    function handleKey(event) {
      if (event.key === "Escape") setSidebarOpen(false);
      if (event.key !== "Tab") return;
      const links = sidebarRef.current?.querySelectorAll("a, button");
      if (!links?.length) return;
      const first = links[0];
      const last = links[links.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    window.addEventListener("keydown", handleKey);
    const desktop = window.matchMedia("(min-width: 1001px)");
    const closeOnDesktop = (event) => { if (event.matches) setSidebarOpen(false); };
    desktop.addEventListener("change", closeOnDesktop);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKey);
      desktop.removeEventListener("change", closeOnDesktop);
      menuButtonRef.current?.focus();
    };
  }, [sidebarOpen]);

  const refresh = useCallback(async (selectedPage = page) => {
    const version = ++refreshVersion.current;
    try {
      const [latestResult, historyResult, statsResult, recentResult] = await Promise.all([
        getLatest(),
        getHistory(selectedPage, PAGE_SIZE),
        getStats(),
        selectedPage === 1 ? Promise.resolve(null) : getHistory(1, RECENT_LIMIT),
      ]);
      if (version !== refreshVersion.current) return;
      setLatest(latestResult);
      setHistory(historyResult);
      setStats(statsResult);
      setRecent((recentResult || historyResult).items.slice(0, RECENT_LIMIT));
      setError("");
    } catch (refreshError) {
      if (version === refreshVersion.current) setError(refreshError.message);
    } finally {
      if (version === refreshVersion.current) setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    let active = true;
    let timer;
    async function poll() {
      await refresh(page);
      if (active) timer = window.setTimeout(poll, 2000);
    }
    poll();
    return () => { active = false; window.clearTimeout(timer); };
  }, [page, refresh]);

  function acceptResult(created) {
    setLatest(created);
    setRecent((previous) => [created, ...previous.filter((item) => item.id !== created.id)].slice(0, RECENT_LIMIT));
  }

  async function simulate() {
    const sample = SIMULATION_SAMPLES[sampleIndex];
    setSimulating(true);
    setActionError("");
    try {
      const image = await sampleToPng(sample);
      const created = await createClassification({
        image,
        filename: `${sample.label.toLowerCase()}.png`,
        label: sample.label,
        confidence: sample.confidence,
        source: "simulation",
      });
      acceptResult(created);
      setSampleIndex((current) => (current + 1) % SIMULATION_SAMPLES.length);
      if (page !== 1) setPage(1);
      await refresh(1);
    } catch (simulationError) {
      setActionError(simulationError.message);
    } finally {
      setSimulating(false);
    }
  }

  async function classifyImage(image, filename) {
    setClassifying(true);
    setActionError("");
    try {
      const created = await createClassification({ image, filename });
      acceptResult(created);
      if (page !== 1) setPage(1);
      await refresh(1);
      await refreshModel();
      return true;
    } catch (classificationError) {
      setActionError(classificationError.message);
      return false;
    } finally {
      setClassifying(false);
    }
  }

  async function cameraClassified(created) {
    acceptResult(created);
    setActionError("");
    if (page !== 1) setPage(1);
    await refresh(1);
    await refreshModel();
  }

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="sidebar-backdrop" type="button" aria-label="Đóng menu bên trái" onClick={() => setSidebarOpen(false)} />}
      <aside id="app-sidebar" ref={sidebarRef} className={`app-sidebar ${sidebarOpen ? "is-open" : ""}`} role={sidebarOpen ? "dialog" : undefined} aria-modal={sidebarOpen || undefined} aria-label="Điều hướng Orange Sort">
        <a className="brand" href="#/camera" aria-label="Trang camera Orange Sort" onClick={() => setSidebarOpen(false)}>
          <span className="brand-mark">OS</span>
          <span><strong>Orange Sort</strong><small>Phân loại nông sản</small></span>
        </a>
        <button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Đóng thanh điều hướng">×</button>
        <p className="sidebar-label">Không gian làm việc</p>
        <nav className="sidebar-nav" aria-label="Điều hướng chính">
          <a href="#/camera" aria-current={view === "camera" ? "page" : undefined} onClick={() => setSidebarOpen(false)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="6" width="18" height="14" rx="3" /><path d="m8 6 2-3h4l2 3" /><circle cx="12" cy="13" r="3" /></svg>
            <span><strong>Camera & phân loại</strong><small>Quan sát và chụp hai góc nhìn</small></span>
          </a>
          <a href="#/history" aria-current={view === "history" ? "page" : undefined} onClick={() => setSidebarOpen(false)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3v17h17M9 15v-4m5 4V7m5 8V4" /></svg>
            <span><strong>Thống kê & lịch sử</strong><small>Tra cứu các lượt phân loại</small></span>
          </a>
        </nav>
        <div className="sidebar-footer"><span className="eyebrow">Orange AI V3</span><p>Một lượt phân loại<br />Hai góc nhìn của cùng một quả</p></div>
      </aside>
      <div className="app-workspace">
      <header className="topbar">
        <div className="topbar-location">
          <button ref={menuButtonRef} type="button" className="sidebar-toggle" aria-label="Mở thanh điều hướng" aria-controls="app-sidebar" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(true)}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg></button>
          <span>Không gian làm việc <span aria-hidden="true">/</span> <strong>{view === "camera" ? "Camera & phân loại" : "Thống kê & lịch sử"}</strong></span>
        </div>
        <div className="system-status">
          <span className={`status-dot ${error ? "has-error" : ""}`} />
          {error ? "Mất kết nối API" : "Hệ thống sẵn sàng"}
        </div>
      </header>

      <main id="top">
        <div className="hero-copy">
          <div>
            <p className="eyebrow">{view === "camera" ? "Quan sát trực tiếp" : "Dữ liệu phân loại"}</p>
            <h1>{view === "camera" ? "Camera & phân loại" : "Thống kê & lịch sử"}</h1>
          </div>
          <p>{view === "camera" ? "Kết nối hai góc nhìn, chụp ảnh và theo dõi những quả vừa phân loại." : "Theo dõi số lượng và xem lại đầy đủ ảnh, kết quả của từng lượt phân loại."}</p>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <strong>Không thể kết nối backend.</strong>
            <span>{error}. Kiểm tra FastAPI đang chạy tại cổng 8000.</span>
            <button type="button" onClick={() => refresh(page)}>Thử lại</button>
          </div>
        )}
        {actionError && <div className="error-banner" role="alert">{actionError}</div>}

        <div className="app-page camera-page" hidden={view !== "camera"}>
        <div className="model-status" role="status">
          <strong>{modelStatus?.status === "ready" ? "AI sẵn sàng" : modelStatus ? "AI chưa sẵn sàng" : "Đang tải mô hình AI…"}</strong>
          <span>{modelStatus?.status === "ready"
            ? `${modelStatus.model} · ${modelStatus.device.toUpperCase()}`
            : modelStatus?.detail || "Lần đầu có thể mất vài giây."}</span>
          <button type="button" onClick={refreshModel}>Kiểm tra AI</button>
        </div>

        <IpCameras onClassified={cameraClassified} classifying={classifying} simulating={simulating} />
        <RecentResults items={recent} loading={loading} />
        <details className="latest-result-details">
          <summary>Chi tiết kết quả mới nhất</summary>
          <LatestResult result={latest} loading={loading} />
        </details>
        <div className="dashboard-grid legacy-camera-grid">
          <details className="legacy-camera-tools">
            <summary>Webcam máy tính, tải ảnh và mô phỏng phân loại</summary>
            <CameraPanel
            sample={SIMULATION_SAMPLES[sampleIndex]}
            simulating={simulating}
            onSimulate={simulate}
            onClassify={classifyImage}
            classifying={classifying}
            />
          </details>
        </div>
        </div>
        <div className="app-page history-page" hidden={view !== "history"}>
        <Stats stats={stats} />
        <HistoryTable history={history} page={page} onPageChange={setPage} />
        </div>

        <p className="disclaimer">
          Kết quả chỉ dựa trên ngoại quan từ ảnh camera, không khẳng định chất lượng ruột quả hoặc mùi.
        </p>
      </main>
      </div>
    </div>
  );
}
