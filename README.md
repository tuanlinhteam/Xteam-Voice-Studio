# Xteam Voice Studio

Phần mềm chuyển văn bản tiếng Việt thành giọng nói, chạy hoàn toàn trên máy tính của bạn với giao diện màu xanh lá đặc trưng.

Không cần tài khoản. Không cần Internet sau khi cài. Văn bản và giọng nói của bạn không bị gửi đi đâu cả.

Chạy trên **Windows**, **Linux** và **macOS** (Mac chip Apple).

---

## 🌟 Tổng quan về Xteam Voice Studio

**Xteam Voice Studio** là giải pháp chuyển đổi văn bản sang giọng nói (TTS) AI chất lượng cao dành riêng cho tiếng Việt, sở hữu giao diện **Modern Emerald Green (Xanh lá)** hiện đại, mượt mà và trực quan.

### 🎨 Giao diện Xanh lá (Emerald Green Theme)
- Thiết kế tone xanh lá chủ đạo (Emerald / Green), tạo cảm giác tươi mới, hiện đại và bảo vệ mắt khi làm việc lâu.
- Hỗ trợ chế độ Sáng (Light) / Tối (Dark) tối ưu trên mọi màn hình.
- Bố cục trực quan: Trình soạn thảo văn bản thông minh, danh sách chọn giọng, bộ điều khiển cảm xúc/ngắt nghỉ, bảng phụ đề SRT và lịch sử tạo audio.

---

## Tính năng nổi bật

### 🎙️ Tạo giọng nói chất lượng cao
- **25+ giọng có sẵn**: Đầy đủ giọng Nam/Nữ, 3 miền Bắc - Trung - Nam với nhiều phong cách đa dạng (tin tức, kể chuyện, đọc truyện, tự nhiên, lồng tiếng...).
- **Nghe thử tức thì**: Nghe thử từng mẫu giọng trực tiếp trước khi tạo.
- **Hỗ trợ tiếng Anh xen kẽ**: Tự động nhận diện và đọc chuẩn xác các từ tiếng Anh lồng trong ngữ cảnh tiếng Việt.
- **Tùy chỉnh tốc độ**: Điều chỉnh tốc độ đọc từ 0.75x đến 1.50x.
- **Đa định dạng xuất ra**: Xuất tệp chất lượng phòng thu **WAV (48 kHz)** hoặc **MP3**.

### 🎭 Điều khiển cách đọc & Cảm xúc
- **Thẻ cảm xúc**: Chèn cảm xúc tức thì tại bất kỳ vị trí nào: `[cười]`, `[thở dài]`, `[hắng giọng]`.
- **Thẻ ngắt nghỉ**: Tùy chỉnh khoảng lặng chính xác: `[nghỉ 2s]`, `[nghỉ 500ms]`.
- **Từ điển phát âm riêng (Custom Dictionary)**: Tùy chỉnh phiên âm cho từ viết tắt hoặc danh từ riêng (ví dụ: `KTX` → "ký túc xá", `AI` → "trí tuệ nhân tạo").

### 🧬 Nhân bản giọng nói (Voice Cloning)
- Tạo giọng đọc riêng biệt từ đoạn âm thanh mẫu chỉ từ 5–8 giây.
- Lưu trữ danh sách giọng nhân bản để tái sử dụng bất cứ lúc nào.

### 👥 Kịch bản hội thoại / Podcast
- Hỗ trợ phân đoạn kịch bản nhiều nhân vật, mỗi nhân vật một giọng đọc khác nhau trong cùng một dự án.

### 📄 Nhập dữ liệu thông minh
- Tự động trích xuất nội dung từ các file **PDF, Word (.docx), TXT**.
- Công cụ **Làm sạch văn bản**: Tự động lọc khoảng trắng thừa, xóa ngắt dòng không mong muốn.

### ⚡ Tạo hàng loạt & Xuất phụ đề SRT
- **Tạo hàng loạt**: Đánh dấu mốc `[P1]`, `[P2]`... để tạo nhiều file audio riêng biệt hoặc tải trọn gói file `.zip`.
- **Phụ đề video (.srt)**: Tự động tạo file phụ đề đồng bộ chính xác từng câu, tương thích kéo thả ngay vào Premiere, CapCut, DaVinci Resolve.

---

## 💻 Cấu hình máy khuyến nghị

| Phần cứng | Tối thiểu | Khuyến nghị |
|---|---|---|
| **Hệ điều hành** | Windows 10/11 64-bit, Ubuntu/Debian, macOS | Như bên trái |
| **CPU** | 4 nhân | 6 nhân trở lên |
| **RAM** | 8 GB | 16 GB trở lên |
| **Ổ đĩa trống** | 3 GB | 5 GB |
| **GPU (Tùy chọn)** | Không bắt buộc | Card NVIDIA (hỗ trợ CUDA) để tăng tốc độ |

---

## 🌐 Tích hợp API (Local Server)

Xteam Voice Studio tích hợp sẵn máy chủ API cục bộ tại `http://127.0.0.1:8001` cho phép các ứng dụng ngoài hoặc kịch bản tự động gọi lệnh:

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| `GET` | `/health` | Kiểm tra trạng thái máy chủ |
| `GET` | `/voices` | Lấy danh sách giọng đọc |
| `POST` | `/api/tts/generate` | Chuyển văn bản thành tệp WAV/MP3 |
| `POST` | `/api/tts/generate-with-subtitles` | Tạo audio kèm phụ đề `.srt` |
| `POST` | `/api/tts/clone` | Nhân bản giọng nói từ audio mẫu |
| `POST` | `/api/tts/conversation` | Xử lý kịch bản hội thoại nhiều giọng |

---

## 🔒 Bản quyền & Quyền riêng tư

* **Bản quyền thương hiệu:** **Xteam Voice Studio** (Phát triển & Tùy biến bởi **Xteam**).
* **Mô hình AI cốt lõi:** Dựa trên nền tảng VieNeu-TTS (Phạm Nguyễn Ngọc Bảo) và các thư viện mã nguồn mở theo chuẩn Apache-2.0 / LGPL.
* **Quyền riêng tư:** Xem chi tiết tại [PRIVACY.md](PRIVACY.md).
* **Thông báo thư viện bên thứ 3:** Xem tại [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).