import { SOURCE_NAMES } from "../categories";
import ClassificationImages from "./ClassificationImages";

function formatDate(value) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

export default function HistoryTable({ history, page, onPageChange }) {
  const items = history?.items ?? [];
  const totalPages = history?.total_pages ?? 0;

  return (
    <section className="panel history-panel" aria-labelledby="history-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Dữ liệu hệ thống</p>
          <h2 id="history-title">Lịch sử phân loại</h2>
        </div>
        <span className="record-count">{history?.total ?? 0} lượt</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Lượt / Ảnh</th>
              <th>Kết quả chung</th>
              <th>Độ tin cậy</th>
              <th>Khay</th>
              <th>Nguồn</th>
              <th>Thời gian</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  <strong className="history-session">Lượt #{item.id}{item.images?.length ? ` · ${item.images.length} ảnh` : ""}</strong>
                  <ClassificationImages result={item} compact />
                </td>
                <td>
                  <strong>{item.display_name}</strong>
                  <span className="mobile-meta">{item.ai_display_name || "Chưa có lớp chi tiết"}</span>
                  {item.aggregation_policy === "worst_grade" && <span className="history-policy">Theo góc có chất lượng thấp hơn</span>}
                </td>
                <td>{(item.confidence * 100).toFixed(1)}%</td>
                <td><span className="tray-chip">{item.tray}</span></td>
                <td>{SOURCE_NAMES[item.source] || item.source}</td>
                <td>{formatDate(item.created_at)}</td>
              </tr>
            ))}
            {!items.length && (
              <tr><td className="table-empty" colSpan="6">Chưa có dữ liệu phân loại.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button type="button" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>Trước</button>
          <span>Trang {page} / {totalPages}</span>
          <button type="button" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>Sau</button>
        </div>
      )}
    </section>
  );
}
