import { useEffect, useRef, useState } from "react";
import { getDeviceStatus, getHistory, getLatest, getMyFarm, getStats, updateMyFarm } from "../api";
import ClassificationImages from "./ClassificationImages";
import HistoryTable from "./HistoryTable";
import RecentResults from "./RecentResults";
import Stats from "./Stats";

const CONVEYOR_STATE_LABELS = {
  running: "Đang chạy băng tải — chờ cam qua LM393",
  inspecting: "Đang dừng băng tải — ESP32 chụp 2 ảnh & gửi EC2",
  sorting_tray_1: "Servo 1 mở 60° — gạt vào Máng 1 (Loại 1)",
  sorting_tray_2: "Servo 2 mở 60° — gạt vào Máng 2 (Loại 2)",
  sorting_tray_3: "Đi thẳng vào Máng 3 (Loại 3 - Khuyết tật/Hỏng)",
  stopped: "Băng tải đang dừng (Bật tại http://192.168.4.1)",
  offline: "Chưa kết nối ESP32",
  idle: "Chờ tín hiệu từ cảm biến LM393",
};

export default function FarmDashboard({ user, activeTab = "live", onTabChange }) {
  const [farm, setFarm] = useState(null);
  const [deviceStatus, setDeviceStatus] = useState(null);
  const [latest, setLatest] = useState(null);
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState(null);
  const [recent, setRecent] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Form cập nhật thông tin nông trại
  const [formState, setFormState] = useState({
    location: "",
    contact_phone: "",
    description: "",
    cam1_rotation: 0,
    cam2_rotation: 0,
  });
  const [formLoaded, setFormLoaded] = useState(false);
  const refreshTimer = useRef(null);

  async function loadFarmData(targetPage = page) {
    try {
      const farmRes = await getMyFarm();
      setFarm(farmRes);
      if (!formLoaded) {
        setFormState({
          location: farmRes.location || "",
          contact_phone: farmRes.contact_phone || "",
          description: farmRes.description || "",
          cam1_rotation: farmRes.cam1_rotation || 0,
          cam2_rotation: farmRes.cam2_rotation || 0,
        });
        setFormLoaded(true);
      }

      const [devRes, latestRes, statsRes, histRes] = await Promise.all([
        getDeviceStatus(farmRes.id).catch(() => null),
        getLatest(farmRes.id).catch(() => null),
        getStats(farmRes.id).catch(() => null),
        getHistory(targetPage, 8, farmRes.id).catch(() => null),
      ]);

      if (devRes) setDeviceStatus(devRes);
      if (latestRes) setLatest(latestRes);
      if (statsRes) setStats(statsRes);
      if (histRes) {
        setHistory(histRes);
        if (targetPage === 1) {
          setRecent(histRes.items.slice(0, 4));
        }
      }
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFarmData(page);
    refreshTimer.current = setInterval(() => {
      loadFarmData(page);
    }, 2000);
    return () => clearInterval(refreshTimer.current);
  }, [page]);

  function copyApiKey() {
    if (!farm?.device_api_key) return;
    navigator.clipboard.writeText(farm.device_api_key);
    setNotice("Đã sao chép API Key! Hãy dán vào trang cấu hình ESP32 tại http://192.168.4.1");
    setTimeout(() => setNotice(""), 4000);
  }

  async function handleSaveSettings(e) {
    e.preventDefault();
    setError("");
    try {
      const updated = await updateMyFarm(formState);
      setFarm(updated);
      setNotice("Đã lưu cấu hình Nông trại và góc xoay Camera thành công!");
    } catch (err) {
      setError(err.message);
    }
  }

  const expires = farm?.subscription_expires_at
    ? new Date(farm.subscription_expires_at)
    : null;
  const isExpired = farm?.days_remaining !== null && farm?.days_remaining <= 0;

  return (
    <div className="farm-dashboard">
      {/* KPI TỔNG QUAN NHÀ VƯỜN */}
      <div className="role-kpi-row">
        <div className="role-kpi-card kpi-farm">
          <span className="kpi-title">Nông trại đang vận hành</span>
          <strong className="kpi-num" style={{ fontSize: "1.15rem" }}>
            {farm?.name || "Đang tải..."}
          </strong>
          <small>📍 {farm?.location || "Việt Nam"} · 📞 {farm?.contact_phone || "—"}</small>
        </div>

        <div className="role-kpi-card kpi-farm">
          <span className="kpi-title">Trạng thái Băng chuyền ESP32</span>
          <strong className="kpi-num" style={{ fontSize: "1.1rem" }}>
            {deviceStatus?.online ? "🟢 Đang trực tuyến" : "⚪ Chờ kết nối ESP32"}
          </strong>
          <small>{CONVEYOR_STATE_LABELS[deviceStatus?.conveyor_state] || "Chờ cảm biến LM393"}</small>
        </div>

        <div className="role-kpi-card kpi-farm">
          <span className="kpi-title">Tổng sản lượng đã phân loại</span>
          <strong className="kpi-num">{stats?.total ?? 0} quả</strong>
          <small>Phiên hiện tại: {deviceStatus?.sorted_count ?? 0} quả</small>
        </div>

        <div className="role-kpi-card kpi-farm">
          <span className="kpi-title">Gói dịch vụ Cloud AI</span>
          <strong className="kpi-num">
            {isExpired ? "Hết hạn" : `Còn ${farm?.days_remaining ?? "—"} ngày`}
          </strong>
          <small>{farm?.service_plan || "Gói Tiêu Chuẩn"}</small>
        </div>
      </div>

      {notice && <div className="notice-banner">{notice}</div>}
      {error && <div className="error-banner">{error}</div>}

      {/* TAB 1: TRỰC TIẾP BĂNG CHUYỀN & ẢNH GỬI VỀ TỪ ESP32 */}
      {activeTab === "live" && (
        <>
          <div className="dashboard-grid farm-top-grid">
            {/* TRẠNG THÁI BĂNG CHUYỀN REAL-TIME */}
            <section className="panel farm-status-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Điều khiển phần cứng tự động</p>
                  <h3>Băng chuyền L298N · Cảm biến LM393 · 2 Servo</h3>
                </div>
                <span className={`status-dot ${deviceStatus?.online ? "is-online" : ""}`} />
              </div>

              <div className="hardware-live-box">
                <div className="conveyor-badge-state">
                  <span className={`state-tag state-${deviceStatus?.conveyor_state || "stopped"}`}>
                    {CONVEYOR_STATE_LABELS[deviceStatus?.conveyor_state] || "Chờ tín hiệu từ ESP32"}
                  </span>
                </div>

                <div className="hardware-counters">
                  <div className="counter-item">
                    <span className="counter-value">{deviceStatus?.sorted_count ?? 0}</span>
                    <span className="counter-label">Quả đã gạt trong ca chạy</span>
                  </div>
                  <div className="counter-item">
                    <span className="counter-value">{stats?.total ?? 0}</span>
                    <span className="counter-label">Tổng sản lượng nhà vườn</span>
                  </div>
                </div>

                <div className="hardware-message">
                  <strong>Trạng thái phản hồi:</strong>
                  <p>
                    {deviceStatus?.message ||
                      "Khi cam đi qua cảm biến LM393, ESP32 tự dừng băng tải, chụp 2 camera và gửi ảnh trực tiếp lên EC2."}
                  </p>
                </div>
              </div>
            </section>

            {/* TÓM TẮT KẾT NỐI NHANH ESP32 */}
            <section className="panel farm-credentials-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Mã kết nối phần cứng của vườn</p>
                  <h3>Device API Key cho ESP32</h3>
                </div>
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => onTabChange && onTabChange("settings")}
                >
                  Cấu hình chi tiết &rarr;
                </button>
              </div>

              <div className="credential-row">
                <label>API Key nạp vào trang cài đặt ESP32 (http://192.168.4.1):</label>
                <div className="key-copy-group">
                  <input
                    type="text"
                    readOnly
                    value={farm?.device_api_key || "Đang tải..."}
                    className="key-input"
                  />
                  <button
                    type="button"
                    className="button button-primary btn-copy"
                    onClick={copyApiKey}
                  >
                    📋 Sao chép Key
                  </button>
                </div>
              </div>

              <div className="setup-guide-box" style={{ marginTop: "10px" }}>
                <h4>Quy trình vận hành băng chuyền tại vườn:</h4>
                <ol>
                  <li>
                    Kết nối điện thoại vào Wi-Fi <code>ESP32-PhanLoaiCam</code> (Mật khẩu:{" "}
                    <code>12345678</code>) và mở <code>http://192.168.4.1</code>.
                  </li>
                  <li>
                    Dán <strong>API Key</strong> trên + nhập 2 IP Camera rồi bấm{" "}
                    <strong>[Lưu & Kiểm tra]</strong>.
                  </li>
                  <li>
                    Bấm <strong>[▶ BẬT BĂNG CHUYỀN]</strong> — ảnh chụp mỗi quả cam sẽ tự động
                    hiển thị trực tiếp ở khung bên dưới!
                  </li>
                </ol>
              </div>
            </section>
          </div>

          {/* HÌNH ẢNH TRỰC TIẾP GỬI VỀ TỪ ESP32 THEO THỜI GIAN THỰC */}
          <section className="panel live-inspection-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Live Stream từ phần cứng ESP32</p>
                <h3>Hình ảnh trực tiếp 2 góc chụp vừa gửi về & Kết quả AI</h3>
              </div>
              {latest && (
                <span className={`badge ${latest.grade === 1 ? "badge-success" : latest.grade === 2 ? "badge-warning" : "badge-danger"}`} style={{ fontSize: ".9rem", padding: "6px 12px" }}>
                  Lượt #{latest.id}: {latest.display_name} (Máng {latest.tray}) · {(latest.confidence * 100).toFixed(1)}%
                </span>
              )}
            </div>

            {latest ? (
              <div className="live-images-dual-view">
                <ClassificationImages result={latest} compact={false} />
                <div className="inspection-decision-summary">
                  <div className="decision-card">
                    <strong>Kết luận phân loại cuối cùng:</strong>
                    <span style={{ fontSize: "1rem", fontWeight: 700, color: "#0f172a" }}>
                      {latest.display_name} — Độ tin cậy {(latest.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="decision-card">
                    <strong>Thuật toán kết hợp 2 góc chụp:</strong>
                    <span>
                      {latest.aggregation_policy === "close_confidence_worse_grade"
                        ? "Hai góc khác loại & độ tin cậy chênh lệch ít (<= 20%) → Lấy loại chất lượng thấp hơn để đảm bảo không sót lỗi."
                        : latest.aggregation_policy === "high_confidence_override"
                        ? "Hai góc khác loại & độ tin cậy chênh lệch lớn (> 20%) → Lấy theo góc chụp có độ tin cậy vượt trội."
                        : "Hai góc chụp đồng thuận cùng một hạng chất lượng."}
                    </span>
                  </div>
                  <div className="decision-card">
                    <strong>Lệnh điều khiển cơ cấu chấp hành:</strong>
                    <span>
                      {latest.tray === 1
                        ? "Kích hoạt Servo 1 quay 60° gạt quả vào Máng 1 (Loại 1)"
                        : latest.tray === 2
                        ? "Kích hoạt Servo 2 quay 60° gạt quả vào Máng 2 (Loại 2)"
                        : "Giữ nguyên 2 Servo (0°), cho quả đi thẳng vào Máng 3 (Loại 3 - Hỏng)"}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="recent-empty">
                <strong>Chưa có quả cam nào đi qua băng chuyền của nông trại</strong>
                <span>Khi cảm biến LM393 phát hiện cam, cặp ảnh 2 góc chụp từ ESP32 sẽ lập tức xuất hiện tại đây.</span>
              </div>
            )}
          </section>

          <RecentResults items={recent} loading={loading} />
        </>
      )}

      {/* TAB 2: THỐNG KÊ & LỊCH SỬ CỦA NÔNG TRẠI */}
      {activeTab === "history" && (
        <div className="farm-history-tab">
          <Stats stats={stats} />
          <div style={{ marginTop: "24px" }}>
            <HistoryTable history={history} page={page} onPageChange={setPage} />
          </div>
        </div>
      )}

      {/* TAB 3: CẤU HÌNH THIẾT BỊ ESP32 & THỜI HẠN DỊCH VỤ */}
      {activeTab === "settings" && (
        <div className="dashboard-grid farm-top-grid">
          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Thông số xác thực thiết bị</p>
                <h3>Khóa Bảo Mật ESP32 & Thuê Bao Dịch Vụ</h3>
              </div>
            </div>

            <div className="credential-row">
              <label>ESP32 Device API Key (Dùng để xác thực nông trại):</label>
              <div className="key-copy-group">
                <input
                  type="text"
                  readOnly
                  value={farm?.device_api_key || ""}
                  className="key-input"
                />
                <button type="button" className="button button-primary" onClick={copyApiKey}>
                  📋 Sao chép
                </button>
              </div>
              <small className="help-text">
                Mỗi nông trại có một mã API Key duy nhất. Không chia sẻ mã này cho người lạ.
              </small>
            </div>

            <div className="credential-row">
              <label>Địa chỉ MAC phần cứng ESP32 đã khóa (Hardware Binding):</label>
              <div>
                <span className={`badge ${farm?.bound_mac_address ? "badge-success" : "badge-warning"}`}>
                  {farm?.bound_mac_address
                    ? `🔒 Đã khóa với MAC: ${farm.bound_mac_address}`
                    : "Chưa khóa MAC (Tự động khóa khi ESP32 kết nối lần đầu)"}
                </span>
              </div>
              <small className="help-text">
                Nếu bạn thay bo mạch ESP32 mới, hãy liên hệ Admin để Reset khóa MAC.
              </small>
            </div>

            <div className="credential-row">
              <label>Thông tin gói cước dịch vụ:</label>
              <p style={{ margin: "6px 0" }}>
                Gói hiện tại: <strong>{farm?.service_plan}</strong>
              </p>
              <p style={{ margin: "6px 0" }}>
                Ngày hết hạn:{" "}
                <strong>
                  {expires ? expires.toLocaleDateString("vi-VN", { dateStyle: "full" }) : "Không giới hạn"}
                </strong>{" "}
                ({isExpired ? "Đã hết hạn" : `Còn ${farm?.days_remaining} ngày`})
              </p>
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Cài đặt nhà vườn & Góc xoay ảnh</p>
                <h3>Cập nhật Thông tin Nông trại</h3>
              </div>
            </div>

            <form onSubmit={handleSaveSettings} className="auth-form">
              <div className="form-group">
                <label>Địa chỉ Nông trại:</label>
                <input
                  type="text"
                  value={formState.location}
                  onChange={(e) => setFormState({ ...formState, location: e.target.value })}
                  placeholder="VD: Huyện Tam Bình, Vĩnh Long"
                />
              </div>
              <div className="form-group">
                <label>Số điện thoại liên hệ (Hiển thị cho Đại lý thu mua):</label>
                <input
                  type="text"
                  value={formState.contact_phone}
                  onChange={(e) => setFormState({ ...formState, contact_phone: e.target.value })}
                  placeholder="VD: 0912345678"
                />
              </div>
              <div className="form-group">
                <label>Mô tả giới thiệu vườn / Giống cam:</label>
                <input
                  type="text"
                  value={formState.description}
                  onChange={(e) => setFormState({ ...formState, description: e.target.value })}
                  placeholder="VD: Chuyên cam sành VietGAP xuất khẩu"
                />
              </div>
              <div className="hardware-counters" style={{ marginBottom: 0 }}>
                <div className="form-group">
                  <label>Góc xoay Camera 1 (Trên đỉnh):</label>
                  <select
                    value={formState.cam1_rotation}
                    onChange={(e) =>
                      setFormState({ ...formState, cam1_rotation: parseInt(e.target.value) })
                    }
                  >
                    <option value={0}>0° (Mặc định)</option>
                    <option value={90}>90° (Xoay phải)</option>
                    <option value={180}>180° (Lật ngược)</option>
                    <option value={270}>270° (Xoay trái)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Góc xoay Camera 2 (Bên hông):</label>
                  <select
                    value={formState.cam2_rotation}
                    onChange={(e) =>
                      setFormState({ ...formState, cam2_rotation: parseInt(e.target.value) })
                    }
                  >
                    <option value={0}>0° (Mặc định)</option>
                    <option value={90}>90° (Xoay phải)</option>
                    <option value={180}>180° (Lật ngược)</option>
                    <option value={270}>270° (Xoay trái)</option>
                  </select>
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="button button-primary">
                  Lưu cấu hình Nông trại
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
