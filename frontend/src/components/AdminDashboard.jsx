import { useEffect, useState } from "react";
import {
  createAdminFarm,
  getAdminFarms,
  getAdminUsers,
  getModelStatus,
  getStats,
  resetFarmMac,
  rotateFarmKey,
  updateAdminFarm,
} from "../api";

export default function AdminDashboard({ activeTab = "farms", onTabChange }) {
  const [farms, setFarms] = useState([]);
  const [users, setUsers] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);
  const [globalStats, setGlobalStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Form tạo farm mới khớp 100% với CreateFarmRequest trong schemas.py
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFarm, setNewFarm] = useState({
    username: "",
    password: "",
    full_name: "",
    farm_name: "",
    location: "",
    contact_phone: "",
    description: "",
    service_plan: "Gói Cao Cấp (AI 2 Góc)",
    subscription_days: 180,
  });

  const [visibleKeys, setVisibleKeys] = useState({});

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [farmsData, usersData, modelData, statsData] = await Promise.all([
        getAdminFarms(),
        getAdminUsers().catch(() => []),
        getModelStatus().catch(() => null),
        getStats().catch(() => null),
      ]);
      setFarms(farmsData);
      setUsers(usersData);
      if (modelData) setModelStatus(modelData);
      if (statsData) setGlobalStats(statsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleCreateFarm(e) {
    e.preventDefault();
    setError("");
    try {
      await createAdminFarm(newFarm);
      setNotice(`Đã tạo thành công nông trại "${newFarm.farm_name}" và cấp tài khoản chủ vườn "${newFarm.username}"!`);
      setShowCreateModal(false);
      setNewFarm({
        username: "",
        password: "",
        full_name: "",
        farm_name: "",
        location: "",
        contact_phone: "",
        description: "",
        service_plan: "Gói Cao Cấp (AI 2 Góc)",
        subscription_days: 180,
      });
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRotateKey(farmId) {
    if (
      !window.confirm(
        "Bạn có chắc chắn muốn cấp lại API Key mới? Key cũ trên ESP32 sẽ bị vô hiệu hóa và khóa MAC sẽ được reset."
      )
    ) {
      return;
    }
    setError("");
    try {
      const res = await rotateFarmKey(farmId);
      setNotice(`Đã cấp API Key mới cho "${res.name}": ${res.device_api_key}`);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleResetMac(farmId) {
    if (!window.confirm("Mở khóa địa chỉ MAC để nông trại đổi sang mạch ESP32 mới?")) {
      return;
    }
    setError("");
    try {
      const res = await resetFarmMac(farmId);
      setNotice(`Đã xóa khóa MAC cho "${res.name}". ESP32 mới sẽ tự động khóa ở lần gọi đầu tiên.`);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleActive(farm) {
    setError("");
    try {
      await updateAdminFarm(farm.id, { is_active: !farm.is_active });
      setNotice(`Đã ${farm.is_active ? "tạm khóa" : "mở khóa"} nông trại "${farm.name}"`);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleDevice(farm) {
    setError("");
    try {
      await updateAdminFarm(farm.id, { device_enabled: !farm.device_enabled });
      setNotice(
        `Đã ${farm.device_enabled ? "ngắt quyền gọi API của ESP32" : "cho phép ESP32 kết nối"} tại "${farm.name}"`
      );
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleExtendDays(farm, days) {
    setError("");
    try {
      await updateAdminFarm(farm.id, { extend_days: days });
      setNotice(`Đã gia hạn thêm ${days} ngày dịch vụ cho "${farm.name}"!`);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  }

  function copyToClipboard(text, label) {
    navigator.clipboard.writeText(text);
    setNotice(`Đã sao chép ${label} vào bộ nhớ tạm!`);
  }

  function toggleKeyVisibility(farmId) {
    setVisibleKeys((prev) => ({ ...prev, [farmId]: !prev[farmId] }));
  }

  return (
    <div className="admin-dashboard">
      {/* KPI TỔNG QUAN DÀNH RIÊNG CHO ADMIN */}
      <div className="role-kpi-row">
        <div className="role-kpi-card kpi-admin">
          <span className="kpi-title">Tổng số Nông trại</span>
          <strong className="kpi-num">{farms.length}</strong>
          <small>{farms.filter((f) => f.is_active).length} đang hoạt động</small>
        </div>
        <div className="role-kpi-card kpi-admin">
          <span className="kpi-title">Thiết bị ESP32 đã khóa MAC</span>
          <strong className="kpi-num">{farms.filter((f) => f.bound_mac_address).length} / {farms.length}</strong>
          <small>Bảo mật phần cứng X-Device-MAC</small>
        </div>
        <div className="role-kpi-card kpi-admin">
          <span className="kpi-title">Tài khoản Hệ thống</span>
          <strong className="kpi-num">{users.length}</strong>
          <small>
            {users.filter((u) => u.role === "farm").length} Chủ vườn ·{" "}
            {users.filter((u) => u.role === "dealer").length} Đại lý
          </small>
        </div>
        <div className="role-kpi-card kpi-admin">
          <span className="kpi-title">Tổng cam đã phân loại Cloud</span>
          <strong className="kpi-num">{globalStats?.total ?? 0} quả</strong>
          <small>Mô hình {modelStatus?.model || "EfficientNet-B0 V3"}</small>
        </div>
      </div>

      {notice && <div className="notice-banner">{notice}</div>}
      {error && <div className="error-banner">{error}</div>}

      {/* TAB 1: QUẢN LÝ NÔNG TRẠI & THIẾT BỊ ESP32 */}
      {activeTab === "farms" && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Quản lý thuê bao & phần cứng</p>
              <h2>Danh sách Nông trại & Khóa thiết bị ESP32 ({farms.length})</h2>
            </div>
            <div className="admin-head-actions">
              <button
                type="button"
                className="button button-primary"
                onClick={() => setShowCreateModal(true)}
              >
                + Thêm Nông Trại & Cấp Tài Khoản
              </button>
              <button type="button" className="button button-secondary" onClick={loadData}>
                Làm mới
              </button>
            </div>
          </div>

          {loading ? (
            <div className="loading-state">Đang tải danh sách nông trại từ EC2...</div>
          ) : (
            <div className="farms-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nông trại & Địa điểm</th>
                    <th>Gói & Thời hạn dịch vụ</th>
                    <th>ESP32 Device API Key</th>
                    <th>Khóa MAC Phần cứng</th>
                    <th>Quyền ESP32</th>
                    <th>Trạng thái</th>
                    <th>Thao tác Quản trị</th>
                  </tr>
                </thead>
                <tbody>
                  {farms.map((farm) => {
                    const expires = farm.subscription_expires_at
                      ? new Date(farm.subscription_expires_at)
                      : null;
                    const isExpired = farm.days_remaining !== null && farm.days_remaining <= 0;

                    return (
                      <tr key={farm.id} className={!farm.is_active ? "row-inactive" : ""}>
                        <td>
                          <strong>#{farm.id}</strong>
                        </td>
                        <td>
                          <strong>{farm.name}</strong>
                          <small className="d-block text-muted">
                            📍 {farm.location || "Chưa cập nhật"} · 📞 {farm.contact_phone || "—"}
                          </small>
                        </td>
                        <td>
                          <div>
                            <span className="badge badge-secondary">{farm.service_plan}</span>
                          </div>
                          {expires ? (
                            <div style={{ marginTop: "4px" }}>
                              <span className={`badge ${isExpired ? "badge-danger" : "badge-success"}`}>
                                {isExpired ? "Đã hết hạn" : `Còn ${farm.days_remaining} ngày`}
                              </span>
                              <small className="d-block text-muted">
                                Hết hạn: {expires.toLocaleDateString("vi-VN")}
                              </small>
                            </div>
                          ) : (
                            <span className="badge badge-warning">Không giới hạn</span>
                          )}
                          <div className="quick-extend-btns">
                            <button
                              type="button"
                              className="btn-link"
                              onClick={() => handleExtendDays(farm, 30)}
                            >
                              +30 ngày
                            </button>
                            <button
                              type="button"
                              className="btn-link"
                              onClick={() => handleExtendDays(farm, 180)}
                            >
                              +180 ngày
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="key-box">
                            <code>
                              {visibleKeys[farm.id]
                                ? farm.device_api_key
                                : `${farm.device_api_key.substring(0, 12)}•••`}
                            </code>
                            <button
                              type="button"
                              className="btn-icon"
                              onClick={() => toggleKeyVisibility(farm.id)}
                              title={visibleKeys[farm.id] ? "Ẩn Key" : "Hiện toàn bộ Key"}
                            >
                              {visibleKeys[farm.id] ? "🙈" : "👁️"}
                            </button>
                            <button
                              type="button"
                              className="btn-icon"
                              onClick={() => copyToClipboard(farm.device_api_key, "API Key")}
                              title="Sao chép API Key"
                            >
                              📋
                            </button>
                          </div>
                        </td>
                        <td>
                          {farm.bound_mac_address ? (
                            <div className="mac-box">
                              <span className="badge badge-success">🔒 {farm.bound_mac_address}</span>
                              <button
                                type="button"
                                className="btn-link btn-danger-link"
                                onClick={() => handleResetMac(farm.id)}
                              >
                                Mở khóa MAC
                              </button>
                            </div>
                          ) : (
                            <span className="text-muted">Chưa khóa (Tự khóa khi ESP32 gọi)</span>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className={`badge ${farm.device_enabled ? "badge-success" : "badge-danger"}`}
                            style={{ border: 0, cursor: "pointer" }}
                            onClick={() => handleToggleDevice(farm)}
                            title="Bấm để Bật/Tắt quyền gọi API từ ESP32"
                          >
                            {farm.device_enabled ? "Cho phép ESP32" : "Đã chặn ESP32"}
                          </button>
                        </td>
                        <td>
                          <span className={`badge ${farm.is_active ? "badge-success" : "badge-danger"}`}>
                            {farm.is_active ? "Hoạt động" : "Tạm ngưng"}
                          </span>
                        </td>
                        <td>
                          <div className="table-actions">
                            <button
                              type="button"
                              className="button button-secondary btn-sm"
                              onClick={() => handleRotateKey(farm.id)}
                            >
                              Đổi Key mới
                            </button>
                            <button
                              type="button"
                              className={`button ${
                                farm.is_active ? "button-secondary" : "button-primary"
                              } btn-sm`}
                              onClick={() => handleToggleActive(farm)}
                            >
                              {farm.is_active ? "Khóa Farm" : "Mở Farm"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* TAB 2: QUẢN LÝ NGƯỜI DÙNG */}
      {activeTab === "users" && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Phân quyền truy cập 3 Role</p>
              <h2>Danh sách Tài khoản Người dùng ({users.length})</h2>
            </div>
            <button type="button" className="button button-secondary" onClick={loadData}>
              Làm mới
            </button>
          </div>

          <div className="users-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tên đăng nhập</th>
                  <th>Họ và tên / Đơn vị</th>
                  <th>Vai trò (Role)</th>
                  <th>Số điện thoại</th>
                  <th>Ngày tạo</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>#{u.id}</td>
                    <td>
                      <strong>{u.username}</strong>
                    </td>
                    <td>{u.full_name || "—"}</td>
                    <td>
                      <span className={`role-badge role-${u.role}`}>
                        {u.role === "admin"
                          ? "QUẢN TRỊ VIÊN (ADMIN)"
                          : u.role === "farm"
                          ? "CHỦ NÔNG TRẠI (FARM)"
                          : "ĐẠI LÝ THU MUA (DEALER)"}
                      </span>
                    </td>
                    <td>{u.phone || "—"}</td>
                    <td>{new Date(u.created_at).toLocaleDateString("vi-VN")}</td>
                    <td>
                      <span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>
                        {u.is_active ? "Đang hoạt động" : "Đã khóa"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* TAB 3: GIÁM SÁT AI & HỆ THỐNG CLOUD */}
      {activeTab === "system" && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Cấu hình thuật toán & AI</p>
              <h2>Trạng thái Máy chủ AI EfficientNet-B0 V3 & Quy tắc Gộp 2 Ảnh</h2>
            </div>
          </div>

          <div className="dashboard-grid farm-top-grid">
            <div className="decision-card">
              <strong>Trạng thái Mô hình AI trên Server EC2:</strong>
              <p>
                Trạng thái:{" "}
                <span className="badge badge-success">
                  {modelStatus?.status === "ready" ? "SẴN SÀNG PHÂN LOẠI" : "Đang kiểm tra"}
                </span>
              </p>
              <p>Tên mô hình: <code>{modelStatus?.model || "orange_classifier_v3_best.pth"}</code></p>
              <p>Phần cứng xử lý: <code>{modelStatus?.device?.toUpperCase() || "CPU"}</code></p>
              <p>Các lớp nhận diện (5 lớp): <code>{(modelStatus?.classes || []).join(", ")}</code></p>
            </div>

            <div className="decision-card">
              <strong>Thuật toán kết hợp 2 góc chụp Camera (Confidence Gap = 20%):</strong>
              <ul style={{ margin: "8px 0 0", paddingLeft: "18px", lineHeight: "1.7" }}>
                <li>
                  <strong>Trường hợp 1 (Cùng loại Grade):</strong> Chọn kết quả có độ tin cậy (Confidence) cao hơn.
                </li>
                <li>
                  <strong>Trường hợp 2 (Khác loại, chênh lệch độ tin cậy &gt; 20%):</strong> Chọn loại có độ tin cậy cao vượt trội (<code>high_confidence_override</code>).
                </li>
                <li>
                  <strong>Trường hợp 3 (Khác loại, chênh lệch độ tin cậy &le; 20%):</strong> Ưu tiên lấy <strong>loại chất lượng thấp hơn / khuyết tật hơn</strong> (Loại 3 &gt; Loại 2 &gt; Loại 1 — <code>close_confidence_worse_grade</code>) để tránh bỏ lọt quả bị thối/nám ở một mặt khuất.
                </li>
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* MODAL THÊM NÔNG TRẠI MỚI */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Thêm Nông Trại & Cấp Tài Khoản Chủ Vườn</h3>
              <button type="button" className="btn-close" onClick={() => setShowCreateModal(false)}>
                ×
              </button>
            </div>
            <form onSubmit={handleCreateFarm} className="auth-form">
              <div className="form-group">
                <label>Tên Nông trại (*):</label>
                <input
                  type="text"
                  required
                  value={newFarm.farm_name}
                  onChange={(e) => setNewFarm({ ...newFarm, farm_name: e.target.value })}
                  placeholder="VD: Nông Trại Cam Sành Tam Bình"
                />
              </div>
              <div className="form-group">
                <label>Họ và tên Chủ nông trại (*):</label>
                <input
                  type="text"
                  required
                  value={newFarm.full_name}
                  onChange={(e) => setNewFarm({ ...newFarm, full_name: e.target.value })}
                  placeholder="VD: Nguyễn Văn Hải"
                />
              </div>
              <div className=" hardware-counters" style={{ marginBottom: 0 }}>
                <div className="form-group">
                  <label>Username đăng nhập (*):</label>
                  <input
                    type="text"
                    required
                    value={newFarm.username}
                    onChange={(e) => setNewFarm({ ...newFarm, username: e.target.value })}
                    placeholder="VD: farm3"
                  />
                </div>
                <div className="form-group">
                  <label>Mật khẩu (*):</label>
                  <input
                    type="password"
                    required
                    value={newFarm.password}
                    onChange={(e) => setNewFarm({ ...newFarm, password: e.target.value })}
                    placeholder="Mật khẩu chủ vườn"
                  />
                </div>
              </div>
              <div className="hardware-counters" style={{ marginBottom: 0 }}>
                <div className="form-group">
                  <label>Địa chỉ / Khu vực:</label>
                  <input
                    type="text"
                    value={newFarm.location}
                    onChange={(e) => setNewFarm({ ...newFarm, location: e.target.value })}
                    placeholder="VD: Vĩnh Long"
                  />
                </div>
                <div className="form-group">
                  <label>Số điện thoại liên hệ:</label>
                  <input
                    type="text"
                    value={newFarm.contact_phone}
                    onChange={(e) => setNewFarm({ ...newFarm, contact_phone: e.target.value })}
                    placeholder="VD: 0909123456"
                  />
                </div>
              </div>
              <div className="hardware-counters" style={{ marginBottom: 0 }}>
                <div className="form-group">
                  <label>Gói dịch vụ:</label>
                  <input
                    type="text"
                    value={newFarm.service_plan}
                    onChange={(e) => setNewFarm({ ...newFarm, service_plan: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Thời hạn (Số ngày):</label>
                  <input
                    type="number"
                    min="1"
                    value={newFarm.subscription_days}
                    onChange={(e) =>
                      setNewFarm({ ...newFarm, subscription_days: parseInt(e.target.value) || 30 })
                    }
                  />
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="button button-primary">
                  Tạo Nông Trại & Sinh API Key
                </button>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Hủy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
