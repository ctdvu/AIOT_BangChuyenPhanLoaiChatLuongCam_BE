-- Chạy bằng tài khoản MySQL có quyền CREATE DATABASE/USER.
-- Bàn giao database trống: không chèn lịch sử, ảnh hoặc cấu hình camera.
-- Backend tự tạo các bảng khi khởi động; script không xóa dữ liệu đã tồn tại.
CREATE DATABASE IF NOT EXISTS orange_sorting
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'orange_user'@'localhost'
  IDENTIFIED BY 'orange_password';
CREATE USER IF NOT EXISTS 'orange_user'@'127.0.0.1'
  IDENTIFIED BY 'orange_password';

GRANT ALL PRIVILEGES ON orange_sorting.* TO 'orange_user'@'localhost';
GRANT ALL PRIVILEGES ON orange_sorting.* TO 'orange_user'@'127.0.0.1';
FLUSH PRIVILEGES;

