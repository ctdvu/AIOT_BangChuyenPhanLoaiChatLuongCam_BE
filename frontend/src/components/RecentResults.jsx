import ClassificationImages from "./ClassificationImages";

function formatTime(value) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value));
}

export default function RecentResults({ items, loading }) {
  return <section className="recent-results" aria-labelledby="recent-results-title">
    <div className="section-heading recent-heading">
      <div><p className="eyebrow">Vừa phân loại</p><h2 id="recent-results-title">Kết quả gần đây</h2><p className="recent-description">4 lượt mới nhất · cập nhật tự động</p></div>
      <a className="history-link" href="#/history">Xem toàn bộ lịch sử <span aria-hidden="true">→</span></a>
    </div>
    {loading && !items.length ? <div className="recent-empty">Đang tải các kết quả gần đây…</div>
      : !items.length ? <div className="recent-empty"><strong>Chưa có kết quả phân loại</strong><span>Kết nối camera và chụp để xem kết quả tại đây.</span></div>
      : <div className="recent-grid">{items.map((item) => <article className="panel recent-card" key={item.id}>
        <div className="recent-card-heading">
          <strong>Lượt #{item.id}</strong>
          <time className="recent-time" dateTime={item.created_at}>{formatTime(item.created_at)}</time>
          <span className="label-badge">Grade {item.grade ?? item.tray}</span>
        </div>
        <ClassificationImages result={item} />
        <div className="recent-details">
          <p className="eyebrow">{item.images?.length > 1 ? "Kết quả chung" : "Kết quả phân loại"}</p>
          <div className="recent-outcome"><strong>{item.display_name}</strong><span>{(item.confidence * 100).toFixed(1)}%</span></div>
          <p className="recent-class">{item.ai_display_name || "Chưa có lớp chi tiết"}{item.images?.length > 1 ? " · Từ hai góc nhìn" : ""}</p>
        </div>
      </article>)}</div>}
  </section>;
}
