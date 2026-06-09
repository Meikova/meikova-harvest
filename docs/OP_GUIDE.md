# Hướng dẫn vận hành và sử dụng (Operating Guide) - EveryThingDownloader

Tài liệu này hướng dẫn chi tiết cách cài đặt, khởi chạy, sử dụng và bảo trì hệ thống EveryThingDownloader chạy trên môi trường Windows cục bộ (local).

---

## 1. Yêu cầu hệ thống trước khi cài đặt
- **Hệ điều hành**: Windows 10/11
- **Python**: Phiên bản 3.12 trở lên (Đã cài đặt và thêm vào biến môi trường PATH)
- **Kết nối Internet**: Cần để tải các thư viện Python, tải tệp tin ffmpeg tự động lần đầu và để tải các video từ YouTube.

---

## 2. Các bước cài đặt và khởi chạy (Local Setup)

### Bước 2.1: Tạo môi trường ảo (venv)
Môi trường ảo giúp cô lập các thư viện của dự án để tránh xung đột hệ thống. Chạy lệnh sau tại thư mục gốc của dự án:
```powershell
python -m venv venv
```

### Bước 2.2: Kích hoạt venv và cài đặt thư viện
Kích hoạt môi trường ảo bằng Powershell và cài đặt các thư viện trong file `requirements.txt`:
```powershell
.\venv\Scripts\Activate.ps1
.\venv\Scripts\pip install -r requirements.txt
```

### Bước 2.3: Khởi chạy ứng dụng
Chạy trực tiếp file `app.py` bằng Python của môi trường ảo:
```powershell
.\venv\Scripts\python.exe app.py
```
**Lưu ý quan trọng ở lần chạy đầu tiên**:
Thư viện `static-ffmpeg` sẽ tự động tải các tệp nhị phân của FFmpeg (khoảng 50-70MB) về máy và cấu hình biến môi trường tự động. Tiến trình khởi chạy lần đầu có thể mất từ 10-30 giây tùy tốc độ mạng. Ở các lần chạy sau, server sẽ khởi động ngay lập tức.

Khi màn hình Console hiện thông báo:
`* Running on http://127.0.0.1:5000` (hoặc `http://localhost:5000`), hệ thống đã sẵn sàng.

---

## 3. Hướng dẫn sử dụng chi tiết (User Guide)

### Bước 1: Truy cập giao diện
Mở trình duyệt Web (Chrome, Edge, Firefox, Brave...) và truy cập đường dẫn:
[http://localhost:5000](http://localhost:5000)

### Bước 2: Dán đường dẫn (URL) cần tải
- Copy link video YouTube hoặc YouTube Shorts (Ví dụ: `https://www.youtube.com/watch?v=...` hoặc `https://www.youtube.com/shorts/...`).
- Nhấp vào nút **Paste** trên giao diện (nếu trình duyệt cấp quyền clipboard) hoặc dán thủ công (`Ctrl + V`) vào ô nhập liệu.
- Nhấn nút **ANALYZE LINK** (hoặc gõ Enter).

### Bước 3: Chọn định dạng và tải xuống
- Chờ vài giây để backend phân tích thông tin video. Giao diện sẽ hiển thị:
  - Ảnh đại diện video (thumbnail).
  - Tiêu đề video, tên kênh và thời lượng.
  - Phân loại: Badge **YouTube Shorts** (màu xanh cyan) hoặc **YouTube Video** (màu tím).
  - Danh sách các tùy chọn tải xuống khả dụng (Ví dụ: Video 1080p, Video 720p, Video 480p, Âm thanh MP3 chất lượng cao).
- Click nút **Get** bên cạnh định dạng mong muốn.
- Hệ thống sẽ bắt đầu tải video từ YouTube về máy chủ trung gian, tự động ghép âm thanh & hình ảnh (đối với video 1080p+), sau đó truyền trực tiếp xuống trình duyệt của bạn với thanh tiến trình đo lường chính xác dung lượng thực tế.
- Trình duyệt sẽ hiển thị hộp thoại lưu tệp (Save File) khi hoàn tất.

---

## 4. Cơ chế dọn dẹp bộ nhớ đệm (Temporary Files Storage)
- Khi người dùng tải xuống, backend sẽ tạo ra một thư mục tạm thời có tên dạng `downloads/temp_<uuid>/`.
- Tệp tin video/âm thanh sẽ được lưu tại đây trong quá trình tải và ghép nối.
- Ngay sau khi truyền tải tệp tin thành công tới trình duyệt (hoặc khi người dùng hủy tải giữa chừng), Python sẽ tự động xóa sạch thư mục `temp_<uuid>` này.
- **Lợi ích**: Đảm bảo không gây tràn ổ đĩa cứng của máy chủ sau một thời gian dài sử dụng.

---

## 5. Hướng dẫn bảo trì và khắc phục lỗi (Troubleshooting)

### Lỗi 1: YouTube chặn tải hoặc báo lỗi "Sign in to confirm you are not a bot" / HTTP Error 403
- **Nguyên nhân**: YouTube thường xuyên thay đổi thuật toán hoặc chặn các IP gửi quá nhiều yêu cầu tải.
- **Khắc phục**: 
  1. Cập nhật thư viện `yt-dlp` lên phiên bản mới nhất. `yt-dlp` được cộng đồng cập nhật liên tục để vượt qua các rào cản của YouTube.
  2. Mở cửa sổ dòng lệnh và chạy lệnh:
     ```powershell
     .\venv\Scripts\pip install --upgrade yt-dlp
     ```
  3. Khởi động lại server `app.py`.

### Lỗi 2: Không thể ghép hình ảnh với âm thanh ở độ phân giải 1080p trở lên
- **Nguyên nhân**: Thư viện `static-ffmpeg` chưa được tải về hoặc bị lỗi quyền ghi file.
- **Khắc phục**: Kiểm tra xem tiến trình Python có bị chặn bởi Antivirus/Windows Defender hay không. Bạn cũng có thể cài đặt FFmpeg thủ công trên hệ điều hành và thêm nó vào PATH hệ thống nếu muốn.
