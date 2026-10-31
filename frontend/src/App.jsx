import { useEffect, useState } from "react";
import {
  clearAuthToken,
  getAuthToken,
  getMe,
  login,
  registerDealer,
} from "./api";
import AdminDashboard from "./components/AdminDashboard";
import AuthBar from "./components/AuthBar";
import DealerDashboard from "./components/DealerDashboard";
import FarmDashboard from "./components/FarmDashboard";

const ROLE_CONFIG = {
  admin: {
    brandMark: "AD",
    brandTitle: "Admin Cloud Portal",
    brandSub: "Quản trị Nông trại & Thiết bị",
    themeClass: "theme-admin",
    defaultTab: "farms",
    tabs: [
      {
        id: "farms",
        title: "🏢 Nông trại & Khóa ESP32",
        desc: "Tạo farm, gia hạn, đổi Key, mở khóa MAC",
      },
      {
        id: "users",
        title: "👥 Tài khoản Hệ thống",
        desc: "Quản lý Admin, Chủ vườn & Đại lý",
      },
      {
        id: "system",
        title: "🤖 Máy chủ AI & Thuật toán",
        desc: "EfficientNet-B0 V3 & Quy tắc gộp 2 ảnh",
      },
    ],
  },
  farm: {
    brandMark: "FM",
    brandTitle: "Nông Trại AIoT",
    brandSub: "Giám sát Băng chuyền ESP32",
    themeClass: "theme-farm",
    defaultTab: "live",
    tabs: [
      {
        id: "live",
        title: "📡 Trực tiếp Băng chuyền & ESP32",
        desc: "Ảnh 2 góc thời gian thực, LM393 & Servo",
      },
      {
        id: "history",
        title: "📊 Thống kê & Lịch sử Vườn",
        desc: "Sản lượng Loại 1, 2, 3 và nhật ký ảnh",
      },
      {
        id: "settings",
        title: "🔑 Khóa ESP32 & Gói Dịch vụ",
        desc: "Lấy API Key, xem MAC & chỉnh góc Camera",
      },
    ],
  },
  dealer: {
    brandMark: "DL",
    brandTitle: "Đại Lý Thu Mua",
    brandSub: "Khảo sát Chất lượng Nông trại",
    themeClass: "theme-dealer",
    defaultTab: "compare",
    tabs: [
      {
        id: "compare",
        title: "🏪 Bảng Xếp hạng Nông trại",
        desc: "So sánh sản lượng, tỉ lệ hỏng & khuyến nghị",
      },
      {
        id: "inspect",
        title: "🔍 Thẩm định Ảnh Mẫu Thực tế",
        desc: "Xem cặp ảnh 2 góc của từng lô cam",
      },
    ],
  },
};

