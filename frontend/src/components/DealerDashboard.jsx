import { useEffect, useState } from "react";
import { getDealerFarmDetail, getDealerFarms } from "../api";
import ClassificationImages from "./ClassificationImages";

const AI_CLASS_LABELS = {
  fresh_orange: "Cam tươi đẹp (Fresh)",
  blackspotted_orange: "Đốm đen (Blackspotted)",
  cankered_orange: "Loét vỏ (Cankered)",
  green_orange: "Cam xanh chưa chín (Green)",
  rotten_orange: "Cam thối / Hỏng (Rotten)",
};

export default function DealerDashboard({ activeTab = "compare", onTabChange }) {
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");
  const [filterRecommendation, setFilterRecommendation] = useState("all");
  const [sortBy, setSortBy] = useState("marketable_rate");

  async function loadFarms(selectedDays = days) {
    setLoading(true);
    setError("");
    try {
      const data = await getDealerFarms(selectedDays);
      setFarms(data);
      if (data.length > 0 && !selectedFarmId) {
        setSelectedFarmId(data[0].farm_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFarms(days);
  }, [days]);

  useEffect(() => {
    if (!selectedFarmId) return;
    let active = true;
    async function loadDetail() {
      setLoadingDetail(true);
      try {
        const res = await getDealerFarmDetail(selectedFarmId, days);
        if (active) setDetailData(res);
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoadingDetail(false);
      }
    }
    loadDetail();
    return () => {
      active = false;
    };
  }, [selectedFarmId, days]);

  const filteredFarms = farms
    .filter((f) => {
      if (filterRecommendation === "all") return true;
      return f.recommendation === filterRecommendation;
    })
    .sort((a, b) => {
      if (sortBy === "total_fruits") return b.total_fruits - a.total_fruits;
      if (sortBy === "spoilage_rate") return a.spoilage_rate - b.spoilage_rate;
      if (sortBy === "marketable_rate") return b.marketable_rate - a.marketable_rate;
      if (sortBy === "grade_1_rate") return b.grade_1_rate - a.grade_1_rate;
      return 0;
    });

  function getBadgeClass(rec) {
    if (rec === "recommended") return "badge-success";
    if (rec === "consider") return "badge-warning";
    if (rec === "high_risk") return "badge-danger";
    return "badge-secondary";
  }

  const totalMarketFruits = farms.reduce((acc, f) => acc + (f.marketable_count || 0), 0);
  const recommendedCount = farms.filter((f) => f.recommendation === "recommended").length;

  return (
    <div className="dealer-dashboard">
      {/* KPI TỔNG QUAN CHO ĐẠI LÝ THU MUA */}
      <div className="role-kpi-row">
        <div className="role-kpi-card kpi-dealer">
          <span className="kpi-title">Nông trại đang cung ứng</span>
          <strong className="kpi-num">{farms.length} nhà vườn</strong>
          <small>Dữ liệu thật từ băng chuyền AI</small>
        </div>
        <div className="role-kpi-card kpi-dealer">
          <span className="kpi-title">Nhà vườn đạt chuẩn Khuyến nghị</span>
          <strong className="kpi-num">{recommendedCount} vườn</strong>
          <small>Tỉ lệ hỏng &le; 15% & Loại 1 &ge; 50%</small>
        </div>
        <div className="role-kpi-card kpi-dealer">
          <span className="kpi-title">Tổng sản lượng thương phẩm (Loại 1+2)</span>
          <strong className="kpi-num">{totalMarketFruits} quả</strong>
          <small>Sẵn sàng thu mua trong {days} ngày qua</small>
        </div>
        <div className="role-kpi-card kpi-dealer">
          <span className="kpi-title">Đang xem hồ sơ</span>
          <strong className="kpi-num" style={{ fontSize: "1.1rem" }}>
            {detailData?.farm?.name || "Chọn nhà vườn"}
          </strong>
          <small>📞 {detailData?.farm?.contact_phone || "—"}</small>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {/* THANH LỌC DỮ LIỆU KHẢO SÁT */}
      <div className="dealer-filter-bar panel" style={{ padding: "14px 18px" }}>
        <div className="filter-item">
          <label>Khoảng thời gian thống kê:</label>
          <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
            <option value={7}>7 ngày gần nhất</option>
            <option value={30}>30 ngày gần nhất</option>
            <option value={90}>90 ngày gần nhất</option>
            <option value={365}>Toàn bộ năm (365 ngày)</option>
          </select>
        </div>

        <div className="filter-item">
          <label>Mức đánh giá chất lượng:</label>
          <select
            value={filterRecommendation}
            onChange={(e) => setFilterRecommendation(e.target.value)}
          >
            <option value="all">Tất cả nông trại ({farms.length})</option>
            <option value="recommended">Đề xuất nhập — Chất lượng tốt</option>
            <option value="consider">Cân nhắc / Chọn lọc theo lô</option>
            <option value="high_risk">Cảnh báo tỉ lệ hỏng cao</option>
          </select>
        </div>

        <div className="filter-item">
          <label>Sắp xếp ưu tiên:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="marketable_rate">Tỉ lệ đạt chuẩn thương phẩm cao nhất</option>
            <option value="spoilage_rate">Tỉ lệ cam hỏng thấp nhất</option>
            <option value="grade_1_rate">Tỉ lệ Cam Loại 1 cao nhất</option>
            <option value="total_fruits">Tổng sản lượng lớn nhất</option>
          </select>
        </div>

        <button
          type="button"
          className="button button-secondary btn-sm"
          style={{ marginLeft: "auto" }}
          onClick={() => loadFarms(days)}
        >
          Làm mới số liệu
        </button>
      </div>

      {/* TAB 1: BẢNG SO SÁNH CÁC NÔNG TRẠI */}
      {activeTab === "compare" && (
        <div className="dealer-split-layout">
          <section className="panel dealer-farms-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">So sánh chất lượng & sản lượng</p>
                <h3>Bảng Xếp Hạng Nông Trại ({filteredFarms.length})</h3>
              </div>
            </div>

            {loading ? (
              <div className="loading-state">Đang tổng hợp thống kê từ các nhà vườn...</div>
            ) : (
              <div className="table-responsive">
                <table className="admin-table dealer-table">
                  <thead>
                    <tr>
                      <th>Nông trại & Khu vực</th>
                      <th>Tổng sản lượng</th>
                      <th>Loại 1 (Đẹp)</th>
                      <th>Loại 2 (Khá)</th>
                      <th>Tỉ lệ Hỏng (Loại 3)</th>
                      <th>Đánh giá Khuyến nghị</th>
                      <th>Thẩm định</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFarms.map((f) => (
                      <tr
                        key={f.farm_id}
                        className={`dealer-row ${selectedFarmId === f.farm_id ? "row-selected" : ""}`}
                        onClick={() => setSelectedFarmId(f.farm_id)}
                      >
                        <td>
                          <strong>{f.farm_name}</strong>
                          <small className="d-block text-muted">
                            📍 {f.location || "—"} · 📞 {f.contact_phone || "—"}
                          </small>
                        </td>
                        <td>
                          <strong>{f.total_fruits}</strong> quả
                          <small className="d-block text-muted">
                            Thương phẩm: {f.marketable_count} quả ({(f.marketable_rate * 100).toFixed(1)}%)
                          </small>
                        </td>
                        <td>
                          <span className="badge badge-success">
                            {(f.grade_1_rate * 100).toFixed(1)}% ({f.grade_1_count})
                          </span>
                        </td>
                        <td>
                          <span className="badge badge-warning">
                            {(f.grade_2_rate * 100).toFixed(1)}% ({f.grade_2_count})
                          </span>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              f.spoilage_rate > 0.2 ? "badge-danger" : "badge-secondary"
                            }`}
                          >
                            {(f.spoilage_rate * 100).toFixed(1)}% ({f.grade_3_count})
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${getBadgeClass(f.recommendation)}`}>
                            {f.recommendation_label}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="button button-primary btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedFarmId(f.farm_id);
                              if (onTabChange) onTabChange("inspect");
                            }}
                          >
                            Xem hồ sơ & Ảnh
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* TÓM TẮT NHANH NÔNG TRẠI ĐANG CHỌN */}
          <section className="panel dealer-detail-panel">
            {detailData ? (
              <div>
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Tóm tắt nhanh nhà vườn</p>
                    <h3>{detailData.farm.name}</h3>
                  </div>
                  <span className={`badge ${getBadgeClass(detailData.stat.recommendation)}`}>
                    {detailData.stat.recommendation_label}
                  </span>
                </div>

                <p className="help-text" style={{ marginBottom: "14px" }}>
                  📍 <strong>Địa chỉ:</strong> {detailData.farm.location || "—"} <br />
                  📞 <strong>Điện thoại chủ vườn:</strong> {detailData.farm.contact_phone || "—"} <br />
                  📝 <strong>Mô tả:</strong> {detailData.farm.description || "—"}
                </p>

                <div className="dealer-stats-cards">
                  <div className="dealer-stat-card">
                    <span className="dstat-label">Sản lượng thương phẩm</span>
                    <span className="dstat-value">
                      {detailData.stat.marketable_count} / {detailData.stat.total_fruits} quả
                    </span>
                  </div>
                  <div className="dealer-stat-card">
                    <span className="dstat-label">Tỉ lệ Thương phẩm (Loại 1+2)</span>
                    <span className="dstat-value" style={{ color: "#15803d" }}>
                      {(detailData.stat.marketable_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="dealer-stat-card">
                    <span className="dstat-label">Tỉ lệ Cam Loại 1</span>
                    <span className="dstat-value" style={{ color: "#0284c7" }}>
                      {(detailData.stat.grade_1_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="dealer-stat-card">
                    <span className="dstat-label">Tỉ lệ Cam Hỏng (Loại 3)</span>
                    <span className="dstat-value" style={{ color: "#b91c1c" }}>
                      {(detailData.stat.spoilage_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="decision-card" style={{ marginBottom: "16px" }}>
                  <strong>Phân tích chi tiết 5 nhóm ngoại quan AI:</strong>
                  <div style={{ marginTop: "8px", display: "grid", gap: "6px" }}>
                    {Object.entries(detailData.stat.by_ai_class || {}).map(([cls, count]) => (
                      <div
                        key={cls}
                        style={{ display: "flex", justifyContent: "space-between", fontSize: ".82rem" }}
                      >
                        <span>{AI_CLASS_LABELS[cls] || cls}:</span>
                        <strong>{count} quả</strong>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className="button button-primary"
                  style={{ width: "100%" }}
                  onClick={() => onTabChange && onTabChange("inspect")}
                >
                  🔍 Mở xem toàn bộ Ảnh Kiểm Định Thực Tế ({detailData.recent_classifications?.length || 0} mẻ)
                </button>
              </div>
            ) : (
              <div className="empty-selection">
                <p>Chọn một nông trại trong bảng bên trái để xem tóm tắt chất lượng.</p>
              </div>
            )}
          </section>
        </div>
      )}

      {/* TAB 2: HỒ SƠ THẨM ĐỊNH CHI TIẾT & ẢNH MẪU THỰC TẾ */}
      {activeTab === "inspect" && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Kiểm định hình ảnh thực tế từ băng chuyền</p>
              <h2>
                Hồ sơ Ảnh Mẫu: {detailData?.farm?.name || "Chọn nông trại"}
              </h2>
            </div>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <select
                value={selectedFarmId || ""}
                onChange={(e) => setSelectedFarmId(parseInt(e.target.value))}
                style={{ padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              >
                {farms.map((f) => (
                  <option key={f.farm_id} value={f.farm_id}>
                    {f.farm_name} (Hỏng: {(f.spoilage_rate * 100).toFixed(1)}%)
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => onTabChange && onTabChange("compare")}
              >
                &larr; Quay lại Bảng so sánh
              </button>
            </div>
          </div>

          {loadingDetail ? (
            <div className="loading-state">Đang tải hình ảnh kiểm định từ máy chủ EC2...</div>
          ) : detailData?.recent_classifications?.length > 0 ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
                gap: "18px",
                marginTop: "16px",
              }}
            >
              {detailData.recent_classifications.map((item) => (
                <div key={item.id} className="dealer-sample-card">
                  <div className="sample-card-head">
                    <strong>Quả #{item.id} · Máng {item.tray}</strong>
                    <span
                      className={`badge ${
                        item.grade === 1
                          ? "badge-success"
                          : item.grade === 2
                          ? "badge-warning"
                          : "badge-danger"
                      }`}
                    >
                      {item.display_name} ({(item.confidence * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <ClassificationImages result={item} compact={false} />
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginTop: "8px",
                      fontSize: ".75rem",
                      color: "#64748b",
                    }}
                  >
                    <span>Lớp AI: {item.ai_display_name || item.ai_class}</span>
                    <span>{new Date(item.created_at).toLocaleString("vi-VN")}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="recent-empty">
              <strong>Nông trại này chưa có ảnh phân loại gần đây</strong>
              <span>Hãy chọn nông trại khác hoặc chờ nhà vườn vận hành băng chuyền.</span>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
