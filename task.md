# Lộ trình Phát triển và Kiểm thử Từng Tính năng

Chúng ta sẽ thực hiện tuần tự từng tính năng. Sau khi hoàn thành một tính năng (Task lớn), tôi sẽ dừng lại để bạn kiểm thử. Khi bạn xác nhận tính năng đó hoạt động tốt, chúng ta mới chuyển sang tính năng tiếp theo.

---

## 📋 Danh sách Task Phát triển

### [x] Task 1: Cắt Video/Audio trước khi tải (Video Trimmer)
- [x] **Giao diện (Frontend)**: Thêm các ô nhập mốc thời gian Start/End và liên kết phím nóng (`[` và `]`) để gán thời gian nhanh trong Preview Modal.
- [x] **Truyền nhận dữ liệu**: Cập nhật hàm gọi API tải xuống ở Frontend để truyền thêm tham số `start_time` và `end_time`.
- [x] **Xử lý Backend**: Cập nhật file [tasks/download.py](file:///d:/JOB/DEV/EveryThingDownloader/tasks/download.py) để chèn tham số `-ss` và `-to` vào lệnh chạy FFmpeg trước khi tải/ghép luồng.
- [x] **Đóng gói & Ghép luồng**: Đảm bảo cắt chính xác đối với cả luồng ghép thích ứng (Adaptive DASH) và video thường.
- [x] **Kiểm thử nội bộ**: Xác nhận file tải về đúng phân đoạn đã chọn.
- [x] **Phân tách Raw vs Custom**: Nút "GET" ngoài tải file nguyên bản, nút "Download Format" tải file đã tùy biến qua preview.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 1**

### [ ] Task 2: Tự động nhận diện Link trong Clipboard (Clipboard Auto-Detect)
- [ ] **Cơ chế quét (Main process)**: Cài đặt luồng check khay nhớ tạm định kỳ trong [electron/main.js](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js).
- [ ] **Giao tiếp IPC**: Gửi sự kiện truyền link phát hiện được sang Renderer process.
- [ ] **Thông báo (Giao diện)**: Tạo giao diện thông báo dạng Toast nhỏ gọn ở góc màn hình gợi ý phân tích link vừa copy.
- [ ] **Độ nhạy & Lọc trùng**: Đảm bảo bỏ qua các link đã được quét hoặc không phải định dạng được hỗ trợ.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 2**

### [ ] Task 3: Hiệu ứng sóng nhạc trực quan khi phát Audio (Waveform Visualizer)
- [ ] **Thêm thẻ Canvas**: Tạo thẻ `<canvas>` động và CSS đi kèm trong vùng chứa trình nghe nhạc.
- [ ] **Xử lý Web Audio**: Kết nối trình phát nhạc với `AudioContext` và `AnalyserNode` ở Frontend.
- [ ] **Vẽ cột tần số**: Lập trình vòng lặp vẽ sóng nhạc chuyển động theo nhịp độ tần số thực tế.
- [ ] **Giải phóng bộ nhớ**: Hủy kết nối AudioContext khi đóng trình xem trước để tránh rò rỉ bộ nhớ.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 3**

### [ ] Task 4: Tải Phụ đề & Dịch tự động (Subtitle Downloader & Translator)
- [ ] **Trích xuất thông tin**: Trả về danh sách phụ đề có sẵn của video trong API `/api/info`.
- [ ] **Giao diện cấu hình**: Thêm tùy chọn phụ đề (Chọn ngôn ngữ, chọn hình thức Softsub/Hardsub) khi bấm tải.
- [ ] **Dịch tự động**: Tích hợp module dịch thuật miễn phí để chuyển đổi phụ đề sang tiếng Việt.
- [ ] **Nhúng phụ đề**: Sử dụng FFmpeg để ghép cứng chữ vào khung hình hoặc nhúng file phụ đề mềm vào luồng video.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 4**

### [ ] Task 5: Tải Playlist & Hàng loạt (Playlist & Batch Downloader)
- [ ] **Phân tích Playlist**: Cấu hình backend gọi yt-dlp ở chế độ flat để lấy nhanh danh sách video trong playlist.
- [ ] **Giao diện đa lựa chọn**: Tạo giao diện hiển thị danh sách video kèm checkbox cho phép người dùng chọn tải.
- [ ] **Quản lý hàng đợi (Queue)**: Lập trình hàng đợi tải tuần tự ở Frontend để quản lý tiến trình của từng file cài đặt.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 5**

### [ ] Task 6: Bộ chuyển đổi định dạng File (Format Converter)
- [ ] **Thêm nút & Lựa chọn**: Thiết kế nút Convert và modal chọn định dạng đầu ra (MP3, MP4 nén...) trong tab Downloaded Files.
- [ ] **Xử lý transcode**: Viết API backend chạy FFmpeg để chuyển đổi định dạng file bất đồng bộ.
- [ ] **Đồng bộ cơ sở dữ liệu**: Cập nhật file mới tạo vào SQLite database để giao diện hiển thị chính xác.
- *Trạng thái checkpoint*: ⏸️ **Dừng lại để người dùng kiểm thử Task 6**