export default function App() {
  const [user, setUser] = useState(null);
  const [userFarm, setUserFarm] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState("live");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // State cho màn hình Login khi chưa đăng nhập
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [registerMode, setRegisterMode] = useState(false);
  const [dealerForm, setDealerForm] = useState({
    username: "",
    password: "",
    full_name: "",
    phone: "",
  });
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  function applySession(tokenResponse) {
    const u = tokenResponse?.user || tokenResponse;
    if (!u || !u.role) {
      clearAuthToken();
      setUser(null);
      setUserFarm(null);
      return;
    }
    setUser(u);
    setUserFarm(tokenResponse?.farm || null);
    const cfg = ROLE_CONFIG[u.role];
    if (cfg) {
      setActiveTab(cfg.defaultTab);
    }
  }

  useEffect(() => {
    async function initAuth() {
      const token = getAuthToken();
      if (token) {
        try {
          const meRes = await getMe();
          applySession(meRes);
        } catch {
          clearAuthToken();
          setUser(null);
        }
      }
      setAuthChecked(true);
    }
    initAuth();
  }, []);

  async function handleAuthChange(authResult) {
    if (!authResult) {
      clearAuthToken();
      setUser(null);
      setUserFarm(null);
      return;
    }
    applySession(authResult);
  }

  async function handleLoginSubmit(e) {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      const res = await login(username, password);
      applySession(res);
      setUsername("");
      setPassword("");
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegisterDealerSubmit(e) {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);
    try {
      const res = await registerDealer(dealerForm);
      applySession(res);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  }

  if (!authChecked) {
    return (
      <div className="login-portal-screen">
        <div className="login-card">
          <p>Đang kiểm tra phiên đăng nhập...</p>
        </div>
      </div>
    );
  }

  /* ============================================================================
     MÀN HÌNH ĐĂNG NHẬP BẰNG TÀI KHOẢN & MẬT KHẨU
     ============================================================================ */
  if (!user) {
    return (
      <div className="login-portal-screen">
        <div className="login-portal-container" style={{ maxWidth: "460px", padding: "32px" }}>
          <div className="login-portal-header" style={{ flexDirection: "column", textAlign: "center", gap: "12px" }}>
            <span className="brand-mark" style={{ width: "48px", height: "48px", fontSize: "1.2rem", borderRadius: "10px" }}>
              OS
            </span>
            <div>
              <h1 style={{ fontSize: "1.35rem" }}>Orange Sort Cloud</h1>
              <p style={{ fontSize: ".86rem" }}>
                Hệ thống Phân loại Cam AIoT & Quản lý Nông trại
              </p>
            </div>
          </div>

          <div className="login-manual-tabs" style={{ justifyContent: "center" }}>
            <button
              type="button"
              className={`tab-btn ${!registerMode ? "active" : ""}`}
              onClick={() => {
                setAuthError("");
                setRegisterMode(false);
              }}
            >
              Đăng nhập
            </button>
            <button
              type="button"
              className={`tab-btn ${registerMode ? "active" : ""}`}
              onClick={() => {
                setAuthError("");
                setRegisterMode(true);
              }}
            >
              Đăng ký Đại lý
            </button>
          </div>

          {authError && <div className="error-banner" style={{ marginBottom: "16px" }}>{authError}</div>}

          {!registerMode ? (
            <form onSubmit={handleLoginSubmit} className="auth-form">
              <div className="form-group">
                <label>Tên đăng nhập</label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Nhập tên đăng nhập"
                />
              </div>
              <div className="form-group">
                <label>Mật khẩu</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Nhập mật khẩu"
                />
              </div>
              <button
                type="submit"
                className="button button-primary"
                style={{ width: "100%", marginTop: "8px", padding: "11px" }}
                disabled={authLoading}
              >
                {authLoading ? "Đang đăng nhập..." : "Đăng nhập"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegisterDealerSubmit} className="auth-form">
              <div className="form-group">
                <label>Tên đăng nhập (*)</label>
                <input
                  type="text"
                  required
                  value={dealerForm.username}
                  onChange={(e) => setDealerForm({ ...dealerForm, username: e.target.value })}
                  placeholder="Nhập tên đăng nhập"
                />
              </div>
              <div className="form-group">
                <label>Mật khẩu (*)</label>
                <input
                  type="password"
                  required
                  value={dealerForm.password}
                  onChange={(e) => setDealerForm({ ...dealerForm, password: e.target.value })}
                  placeholder="Tối thiểu 6 ký tự"
                />
              </div>
              <div className="form-group">
                <label>Họ tên / Tên Đại lý (*)</label>
                <input
                  type="text"
                  required
                  value={dealerForm.full_name}
                  onChange={(e) => setDealerForm({ ...dealerForm, full_name: e.target.value })}
                  placeholder="Công ty / Đại lý thu mua..."
                />
              </div>
              <div className="form-group">
                <label>Số điện thoại liên hệ</label>
                <input
                  type="text"
                  value={dealerForm.phone}
                  onChange={(e) => setDealerForm({ ...dealerForm, phone: e.target.value })}
                  placeholder="Số điện thoại"
                />
              </div>
              <button
                type="submit"
                className="button button-primary"
                style={{ width: "100%", marginTop: "8px", padding: "11px" }}
                disabled={authLoading}
              >
                {authLoading ? "Đang xử lý..." : "Đăng ký tài khoản Đại lý"}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  /* ============================================================================
     GIAO DIỆN RIÊNG BIỆT CHO TỪNG ROLE SAU KHI ĐĂNG NHẬP
     ============================================================================ */
  const roleCfg = ROLE_CONFIG[user.role] || ROLE_CONFIG.farm;
  const activeTabObj = roleCfg.tabs.find((t) => t.id === activeTab) || roleCfg.tabs[0];

  return (
    <div className={`app-shell ${roleCfg.themeClass}`}>
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Đóng menu"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* SIDEBAR RIÊNG BIỆT CỦA TỪNG ROLE */}
      <aside
        id="app-sidebar"
        className={`app-sidebar ${sidebarOpen ? "is-open" : ""}`}
        aria-label="Điều hướng theo vai trò"
      >
        <div className="brand">
          <span className={`brand-mark mark-${user.role}`}>{roleCfg.brandMark}</span>
          <span>
            <strong>{user.role === "farm" && userFarm ? userFarm.name : roleCfg.brandTitle}</strong>
            <small>{roleCfg.brandSub}</small>
          </span>
        </div>

        <p className="sidebar-label">
          Menu dành riêng cho {user.role === "admin" ? "Admin" : user.role === "farm" ? "Chủ Nông Trại" : "Đại Lý"}
        </p>

        <nav className="sidebar-nav">
          {roleCfg.tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`nav-item-btn ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => {
                setActiveTab(tab.id);
                setSidebarOpen(false);
              }}
            >
              <span>
                <strong>{tab.title}</strong>
                <small>{tab.desc}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`role-badge role-${user.role}`}>
            {user.role === "admin"
              ? "QUYỀN QUẢN TRỊ (ADMIN)"
              : user.role === "farm"
              ? "TÀI KHOẢN NÔNG TRẠI"
              : "TÀI KHOẢN ĐẠI LÝ"}
          </span>
          <p style={{ marginTop: "8px" }}>
            Đang đăng nhập: <strong>{user.full_name || user.username}</strong>
          </p>
        </div>
      </aside>

      <div className="app-workspace">
        <header className="topbar">
          <div className="topbar-location">
            <button
              type="button"
              className="sidebar-toggle"
              onClick={() => setSidebarOpen(true)}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <span>
              <strong>{roleCfg.brandTitle}</strong> <span aria-hidden="true">/</span>{" "}
              <span>{activeTabObj?.title}</span>
            </span>
          </div>
          <div className="system-status">
            <span className="status-dot" />
            Cloud EC2 Online
          </div>
        </header>

        {/* THANH CHUYỂN NHANH ROLE VÀ ĐĂNG XUẤT */}
        <AuthBar user={user} onAuthChange={handleAuthChange} />

        <main id="top">
          {user.role === "admin" && (
            <AdminDashboard activeTab={activeTab} onTabChange={setActiveTab} />
          )}

          {user.role === "farm" && (
            <FarmDashboard user={user} activeTab={activeTab} onTabChange={setActiveTab} />
          )}

          {user.role === "dealer" && (
            <DealerDashboard activeTab={activeTab} onTabChange={setActiveTab} />
          )}
        </main>
      </div>
    </div>
  );
}
