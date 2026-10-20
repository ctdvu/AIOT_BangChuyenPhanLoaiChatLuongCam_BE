export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal: AbortSignal.timeout(60000), ...options });
  } catch (error) {
    throw new Error(error.name === "TimeoutError"
      ? "Backend phản hồi quá chậm. Kiểm tra server rồi thử lại."
      : "Không liên lạc được backend. Kiểm tra FastAPI, địa chỉ API và kết nối mạng.");
  }
  if (!response.ok) {
    let message = `Yêu cầu thất bại (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item) => item.msg).join(", ");
      }
    } catch {
      // Giữ thông báo theo mã HTTP nếu response không phải JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

export const getCameras = () => request("/api/cameras/status", { signal: AbortSignal.timeout(10000) });
export const cameraStreamUrl = (id, generation) => `${API_BASE_URL}/api/cameras/${id}/stream?v=${generation}`;
export const cameraImageUrl = (path) => `${API_BASE_URL}${path}`;
const cameraPost = (path, body) => request(`/api/cameras${path}`, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
export const connectCamera = (id, url, simulation = false) => cameraPost("/connect", { camera_id: id, url, simulation });
export const disconnectCamera = (id) => cameraPost("/disconnect", { camera_id: id });
export const captureCamera = (id) => cameraPost(id ? `/${id}/capture` : "/capture", {});
export const classifyCameras = (id) => cameraPost(id ? `/${id}/classify` : "/classify", {});
export const saveCameraUrl = (id, url) => request(`/api/cameras/${id}/config`, {
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }),
});
export const rotateCamera = (id, rotation) => request(`/api/cameras/${id}/rotation`, {
  method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rotation }),
});

export async function getLatest() {
  const response = await fetch(`${API_BASE_URL}/api/classifications/latest`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Không lấy được kết quả mới nhất (${response.status})`);
  return response.json();
}

export function getHistory(page = 1, pageSize = 8) {
  return request(`/api/classifications?page=${page}&page_size=${pageSize}`);
}

export function getStats() {
  return request("/api/stats");
}

export function getModelStatus() {
  return request("/api/model");
}

export function createClassification({ image, filename, label, confidence, source = "model" }) {
  const formData = new FormData();
  formData.append("image", image, filename);
  if (label != null) formData.append("label", label);
  if (confidence != null) formData.append("confidence", String(confidence));
  formData.append("source", source);

  return request("/api/classifications", {
    method: "POST",
    body: formData,
  });
}
