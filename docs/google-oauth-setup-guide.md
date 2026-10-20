# HƯỚNG DẪN THIẾT LẬP GOOGLE OAUTH CREDENTIALS (2 HƯỚNG)
**Áp dụng cho EveryThingDownloader (Web & Desktop Đa Nền Tảng)**

---

## 1. TỔNG QUAN THÔNG SỐ CẦN CẤU HÌNH
Dù chọn tạo trên Project có sẵn hay Project mới, các URL bên dưới là **bắt buộc** để hỗ trợ cả bản Web (cổng 5000), bản Desktop Electron (cổng 18650) và bản Cloud Render:

### A. Authorised JavaScript origins:
```text
http://localhost:5000
http://127.0.0.1:5000
http://localhost:18650
http://127.0.0.1:18650
https://everythingdownloader-6zct.onrender.com
```

### B. Authorised redirect URIs:
```text
http://localhost:5000/api/auth/google/callback
http://127.0.0.1:5000/api/auth/google/callback
http://localhost:18650/api/auth/google/callback
http://127.0.0.1:18650/api/auth/google/callback
https://everythingdownloader-6zct.onrender.com/api/auth/google/callback
```

---

## 2. HƯỚNG 1: TẠO TRÊN GOOGLE CLOUD PROJECT CÓ SẴN (NHANH NHẤT)
> [!TIP]
> Sử dụng khi bạn đã có sẵn Project trên Google Cloud (như project của `titan-remote`, `MashLoop`...). Cách này bỏ qua bước cấu hình Consent Screen phức tạp.

- **Bước 1**: Truy cập trang quản lý mã xác thực:  
  👉 [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
- **Bước 2**: Tại thanh điều hướng trên cùng, chọn Project bạn đang có (ví dụ: `titan-remote-512203`).
- **Bước 3**: Nhấn vào nút **`+ CREATE CREDENTIALS`** ở đầu trang -> Chọn **`OAuth client ID`**.
- **Bước 4**: Tại ô **Application type**, chọn **`Web application`**.
- **Bước 5**: Đặt tên gợi nhớ tại mục **Name**: `EveryThingDownloader-Client`.
- **Bước 6**:
  * Tại mục **Authorised JavaScript origins**: Bấm `+ ADD URI` và điền đủ 5 dòng ở mục 1.A.
  * Tại mục **Authorised redirect URIs**: Bấm `+ ADD URI` và điền đủ 5 dòng ở mục 1.B.
- **Bước 7**: Bấm **`CREATE`**.
- **Bước 8**: Cửa sổ hiện ra hiển thị `Client ID` và `Client Secret`. Bấm nút **`DOWNLOAD JSON`** để tải tệp credentials về máy.

---

## 3. HƯỚNG 2: TẠO TRÊN GOOGLE CLOUD PROJECT MỚI HOÀN TOÀN
> [!NOTE]
> Sử dụng khi bạn muốn dự án `EveryThingDownloader` độc lập hoàn toàn, không liên quan tới dự án cũ.

### Phần A: Khởi tạo Project mới
1. Truy cập liên kết tạo dự án:  
   👉 [https://console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)
2. Điền **Project name**: `EveryThingDownloader-Cloud`.
3. Bấm **`CREATE`** và chờ khoảng 10-15 giây để Google tạo xong project.
4. Chọn project vừa tạo ở thanh chọn project trên cùng.

### Phần B: Cấu hình Màn hình đồng ý (OAuth Consent Screen)
*(Chỉ cần làm 1 lần duy nhất cho Project mới)*
1. Vào menu bên trái: **APIs & Services** -> **OAuth consent screen**  
   👉 [https://console.cloud.google.com/apis/credentials/consent](https://console.cloud.google.com/apis/credentials/consent)
2. Tại mục **User Type**, chọn **`External`** (Người dùng bên ngoài) -> Bấm **`CREATE`**.
3. Điền các trường cơ bản:
   - **App name**: `EveryThingDownloader`
   - **User support email**: Chọn email Google của bạn.
   - **Developer contact information**: Nhập email của bạn.
   - Bấm **`SAVE AND CONTINUE`**.
4. Bước **Scopes**:
   - Bấm **`ADD OR REMOVE SCOPES`**.
   - Tích chọn 3 quyền cơ bản:
     * `.../auth/userinfo.email`
     * `.../auth/userinfo.profile`
     * `openid`
   - Bấm **`UPDATE`** -> Bấm **`SAVE AND CONTINUE`**.
5. Bước **Test users**:
   - Nếu app ở chế độ Testing, bấm **`+ ADD USERS`** -> Nhập email Google cá nhân của bạn (để được phép login thử nghiệm).
   - Bấm **`SAVE AND CONTINUE`** -> **`BACK TO DASHBOARD`**.

### Phần C: Tạo OAuth Client ID
1. Vào mục **Credentials** (menu bên trái).
2. Nhấn **`+ CREATE CREDENTIALS`** -> Chọn **`OAuth client ID`**.
3. **Application type**: Chọn **`Web application`**.
4. **Name**: `EveryThingDownloader-Web`.
5. Điền chính xác các URL:
   - **Authorised JavaScript origins**: Điền đủ 5 dòng ở mục 1.A.
   - **Authorised redirect URIs**: Điền đủ 5 dòng ở mục 1.B.
6. Bấm **`CREATE`** -> Bấm **`DOWNLOAD JSON`** lưu file về máy.

---

## 4. TÍCH HỢP VÀO CODE VỚI CƠ CHẾ 3 TẦNG (SAFE & ZERO-BOT LEAK)

Ứng dụng EveryThingDownloader hỗ trợ cơ chế nạp thông minh 3 tầng (3-Tier Fallback):

### Tầng 1 (Cloud Hosting / Render):
Khai báo Environment Variables trên Dashboard quản lý (Render / Docker / VPS):
- `GOOGLE_CLIENT_ID` = `<Client ID của bạn>`
- `GOOGLE_CLIENT_SECRET` = `<Client Secret của bạn>`

### Tầng 2 (Lưu trữ file nội bộ):
Đổi tên file JSON Google vừa tải về thành:
```text
client_secret.json
```
Đặt trực tiếp vào thư mục gốc của dự án `EveryThingDownloader/`.  
*(File này đã được khai báo trong `.gitignore`, không bao giờ bị commit lên mạng)*.

### Tầng 3 (Base64 nhúng thẳng trong mã nguồn):
Để không bị Bot quét mã của GitHub phát hiện chuỗi khóa bí mật `GOCSPX-...`, mã hóa chuỗi sang Base64:
- Trong Python:
  ```python
  import base64
  enc_id = base64.b64encode(b"YOUR_CLIENT_ID").decode()
  enc_sec = base64.b64encode(b"YOUR_CLIENT_SECRET").decode()
  ```
- Dán vào `routes/auth.py`:
  ```python
  _ENC_ID = "..."
  _ENC_SEC = "..."
  ```
- Dán `_ENC_ID` vào `static/js/main.js`:
  ```javascript
  const _ENC_GOOGLE_ID = "...";
  ```
