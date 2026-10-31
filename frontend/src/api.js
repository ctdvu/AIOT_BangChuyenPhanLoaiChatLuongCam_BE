export const API_BASE_URL = (
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL) || "http://localhost:8000"
).replace(/\/$/, "");

let currentToken = typeof localStorage !== "undefined" ? localStorage.getItem("orange_sort_token") : null;

export function getAuthToken() {
  return currentToken;
}

export function setAuthToken(token) {
  currentToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("orange_sort_token", token);
    } else {
      localStorage.removeItem("orange_sort_token");
    }
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

export async function request(path, options = {}) {
  let response;
  const headers = { ...(options.headers || {}) };
  if (currentToken && !headers.Authorization) {
    headers.Authorization = `Bearer ${currentToken}`;
  }

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      signal: AbortSignal.timeout(60000),
      ...options,
      headers,
    });
  } catch (error) {
    throw new Error(
      error.name === "TimeoutError"
        ? "Backend phản hồi quá chậm. Kiểm tra server rồi thử lại."
        : "Không liên lạc được backend. Kiểm tra FastAPI, địa chỉ API và kết nối mạng."
    );
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
      // Giữ nguyên mã status nếu body không phải JSON
    }
    throw new Error(message);
  }
  return response.json();
}

/* ================= AUTH API ================= */
export async function login(username, password) {
  const result = await request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (result.access_token) {
    setAuthToken(result.access_token);
  }
  return result;
}

export async function registerDealer(payload) {
  return request("/api/auth/register-dealer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getMe() {
  return request("/api/auth/me");
}

export function logout() {
  clearAuthToken();
}

/* ================= ADMIN API ================= */
export function getAdminFarms() {
  return request("/api/admin/farms");
}

export function createAdminFarm(payload) {
  return request("/api/admin/farms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateAdminFarm(farmId, payload) {
  return request(`/api/admin/farms/${farmId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function rotateFarmKey(farmId) {
  return request(`/api/admin/farms/${farmId}/rotate-key`, {
    method: "POST",
  });
}

export function resetFarmMac(farmId) {
  return request(`/api/admin/farms/${farmId}/reset-mac`, {
    method: "POST",
  });
}

export function getAdminUsers() {
  return request("/api/admin/users");
}

/* ================= FARM PORTAL API ================= */
export function getMyFarm() {
  return request("/api/farm/me");
}

export function updateMyFarm(payload) {
  return request("/api/farm/me", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/* ================= DEALER API ================= */
export function getDealerFarms(days = 30) {
  return request(`/api/dealer/farms?days=${days}`);
}

export function getDealerFarmDetail(farmId, days = 30) {
  return request(`/api/dealer/farms/${farmId}?days=${days}`);
}

/* ================= CLASSIFICATIONS & DEVICE API ================= */
export async function getLatest(farmId = null) {
  const query = farmId ? `?farm_id=${farmId}` : "";
  const token = getAuthToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${API_BASE_URL}/api/classifications/latest${query}`, { headers });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Không lấy được kết quả mới nhất (${response.status})`);
  return response.json();
}

export function getHistory(page = 1, pageSize = 8, farmId = null) {
  const query = farmId ? `&farm_id=${farmId}` : "";
  return request(`/api/classifications?page=${page}&page_size=${pageSize}${query}`);
}

export function getStats(farmId = null) {
  const query = farmId ? `?farm_id=${farmId}` : "";
  return request(`/api/stats${query}`);
}

export function getModelStatus() {
  return request("/api/model");
}

export function getDeviceStatus(farmId = null) {
  const query = farmId ? `?farm_id=${farmId}` : "";
  return request(`/api/device/status${query}`);
}

/* ================= CAMERAS API ================= */
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
