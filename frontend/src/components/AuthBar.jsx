export default function AuthBar({ user, onAuthChange }) {
  function handleLogout() {
    if (onAuthChange) onAuthChange(null);
  }

  const roleBadgeText = {
    admin: "QUẢN TRỊ VIÊN (ADMIN)",
    farm: "CHỦ NÔNG TRẠI (FARM)",
    dealer: "ĐẠI LÝ THU MUA (DEALER)",
  };

  if (!user) return null;

  return (
    <div className="auth-bar">
      <div className="auth-bar-inner">
        <div className="auth-user-info">
          <span className={`role-badge role-${user.role}`}>
            {roleBadgeText[user.role] || user.role}
          </span>
          <span className="auth-username">
            Tài khoản: <strong>{user.full_name || user.username}</strong> ({user.username})
          </span>
          <button
            type="button"
            className="button button-secondary btn-logout"
            style={{ marginLeft: "auto" }}
            onClick={handleLogout}
          >
            Đăng xuất
          </button>
        </div>
      </div>
    </div>
  );
}
