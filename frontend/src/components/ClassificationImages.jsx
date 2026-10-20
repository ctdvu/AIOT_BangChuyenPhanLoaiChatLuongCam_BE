export default function ClassificationImages({ result, compact = false }) {
  if (!result.images?.length) {
    return compact
      ? <a href={result.image_url} target="_blank" rel="noreferrer" aria-label={`Mở ảnh của lượt ${result.id}`}><img className="table-image" src={result.image_url} alt="Ảnh phân loại" /></a>
      : <a className="result-image-wrap" href={result.image_url} target="_blank" rel="noreferrer" aria-label={`Mở ảnh của lượt ${result.id}`}><img src={result.image_url} alt={`Kết quả ${result.display_name}`} /></a>;
  }

  return <div className={compact ? "history-images" : "result-camera-images"}>
    {result.images.map((image) => <figure key={image.camera_id}>
      <a href={image.image_url} target="_blank" rel="noreferrer" aria-label={`Mở ảnh Camera ${image.camera_id} của lượt ${result.id}`}>
        <img src={image.image_url} alt={`Camera ${image.camera_id} · ${image.ai_display_name}`} />
      </a>
      <figcaption>
        <strong>Camera {image.camera_id}{image.simulation ? " · Mô phỏng" : ""}</strong>
        <span>{image.ai_display_name}</span>
        <span>Grade {image.grade} · {(image.confidence * 100).toFixed(1)}%</span>
        <time dateTime={image.captured_at} title={new Date(image.captured_at).toLocaleString("vi-VN")}>{new Date(image.captured_at).toLocaleTimeString("vi-VN", {
          hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3,
        })}</time>
      </figcaption>
    </figure>)}
  </div>;
}
