import { AI_CLASS_NAMES, SOURCE_NAMES } from "../categories";
import ClassificationImages from "./ClassificationImages";

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

export default function LatestResult({ result, loading }) {
  return (
    <section className="panel latest-panel" aria-labelledby="latest-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Kết quả gần nhất</p>
          <h2 id="latest-title">Lượt phân loại mới nhất</h2>
        </div>
        {result && <span className={`label-badge label-${result.label}`}>Grade {result.grade ?? result.tray}</span>}
      </div>

      {loading && !result ? (
        <div className="empty-state">Đang tải dữ liệu…</div>
      ) : !result ? (
        <div className="empty-state">
          <span className="empty-icon">○</span>
          <strong>Chưa có kết quả</strong>
          <span>Tải ảnh cam hoặc chụp webcam để phân loại bằng AI.</span>
        </div>
      ) : (
        <div className="latest-content">
          <ClassificationImages result={result} />
          <dl className="result-details">
            <div>
              <dt>{result.images?.length > 1 ? "Kết quả chung" : "Phân loại"}</dt>
              <dd>{result.display_name}</dd>
            </div>
            <div>
              <dt>Lớp cam</dt>
              <dd>{result.ai_display_name || "Chưa có lớp chi tiết"}</dd>
            </div>
            <div>
              <dt>Độ tin cậy</dt>
              <dd>{(result.confidence * 100).toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Khay nhận</dt>
              <dd>Khay {result.tray}</dd>
            </div>
            <div>
              <dt>Thời gian</dt>
              <dd>{formatDate(result.created_at)}</dd>
            </div>
            <div>
              <dt>Nguồn kết quả</dt>
              <dd>{SOURCE_NAMES[result.source] || result.source}</dd>
            </div>
          </dl>
          {result.aggregation_policy === "worst_grade" && <p className="capture-policy">Lượt #{result.id} · Hai ảnh cùng một quả. Kết quả chung lấy góc nhìn có Grade cao hơn (chất lượng thấp hơn); cùng Grade thì chọn độ tin cậy cao hơn. Độ tin cậy và xác suất bên dưới thuộc góc được chọn.</p>}
          {result.probabilities && (
            <div className="probabilities">
              <h3>{result.images?.length > 1 ? "Xác suất của góc dùng cho kết quả chung" : "Xác suất 5 lớp"}</h3>
              {Object.entries(result.probabilities)
                .sort((a, b) => b[1] - a[1])
                .map(([name, probability]) => (
                  <div className="probability-row" key={name}>
                    <span>{AI_CLASS_NAMES[name] || name}</span>
                    <progress max="1" value={probability} aria-label={`Xác suất ${AI_CLASS_NAMES[name] || name}`} />
                    <strong>{(probability * 100).toFixed(1)}%</strong>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
