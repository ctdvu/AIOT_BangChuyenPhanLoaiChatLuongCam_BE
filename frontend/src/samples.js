export const SIMULATION_SAMPLES = [
  {
    label: "CAM_DEP",
    name: "Loại 1 – Cam tươi",
    confidence: 0.96,
    image: "/samples/cam-dep.svg",
  },
  {
    label: "CAM_KHUYET_TAT",
    name: "Cam có khuyết tật",
    confidence: 0.87,
    image: "/samples/cam-khuyet-tat.svg",
  },
  {
    label: "CAM_HONG",
    name: "Loại 3 – Cam xanh hoặc thối",
    confidence: 0.93,
    image: "/samples/cam-hong.svg",
  },
];

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Không đọc được ảnh mẫu"));
    image.src = source;
  });
}

/** Chuyển ảnh minh họa SVG thành PNG trước khi gửi vì API chỉ nhận JPEG/PNG/WebP. */
export async function sampleToPng(sample) {
  const image = await loadImage(sample.image);
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 640;
  const context = canvas.getContext("2d");
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png", 0.92));
  if (!blob) throw new Error("Không thể tạo ảnh mô phỏng");
  return blob;
}
