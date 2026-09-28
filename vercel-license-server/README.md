# Hướng dẫn Triển khai Máy chủ Quản lý Bản quyền trên Vercel

Hệ thống quản lý bản quyền Xteam License Server cho phép Admin kích hoạt, gia hạn và khóa mã máy (Hardware ID) của khách hàng từ xa qua web.

---

## 🚀 Cách 1: Deploy lên Vercel qua GitHub (Khuyên dùng - 1 phút)

1. **Tạo GitHub Repository mới:**
   - Đặt tên ví dụ: `xteam-voice-license`.
   - Tải toàn bộ nội dung trong thư mục này (`vercel-license-server/`) lên repository đó.

2. **Kết nối và Deploy trên Vercel:**
   - Truy cập [vercel.com](https://vercel.com) và đăng nhập.
   - Bấm **"Add New..."** $\rightarrow$ **"Project"** $\rightarrow$ Chọn repository `xteam-voice-license` vừa tạo.
   - (Tùy chọn) Trong mục **Environment Variables**, bạn có thể thêm:
     - `ADMIN_PASSWORD`: Mật khẩu đăng nhập Admin (mặc định là `xteam2026`).
   - Bấm **Deploy**.

3. **Lấy địa chỉ Web Vercel của bạn:**
   - Sau khi deploy xong, Vercel sẽ cấp cho bạn đường link (Ví dụ: `https://xteam-voice-license.vercel.app`).
   - Mở link đó trên trình duyệt (máy tính hoặc điện thoại) để vào **Trang Quản Trị (Admin Dashboard)**.

---

## 💻 Cách 2: Chạy thử nghiệm trên máy tính nội bộ (Local)

Chạy lệnh sau tại thư mục này:
```bash
node server.js
```
- Dashboard Admin sẽ mở tại: `http://localhost:3000`
- Mật khẩu đăng nhập mặc định: `xteam2026`

---

## 📱 Cách Kích hoạt cho Khách hàng:

1. Khi khách hàng mở phần mềm `Xteam-Voice-Studio.exe`, màn hình sẽ hiện:
   * **Mã máy của bạn:** `XTM-XXXX-XXXX-XXXX`
2. Khách bấm nút **"Sao chép"** và gửi mã đó cho bạn qua Zalo/Telegram.
3. Bạn mở trang Vercel Admin:
   * Nhập **Tên khách hàng**
   * Dán **Mã máy (HWID)**
   * Chọn **Thời hạn (1 tháng, 3 tháng, 6 tháng, 1 năm, Vĩnh viễn)**
   * Bấm **"Kích hoạt ngay"**.
4. Khách hàng bấm **"Kiểm tra kích hoạt lại"** trên phần mềm $\rightarrow$ Phần mềm lập tức mở khóa VIP và hiển thị tên khách hàng cùng số ngày sử dụng!
