export default function Stats({ stats }) {
  const categories = stats?.by_category ?? [];
  return (
    <section className="stats-section" aria-labelledby="stats-title">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">Thống kê</p>
          <h2 id="stats-title">Số lượng đã phân loại</h2>
        </div>
        <div className="total-count">
          <strong>{stats?.total ?? 0}</strong>
          <span>Tổng số quả</span>
        </div>
      </div>
      <div className="stat-grid">
        {categories.map((item) => (
          <article className={`stat-card stat-${item.label}`} key={item.label}>
            <span className="stat-marker" aria-hidden="true" />
            <div>
              <strong>{item.count}</strong>
              <span>{item.display_name}</span>
            </div>
            <small>Khay {item.tray}</small>
          </article>
        ))}
        {!categories.length && [1, 2, 3].map((tray) => (
          <article className="stat-card is-placeholder" key={tray}>
            <span className="stat-marker" />
            <div><strong>0</strong><span>Đang tải…</span></div>
            <small>Khay {tray}</small>
          </article>
        ))}
      </div>
      <div className="ai-class-stats">
        {(stats?.by_ai_class ?? []).map((item) => (
          <div key={item.ai_class}>
            <span>{item.display_name}</span>
            <strong>{item.count}</strong>
            <small>Grade {item.grade}</small>
          </div>
        ))}
      </div>
      <p className="next-sample">Mỗi lượt chụp hai camera tính là 1 quả. Thống kê 5 lớp dùng kết quả chung của lượt; bản ghi cũ và mô phỏng theo khay vẫn nằm trong tổng số.</p>
    </section>
  );
}
