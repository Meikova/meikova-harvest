# PROJECT SESSION HANDOFF LOG

## Project Status
- Path: `D:\JOB\DEV\EveryThingDownloader`
- Mode: Desktop Electron Application (`electron/`) + Python Flask Backend (`app.py`)
- Standards: Antigravity Titan Standards, Ponytail Philosophy, TDD, Verification-Before-Completion.

## Last Updated
- Timestamp: 2026-10-20 14:26:00
- Version: v2.0.3 (Tray Vector Icons, Dynamic Asset Resolution & Modal Update Fixed)
- Exit Code: 0 (Node syntax checks OK, PyInstaller server build OK, app.asar packed)

## Summary of Accomplishments (Sprint v68 - System Tray Vector Icons & Live Asset Resolution Fix)
1. **Bổ sung Bộ Vector Icons Phát quang Neon Cho System Tray Context Menu (`electron/main.js`)**:
   - Khắc phục hiện tượng menu khay hệ thống bị trống bằng cách bổ sung 7 biểu tượng vector sắc nét (16x16 / 32x32 supersampled) vào từng mục menu:
     * Header `EveryThingDownloader`: Logo vô cực $\infty$ phát quang neon cyan (`logo.png`).
     * `Mở EveryThingDownloader`: Cửa sổ ứng dụng desktop (`window.png`).
     * `Mở trên trình duyệt Web`: Địa cầu kết nối web (`browser.png`).
     * `Mở thư mục tải về`: Thư mục tải về kèm mũi tên (`folder.png`).
     * `Khởi động lại Backend Engine`: Vòng xoay nạp lại động cơ (`refresh.png`).
     * `Kiểm tra bản cập nhật...`: Mũi tên tải nâng cấp vào khay (`update.png`).
     * `Thoát ứng dụng`: Nút nguồn thoát màu đỏ mềm (`quit.png`).
   - Đóng gói toàn bộ bộ icon vào `electron/resources/tray_icons/` và nạp tự động qua `getTrayIcon(name)`.

2. **Khắc phục Triệt để Lỗi Bấm "Check App Update" Không Phản Hồi**:
   - **Nguyên nhân gốc rễ**: File `server.exe` cũ đóng gói cố định `static/js/main.js` trong `sys._MEIPASS` không chứa bộ lắng nghe sự kiện `onAppAlert`. Khi `main.js` phát `app-alert` qua IPC, renderer cũ không nhận được nên không mở modal.
   - **Khắc phục**:
     * Cập nhật `app.py`: Bổ sung cơ chế `_resolve_app_asset_dir` ưu tiên nạp động `static` và `templates` từ thư mục mã nguồn `D:\JOB\DEV\EveryThingDownloader` và thư mục kế bên `server.exe` trước khi fallback về `sys._MEIPASS`. Nhờ đó mọi thay đổi CSS/JS/HTML đều có hiệu lực ngay lập tức.
     * Build lại `EveryThingDownloader-Web-2.0.3.exe` bằng PyInstaller và cập nhật đồng bộ vào `resources/server.exe`.
     * Đóng gói lại `app.asar` chứa đầy đủ mã nguồn Electron mới nhất và bộ icon khay hệ thống.

## Summary of Accomplishments (Sprint v67 - In-App Ambient Alert Modals & Windows Dark Tray Menu)
1. **Triệt tiêu Hộp thoại Win32 Nền Trắng, Chuẩn hóa In-App Ambient Alert Modal**:
   - Thay thế toàn bộ các lệnh gọi `dialog.showMessageBox` / `dialog.showErrorBox` trong `electron/main.js` (như thông báo "No Updates", "Restarted", v.v.) bằng hàm điều hướng IPC `sendAppAlert(title, message, type)`.
   - Preload script `electron/preload.js` bổ sung `onAppAlert` lắng nghe thông điệp hệ thống gửi từ main process.
   - Renderer `static/js/main.js` bắt sự kiện `onAppAlert` và hiển thị modal `#confirm-modal` chuẩn buồng tối ambient instrument.
   - Thêm bộ chuyển đổi phong cách động `applyModalTypeStyle(type)`:
     * `info`: Đèn viền phát quang động `--cyan` neon, icon thông tin vòng tròn sạch (clean vector SVG), nút "Đã hiểu" cyber gradient.
     * `success`: Đèn viền ngọc lục bảo `#10b981`, icon tích chọn thành công, nút gradient lục bảo.
     * `warning` / `danger` / `error`: Đèn viền hổ phách/đỏ cảnh báo, icon cảnh báo quang học, nút gradient đỏ nổi bật.

2. **Kích hoạt Dark Theme cho System Tray Context Menu & Native Dialogs (`electron/main.js`)**:
   - Tích hợp module `nativeTheme` và bật `nativeTheme.themeSource = 'dark'`.
   - Windows 10/11 tự động render toàn bộ Menu chuột phải khay hệ thống (System Tray context menu) và hộp thoại chọn tệp/thư mục ở chế độ Dark Mode sắc nét (nền đen/xám than, chữ trắng, highlight tối), xóa sổ hoàn toàn hiện tượng menu trắng chói mắt.
   - Tối ưu các mục trong `buildTrayMenu()`: Tinh gọn ngôn ngữ tiếng Việt trực quan, checkbox trạng thái cho "Khởi động cùng Windows", hỗ trợ click chuột trái để mở/phục hồi cửa sổ chính.

3. **Tối ưu Hóa Luồng Kiểm tra Cập nhật (Update Check Flow)**:
   - Khi bấm "Check App Update", hiển thị thanh tiến trình nổi không chặn màn hình thay vì bật alert blocking thừa.
   - Lắng nghe sự kiện `onUpdateAvailable` trong renderer để mở in-app confirm modal hỏi tải cập nhật tự động thay vì bật hộp thoại Win32.
   - Khi tải xong bản cập nhật ngầm, tự động hiển thị các nút thao tác "Cài đặt ngay" / "Cài đặt khi đóng ứng dụng" ngay trên card nổi in-app.

4. **Kiểm chứng & Đóng gói**:
   - `node -c electron/main.js; node -c static/js/main.js`: Exit Code 0.
   - Python unit tests: 79/79 passed in 50.41s.
   - Đóng gói đè `app.asar` trực tiếp vào thư mục cài đặt `C:\Users\kiemp\AppData\Local\Programs\EveryThingDownloader\resources\app.asar`.

## Summary of Accomplishments (Sprint v66 - System Tray Zero-Emoji, Dynamic Harmonization & Taskbar Icon Fix)
1. **Loại bỏ Hoàn toàn 8 Emoji Trong System Tray Context Menu (`electron/main.js`)**:
   - Loại bỏ 100% các ký tự emoji: `✨`, `📥`, `🌐`, `📂`, `⚙️`, `🔄`, `🔔`, `🛑`.
   - Chuẩn hóa văn bản menu theo phong cách chuyên nghiệp sạch sẽ, tối giản (Less Text, More Signal):
     * `EveryThingDownloader (v2.0.3)`
     * `Open Application`
     * `Open in Default Browser`
     * `Open Downloads Folder`
     * `Start with Windows (Enabled / Disabled)`
     * `Restart Backend Server`
     * `Check for Updates`
     * `Quit`

2. **Khắc phục Triệt để Icon Windows Taskbar & Bộ nhớ Đệm Explorer**:
   - Trỏ shortcut Start Menu `EveryThingDownloader.lnk` trực tiếp vào tệp đa độ phân giải `icon.ico,0`.
   - Phân tách AppID môi trường dev `isDev ? 'com.everythingdownloader.dev' : 'com.everythingdownloader.app'` để không bị Windows kéo icon cũ từ shortcut production.
   - Bổ sung `mainWindow.setIcon(getAppIcon())` trực tiếp khi khởi tạo cửa sổ frameless.
   - Khởi động lại `explorer.exe` làm sạch bộ nhớ đệm Taskbar trong RAM (Taskbar hiện đã hiển thị chuẩn logo vô cực $\infty$).

3. **Đồng bộ Dynamic Lighting Logo & Thiết kế lại Thang cuộn (Scrollbar)**:
   - Header logo chuyển thành inline vector `<svg class="header-logo-svg">` tự động đổi màu theo `--cyan` / `--accent`.
   - Thang cuộn toàn hệ thống đưa về chuẩn siêu mỏng `4px`, bo tròn `999px`, nền trong suốt và thumb phát quang động theo `--cyan-rgb`.
   - Đóng gói đè `app.asar` vào thư mục cài đặt Desktop.

## Summary of Accomplishments (Sprint v65 - Zero-Icon Mandate & Ambient Instrument UI Alignment)
1. **Thi hành Triệt để Zero-Icon Mandate (100% Inline Vector SVG)**:
   - Quét toàn diện codebase, xóa bỏ 100% thẻ icon font FontAwesome `<i class="fas ...">` và ký tự unicode đóng `×`:
     * `templates/index.html` dòng 978: Thay `×` trong `#btn-close-cookies` bằng inline vector SVG `stroke="currentColor"`.
     * `templates/index.html` dòng 2255: Thay `×` trong `#btn-loop-clear` bằng inline vector SVG `stroke="currentColor"`.
     * `templates/index.html` dòng 2347: Thay `<i class="fas fa-palette">` bằng inline vector SVG Palette.
     * `templates/index.html` dòng 2362: Thay `<i class="fas fa-fill-drip">` bằng inline vector SVG Paint/Drop.
     * `templates/index.html` dòng 2390: Thay `<i class="fas fa-border-style">` bằng inline vector SVG Outline/Stroke.
   - Thêm `aria-label` và thuộc tính vector chuẩn (`viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`).

2. **Chuẩn hóa Optical Center Alignment & Typography Baseline trong `static/css/styles.css`**:
   - Thêm khối quy tắc căn tâm quang học chống lệch baseline theo chuẩn `/ambient-instrument-ui`:
     * Áp dụng `display: inline-flex; align-items: center; justify-content: center; vertical-align: middle;` cho toàn bộ các nút bấm (`.btn-pill`, `.chip`, `.tab-item`, `.btn-menu-action`, `.settings-close-btn`, `.header-action-btn`, `.btn-primary`, `.btn-get`, `.btn-control`, `.btn-task-action`, v.v.).
     * Triệt tiêu khoảng trống baseline ẩn: `button svg, ... svg { display: block; flex-shrink: 0; }`.
     * Khóa dòng quang học text: `display: inline-block; line-height: 1; transform: translateY(-0.5px);` cho dấu tiếng Việt.
     * Căn chuẩn dòng text chạy inline: `p svg, li svg, dd svg, .text-inline svg { display: inline-block; vertical-align: -0.125em; flex-shrink: 0; margin-right: 4px; }`.
   - Cập nhật styling cho `.settings-close-btn svg`, `.btn-menu-action.btn-menu-clear svg`, `.color-picker-wrapper svg`.

3. **Tối ưu Hóa Màn hình Khởi động Desktop (`electron/splash.html`)**:
   - Dọn dẹp đoạn code trùng lặp thừa ở cuối file.
   - Cập nhật thông điệp telemetry khởi động theo chuẩn Ambient Instrument: `SYS // STARTING SERVER`, `SYS // LOADING ENGINES`, `SYS // INITIALIZING INGESTION`, `SYS // CONNECTING DAEMON`, `SYS // PREPARING STAGE`.
   - Đóng gói lại file `app.asar` và cập nhật trực tiếp vào thư mục cài đặt `C:\Users\kiemp\AppData\Local\Programs\EveryThingDownloader\resources\app.asar`.

4. **Kiểm chứng Toàn diện**:
   - Cú pháp JavaScript `node -c electron/main.js`: Exit Code 0.
   - Cú pháp JavaScript `node -c static/js/main.js`: Exit Code 0.
   - Toàn bộ 79 bài kiểm thử đơn vị Python `python -m unittest discover tests`: Exit Code 0 (79/79 passed in 57.59s).
   - Kiểm tra rà soát zero-icon: 0 thẻ `<i>`, 0 ký tự `×`, 0 font icon ngoài.

## Summary of Accomplishments (Sprint v64 - Desktop Startup Timeout Fix & Live Program Hot-Swap)
1. **Chẩn đoán Nguyên nhân Gốc rễ từ Ảnh Chụp Màn hình của Người dùng**:
   - Ảnh 1 hiển thị góc dưới màn hình splash phiên bản cũ **`v2.0.2`**.
   - Ảnh 2 hiển thị nhật ký lỗi:
     `[INFO] Initializing static-ffmpeg...`
     `Downloading https://github.com/zackees/ffmpeg_bins/raw/main/v8.0/win32.zip -> ...\_MEIxxxxxx\static_ffmpeg\bin\win32.zip`
     `Server did not respond within 60s.`
   - Bản cài đặt `v2.0.2` cũ chạy tải 80MB từ GitHub raw đồng bộ trên luồng chính trước khi khởi động Flask server. Do mạng tải > 60s, Electron timeout báo lỗi và thư mục tạm `_MEIxxxxxx` bị xóa mỗi lần tắt, gây lặp lại lỗi liên tục.

2. **Khắc phục Triệt để**:
   - Nạp sẵn `ffmpeg.exe` và `ffprobe.exe` vĩnh viễn vào `C:\Users\kiemp\AppData\Roaming\EveryThingDownloader\bin\` và `C:\Users\kiemp\AppData\Local\Programs\EveryThingDownloader\resources\`.
   - Cập nhật `app.py`: Tự động nhận diện thư mục bin nội bộ và system path, chuyển khởi tạo FFmpeg sang background daemon thread không chặn luồng chính.
   - Build lại `EveryThingDownloader-Web-2.0.3.exe` qua PyInstaller và cập nhật trực tiếp vào thư mục cài đặt `C:\Users\kiemp\AppData\Local\Programs\EveryThingDownloader\resources\server.exe`.
   - Khởi chạy trực tiếp: Server phản hồi HTTP 200 trong < 200ms, ứng dụng Desktop hiện diện và hoạt động trơn tru.

## Summary of Accomplishments (Sprint v63 - Ambient Instrument UI & Infinite Lemniscate Logo Redesign)
1. **Thiết kế Logo Vô Cực ($\infty$ Lemniscate) Độc Bản**:
   - **Tham chiếu kiến trúc**: Chuẩn hóa từ 2 dự án `MashLoop` (`D:\JOB\DEV\MashLoop`) và `titan-remote` (`D:\JOB\DEV\titan-remote`).
   - **Khắc phục lỗi đè viền**: Loại bỏ hoàn toàn đa lớp underglow, concentric circles và stroke chồng lấn; sử dụng chính xác 1 đường cong Bernoulli Lemniscate duy nhất với nét stroke `#00E5FF` (Electric Cyan) dày `44.8`, kèm 1 hạt satellite photon quang học `#FFFFFF` tại `(371.2, 198.4)` trên nền phòng tối `#080C14` bo góc mềm `rx="112"`.
   - **Đồng bộ hóa toàn bộ tài nguyên thương hiệu**:
     + `static/logo.svg` và `static/favicon.svg`
     + `static/logo.png` và `static/favicon.png` (sử dụng Electron headless renderer)
     + `electron/resources/icon.png` và `electron/resources/icon.ico` (đa kích thước 16x16 đến 256x256 qua Pillow)
     + `electron/splash.html` (giao diện khởi động phòng tối với typography Unbounded + JetBrains Mono)

2. **Tái cấu trúc Hệ Thống Design Tokens (CSS OKLCH Dynamic Lighting)**:
   - Khai báo CSS `@property` cho phép trình duyệt nội suy mượt mà ánh sáng: `--pulse`, `--acc-l`, `--acc-c`, `--acc-h`, `--acc2-l`, `--acc2-c`, `--acc2-h`, `--gh`, `--gc`.
   - Thiết lập bảng màu buồng tối: `--ink-0` (0.15 lightness), `--ink-1`, `--ink-2`, `--ink-3`, hairline border `--line` (0.7 opacity) và `--line-soft` (0.35 opacity).
   - Ánh sáng Emissive Phosphor: `--accent: oklch(var(--acc))` với tông Electric Cyan chủ đạo (`hue: 215`) kết hợp Electric Indigo (`hue: 285`).

3. **Chuẩn hóa Giao diện Ambient Instrument**:
   - **Hệ thống Typography 3 Tầng**:
     + Display / Brand: `Unbounded` (500, 600) — hình học lặp vô tận.
     + UI / Body: `Be Vietnam Pro` (400, 500, 600) — an toàn 100% cho dấu thanh tiếng Việt.
     + Telemetry / Data: `JetBrains Mono` (400, 500) — `tabular-nums` cho kích thước, thời lượng, timecode, tốc độ tải.
   - **Header Bar**: Logo vô cực + `EVERYTHING ∞ DOWNLOADER` + corner telemetry readout (`SYS // READY`).
   - **Navigation Tabs**: Chuyển đổi sang tactile segmented pill deck dạng trượt (`main-tabs`, `main-tab-btn`).
   - **Floating Downloads Manager**: Bo góc mềm, viền hairline, badge số lượng tabular monospace.

4. **Kiểm chứng Toàn diện**:
   - Sao lưu toàn bộ phiên bản trước vào nhánh an toàn `backup/v2.0.3-pre-ambient-ui` trên GitHub.
   - Kiểm tra cú pháp JS (`static/js/main.js`, `electron/main.js`, `electron/preload.js`): Exit Code 0.
   - Chạy toàn bộ test suite `python -m unittest discover tests`: Exit Code 0.
1. **Khắc phục Triệt để Lỗi Server Không Phản Hồi Trong 60s (`Server did not respond within 60s`)**:
   - **Nguyên nhân gốc rễ (nhờ chẩn đoán chi tiết)**:
     + Trong `app.py`, hàm `static_ffmpeg.add_paths()` được gọi đồng bộ (synchronous) ngay tại luồng chính trước khi khởi động Flask server.
     + Thư viện `static_ffmpeg` cố gắng tải gói nén 80MB `win32.zip` từ GitHub raw (`github.com/zackees/ffmpeg_bins/...`) về thư mục tạm `_MEIxxxxxx` của PyInstaller.
     + Do kết nối mạng tải 80MB mất hơn 60 giây, tiến trình Flask bị block hoàn toàn, không thể bind port TCP 18650, dẫn đến việc Electron báo timeout 60s.
     + Hơn nữa, thư mục `_MEIxxxxxx` bị xóa sạch mỗi khi tắt app, khiến mỗi lần mở app lại bị tải lại 80MB từ đầu.
   - **Giải pháp xử lý (Ponytail standard & Zero-fluff)**:
     + Chuyển toàn bộ logic khởi tạo FFmpeg sang luồng daemon nền (`_init_ffmpeg_async`), giải phóng hoàn toàn luồng chính. Flask server khởi động ngay lập tức trong <200ms.
     + Kích hoạt cờ `weak=True` để ưu tiên sử dụng `ffmpeg`/`ffprobe` có sẵn trên hệ thống nếu người dùng đã cài đặt.
     + Tự động lưu trữ vĩnh viễn tệp thực thi `ffmpeg` và `ffprobe` vào User Data Directory (`USER_DATA_DIR/bin`) để tái sử dụng vĩnh viễn giữa các phiên làm việc và cập nhật.
     + Nâng cấp phiên bản toàn hệ thống lên **`v2.0.3`**.
   - **Kiểm chứng**: Khởi động server tức thì (<200ms), 79 tests đạt Exit Code 0.

## Summary of Accomplishments (Sprint v61 - Hotfix v2.0.2: PyInstaller CI Spec Datas Fix & Downloads Persistence)
1. **Khắc phục Triệt để Lỗi Build trên Linux/macOS GitHub Actions (`Unable to find .../downloads`)**:
   - **Nguyên nhân cốt lõi**: Trong file `build_tool/packager.py`, `PYINSTALLER_SPEC.datas` chứa `('{root_dir}/downloads', 'downloads')`. Thư mục `downloads/` nằm trong `.gitignore`, không được theo dõi trong git nên trên môi trường runner mới của GitHub Actions, thư mục này không tồn tại khi checkout, khiến PyInstaller lập tức dừng khẩn cấp với mã lỗi 1.
   - **Giải pháp xử lý**:
     + Loại bỏ hoàn toàn `('{root_dir}/downloads', 'downloads')` khỏi `datas` trong `build_tool/packager.py`. Thư mục `downloads` là vùng đệm runtime và được `config.py` tự tạo lúc chạy ứng dụng, không phải tài nguyên tĩnh của gói nhị phân.
     + Bổ sung file `.gitkeep` vào thư mục `downloads/` và cập nhật `.gitignore` (`downloads/*` và `!downloads/.gitkeep`) để bảo đảm git luôn duy trì thư mục trên mọi máy.
     + Nâng cấp phiên bản toàn hệ thống lên **`v2.0.2`**.
     + Bổ sung kiểm thử đơn vị `test_packager_datas_excludes_downloads` trong `tests/test_builder_version.py`.
   - **Kiểm chứng**: Toàn bộ unit tests đạt Exit Code 0 (`Ran 79 tests, OK`).

## Summary of Accomplishments (Sprint v60 - Hotfix v2.0.1: Standalone Server Startup Fix & Packaging Pipeline Hardening)
1. **Khắc phục Triệt để Lỗi Khởi động Server (`Server did not start within 60s`) trên Bản Cài đặt Desktop**:
   - **Nguyên nhân cốt lõi phát hiện được**:
     + `build_tool/packager.py`: Danh sách `hiddenimports` của PyInstaller bị thiếu hàng loạt submodule thiết yếu (`routes.build`, `routes.convert`, `routes.extension`, `tasks.*`, `extractors.*`, `utils.*`, `requests`, `mutagen`, `edge_tts`, `quickjs`, `curl_cffi`, v.v.). Khi PyInstaller đóng gói `server.exe`, các module này bị bỏ rơi, dẫn đến `ModuleNotFoundError` ngay khi ứng dụng khởi chạy.
     + `build_tool/obfuscator.py`: Bộ biến đổi AST tự tạo (`_NameScrambler`, `_inject_dead_code`, `_StringEncoder`) làm hỏng cú pháp Python: `_inject_dead_code` chèn code không lùi dòng vào giữa các hàm gây `IndentationError`; `_NameScrambler` đổi tên biến ngẫu nhiên giữa các file gây `NameError`; PyArmor trial bị lỗi `ERROR out of license` khi kích hoạt `--mix-str`.
     + License Guard có `import tkinter as _tk` trong khi `packager.py` lại cấu hình `excludes=['tkinter']`.
     + `electron/main.js`: Lỗi thoát của `flaskProcess` bị nuốt chửng khi `mainWindow` chưa khởi tạo; `waitForServer` bị treo chờ đủ 60 giây mới báo lỗi hết hạn chung chung.
   - **Giải pháp xử lý (Ponytail standard & Zero-fluff)**:
     + Mở rộng toàn diện `hiddenimports` trong `build_tool/packager.py` bao phủ 100% các submodule và thư viện động.
     + Chuẩn hóa an toàn `build_tool/obfuscator.py` và `build_tool/builder_cli.py`: Thiết lập mặc định `False` cho các bộ biến đổi AST phá vỡ cú pháp; sửa `_inject_dead_code` tự căn chỉnh thụt dòng đúng chuẩn; loại bỏ `--mix-str` khỏi PyArmor; thay thế hoàn toàn `tkinter` trong License Guard bằng Windows native API (`ctypes.windll.user32.MessageBoxW`).
     + Nâng cấp `electron/main.js`: Bổ sung kiểm tra file thực thi `server.exe` trước khi gọi `spawn`; lưu trữ bộ đệm `startupStderr`; bắt ngay sự kiện thoát tiến trình sớm để báo lỗi chi tiết kèm mã thoát và traceback ngay lập tức thay vì bắt người dùng chờ 60 giây.
     + Cập nhật workflow CI/CD `.github/workflows/build-and-release.yml` sử dụng PyInstaller chuẩn hóa native bytecode.
     + Đồng bộ toàn bộ phiên bản dự án lên `v2.0.1` (`electron/package.json`, `electron/config.json`, `electron/package-lock.json`, `electron/splash.html`, `build_tool/builder_gui.html`, `build_tool/packager.py`, `update.json`).

2. **Kiểm thử Xác thực Toàn diện**:
   - Viết bài kiểm thử tự động `tests/test_builder_version.py` kiểm tra: Toàn vẹn `hiddenimports`, tính an toàn của cấu hình Obfuscation mặc định, và tính đồng nhất của phiên bản `v2.0.1` trên toàn bộ hệ thống.
   - Kết quả: Toàn bộ 78 tests chạy thành công tuyệt đối (`Ran 78 tests in 47.211s, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c electron/main.js` đạt Exit Code 0.

## Summary of Accomplishments (Sprint v59 - Universal Website Media Analyzer & Direct Fast-Path Harvester)
1. **Nâng cấp Toàn diện Bộ Phân tích Đa phương tiện cho Mọi Website (`extractors/generic.py`, `extractors/__init__.py`, `routes/info.py`)**:
   - **Đường tắt Tức thì cho Media Trực tiếp (Direct Media Fast-Path)**:
     + Xây dựng `is_direct_media_url(url)` và `extract_direct_media_info(url)` trong `extractors/generic.py`.
     + Phát hiện ngay lập tức các tệp trực tiếp (`.m3u8`, `.mpd`, `.mp4`, `.webm`, `.mkv`, `.avi`, `.mov`, `.flv`, `.ts`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.aac`, `.ogg`, `.opus`, `.wma`) với độ trễ <100ms mà không cần gọi tiến trình yt-dlp nặng nề.
     + Hỗ trợ mở rộng biến thể phân giải (Resolution Variant Expansion) cho HLS Master Playlist: Tự động tải manifest và trích xuất từng luồng độ phân giải (1080p FHD, 720p HD, 480p SD, 360p) kèm ước lượng kích thước chính xác qua `resolve_hls_size`.
     + Tích hợp trực tiếp vào đầu hàm `get_video_info` trong `routes/info.py`.
   - **Tái cấu trúc Thứ tự Trích xuất Ngữ nghĩa (Universal Semantic Extraction Pipeline)**:
     + Đưa các bộ bóc tách có cấu trúc ngữ nghĩa (Semantic Metadata) lên hàng đầu trước khi dùng quét chuỗi thô (raw regex scanning):
       1. Schema.org JSON-LD VideoObject & AudioObject (`@type: VideoObject`, `AudioObject`, `@graph`).
       2. OpenGraph & Twitter Cards (`og:video`, `og:audio`, `twitter:player:stream`).
       3. Modern Framework Payloads (`__NEXT_DATA__`, `__NUXT__`, `window.__INITIAL_STATE__`).
       4. Trình phát Web nhúng phổ quát (JWPlayer, Video.js, Plyr, DPlayer, ArtPlayer configs).
       5. Thẻ HTML5 `<video>` và `<audio>` (bóc tách cả thẻ `<source>` lồng bên trong).
       6. Thu thập iframe đệ quy (Recursive Iframe Harvesting, tối đa 3 cấp) kèm soi query parameters.
       7. Quét sâu mã nguồn script & Dean Edwards packer (Fallback).
   - **Phân loại Chính xác Luồng Âm thanh (Audio vs Video Stream Classification)**:
     + Chấm dứt tình trạng gán nhãn cứng `type: "video"`, `ext: "mp4"` cho các thẻ `<source>` âm thanh (`.mp3`, `.ogg`, `.wav`) và thẻ meta `og:audio`.
     + Tách biệt triệt để kết quả vào `video_options` và `audio_options`.
     + Khi trang chỉ có tệp âm thanh, tự động gán nhãn `category: "Web Audio"` và cập nhật platform label tương ứng.
   - **Giải quyết Triệt để Xung đột Khóa Trùng lặp (Deduplication Key Collision)**:
     + Cập nhật khóa gom nhóm: Với các nguồn đa phương tiện chung (`Direct Link`, `HTML5...`, `Schema.org`, `OpenGraph`, `Next.js`, `Web Player`, `Embed`), khóa phân biệt bao gồm cả `(type, server, episode, url)`.
     + Bảo toàn 100% các luồng video và audio khác nhau trên cùng một trang, không bị ghi đè hoặc loại bỏ nhầm.

2. **Kiểm thử Xác thực Toàn diện (`tests/test_universal_analyzer.py`)**:
   - Viết 10 bài kiểm thử đơn vị chuyên sâu bao phủ:
     + Direct MP4 Fast-Path (<100ms)
     + Direct HLS Master Playlist Variant Expansion (1080p, 720p, 480p)
     + Direct Audio Extraction (MP3)
     + Schema.org JSON-LD VideoObject & AudioObject
     + OpenGraph `og:video` & `og:audio`
     + HTML5 `<audio>` & `<source>` tags
     + Next.js `__NEXT_DATA__` embedded payload
     + Universal Web Player configs
     + Iframe depth traversal & stream query parameter decoding
     + Route integration fast-path trong `routes/info.py`.
   - Kết quả: Toàn bộ 75 tests trong test suite dự án chạy thành công tuyệt đối (`Ran 75 tests in 22.845s, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c static/js/main.js` đạt Exit Code 0.

## Summary of Accomplishments (Sprint v58 - Enterprise SRS Specification & Deep Security Hardening)
1. **Hoàn thiện Tài liệu Đặc tả Yêu cầu Phần mềm Chuẩn Doanh nghiệp (`docs/ENTERPRISE_SRS_SPECIFICATION.md`)**:
   - Biên soạn tài liệu SRS toàn diện theo tiêu chuẩn IEEE 830-1998 và ISO/IEC/IEEE 29148:2018.
   - Rà soát chuyên sâu toàn bộ **12 luồng dữ liệu** của EveryThingDownloader: Phân định rõ các luồng đã sẵn sàng cho môi trường doanh nghiệp (Production) và các luồng còn mang tính chất thử nghiệm/ủy thác (Demo/Stub/Partial).
   - Đánh giá kiến trúc hiện tại, xác định 3 nút thắt cổ chai lớn (Unbounded Concurrency, BitTorrent chỉ parse metadata mà chưa có P2P engine, và Nguy cơ tràn RAM khi thu luồng MSE).
   - Thiết lập mô hình Kiến trúc Mục tiêu (Enterprise Target Architecture) tích hợp Centralized Queue Manager, dual-engine yt-dlp + Aria2c RPC daemon, và Chunked Disk Spooling.
   - Đặc tả chi tiết 7 Module tính năng doanh nghiệp mở rộng: Hàng đợi tải tập trung, P2P BitTorrent Native, Giới hạn băng thông (Bandwidth Throttling), Lập lịch tải ngoài giờ cao điểm, Quản lý tải Playlist hàng loạt, Cổng xuất đám mây (Google Drive/Dropbox/S3), và Bộ phân tích kỹ thuật tệp tin chuyên sâu (Deep Media Inspector).

2. **Củng cố Ranh giới An ninh & Khắc phục Lỗ hổng Trọng yếu (`utils/security.py`, `app.py`, `routes/download.py`, `routes/convert.py`, `routes/build.py`)**:
   - **Phòng ngự SSRF (Server-Side Request Forgery)**:
     + Xây dựng hàm `is_safe_remote_url(url)` trong `utils/security.py`.
     + Phân giải DNS và kiểm tra địa chỉ IP đích bằng `ipaddress`: Chặn toàn bộ dải Private IP (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), Loopback (127.0.0.1, localhost, ::1), Link-local (169.254.169.254 AWS/GCP cloud metadata), Multicast và Reserved.
     + Áp dụng kiểm tra nghiêm ngặt tại `/api/proxy/stream`, `/api/download/image`, và `/api/system/proxy-sub`.
   - **Phòng ngự Path Traversal & Thực thi mã ngoài ý muốn (Arbitrary File Execution)**:
     + Xây dựng hàm `is_safe_local_media_path(file_path)` trong `utils/security.py`.
     + Chặn hoàn toàn danh sách đen phần mở rộng tệp thực thi độc hại: `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.js`, `.msi`, `.reg`, `.scr`, `.pif`, `.com`, `.hta`, `.sh`, `.py`, `.dll`, `.sys`, `.cpl`, `.jar`.
     + Giam giữ đường dẫn trong danh sách thư mục được ủy quyền (`TEMP_DOWNLOAD_DIR`, `USER_DATA_DIR`, `BASE_DIR`, thư mục Downloads/Videos/Music của người dùng).
     + Chặn truy cập thư mục hệ điều hành nhạy cảm (`C:\Windows`, `/etc`, `/bin`, v.v.).
     + Áp dụng tại `/api/download/open-file`, `/api/convert/probe`, `/api/convert/preview-stream`, `/api/convert`, và `/api/system/proxy-sub`.
   - **Khóa chặt Ranh giới CORS (Cross-Origin Resource Sharing)**:
     + Trong `app.py`, thay thế khai báo mở `CORS(app)` bằng cấu hình origin nghiêm ngặt, chỉ cho phép `localhost`, `127.0.0.1`, và scheme của Electron (`file://`, `vscode-webview://`, `app://`).

3. **Bộ Kiểm thử Bảo mật Toàn diện (`tests/test_security_boundary.py`)**:
   - Bổ sung 10 bài kiểm thử đơn vị bao phủ: Chặn SSRF trên Private IP / Cloud Metadata / Loopback, Chặn Path Traversal, Chặn tệp thực thi `.exe`, Chặn truy cập tệp Windows System, Cho phép tệp đa phương tiện hợp lệ trong temp/downloads.
   - Toàn bộ bộ kiểm thử 65 tests chạy thành công tuyệt đối (`Ran 65 tests in 11.051s, OK`, Exit Code 0).
   - Cú pháp JavaScript của `electron/main.js`, `electron/preload.js`, `static/js/main.js` kiểm chứng đạt Exit Code 0.

## Summary of Accomplishments (Sprint v57 - Direct Media Launch, Custom Downloads Directory, In-App Quick Play & Offline/Online Network Resiliency)
1. **Khởi chạy trực tiếp tệp tin & Xem trong thư mục cho tác vụ hoàn thành (`electron/main.js`, `electron/preload.js`, `routes/download.py`, `static/js/main.js`, `static/css/styles.css`, `tests/test_proxy_and_preview.py`)**:
   - **Nút Phát/Mở trực tiếp (Direct Launch `[Play]`) & Mở thư mục (`[Folder]`)**:
     + Trước đây: Khi tải hoặc chuyển đổi định dạng xong, người dùng chỉ thấy nút "Folder" hoặc "Save". Muốn xem video/nghe nhạc phải mở File Explorer, tìm file rồi nhấp đúp chuột.
     + Hiện tại: Bổ sung nút **Play** với biểu tượng vector SVG Play trực tiếp trên thẻ tác vụ. Khi bấm, tệp tin được khởi chạy ngay lập tức bằng trình phát mặc định của hệ điều hành (VLC, Windows Media Player, MPC-HC, v.v.) qua IPC `open-file` (`shell.openPath`) hoặc backend endpoint `/api/download/open-file`.
     + Bổ sung nút **Folder** với biểu tượng vector SVG Folder để mở và đánh dấu tệp tin trong Explorer/Finder.
   - **Xem trước tức thì trong ứng dụng (`openCompletedTaskPreview()`)**:
     + Với môi trường trình duyệt web (hoặc trước khi lưu file), thẻ tác vụ cung cấp nút **Play** kích hoạt ngay trình phát preview modal tích hợp sẵn của EveryThingDownloader qua stream `/api/download/file/${downloadId}?preview=true` mà không cần tải lại file.
   - **Chuẩn hóa 100% SVG Vector icon**:
     + Toàn bộ các nút hành động tác vụ (`btn-task-open`, `btn-task-folder`, `btn-task-preview`, `btn-task-save`, `btn-task-retry`, `btn-task-clear`) đều sử dụng inline SVG vector chuẩn.

2. **Cấu hình tùy chọn thư mục tải về trong Global Settings (`templates/index.html`, `static/js/main.js`, `electron/main.js`, `electron/preload.js`)**:
   - Thêm hàng thiết lập **Downloads Location** trong menu Global Settings, hiển thị đường dẫn thư mục lưu trữ hiện tại.
   - Bổ sung nút **Open** mở ngay thư mục downloads và nút **Change** (trên Electron) cho phép người dùng chọn bất kỳ thư mục nào trên máy tính.
   - Tự động lưu và đồng bộ thư mục tùy chỉnh vào file `settings.json` trong User Data Directory (`app.getPath('userData')`), không bị mất khi cập nhật phiên bản.
   - Hộp thoại lưu file (`save-file`) tự động mở đúng thư mục người dùng đã cấu hình thay vì thư mục Downloads mặc định.

3. **Giám sát kết nối mạng Online / Offline tự phục hồi (`static/js/main.js`, `static/css/styles.css`)**:
   - Bổ sung trình lắng nghe sự kiện mạng toàn cục `window.addEventListener('offline')` và `online`.
   - Khi mất mạng: Hiển thị thanh thông báo nổi Glassmorphism màu hổ phách cảnh báo kết nối Internet bị gián đoạn.
   - Khi có mạng trở lại: Hiển thị thanh thông báo nổi Glassmorphism màu xanh lục/cyan xác nhận mạng đã phục hồi, đồng thời hỗ trợ người dùng bấm **Retry** khôi phục ngay các tác vụ bị gián đoạn.

4. **Kiểm chứng xác thực (Verification)**:
   - Toàn bộ 55 bài kiểm thử unit tests chạy thành công (`Ran 55 tests in 11.933s, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c electron/main.js electron/preload.js static/js/main.js` đạt Exit Code 0 sạch lỗi.

## Summary of Accomplishments (Sprint v56 - Download Task Instant Retry & Resilient Error Recovery)
1. **Cơ chế Thử lại Tải tệp tin (Instant Download Retry) khi gặp sự cố (`static/js/main.js`, `static/css/styles.css`)**:
   - **Nút Thử lại (Retry) trên thẻ tác vụ thất bại**:
     + Trước đây: Khi một tác vụ tải về bị lỗi mạng, đứt kết nối SSE hoặc lỗi server, thẻ tác vụ chỉ hiện nút "Clear". Người dùng buộc phải phân tích lại đường link hoặc cuộn tìm lại định dạng để bấm Get từ đầu.
     + Hiện tại: Tự động lưu thông tin payload tải (`_retryPayload` cho direct download, `_retryStream` cho MSE stream capture) ngay trên thẻ tác vụ. Khi tác vụ chuyển sang trạng thái lỗi (`state-error`), nút **Retry** nổi bật xuất hiện bên cạnh nút **Clear**.
   - **Tái khởi tạo kết nối thông minh (`retryTask()`)**:
     + Bấm "Retry" lập tức đặt lại thanh tiến độ về 5% (hiệu ứng sọc neon chuyển động), đổi trạng thái thành "Retrying... -> Re-connecting...", đổi nút thành "Cancel" và phát yêu cầu tải mới lên server mà không cần người dùng thao tác lại URL.
     + Tái kết nối luồng SSE EventSource và tự động cập nhật tiến độ cho tới khi file tải xong hoàn tất.
   - **Tái cấu trúc module hóa trình lắng nghe SSE (`setupTaskSSE()`)**:
     + Đóng gói logic phân tích thông điệp SSE (`pending`, `downloading`, `merging`, `complete`, `error`) thành hàm dùng chung duy nhất, tái sử dụng giữa `triggerDownload` và `retryTask`, loại bỏ hoàn toàn mã trùng lặp.
   - **Định kiểu CSS chuẩn thiết kế (`static/css/styles.css`)**:
     + Bổ sung class `.btn-task-retry` với viền phát sáng cyan neon (`rgba(0, 243, 255, 0.25)`), hiệu ứng hover đổi màu mượt mà, hỗ trợ cả dark theme và light theme.

2. **Kiểm chứng xác thực (Verification)**:
   - Toàn bộ 30 tests trong test suites chạy qua thành công (`Ran 30 tests in 10.296s, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c electron/main.js electron/preload.js static/js/main.js` đạt Exit Code 0 sạch lỗi.

## Summary of Accomplishments (Sprint v55 - Unified Downloads Directory, Manager Quick Actions & Pure SVG Standard)
1. **Thống nhất thư mục Downloads chuẩn người dùng & Tiện ích Downloads Manager (`electron/main.js`, `routes/download.py`, `templates/index.html`, `static/css/styles.css`, `static/js/main.js`, `tests/test_proxy_and_preview.py`)**:
   - **Thống nhất thư mục lưu trữ tải về (`getAppDownloadsDir()`)**:
     + Thay thế việc trỏ vào thư mục cài đặt `resourcesPath\downloads` (vốn có nguy cơ thiếu quyền Administrator trong Program Files và bị NSIS dọn khi update).
     + Trỏ thống nhất toàn bộ các luồng mở thư mục, tải tệp tin của Electron (`will-download`), menu Tray, phím tắt `Ctrl+Shift+D`, và IPC `open-downloads-folder` về thư mục tiêu chuẩn của người dùng: `app.getPath('downloads')/EveryThingDownloader` (hoặc `Downloads` của hệ điều hành).
   - **Bổ sung API backend mở thư mục lưu trữ (`routes/download.py`)**:
     + Thêm endpoint `/api/download/open-folder`: Tự động khởi chạy trình quản lý file hệ điều hành (Explorer trên Windows qua `os.startfile`, Finder trên macOS qua `open`, File Manager trên Linux qua `xdg-open`) để mở thư mục lưu trữ khi người dùng truy cập qua trình duyệt ngoài.
     + Viết unit test tự động trong `tests/test_proxy_and_preview.py` xác minh endpoint phản hồi 200 OK.
   - **Nâng cấp thanh công cụ Downloads Manager Header (`templates/index.html`, `static/js/main.js`, `static/css/styles.css`)**:
     + Thêm nút **Mở thư mục Downloads** (`#downloads-open-folder-btn`): Bấm 1 chạm để mở ngay thư mục chứa file đã tải trong Windows Explorer.
     + Thêm nút **Dọn sạch danh sách hoàn thành** (`#downloads-clear-all-btn`): Cho phép người dùng dọn tất cả tác vụ đã xong/lỗi trong 1 cú click thay vì phải bấm Clear thủ công từng thẻ.
   - **Triệt tiêu 100% ký tự Unicode và HTML Entity icon còn sót**:
     + Thay thế `&#9662;` (`▾`) tại nút thu gọn `#downloads-toggle-btn` bằng SVG Chevron mượt mà có hiệu ứng xoay 180 độ.
     + Thay thế toàn bộ `&times;` (`×`) tại `#close-settings-menu-btn`, `#close-transcript-sidebar-btn`, `#close-toast-btn` bằng SVG Cross vector chuẩn.
     + Đạt chuẩn 100% SVG Vector trên toàn hệ thống.

2. **Kiểm chứng xác thực (Verification)**:
   - Toàn bộ 48 tests trong test suites chạy qua thành công (`Ran 48 tests in 8.228s, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c electron/main.js electron/preload.js static/js/main.js` đạt Exit Code 0 sạch lỗi.

## Summary of Accomplishments (Sprint v54 - Auto-Update Overhaul, User Data Persistence & Silent Background Upgrades)
1. **Tối ưu hóa toàn diện cơ chế Cập nhật Phiên bản (Auto-Update Overhaul) (`electron/main.js`, `electron/preload.js`, `config.py`, `app.py`, `utils/cookies.py`, `routes/cookies.py`, `templates/index.html`, `static/css/styles.css`, `static/js/main.js`, `tests/test_user_data_persistence.py`)**:
   - **Không khóa giao diện khi tải cập nhật (Zero UI Blocking)**:
     + Loại bỏ hoàn toàn cửa sổ `modal: true` chặn tương tác người dùng trong lúc tải bản cài mới.
     + Chuyển luồng tải về chế độ ngầm (Background streaming) qua `downloadFile` trong Electron, phát tín hiệu IPC `update-download-progress`.
     + Bổ sung thẻ thông báo nổi không chiếm màn hình (`#update-progress-toast`) theo phong cách Glassmorphism (Cyan/Violet neon), hiển thị tiến độ tải (%), dung lượng (MB/MB), tốc độ tải (KB/s, MB/s) theo thời gian thực mà không làm gián đoạn bất kỳ thao tác nào của người dùng.
   - **Triệt tiêu cửa sổ Terminal/CMD đen khi bấm Cài đặt (Zero CMD Flash)**:
     + Thay thế triệt để lệnh `cmd.exe /c ...` bằng PowerShell ẩn (`powershell.exe -WindowStyle Hidden -NoProfile -NonInteractive -Command "Start-Sleep -Milliseconds 600; Start-Process -FilePath '...'"` kèm `windowsHide: true, stdio: 'ignore'`).
     + Trình cài đặt NSIS được khởi chạy mượt mà, hoàn toàn không có bất kỳ cửa sổ CMD/terminal màu đen nào chớp nháy trên màn hình.
   - **Khắc phục lỗi đụng độ cổng 5000 và treo SQLite WAL khi mở lại app**:
     + Bổ sung endpoint ngắt kết nối an toàn `/api/system/shutdown` trên Flask backend, thực thi `PRAGMA wal_checkpoint(TRUNCATE)` để ghi đồng bộ toàn bộ transaction log của SQLite vào file chính và đóng kết nối sạch sẽ trước khi tắt app.
     + Trước khi khởi chạy bộ cài hoặc đóng app, Electron gọi shutdown backend và chờ 400ms để nhả hoàn toàn file lock.
     + Loại bỏ cờ điều kiện `isDev` khi dọn cổng 5000: Đảm bảo cả bản đóng gói production cũng tự động quét và giải phóng các tiến trình `server.exe` mồ côi chiếm cổng 5000 trước khi khởi động.
   - **Bảo toàn dữ liệu người dùng qua các lần cập nhật (100% Data Persistence)**:
     + Chuyển thư mục lưu trữ cơ sở dữ liệu `downloads.db` và cookies từ thư mục cài đặt (`resourcesPath` - vốn bị NSIS xóa sạch mỗi lần cài đè) sang thư mục tiêu chuẩn của hệ điều hành (`%APPDATA%\EveryThingDownloader` trên Windows hoặc `app.getPath('userData')`).
     + Bổ sung cơ chế tự động di chuyển dữ liệu cũ (`migrate_legacy_user_data()`): Tự động phát hiện và sao chép an toàn `downloads.db` cùng các file cookies từ thư mục cũ sang `USER_DATA_DIR` ngay khi khởi động lần đầu.
     + Viết bộ kiểm thử TDD (`tests/test_user_data_persistence.py`) kiểm chứng đầy đủ 3 kịch bản: nhận diện biến môi trường `EVERYTHING_USER_DATA`, nhận diện APPDATA, và tự động di chuyển database/cookies cũ.
   - **Giao diện & Tiện ích cập nhật**:
     + Thêm nút "Check App Update" trực tiếp trong menu Settings dropdown (`templates/index.html`) với icon SVG vector chuẩn.
     + Thêm lựa chọn: "Cài đặt & Khởi động lại ngay" hoặc "Cài khi thoát ứng dụng" (tự động chạy installer khi tắt app).
     + 100% icon biểu tượng sử dụng SVG inline, tuân thủ nghiêm ngặt tiêu chuẩn không emoji.

2. **Kiểm chứng xác thực (Verification)**:
   - Python unit test suite: `tests/test_user_data_persistence.py` chạy qua 3/3 tests (Exit Code 0).
   - Kiểm tra cú pháp JavaScript: `node -c electron/main.js electron/preload.js static/js/main.js` đạt Exit Code 0 sạch lỗi.

## Summary of Accomplishments (Sprint v53 - Anime & Multi-Episode Stream Navigation Suite)
1. **Thanh điều hướng tập phim toàn diện cho Stream Player & Trình phát Video (`templates/index.html`, `static/css/styles.css`, `static/js/main.js`, `extractors/generic.py`)**:
   - **Tập trước / Tập sau & Dropdown chọn tập (`#preview-episode-nav`)**: Tích hợp thanh công cụ chọn tập ngay tại chân trang Preview Modal (`preview-footer-toolbar`), hiển thị đồng bộ cho cả video player và trình phát webview stream (như AnimeVietSub).
   - **Huy hiệu đếm số tập (`#preview-ep-counter`)**: Hiển thị trực quan tiến độ tập (VD: `Tập 2 / 24`) bằng badge gradient bo tròn, tự động cập nhật khi đổi tập.
   - **Nút điều hướng nổi trên màn hình (`#preview-stream-floating-prev`, `#preview-stream-floating-next`)**: Xuất hiện mượt mà khi di chuột vào khung phát webview player, hỗ trợ bấm 1 chạm để qua tập trước hoặc tập sau.
   - **Tự động nhận diện tập từ URL đầu vào (`extractors/generic.py`)**: Khi nhập link tập cụ thể (VD: `tap-02-42082.html`), hệ thống tự động bóc tách số tập, gán cờ `is_current: True` và chọn mặc định đúng tập được yêu cầu thay vì quay về Tập 01.
   - **Đánh dấu nổi bật tập đang chọn trên danh sách chính (`static/js/main.js`, `static/css/styles.css`)**: Tô viền phát sáng cyan neon `.active-episode-row` và gắn badge `[▶ Đang chọn]` giúp người dùng nhận biết ngay vị trí tập phim.
   - **Phím tắt chuyển tập tiện lợi**:
     + `Shift + N` hoặc `PageDown`: Chuyển sang tập sau (Next Episode).
     + `Shift + P` hoặc `PageUp`: Quay lại tập trước (Previous Episode).
     + `]` / `[`: Chuyển tập kế tiếp / tập trước tức thì khi đang ở chế độ xem webview player.
     + Cập nhật bảng hướng dẫn phím tắt trực tiếp trong Shortcuts Help (`H` hoặc `?`).
   - **Tự động chuyển tập khi hết phim (Autoplay Next Episode)**: Bắt sự kiện kết thúc phát từ cả HTML5 video (`ended`) lẫn player JWPlayer (`complete` -> `__WV_ENDED__`) trong Electron webview để tự động nhảy sang tập kế tiếp nếu bật toggle Autoplay.
   - **Thông báo Toast trực quan**: Hiển thị toast thông báo mượt mà (`showPlayerToast`) mỗi khi chuyển tập.
   - **Chuẩn 100% SVG Vector**: Tuyệt đối không dùng emoji, icon fonts hay raster icons.

2. **Kiểm chứng xác thực (Verification)**:
   - Toàn bộ 50 unit tests trong Python test suite chạy qua thành công (`Ran 50 tests, OK`, Exit Code 0).
   - Kiểm tra cú pháp JavaScript `node -c static/js/main.js` đạt Exit Code 0 sạch lỗi.

## Summary of Accomplishments (Sprint v52 - Strict 100% Inline SVG Icons Standard)
1. **Triệt tiêu hoàn toàn emoji và chuẩn hóa 100% biểu tượng bằng vector SVG inline (`templates/index.html`, `static/css/styles.css`)**:
   - **Yêu cầu & Tiêu chuẩn**:
     - Tuân thủ quy định nghiêm ngặt: chỉ sử dụng định dạng SVG cho toàn bộ icon trong hệ thống, loại bỏ triệt để emoji và icon fonts.
   - **Xử lý triệt để**:
     - **Format Converter Studio (`templates/index.html`)**:
       + Thay thế toàn bộ 11 emoji tại các nút Quick Preset (`⚡`, `🎵`, `💎`, `🖼️`, `📸`, `🌐`, `🍏`, `🎞️`, `🌐`, `🎯`) bằng các thẻ `<svg>` inline chuyên nghiệp (Fast MP4, Audio MP3, Lossless FLAC, Clean PNG, Photo JPG, Modern WebP, Apple MOV, Cinema MKV, Web Animation, App Icon).
     - **Voice FX Studio (`templates/index.html`)**:
       + Thay thế toàn bộ 8 emoji hiệu ứng âm thanh (`🎙️`, `🔊`, `✨`, `🏛️`, `🎚️`, `📻`, `📞`, `🌊`) bằng các icon SVG chuẩn kỹ thuật phòng thu (Original, Bass Boost, Clarity, Reverb, Pitch, Radio/Lo-Fi, Tele/Old-School, 8D Audio).
     - **CSS Tuning (`static/css/styles.css`)**:
       + Thêm quy tắc định kiểu flexbox, căn giữa, kích thước chuẩn cho `.converter-preset-btn svg` (13x13px) và `.voice-icon svg` (18x18px) với hiệu ứng transition mượt mà khi hover.
     - **Kiểm chứng tự động**:
       + Chạy script rà soát Unicode emoji range trên toàn bộ mã nguồn `templates/index.html`, `static/js/main.js`, `static/css/styles.css`: Đạt 0 emoji (100% thuần SVG vector).

2. **Kiểm chứng xác thực (Verification)**:
   - Full test suite: 45/45 unit tests passed (Exit Code 0).
   - Node syntax check: `electron/main.js`, `electron/preload.js`, `static/js/main.js` sạch 0 lỗi.

## Summary of Accomplishments (Sprint v51 - Native Desktop Save File Dialog & Eliminate Browser Popup On Save)
1. **Khắc phục lỗi bấm Save bị mở trình duyệt ngoài và không hiện cửa sổ chọn thư mục lưu (`electron/main.js`, `electron/preload.js`, `static/js/main.js`, `routes/download.py`)**:
   - **Nguyên nhân gốc rễ**:
     - Nút Save trong Downloads Manager trước đây dùng thẻ `<a href="/api/download/file/${downloadId}" target="_blank">Save</a>`.
     - Trong Electron (`electron/main.js`), sự kiện `contents.setWindowOpenHandler` bắt mọi URL mở tab mới (`target="_blank"`) và chuyển tiếp qua `shell.openExternal(url)`, làm bật trình duyệt mặc định của hệ điều hành (Chrome/Edge) và tải file qua trình duyệt thay vì lưu trong app desktop.
     - Ứng dụng trước đây chưa trang bị IPC Native Save Dialog (`dialog.showSaveDialog`) cho người dùng tùy chọn thư mục và tên file lưu, cũng như thiếu endpoint sao chép tệp tin đã chuyển đổi trực tiếp trên ổ cứng.
   - **Xử lý triệt để**:
     - **Backend Direct Save (`routes/download.py`)**: Tạo endpoint `/api/download/save-to-disk` nhận `download_id` và `target_path`, sử dụng `shutil.copy2` sao chép file từ cache nội bộ sang đích đến người dùng chọn trong 1 phần nghìn giây. Bổ sung `filename` vào phản hồi `/api/download/status`.
     - **Electron Main & Preload (`electron/main.js`, `electron/preload.js`)**:
       + Bổ sung IPC handler `save-file`: gọi `dialog.showSaveDialog` mở hộp thoại chọn thư mục chuẩn Windows, prefill tên file tương ứng, và yêu cầu backend lưu trực tiếp.
       + Bổ sung IPC listener `show-item-in-folder`: gọi `shell.showItemInFolder(path)` mở đúng vị trí file trong Windows Explorer.
       + Trong `contents.setWindowOpenHandler`: Chặn triệt để các đường dẫn `/api/download/file/`, nghiêm cấm chuyển tiếp sang trình duyệt bên ngoài.
     - **Giao diện Downloads Manager (`static/js/main.js`)**:
       + Đổi nút Save từ thẻ `<a>` sang `<button>` gọi `handleSaveTaskFile`.
       + Khi tác vụ hoàn tất: Trong môi trường Electron desktop, tự động gọi `handleSaveTaskFile` hiển thị cửa sổ Save File Dialog ngay lập tức để người dùng chọn vị trí lưu.
       + Sau khi lưu thành công: Nút chuyển sang `Folder` (bấm mở ngay thư mục chứa file trong Explorer).
       + Giữ fallback sạch cho môi trường web thông thường bằng thẻ `<a download>` không mở tab mới.

2. **Kiểm chứng xác thực (Verification)**:
   - Toàn bộ test suite: 45/45 tests passed (Exit Code 0).
   - Kiểm tra cú pháp JavaScript & Electron: `node -c` Exit Code 0.

## Summary of Accomplishments (Sprint v50 - Fix Image-to-Video Infinite FFmpeg Loop & Freeze at 99%)
1. **Khắc phục lỗi treo vô hạn và đứng hình ở 99% khi convert ảnh (JPG/PNG) sang Video (MOV/MP4/MKV) (`tasks/convert.py`)**:
   - **Nguyên nhân gốc rễ**:
     - Trước Sprint v49, backend chưa nhận diện `image_stream` nên coi ảnh là file không có video và không có audio. Nó nhảy vào nhánh ghép video canvas nền `ffmpeg -f lavfi -i color=c=0x0f172a... -i YEU_CAU.jpg -shortest`. Vì luồng `color` là vô hạn và ảnh không có track audio để `-shortest` ngắt, FFmpeg chạy vòng lặp vô hạn (tiến trình cũ PID 48132 đã ngốn 11.835s CPU và sinh file 35MB liên tục phình to mà không dừng).
     - Phép tính tiến độ: `total_duration` của ảnh nguồn chỉ là `0.04s`. Khi FFmpeg vừa sinh frame đầu tiên (0.04s), phép tính `(0.04 / 0.04) * 100` đã đạt 100% và bị chặn ở `min(99%)`, làm giao diện lập tức nhảy lên 99% và đứng im suốt thời gian xử lý.
   - **Xử lý triệt để**:
     - Buộc dừng (kill) tiến trình FFmpeg chạy ngầm bị treo (PID 48132) và xóa file `.mov` rác chưa hoàn chỉnh.
     - Cập nhật `tasks/convert.py`: Khi nguồn là ảnh tĩnh và đích là video (`is_source_image and is_video_target`), thiết lập chính xác `total_duration = 5.0` tương ứng cờ `-loop 1 -t 5` giúp thanh tiến độ tăng dần đều đặn.
     - Tự động bổ sung bộ lọc chia hết cho 2 `scale=trunc(iw/2)*2:trunc(ih/2)*2` khi giữ nguyên kích thước ảnh gốc, tránh lỗi encoder `libx264` với ảnh có kích thước lẻ.
     - Thêm preset tốc độ cao `-preset veryfast` khi encode ảnh sang video cho MP4, MOV, MKV và `-deadline realtime` cho WebM.
     - Benchmark thực tế: Chuyển đổi `YEU_CAU.jpg` (2K) sang `MOV` hoàn thành xuất sắc trong **1.53 giây** (file 123 KB, video 5s chuẩn H.264).

## Summary of Accomplishments (Sprint v49 - Format Converter Image Preview & Image Transcoding Studio)
1. **Khắc phục lỗi không xem trước được ảnh trong Format Converter (`static/js/main.js`, `templates/index.html`, `static/css/styles.css`, `routes/convert.py`)**:
   - **Nguyên nhân gốc rễ**:
     - Trong `static/js/main.js`: `setupPreviewPlayer` trước đây chỉ kiểm tra `isVideoExt` và `isAudioExt`. Mọi file khác (như ảnh `.jpg`, `.png`, `.webp`, `.bmp`) đều rơi vào nhánh `else { videoPlayer.src = mediaSrc; }`, gán URL ảnh vào thẻ HTML5 `<video>`, dẫn đến việc video player không thể render và hiển thị hộp đen không phát được (như trên ảnh chụp màn hình).
     - Trong `routes/convert.py`: Endpoint `/api/convert/preview-stream` trước đây thiếu mapping MIME types cho định dạng ảnh, trả về `application/octet-stream` thay vì `image/jpeg`, `image/png`, v.v.
     - Trong `tasks/convert.py`: Hàm `probe_media_file` lọc bỏ `png`, `jpg`, `jpeg`, `bmp`, `tiff` khỏi `video_stream`, nhưng không nhận diện `image_stream`, dẫn đến ảnh bị coi là file không có cả video lẫn audio, kích hoạt nhánh ghép canvas đen 0 giây và báo lỗi.
   - **Xử lý triệt để**:
     - **Frontend DOM (`templates/index.html`, `static/css/styles.css`)**: Bổ sung `#converter-image-wrapper` và thẻ `<img>` (`#converter-image-preview`) responsive với hiệu ứng đổ bóng và bo góc hiện đại. Thêm nhóm định dạng ảnh (PNG, JPG, WebP, ICO, BMP, TIFF) và 4 nút Quick Preset cho ảnh (Clean PNG, JPEG Photo, WebP Modern, App Icon).
     - **Player Engine (`static/js/main.js`)**: Cập nhật `setupPreviewPlayer` và `resetConverterUI`: khi phát hiện file ảnh (`isImageExt`), lập tức ẩn video/audio player, hiển thị `#converter-image-wrapper`, gán `imagePreview.src = mediaSrc`, đổi huy hiệu thời lượng thành `"Image Preview"`, đổi icon tệp tin sang icon ảnh, và tự động ẩn thanh công cụ cắt ghép thời gian (Trimming) vì ảnh tĩnh không có timeline.
     - **Backend Streaming (`routes/convert.py`)**: Bổ sung đầy đủ MIME types cho ảnh (`jpg`, `jpeg`, `png`, `webp`, `bmp`, `ico`, `tiff`, `svg`, `avif`).
     - **Transcoder Engine (`tasks/convert.py`)**: Nhận diện `is_image: True`, trích xuất độ phân giải ảnh, hỗ trợ chuyển đổi giữa các định dạng ảnh (JPG -> PNG, PNG -> WebP, PNG -> ICO 256x256, BMP, TIFF), chuyển ảnh tĩnh thành video 5s lặp (`-loop 1 -t 5`), hoặc chuyển video/GIF sang WebP hoạt ảnh.

2. **Kiểm chứng xác thực (Verification)**:
   - Full test suite: 45/45 unit tests passed (Exit Code 0).
   - AST & cú pháp JavaScript sạch 0 lỗi.

## Summary of Accomplishments (Sprint v48 - Fix Undefined Name 'exe' in Builder CLI)
1. **Khắc phục lỗi phân tích tĩnh / Language Server báo lỗi biến `exe` (`build_tool/builder_cli.py`)**:
   - **Nguyên nhân**: Dòng 109 viết f-string dạng `{exe if "exe" in locals() else prebuilt_exe}`. Dù có mệnh đề điều kiện, trình phân tích cú pháp tĩnh (Pyright / Pylance / IDE) vẫn phân tích node `exe` dưới dạng `ast.Load` và báo lỗi: `Could not find name 'exe'. Did you mean 'exec'?`.
   - **Xử lý**: Đổi thành `{prebuilt_exe}` vì biến đã được gán trực tiếp từ `prebuilt_exe = packager.build_web_exe(progress_cb=info)` ở dòng ngay trước đó.
   - **Kiểm chứng**: AST scan 0 lỗi, `builder_cli.py --help` chạy hoàn hảo (Exit Code 0).

## Summary of Accomplishments (Sprint v47 - Fix Native Windows Scrollbars, FFmpeg Pipe Deadlock & Zero-Audio Conversion Engine)
1. **Khắc phục lỗi thanh cuộn mặc định Windows không áp dụng Custom CSS (`static/css/styles.css`)**:
   - **Nguyên nhân gốc rễ**: 
     - Trên trình duyệt Chromium (Windows), khi khai báo `scrollbar-width: thin;` trên `.converter-presets-bar` mà không khai báo `scrollbar-color`, Chromium ưu tiên cơ chế dựng native của Windows OS và bỏ qua các quy tắc `::-webkit-scrollbar`, dẫn đến việc xuất hiện thanh trượt cuộn màu xám nhạt mặc định xấu xí của Windows.
     - `.preset-buttons-wrap` đặt `flex-wrap: nowrap;` làm các nút preset bị tràn bề ngang trên màn hình thường.
   - **Xử lý triệt để**:
     - Bổ sung quy tắc CSS chuẩn `*` và `html, body`: `scrollbar-width: thin; scrollbar-color: rgba(99, 179, 237, 0.4) transparent;` để toàn bộ ứng dụng và mọi phần tử trên Windows đều dùng thanh cuộn tím/cyan hiện đại.
     - Trong `.converter-presets-bar`: Bổ sung `scrollbar-color: rgba(6, 182, 212, 0.4) transparent;` cùng bộ định kiểu `::-webkit-scrollbar` đồng bộ tông cyan neon.
     - Đổi `.preset-buttons-wrap` thành `flex-wrap: wrap; gap: 8px;` giúp 7 nút preset tự động xuống dòng gọn gàng, loại bỏ hoàn toàn việc cuộn ngang không cần thiết.

2. **Khắc phục lỗi chuyển đổi file (Conversion Failed / Blank Stderr / Silent Videos) (`tasks/convert.py`)**:
   - **Nguyên nhân gốc rễ**:
     - Trong `tasks/convert.py`: `subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)` dẫn đến pipe deadlock trên Windows vì `stdout` không có luồng tiêu thụ.
     - Vòng lặp `while True: line = process.stderr.readline()` đọc đến EOF. Khi tiến trình gặp lỗi (returncode != 0), lệnh `process.stderr.read()` phía sau luôn trả về chuỗi rỗng `""`, làm mất sạch thông điệp báo lỗi từ FFmpeg.
     - Khi chuyển đổi tệp không có âm thanh (silent video như `DEMO.mp4`) sang định dạng âm thanh (MP3, FLAC...), FFmpeg báo lỗi `Output file does not contain any stream` và thoát với mã 1.
     - Khi chuyển đổi silent video sang video container (MP4, MKV, MOV...), backend vẫn truyền `-c:a aac -b:a 320k` và các bộ lọc audio dù không có track audio.
   - **Xử lý triệt để**:
     - Đổi `stdout=subprocess.DEVNULL`.
     - Tích lũy bộ đệm trượt 40 dòng cuối cùng của stderr (`stderr_tail`) trong quá trình đọc, giữ trọn vẹn thông báo lỗi chi tiết khi FFmpeg gặp sự cố.
     - Kiểm tra thẩm định `if is_audio_target and not has_audio`: Báo lỗi rõ ràng ngay lập tức `Tập tin nguồn không chứa luồng âm thanh để chuyển đổi sang định dạng âm thanh.`
     - Đối với video không có âm thanh chuyển sang định dạng video container: Tự động gán `-an` và không thêm bất kỳ cờ mã hóa âm thanh nào.

3. **Khắc phục che giấu thông báo lỗi & Reset giao diện đột ngột trong UI (`static/js/main.js`)**:
   - Trong `handleDownloadFailure`: Khi tác vụ là `convert-*`, hiển thị nguyên văn lỗi chuyển đổi thực tế thay vì ghi đè bằng câu generic `"Download failed. Please check your connection or view technical details below."`.
   - Trong `initFormatConverter`:
     - Nhận diện `probe.has_audio === false` để làm mờ (dim) và cảnh báo người dùng khi chọn các preset âm thanh (Best MP3, Lossless FLAC).
     - Bỏ lệnh `resetConverterUI()` tự động ngay khi bấm bắt đầu chuyển đổi, giữ nguyên thẻ tệp tin và mở Downloads Manager để người dùng quan sát tiến độ mà không bị chuyển đột ngột về màn hình chào.

4. **Kiểm chứng xác thực (Verification)**:
   - Standalone Python test 4 kịch bản:
     + Silent video -> MP3: Báo lỗi chính xác không có luồng audio (Exit clean).
     + Silent video -> MP4: Hoàn thành 100% với `-an`.
     + Video có audio -> MP3: Hoàn thành 100%.
     + Video có audio -> MP4 Universal: Hoàn thành 100%.
   - Full test suite: Exit Code 0.

## Summary of Accomplishments (Sprint v46 - Comprehensive Format Converter Studio Revamp & Requirements Audit)
0. **Rà soát & Hoàn thiện `requirements.txt` và cài đặt vào venv nội bộ (`requirements.txt`)**:
   - Rà soát toàn bộ AST import trong codebase: Bổ sung các package thiết yếu bị thiếu gồm `pillow>=11.1.0` (xử lý ảnh/thumbnail), `mutagen>=1.47.0` (gắn metadata âm thanh yt-dlp), `pycryptodomex>=3.20.0` (giải mã AES HLS stream), `brotli>=1.1.0` (nén HTTP), `websockets>=13.0` (streaming TTS), `aiohttp>=3.9.0`.
   - Cài đặt thành công toàn bộ dependencies vào môi trường venv nội bộ (`.\venv\Scripts\python.exe -m pip install -r requirements.txt`).
   - Chạy lại test suite: 45/45 tests passed (Exit Code 0).

1. **Khắc phục lỗi bảo mật nghiêm trọng xóa nhầm tệp tin gốc của người dùng (`tasks/convert.py`)**:
   - **Nguyên nhân gốc rễ**: Trước đây trong khối `finally` của `tasks/convert.py`, hàm luôn gọi `os.remove(file_path)` mà không kiểm tra vị trí file. Nếu người dùng chọn file từ ổ đĩa (ví dụ `D:\Videos\my_file.mp4`), tệp tin gốc của họ sẽ bị xóa vĩnh viễn sau khi chuyển đổi!
   - **Xử lý triệt để**: Bổ sung rào chắn an toàn kép: chỉ xóa tệp tin tạm nằm trong thư mục `TEMP_DOWNLOAD_DIR/uploads` (`if abs_fp.startswith(abs_up): os.remove(...)`). Tuyệt đối không xóa bất kỳ tệp tin nào bên ngoài thư mục upload tạm của máy chủ.

2. **Chế độ Zero-Copy trực tiếp trên Electron (`file.path` / `window.electronAPI.selectFile()`)**:
   - Tận dụng `file.path` trong Electron để đọc trực tiếp từ ổ đĩa, loại bỏ 100% thời gian upload HTTP localhost cho các video dung lượng lớn (10GB+ chuyển đổi tức thì không cần chờ tải lên).
   - Thêm nút "Choose Local File" gọi native OS file dialog thông qua `window.electronAPI.selectFile()`.

3. **Bổ sung Media Probe & Trích xuất thông tin luồng phát (`/api/convert/probe`)**:
   - Sử dụng `ffprobe` trích xuất chính xác: Thời lượng (Duration), Độ phân giải (Resolution e.g. 1080p, 4K), Codec video, Codec âm thanh & số kênh (e.g. AAC 2ch, FLAC), Bitrate.
   - Hiển thị hệ thống huy hiệu (badges) trực quan ngay trên thẻ tệp tin đã chọn.

4. **Hỗ trợ đầy đủ 13+ định dạng & Kỹ thuật Fast Remux (Stream Copy)**:
   - Video: `MP4`, `MKV`, `WebM`, `MOV`, `AVI`, `TS`.
   - Âm thanh: `MP3`, `WAV`, `FLAC`, `M4A`, `OGG`, `OPUS`.
   - Hoạt ảnh: `GIF`, `WebP`.
   - Chế độ Fast Remux (`-c copy`) cho phép đổi container trong nháy mắt với 0% suy hao chất lượng và tốc độ tối đa.
   - Tối ưu bộ giải thuật tạo ảnh GIF chất lượng cao 1 pass: `split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3`.

5. **Thanh 1-Click Quick Presets & Bộ điều khiển cắt gọt (Trimming) đồng bộ Player**:
   - 7 cấu hình nhanh 1-chạm: Universal MP4, Fast Remux (Copy), Best MP3 (320k), Lossless FLAC, Apple MOV, Animated GIF, Animated WebP.
   - Trimming controls: Lấy timestamp hiện tại trực tiếp từ Video/Audio Player điền vào điểm bắt đầu (Start) và điểm kết thúc (End) chỉ với 1 click.
   - Cung cấp endpoint `/api/convert/preview-stream` hỗ trợ HTTP Range để Player xem trước tua mượt mà không độ trễ.
   - Cập nhật huy hiệu tóm tắt cấu hình thời gian thực (e.g. `MP4 • H264 • 1080p • 320k`).

6. **Giải quyết triệt để lỗi giao diện bảng điều khiển Downloads Manager che khuất Format Converter**:
   - Bổ sung `margin-bottom: 95px` cho `.converter-container` trong `static/css/styles.css`, đảm bảo bảng nổi Downloads Manager không bao giờ che khuất các nút bấm hoặc thẻ tính năng.

7. **Kiểm thử chất lượng tự động (Verification)**:
   - Viết mới `tests/test_converter_studio.py` kiểm chứng: Probe endpoint, Preview streaming, Task enqueuing, và bài test rào chắn bảo vệ file gốc người dùng.
   - Toàn bộ test suite chạy thành công: 45/45 tests passed, Exit Code 0. Node syntax check `main.js`: Exit Code 0.
   - **Nguyên nhân gốc rễ**: 
     - Môi trường Python toàn cục (`C:\enviroment_dev\PYTHON\Python312`) cài bản `yt-dlp` cũ (2026.06.09) thiếu bản vá trích xuất TikTok, dẫn đến lỗi `Unexpected response from webpage request`.
     - Trong `routes/info.py`, danh sách `tiktok_auth_keywords` bắt cả các từ khóa chung chung như `"unexpected response"`, `"unable to extract"`, `"not available"`. Bất kỳ lỗi nào của yt-dlp đều bị quy chụp thành lỗi tài khoản/captcha, và luôn hiển thị thông báo "This TikTok Video or Slideshow requires account cookies...".
     - Kể cả khi người dùng đã tải lên file cookie hợp lệ (`www.tiktok.com_04-10-2026.json`), thông báo lỗi vẫn tiếp tục lặp lại yêu cầu tải lên cookie.
   - **Xử lý triệt để**:
     - Nâng cấp `yt-dlp` toàn cục lên `2026.8.19` và cài đặt `yt-dlp-ejs` (0.8.0).
     - Trong `routes/info.py`: Loại bỏ các từ khóa extractor lỗi thời (`unexpected response`, `unable to extract`, `not available`) khỏi `tiktok_auth_keywords`.
     - Bổ sung kiểm tra `get_cookie_file_path(client_id)`: Nếu client đã tải lên cookie mà vẫn gặp captcha/chặn IP thì hiển thị thông báo chính xác hướng dẫn mở trình duyệt vượt Captcha rồi xuất lại, tránh gây hoang mang.
     - Trong `app.py`: Tự động tiêm đường dẫn `venv/Lib/site-packages` lên đầu `sys.path` để luôn ưu tiên thư viện của venv cục bộ.
     - Trong `electron/main.js`: Bổ sung thiết lập `VIRTUAL_ENV` và gắn `venv/Scripts` vào đầu `PATH` khi khởi động Flask server ở chế độ dev.
   - **Kiểm chứng**:
     - Standalone assertion test với link TikTok người dùng cung cấp và cookie client: HTTP 200, trích xuất thành công 3 định dạng video (1080p, 720p, 576p) và 2 slide ảnh.
     - Test suite `.\venv\Scripts\python.exe -m unittest discover tests`: 39/39 tests passed, Exit Code 0.
1. **Triệt tiêu 100% Popup quảng cáo cờ bạc BOM88 & các nút bấm khi bấm dừng video (Pause)**:
   - **Nguyên nhân gốc rễ**: Trình phát CDN (`storage.googleapiscdn.com`) gửi request AJAX ngầm tới `https://storage.googleapiscdn.com/admin/api/ads/active`. Endpoint này trả về cấu hình `{ "pauseAd": { "image": "...", "link": "..." } }`. Khi nhận được cấu hình này, script trình phát khởi tạo listener trên sự kiện `pause` của JWPlayer và tự động chèn phần tử DOM `<div id="avs-pause-ad">` (chứa hình ảnh BOM88, nhãn "Quảng cáo" và 2 nút "Đóng quảng cáo" / "Đóng và xem tiếp").
   - **Xử lý tận gốc (Root Cause Solution)**:
     - **Cấp Network (Electron Native)**: Kích hoạt `session.defaultSession.webRequest.onBeforeRequest` ngay khi `app.whenReady()`. Tự động can thiệp và chuyển hướng mọi request tới `admin/api/ads/active` sang Data URI `data:application/json;charset=utf-8,{"pauseAd":null,"ads":[]}`. Đồng thời hủy (`cancel: true`) mọi request tải ảnh/script liên quan đến BOM88, doubleclick, googlesyndication.
     - **Cấp Webview DOM & Script**: Tiêm hook ghi đè `XMLHttpRequest` và `fetch` trả về `{ "pauseAd": null, "ads": [] }`. Mở rộng `MutationObserver` dọn sạch bất kỳ DOM nào liên quan đến `.avs-pause-ad-box`, `[id*="pause-ad"]`, `.avs-resume-box`.
     - **Cấp Backend Fallback (`routes/build.py`)**: Bổ sung endpoint `/admin/api/ads/active` và `/ads/active` trả về `{ "pauseAd": None, "ads": [] }` cho môi trường browser/iframe.
     - **Kiểm chứng thực tế (`scratch/test_net_block_ad.js`)**: Xác minh trên Electron thật: `padExists: false`, `bom88InBody: false`, `quangCaoInBody: false`. Hoàn toàn không còn bất kỳ thành phần quảng cáo BOM88 hay nút thừa nào khi Pause.

2. **Khắc phục triệt để hiện tượng Preview lần đầu bị tối đen màn hình (phải tắt đi bấm lại mới xem được)**:
   - **Nguyên nhân gốc rễ**:
     - Lệch pha `Referer`: Token phát video của CDN yêu cầu đúng Referer từ domain nguồn (`animevietsub.love`, `.tv`...). Khi vừa analyze xong, `activeStreamReferer` trong Electron main process chưa kịp nhận diện. Khi bấm Preview lần đầu, webview gửi request tới CDN với Referer mặc định cũ -> CDN trả 403 Forbidden -> Màn hình tối đen. Đến lần Preview thứ hai, IPC `setStreamReferer` đã ghi nhận nên mới xem được.
     - Chromium Layout Race: `<webview>` ban đầu ở trạng thái `display: none` (`class="hidden"`). Khi vừa bỏ `hidden` mà gán `.src` ngay lập tức, WebContents chưa kịp gắn kết layout khiến Chromium phát sinh `ERR_ABORTED (-3)`.
   - **Xử lý triệt để**:
     - Trong `static/js/main.js`: Gọi `window.electronAPI.setStreamReferer()` ngay khi `displayMetadata` vừa phân tích xong, đi trước thời điểm người dùng click Preview.
     - Bổ sung thuộc tính `data-referer` vào tất cả nút `.btn-preview` và truyền trực tiếp vào `triggerPreview`.
     - Trong `electron/main.js`: Bổ sung cơ chế tự động trích xuất Referer từ request headers của CDN.
     - Thêm tick 30ms trước khi gán `previewWebpageWebview.src = streamUrl` để Chromium gắn kết WebContents hoàn chỉnh.

3. **Phản hồi tức thì biểu tượng Pause SVG phần mềm (0ms latency)**:
   - Trong webview player script: Khi JWPlayer kích hoạt `pause` hoặc `play`, phát tín hiệu tức thì qua `console.log('__WV_PAUSED__')` và `console.log('__WV_PLAYING__')`.
   - Trong `main.js`: Host lắng nghe sự kiện `console-message` của `<webview>`. Ngay khi video tạm dừng, biểu tượng `#preview-webpage-pause-indicator` (vòng tròn mờ có SVG pause `||` ở giữa) hiển thị ngay lập tức; khi tiếp tục phát, biểu tượng tự động biến mất.

4. **Quản lý vòng đời tiến trình Dev & Ngăn ngừa đụng độ Single Instance**:
   - Trong `electron/main.js`: Khi chạy ở chế độ dev (`isDev`), sự kiện `mainWindow.on('close')` sẽ thoát ứng dụng hoàn toàn (`app.quit()`) thay vì ẩn ngầm vào khay hệ thống (tránh việc cửa sổ cũ ẩn ngầm chặn instance mới).
   - Trong `run_desktop.bat`: Tự động dọn dẹp các tiến trình `electron.exe` mồ côi (`taskkill /f /im electron.exe`) trước khi khởi chạy dev server.

## Last Updated
- Timestamp: 2026-10-04 18:46:00
- Exit Code: 0 (Python unit tests running/passing, Node syntax checks passed, Electron Webview tests passed 100%)

## Summary of Accomplishments (Sprint v43 - Fix First Preview Black Screen, Eradicate BOM88 Pause Overlay & Software Pause SVG Indicator)
1. **Khắc phục triệt để lỗi Preview lần đầu sau Analyze bị tối đen màn hình (`static/js/main.js`)**:
   - **Nguyên nhân gốc rễ**: Khi bấm Xem trước, `triggerPreview` gọi `stopAllPreviewPlaybacks()` điều hướng webview về `about:blank`. Ngay lập tức trong cùng event tick, mã nguồn gán `previewWebpageWebview.src = streamUrl`. Hai lệnh điều hướng đụng độ khiến Chromium hủy request bằng mã `ERR_ABORTED (-3)`. Đồng thời `dom-ready` kích hoạt trước trên trang `about:blank` khiến event listener tự gỡ bỏ trước khi trang video thật kịp nạp.
   - **Xử lý triệt để**:
     - Thêm tham số `isClosingModal = false` vào `stopAllPreviewPlaybacks`. Chỉ điều hướng về `about:blank` khi người dùng bấm nút đóng modal Preview (`closePreviewModal()`).
     - Trong `triggerPreview`, gắn listener `dom-ready` trước khi gán `src` và kiểm tra bỏ qua nếu URL là `about:blank`.
     - Nếu `src === streamUrl`, gọi `loadURL(streamUrl)` cưỡng chế reload thay vì gán `.src` khiến Chromium bỏ qua.
     - Hợp nhất cấu hình `onBeforeSendHeaders` trong `electron/main.js` cấp header `Referer` động cho toàn bộ tài nguyên `googleapiscdn.com`.

2. **Triệt tiêu 100% Popup quảng cáo cá cược BOM88 khi Pause bằng hệ thống phòng thủ 4 lớp (`electron/main.js`, `static/js/main.js`, `routes/build.py`)**:
   - **Nguyên nhân**: Khi JWPlayer phát sự kiện `pause`, script website nhúng DOM `#avs-pause-ad` (chứa banner BOM88, nhãn "Quảng cáo" và 2 nút "Đóng quảng cáo" / "Đóng và xem tiếp").
   - **Xử lý 4 lớp triệt để**:
     - **Lớp 1 (Electron Native Main Process)**: Trong `electron/main.js` sự kiện `app.on('web-contents-created')`, tự động tiêm CSS ẩn `#avs-pause-ad, #avs-resume-overlay` (`display: none !important`) và script xóa DOM trực tiếp trên cả 2 hook `dom-ready` và `did-finish-load` của mọi webview.
     - **Lớp 2 (Player Pause Event Hook)**: Trong webview, hook sự kiện `p.on('pause')` của JWPlayer; ngay khi vừa phát lệnh pause, tự động xóa sạch `#avs-pause-ad` trong vòng 10ms.
     - **Lớp 3 (Continuous Polling Scrub)**: Trong vòng lặp polling 500ms và phím tắt Space/K tại `static/js/main.js`, liên tục kiểm tra và gọi `document.getElementById('avs-pause-ad')?.remove()`.
     - **Lớp 4 (Proxy Style Fallback)**: Bổ sung bộ chọn ẩn `#avs-pause-ad` vào `routes/build.py` cho chế độ nhúng iframe.

3. **Hiển thị biểu tượng SVG Pause phần mềm trực quan (`templates/index.html` & `static/js/main.js`)**:
   - Bổ sung `#preview-webpage-pause-indicator` chứa SVG Pause chính thức của EveryThingDownloader nổi bật giữa khung hình khi video tạm dừng.
   - Khi video phát (`playing`): Tự động ẩn biểu tượng.
   - Khi video dừng (`paused`): Tự động hiện biểu tượng và cập nhật trạng thái `[PAUSED]` trên thanh thông tin.
   - Cho phép click trực tiếp vào biểu tượng hoặc bấm phím `Space`/`K` để tiếp tục phát video nhanh chóng.


## Summary of Accomplishments (Sprint v41 - Fix Preview Modal Sound Leak on Close & Pause Ad Auto-Resume)
1. **Triệt tiêu 100% tiếng ồn / rò rỉ âm thanh khi đóng Preview Modal (`stopAllPreviewPlaybacks` trong `static/js/main.js`)**:
   - **Nguyên nhân gốc rễ**: Khi người dùng nhấn nút đóng modal Preview (`#close-preview-modal`), mã nguồn trước đó chỉ thêm class `hidden` và xóa timer. Trong Electron, `<webview>` vẫn giữ guest WebContents và Chromium audio decoder trong RAM, khiến video tiếp tục giải mã và âm thanh phát ngầm liên tục.
   - **Xử lý triệt để**:
     - Inject lệnh dừng khẩn cấp vào webview: `jwplayer('player')?.stop(); jwplayer('player')?.pause();` và duyệt toàn bộ thẻ `<video>`, `<audio>` để gọi `v.pause(); v.muted = true; v.removeAttribute('src'); v.load();`.
     - Điều hướng WebContents về `loadURL("about:blank")` (hoặc `src = "about:blank"`), giải phóng hoàn toàn media decoder và cắt đứt tức thì luồng âm thanh.

2. **Triệt tiêu lỗi không thể tạm dừng video / Popup quảng cáo chớp tắt tự phát lại (`triggerPreview` trong `static/js/main.js`)**:
   - **Nguyên nhân gốc rễ**:
     - Trong vòng lặp polling 500ms `window._previewWebviewPollTimer`, đoạn mã cũ có câu lệnh `if (v.paused && jwState !== 'playing') v.play().catch(()=>{});`. Do đó mỗi khi người dùng bấm Pause, polling loop lập tức cưỡng bức gọi `play()`.
     - Đồng thời, khi JWPlayer kích hoạt sự kiện `pause`, script website nhúng hộp thoại quảng cáo có 2 nút ("Đóng quảng cáo" / "Đóng và xem tiếp"). Khi kết hợp với lệnh ép play, hộp thoại này chỉ chớp lên trong tích tắc rồi biến mất và video tiếp tục phát.
   - **Xử lý triệt để**:
     - Xóa bỏ hoàn toàn câu lệnh cưỡng bức `v.play()` trong polling loop.
     - Mở rộng CSS tiêm vào webview để ẩn toàn diện các class/id quảng cáo khi dừng: `.pause-ad, #pause-ad, .pause-banner, [class*="pause-ad"], [id*="pause-ad"], [class*="pause_ad"], [id*="pause_ad"], [class*="pause-adv"], [id*="pause-adv"], .avs-pause-ad, #avs-pause-ad, .jw-pause-ad`.
     - Tích hợp `MutationObserver` bên trong webview tự động xóa sổ ngay lập tức bất kỳ phần tử DOM nào chứa nội dung "Quảng cáo", "Đóng quảng cáo" hoặc "Đóng và xem tiếp" ngay khi chúng vừa chớm xuất hiện.
     - Kết quả: Bấm Pause video đứng hình chuẩn xác 100%, không hiện quảng cáo, không bị tự động phát lại. Bấm Play video phát tiếp bình thường.

## Summary of Accomplishments (Sprint v40 - Electron Native Webview Preview, Zero Ads/F12 Bypass, Auto Download Catch & Dynamic Sizing)
1. **Khắc phục triệt để lỗi Preview bị đệm mãi (100% Red Spinner), cản trở bởi quảng cáo và cảnh báo DevTools/F12**:
   - Chuyển đổi cơ chế hiển thị Preview từ `iframe` truyền thống sang `<webview id="preview-webpage-webview">` độc lập của Electron.
   - `<webview>` là một guest WebContents độc lập (`window.top === window`), loại bỏ xung đột chống nhúng (anti-embed checks) trong các script player (`avs-loader.js`).
   - Tự động inject CSS triệt tiêu 100% tất cả các lớp quảng cáo, banner cờ bạc/BOM88, hộp cảnh báo DevTools/F12 (`#avs-compat-fallback`, `.browser-warning`, `.avs-ads`, `.jw-ad-container`).
   - Tự động hook `SourceBuffer.prototype.appendBuffer` và kích hoạt JWPlayer phát ngay lập tức.
   - Thử nghiệm thực tế: Video bắt đầu phát mượt mà sau 2-3 giây (`jwState: "playing"`), hiển thị hình ảnh & âm thanh rõ ràng, không có bất kỳ banner cản trở nào.

2. **Dung lượng ước tính động & cập nhật thời gian thực**:
   - Thay thế việc hardcode `~350 MB (HD Stream)` bằng cơ chế tính toán động theo thời lượng thực tế của video: `duration * 275000 bytes` (ví dụ: tập 23:40 ước tính chính xác `~390.5 MB`).
   - Trong quá trình phát Preview, polling liên tục cập nhật thanh thông tin Preview: `Type: STREAM PLAYER | 00:05 / 23:40 (~390.5 MB) | Đệm: 2.8 MB`.

3. **Khắc phục triệt để lỗi nhấn GET / Preview tự động bật trình duyệt ngoài (Google Chrome)**:
   - **Nguyên nhân gốc rễ**: Trong `electron/main.js`, sự kiện `app.on('web-contents-created')` áp dụng chung cho cả `webview`. Hàm `contents.on('will-navigate')` phát hiện URL không phải localhost nên đã gọi `event.preventDefault()` và `shell.openExternal(url)` mở Chrome, đồng thời `setWindowOpenHandler` bắt các popup của player và cũng chuyển sang Chrome. Hậu quả là Chrome bị bật lên chiếm nửa màn hình còn webview trong app bị chặn load.
   - **Xử lý triệt để**:
     - Phân tách rõ ràng: Kiểm tra `contents.getType() === 'webview'`.
     - Với guest webview: Tuyệt đối chặn toàn bộ popup ngoài (`return { action: 'deny' }`), cho phép webview tự do điều hướng đến URL stream CDN nội bộ mà không gọi `shell.openExternal`.
     - Xóa bỏ cờ `allowpopups` trên cả `<webview id="preview-webpage-webview">` trong `templates/index.html` và `bgView` trong `static/js/main.js`.
     - Tự động click bỏ qua hộp thoại xác nhận phát tiếp ("Xem tiếp" / "Từ đầu") trong luồng thu ngầm của GET button.

4. **Khắc phục triệt để lỗi nhấn Tải về (GET) bị treo ở 0% ("Khởi chạy bộ thu luồng video...")**:
   - **Nguyên nhân**: `<webview>` ngầm trước đó bị đặt kích thước 1x1px ở vị trí -9999px (bị Chromium đóng băng layout và rendering) và thiếu vòng lặp polling kiểm tra tiến độ, đồng thời thiếu listener bắt sự kiện tải xuống từ webview.
   - **Xử lý triệt để**:
     - Trong `electron/main.js`: Bổ sung `session.defaultSession.on('will-download')` tự động lưu các file tải về từ Blob URL hoặc webview trực tiếp vào thư mục `downloads/` với tên file chuẩn xác mà không bị chặn hay chờ tương tác người dùng.
     - Trong `static/js/main.js`:
       - Cấu hình kích thước layout chuẩn `1280x720` cho `<webview>` thu ngầm (`bgView`) với `opacity: 0.001; z-index: -9999`.
       - Inject CSS xóa sạch quảng cáo và script ép tua `playbackRate = 16.0` cùng `muted = true`.
       - Xây dựng vòng lặp polling 800ms cập nhật tiến độ liên tục: % đệm, dung lượng MB thu thập được, thời gian đã tua, hiển thị thông báo thời gian thực trên thẻ Downloads Manager.
       - Tự động hoàn tất và xuất file `.mp4` khi video phát đến cuối (`stats.ended || stats.pos >= stats.dur - 3`).
       - Bổ sung kiểm tra `isStreamOption` trong cả bảng ungrouped và folder options để nút GET luôn kích hoạt đúng trình thu luồng.

5. **Kiểm thử & Xác minh**:
   - `node -c static/js/main.js electron/main.js`: Exit Code 0.
   - `electron.cmd scratch/test_webview_integration.js`: PASS 100% (Phát mượt, thu được 8 chunks 2.82 MB sau 3s, 0 popup trình duyệt ngoài).
   - `unittest discover tests`: PASS 39/39 (Exit Code 0).

## Summary of Accomplishments (Sprint v39 - Fix 403 Forbidden on CDN Playlist, Dynamic Multi-Domain Stream Referer & MSE Capture Acceleration)
1. **Khắc phục triệt để lỗi HTTP 403 Forbidden trên Google CDN Playlist (`storage.googleapiscdn.com/playlist/...`)**:
   - **Nguyên nhân gốc rễ**: Token phát video của Google CDN yêu cầu header `Referer` phải trùng khớp chính xác với tên miền gốc đã phát hành token (ví dụ: `https://animevietsub.nl/`). Trước đây `electron/main.js` và `routes/build.py` bị hardcode cứng `https://animevietsub.love/` và đồng thời chặn script `avs-shield.min.js`. Khi truy cập `animevietsub.nl` (hoặc các mirror `.tv`, `.meme`), Google CDN phát hiện sai lệch Referer và từ chối cấp playlist với mã 403 Forbidden. JWPlayer không nạp được luồng nên báo lỗi `232403` và hiển thị poster tĩnh (poster Anya có nội dung về quảng cáo).
   - **Xử lý triệt để**:
     - Trong `electron/preload.js`: Bổ sung API `setStreamReferer(referer)`.
     - Trong `electron/main.js`:
       - Xóa bỏ hoàn toàn bộ chặn `onBeforeRequest` trên `*avs-shield*` để các module mã hóa / giải mã token của trình phát hoạt động đầy đủ.
       - Thêm state `activeStreamReferer` và IPC listener `set-stream-referer`.
       - Trong `session.defaultSession.webRequest.onBeforeSendHeaders`: Tự động trích xuất origin của trang web nguồn (hỗ trợ mọi domain mirror: `.nl`, `.love`, `.tv`, `.meme`...) và cập nhật động header `Referer` tương ứng cho mọi request tới `googleapiscdn.com`.
     - Trong `routes/build.py`:
       - Tiếp nhận tham số `referer` từ request query.
       - Gán header `Referer` theo tham số động thay vì hardcode.
       - Giữ nguyên script `avs-shield.min.js`, xóa mock `createShield` gây xung đột.
2. **Cải tiến luồng thu thập MSE Stream ngầm (`triggerStreamDownload` & `inject_script`)**:
   - Trong `routes/build.py` (`inject_script`): Khi phát hiện `auto_stream=1`, tự động kích hoạt tăng tốc bộ đệm (`playbackRate = 16.0` và `muted = true`) giúp JWPlayer nạp và giải mã toàn bộ khối MSE nhanh gấp 16 lần mà không bị chính sách autoplay chặn âm thanh cản trở.
   - Thêm lắng nghe sự kiện `MSE_STREAM_COMPLETE` khi kết thúc video để đóng gói Blob `.mp4` ngay lập tức.
   - Trong `static/js/main.js`:
     - Truyền `referer` qua `setStreamReferer` và query parameter khi khởi chạy `triggerStreamDownload` và `triggerPreview`.
     - Bổ sung fallback thông minh trên nút "Save Video (.mp4)": Nếu bấm lưu trước khi video kịp buffer đầy đủ trong RAM, hệ thống sẽ tự động chuyển tiếp sang tác vụ thu thập ngầm trong Downloads Manager để lưu trọn vẹn tập phim thành file `.mp4`.
3. **Kiểm thử & Xác minh**:
   - `node -c electron/preload.js electron/main.js static/js/main.js`: Exit Code 0.
   - `python -m py_compile routes/build.py`: Exit Code 0.
   - Bổ sung unit test `tests/test_stream_referer.py`.
   - Chạy toàn bộ test suite `unittest discover tests`: **39/39 tests PASS (Exit Code 0)**.

## Summary of Accomplishments (Sprint v38 - Dynamic Duration Sizing, Direct GET Stream Downloader & Eradication of F12 / Ads)
1. **Tính toán kích thước luồng stream động (Dynamic Sizing thay vì ~350 MB cố định)**:
   - Trong `extractors/generic.py`: Khởi tạo nhãn `"size": "Stream (MSE / HD)"` ban đầu; trong `resolve_opt_size`, nếu có `duration` thì tính toán chính xác dung lượng dựa trên công thức bitrate luồng (`duration_seconds * 275000 bytes`).
   - Trong `static/js/main.js`:
     - Bổ sung `computeDynamicStreamSize` trong `displayMetadata` tính toán theo `duration` thực tế hoặc hiển thị `Stream (MSE / HD)`.
     - Trong `triggerPreview`: Lắng nghe thời lượng phát thực tế từ JWPlayer (`getDuration()`) hoặc thẻ `<video>` (`duration`) để cập nhật thời gian thực vào thanh thông tin Preview (`Type: STREAM PLAYER | 23:40 (~372 MB)`).

2. **Nút GET tải trực tiếp về máy (Automated Background Stream Downloader)**:
   - Xóa bỏ việc ép người dùng chuyển hướng sang modal Preview khi bấm nút `Get`.
   - Xây dựng hàm `triggerStreamDownload` trong `static/js/main.js`:
     - Tạo task card trong Downloads Manager với nhãn `MSE STREAM` và thanh tiến trình.
     - Khởi chạy iframe thu thập ngầm (`bg-capture`) kết nối với `/api/system/proxy-sub?mode=html&auto_stream=1`.
     - Lắng nghe message `MSE_CHUNK_CAPTURED`, cập nhật phần trăm và số MB đã thu thập vào thẻ Downloads Manager theo thời gian thực.
     - Khi stream hoàn tất: tự động đóng gói Blob `.mp4`, kích hoạt tải file về máy và chuyển trạng thái task sang `state-complete` (`Done!`).

3. **Triệt tiêu hoàn toàn lỗi F12 (DevTools) & Quảng cáo**:
   - Trong `utils/helpers.py`: Bổ sung domain `googleapiscdn.com` vào `get_referer_by_url` trả về `https://animevietsub.love/`.
   - Trong `routes/build.py`:
     - Đặt headers `Origin: https://storage.googleapiscdn.com` và `Referer: https://animevietsub.love/`.
     - Chèn thẻ `<base href="https://storage.googleapiscdn.com/">` giải quyết triệt để đường dẫn relative script.
     - Bóc tách và xóa hoàn toàn thẻ script `avs-shield.min.js`, vô hiệu hóa 100% các hàm đo window size, listener F12, debugger loop.
     - Vô hiệu hóa `showFallback` banner.
     - Bổ sung CSS ẩn triệt để quảng cáo, banner, popup cờ bạc/BOM88.
     - Ngăn chặn triệt để keydown F12, Ctrl+Shift+I trong iframe.
   - Trong `electron/main.js`:
     - Intercept `*avs-shield*` trong `onBeforeRequest` chuyển hướng sang script vô hại.
     - Đăng ký `before-input-event` trên `mainWindow.webContents` để phím tắt F12 và Ctrl+Shift+I mở DevTools ở chế độ tách rời (`mode: 'detach'`) và `preventDefault()` không cho sự kiện phím truyền xuống trang web.

4. **Kiểm thử & Xác minh**:
   - `node -c static/js/main.js`: Exit Code 0.
   - `node -c electron/main.js`: Exit Code 0.
   - `unittest discover tests`: 36/36 tests PASS (Exit Code 0).

## Summary of Accomplishments (Sprint v37 - Fix Unknown Size, Preview DEMUXER Error & 1-Click Stream Capture)
1. **Khắc phục triệt để Unknown Size trên tất cả tập phim / luồng stream**:
   - Trong `extractors/generic.py`:
     - Thiết lập giá trị mặc định `"size": "~350 MB (HD Stream)"` khi khởi tạo AnimeVietSub options.
     - Trong `resolve_opt_size`: Bổ sung cơ chế fallback `is_stream_opt` (kiểm tra `is_hls`, `is_dash`, URL player/embed, nhãn stream hoặc format `avs_`) nếu `size_bytes` từ HEAD request trả về `< 1 MB` hoặc `None`, tự động gán kích thước ước tính `~350 MB (HD Stream)`.
   - Trong `static/js/main.js`:
     - Trong `displayMetadata` (cả bảng ungrouped lẫn server grouped), bổ sung logic fallback hiển thị `~350 MB (HD Stream)` cho các option luồng phát nếu `option.size === "Unknown Size"`.
     - Trong `triggerPreview` (dropdown chọn tập trong Preview modal), bổ sung `getEffectiveOptSize` hiển thị `(~350 MB (HD Stream))` thay vì `(Unknown Size)`.

2. **Khắc phục lỗi Preview (DEMUXER_ERROR_COULD_NOT_OPEN)**:
   - Trong `static/js/main.js` (`triggerPreview`):
     - Xác định biến `isStreamWebPlayer` bao gồm các điều kiện: `ext === "html"`, `type === "webpage"`, `formatId.startsWith("avs_")`, `label.includes("[STREAM]")`, hoặc URL player embed (`/player/`, `googleapiscdn.com`, `.html`).
     - Gán `isHtmlPage = isStreamWebPlayer` để định tuyến luồng phát Web Player vào `previewWebpageIframe` (kèm anti-ad, spoof viewport, devtools bypass và MSE chunk hook), tuyệt đối KHÔNG đưa vào thẻ `<video src="...">`.
     - Chấm dứt hoàn toàn lỗi `MEDIA_ERR_SRC_NOT_SUPPORTED` / `FFmpegDemuxer: open context failed` và không bị loop gọi server fallback preview.

3. **Khắc phục lỗi Tải về (Download failed) khi bấm "Get" ở bảng tập phim**:
   - Trong `static/js/main.js` (`btn-get` click listener):
     - Mở rộng điều kiện kiểm tra `isStreamOption` cho cả `ext === "html"` lẫn các option dạng stream player (`formatId.startsWith("avs_")`, `label.includes("[STREAM]")`, URL player).
     - Tự động chuyển hướng click sang nút Preview tương ứng kèm thông báo `showPlayerToast("Đang mở Stream Player để xem và lưu video MP4 trực tiếp...")`.
     - Trong Preview modal, nút `previewDownloadBtn` ("Save Video (.mp4)") trích xuất trực tiếp các khối MSE buffer trong RAM thành file `.mp4` hoàn chỉnh.

4. **Kiểm thử & Xác minh**:
   - Kiểm tra cú pháp JavaScript `node -c static/js/main.js` thành công (Exit Code 0).
   - Chạy test suite `unittest discover tests`.

## Summary of Accomplishments (Sprint v36 - MSE Stream Capture & Direct MP4 Download from Web Player)
1. **Hook MSE `SourceBuffer.prototype.appendBuffer` trong `routes/build.py`**:
   - Trong `proxy_subtitle_endpoint` (`inject_script`): Bổ sung hook vào `SourceBuffer.prototype.appendBuffer` để tự động thu thập toàn bộ media chunks (`ArrayBuffer`) được giải mã và đẩy vào player.
   - Thêm phương thức `window.getCapturedStreamBlob(mimeType)` trả về `Blob` định dạng video (`video/mp4`).
   - Lưu trữ tham chiếu `_realParent` trước khi mock `window.parent`, truyền dữ liệu `postMessage({ type: 'MSE_CHUNK_CAPTURED', totalChunks, totalBytes })` về cửa sổ cha.
2. **Cơ chế lưu video MP4 trực tiếp trong `static/js/main.js`**:
   - Trong `previewDownloadBtn.onclick`: Thêm kiểm tra chế độ Web Player (`previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden")`).
   - Tuyệt đối không gọi `triggerDownload()` tải file `.html`.
   - Trích xuất blob video trực tiếp từ `iframeWin.getCapturedStreamBlob('video/mp4')` và tải xuống dưới dạng `${safeTitle}.mp4`.
   - Fallback: Nếu chưa có MSE chunk, kiểm tra thẻ `<video>` trong iframe: tải trực tiếp nếu có URL stream sạch hoặc sử dụng `MediaRecorder` để ghi luồng phát.
   - Bổ sung helper `showPlayerToast` hiển thị thông báo tiến trình trích xuất video trực quan, không gây nghẽn UI.
   - Lắng nghe sự kiện `MSE_CHUNK_CAPTURED` trên window cha để cập nhật thời gian thực số MB video đã bắt trong RAM trên nút tải và thông tin Preview.
3. **Cập nhật giao diện trong `displayMetadata`**:
   - Hiển thị badge `STREAM PLAYER` nổi bật thay cho nhãn `WEBPAGE`.
   - Cập nhật tiêu đề nhóm thành `Stream Player Options`.
   - Intercept nút `Get` của dòng Stream Player để tự động kích hoạt Preview mở trình phát thay vì tải file html.
4. **Kiểm thử & Xác minh**:
   - Thêm bài kiểm thử tự động `tests/test_mse_stream_capture.py`.
   - Kiểm tra cú pháp JavaScript `node -c static/js/main.js` thành công.
   - Toàn bộ test suite chạy thành công: **36/36 tests PASS (Exit Code 0)**.

## Summary of Accomplishments (Sprint v35 - Backend Deep Harvester & Stream Deobfuscation Enhancement)
1. **Trích xuất & Đào sâu luồng Media thực tế trong `extractors/generic.py`**:
   - **AnimeVietSub format options**: Chuyển đổi toàn bộ format option AnimeVietSub từ `ext: "html"` / `type: "webpage"` sang `ext: "mp4"`, `type: "video"`, `resolution: "Web Stream (MSE)"`, `label: f"Server: AnimeVsub [STREAM] ({ep_label})"`.
   - **RoPhim format options**: Chuyển đổi từ `ext: "html"` sang `ext: "mp4"`, `type: "video"`.
   - **DooPlay & Data-link Player**: Tích hợp giải mã script (`deobfuscate_script`) và quét đa dạng luồng (`scan_text_for_media_urls`) trên nội dung HTML nhúng nếu chưa bóc tách được trực tiếp.
   - **Step 8 (Raw links & script blocks)**: Quét toàn bộ khối `<script>` trong `page_html`, chạy giải mã deobfuscator (Dean Edwards packer, hex, unicode, base64) để tìm kiếm triệt để mọi luồng media `.m3u8`, `.mpd`, `.mp4`.
   - **Step 9 (Recursive iframe)**: Soi query parameter của iframe URL (`?url=`, `?source=`, `?file=`, `?v=`, `?src=`, `?link=`) để bóc tách luồng trực tiếp ngay lập tức mà không cần fetch HTML nếu đã có sẵn. Quét mọi script block trong HTML của iframe.
   - Gán đồng bộ `ext: "mp4"` và `type: "video"` cho mọi luồng video stream phát hiện được.
   - Di chuyển `cookies_dict = {}` lên đầu hàm `generic_html_link_harvester` để đảm bảo scope nhất quán trong nested function.

2. **Triệt tiêu lỗi lưu file `.html` & Giải mã Player trong `tasks/download.py`**:
   - Xóa bỏ `or is_avs` khỏi khối tải fallback webpage (`if format_id == "generic_fallback" and ext == "html":`). Tuyệt đối không lưu file .html khi tải video stream.
   - Thêm cơ chế tự động giải mã luồng từ trang player/embed: Khi nhận URL player/embed chưa có extension media trực tiếp, thực hiện fetch HTML, chạy `deobfuscate_script` và `scan_text_for_media_urls` để giải mã luồng trực tiếp (.m3u8, .mpd, .mp4) trước khi chuyển qua yt-dlp/ffmpeg.
   - Cơ chế phát hiện luồng WebCrypto MSE trong RAM trình duyệt: Báo lỗi có chỉ dẫn chi tiết: *"Luồng phát được mã hóa WebCrypto/MSE trong RAM trình duyệt. Vui lòng mở 'Xem trước' (Preview) và bấm 'Lưu Video (.mp4)' để thu trực tiếp!"*.

3. **Kiểm thử & Xác minh (Verification)**:
   - Viết các test case tự động trong `tests/test_generic_deobfuscator.py` kiểm thử: script deobfuscation harvester, iframe query param detection, WebCrypto MSE rejection, và player stream resolution.
   - Chạy lệnh `.\venv\Scripts\python.exe -m unittest discover -p "test_*.py" tests`: **35/35 tests PASS - Exit Code 0**.
1. **Root Cause Analysis (Poster Anya "Website này có quảng cáo!" & Tối đen)**:
   - **Mồi nhử Anti-Adblock**: Console hiển thị 2 lỗi đỏ:
     `GET https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js net::ERR_BLOCKED_BY_CLIENT`
     `HEAD https://securepubads.g.doubleclick.net/tag/js/gpt.js net::ERR_BLOCKED_BY_CLIENT`
   - Đoạn mã của AnimeVietSub cố tình gửi request tới 2 URL này để kiểm tra xem client có đang chạy trình chặn quảng cáo hay không. Khi Electron `onBeforeRequest` hủy request (`cancel: true`), script bắt được lỗi mạng `ERR_BLOCKED_BY_CLIENT`, lập tức chèn poster Anya và cắt luồng stream video (khiến player tối đen).
2. **Permanent Solution**:
   - [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js):
     - Xóa bỏ hoàn toàn `session.defaultSession.webRequest.onBeforeRequest`. Mọi network request chạy tự nhiên 200 OK, website không bao giờ phát hiện AdBlock và cấp đầy đủ video stream.
     - Giữ `contents.setWindowOpenHandler` chặn đứng toàn bộ popup quảng cáo/cờ bạc nếu người dùng click vào vùng player.
     - DevTools mở ở chế độ cửa sổ rời (`mode: 'detach'`), không làm co hẹp cửa sổ chính nên script đo viewport không phát hiện được DevTools.
   - [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
     - Xử lý quảng cáo trong DOM: Inject CSS ẩn toàn bộ banner BOM88, `.avs-ads`, `#avs-ads`, `.jw-ad-container` và chạy scrubber định kỳ xóa các thẻ cờ bạc/BOM88 khỏi DOM mà không gây bất kỳ lỗi mạng nào.
     - Khóa `outerWidth/Height` bằng `innerWidth/Height` trong `iframeWin` để vô hiệu hóa phép đo DevTools.
3. **Verification**:
   - Toàn bộ 28 bài unit tests đạt chuẩn (Exit Code 0).

## Summary of Accomplishments (Sprint v33 - Elimination of ERR_UNSAFE_REDIRECT & Restoring Fluid Playback)
1. **Black Screen & ERR_UNSAFE_REDIRECT Root Cause**:
   - Chromium nghiêm cấm chuyển hướng (redirect) từ `https://` sang `data:` URI (`net::ERR_UNSAFE_REDIRECT`).
   - Service Worker của `storage.googleapiscdn.com` khi gặp `ERR_UNSAFE_REDIRECT` trên `vast.js` và `ads/active` đã ném lỗi `FetchEvent network error: the promise was resolved with an error response object`, làm sập toàn bộ tiến trình khởi động JWPlayer và gây tối đen màn hình.
2. **Permanent Resolution**:
   - [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js):
     - Gỡ bỏ hoàn toàn việc can thiệp `data:` URI trên các tài nguyên nội bộ của CDN player (`ads/active`, `vast.js`, `avs-shield.min.js`), để Service Worker và JWPlayer khởi động mượt mà không có bất kỳ lỗi mạng nào.
     - Tiếp tục chặn triệt để các mạng quảng cáo/cờ bạc và tracking bên ngoài (`doubleclick.net`, `googlesyndication.com`, `bom88`, `bet88`, v.v.).
     - Mở DevTools ở chế độ tách rời độc lập (`mode: 'detach'`), loại bỏ 100% nguyên nhân gây lệch kích thước cửa sổ (`outerHeight - innerHeight`), khiến anti-devtools detector hoàn toàn không phát hiện được.
   - [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
     - Tiệt tiêu quảng cáo BOM88 và các banner động bằng CSS injection (`display: none !important`) kết hợp bộ dọn dẹp định kỳ (periodic scrubber) trong 5 giây đầu.
     - Vô hiệu hóa các cảnh báo bằng cách spoof `outerWidth/Height` trong `iframeWin`.
3. **Verification**:
   - Cú pháp Node.js trên cả 2 file `electron/main.js` và `static/js/main.js` hợp lệ 100%.
   - Chạy test suite: 28/28 tests passed (Exit Code 0).

## Summary of Accomplishments (Sprint v32 - Developer Tools & Anti-Adblock Warning Eradication)
1. **Developer Tools Detection Bypass ("Developer Tools đang mở")**:
   - **Root Causes**:
     - Script `avs-shield.min.js` liên tục giám sát kích thước cửa sổ (`outerWidth`/`outerHeight` so với `innerWidth`/`innerHeight`). Khi mở DevTools (docked ở bottom trong Electron dev mode), độ lệch kích thước vượt ngưỡng khiến `avs-shield.min.js` redirect iframe sang `devtools-warning`.
   - **Solutions**:
     - [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js):
       - Chặn và chuyển hướng `*avs-shield*` sang script trung hòa vô hại (`data:application/javascript,.../* avs-shield neutralized */`). Kiểm tra xác nhận `init.min.js` không hề phụ thuộc hay gọi `avs-shield`.
       - Chặn toàn bộ network request và frame navigation tới `*devtools-warning*`.
     - [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
       - Ghi đè `outerWidth` và `outerHeight` của `iframeWin` trỏ về `innerWidth`/`innerHeight` để vô hiệu hóa phép đo kích thước.
       - Inject CSS ẩn triệt để mọi phần tử chứa class/id `devtools`, `devtools-warning`.

2. **Anti-Adblock Detection Bypass ("Phát hiện trình chặn quảng cáo")**:
   - **Root Causes**:
     - Sử dụng `cancel: true` trên các request kiểm tra quảng cáo (`*ads/active*`, `*vast.js*`) làm browser trả về lỗi mạng `net::ERR_BLOCKED_BY_CLIENT`. Khối `catch()` / `onerror` của player phát hiện lỗi mạng và lập tức kích hoạt màn hình cảnh báo `adblock-warning`.
   - **Solutions**:
     - Áp dụng nguyên lý uBlock Origin: **Không bao giờ ngắt kết nối gây lỗi mạng, mà MOCK dữ liệu rỗng HTTP 200 OK**:
       - Cho API ads (`*ads/active*`, `*api/ads*`): redirect sang `data:application/json;charset=utf-8,{"status":200,"success":true,"ads":[],"data":[]}`.
       - Cho VAST script (`*vast.js*`): redirect sang `data:application/javascript;charset=utf-8,/* vast harmless */;window.vastLoaded=true;`.
       - Cho VAST XML (`*vast.xml*`): redirect sang `data:text/xml;charset=utf-8,<VAST version="3.0"/>`.
     - Kết quả: Player script nhận HTTP 200 thành công, anti-adblock không bị kích hoạt, đồng thời danh sách quảng cáo rỗng ngăn chặn 100% banner cờ bạc BOM88.
     - Chặn frame navigation và network request tới `*adblock-warning*`.

## Summary of Accomplishments (Sprint v31 - Aspect Ratio 16:9 & Intrusive Ad Blocking)
1. **Aspect Ratio & Modal Sizing (16:9 Auto-Fitting)**:
   - **Root Causes**:
     - `#preview-webpage-iframe` có inline style cứng nhắc `min-height: 550px;`, gây vỡ layout và co bẹp khi kích thước modal card nhỏ hơn.
     - Hàm `fitPreviewToMedia` chỉ kiểm tra `isVideoVisible` và `isImageVisible`, bỏ qua `previewWebpageContainer` (`isWebpageVisible`), khiến nút "Fit to Media Size" vô hiệu với webpage player và mở ra với kích thước ngẫu nhiên/bẹp dúm.
   - **Solutions**:
     - [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html): Gỡ bỏ `min-height: 550px` cứng nhắc.
     - [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css): Thêm quy tắc CSS chuyên dụng cho `#preview-webpage-container` và `#preview-webpage-iframe` (width/height 100%, black background, border-radius).
     - [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
       - Bổ sung nhánh `isWebpageVisible` vào `fitPreviewToMedia()` với tỷ lệ chuẩn 16:9 (`1920x1080`).
       - Expose `window._fitPreviewToMedia` và tự động kích hoạt khi mở `isHtmlPage` để modal tự động căn chuẩn 16:9 theo tỷ lệ màn hình người dùng.
2. **Block Intrusive Overlay Ads & Popups (BOM88 / VAST / Active Ads)**:
   - **Root Causes**:
     - Player nhúng từ CDN load `/admin/api/ads/active` và `/static/jwplayer/vast.js`, kích hoạt popup quảng cáo cờ bạc (BOM88) đè lên giao diện video.
     - Các click vô tình vào player có thể kích hoạt `window.open` nhảy tab ngoài.
   - **Solutions**:
     - [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js):
       - Thêm `session.defaultSession.webRequest.onBeforeRequest` cancel triệt để toàn bộ request tới `*ads/active*`, `*vast.js*`, `*doubleclick*`, `*adservice*`, `*bom88*`, v.v.
       - Thêm `contents.setWindowOpenHandler` trong `web-contents-created` chặn đứng toàn bộ popup quảng cáo cờ bạc/tracker.
     - [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
       - Trong `previewWebpageIframe.onload`, inject CSS triệt tiêu toàn bộ element quảng cáo, banner, VAST container còn sót trong DOM của iframe.
3. **Direct Video Stream Explanation**:
   - Stream AnimeVietSub dùng chuẩn mã hóa bảo vệ bản quyền `SAMPLE-AES-CTR` (`KEYFORMAT="urn:avs:shield:v3"`).
   - Danh sách chunk `.m3u8` là dummy URL giả (`storage.googleapiscdn.com/chunks/.../seg000.html`). `avs-loader.js` dùng WebCrypto AES-CTR giải mã URL thực trên CDN Google Photos (`lh3.googleusercontent.com`).
   - HTML5 `<video>` thông thường không có runtime giải mã WebCrypto này nên bắt buộc chạy qua sandboxed iframe player để phát mượt mà, zero-CPU và nét nhất.

## Summary of Accomplishments (Sprint v30 - AnimeVietSub Native Player & Localhost Referrer Fix)
1. **AnimeVietSub Iframe Player Black Screen & Segment 403/429 Fix**:
   - **Root Causes**:
     1. **`Referer` & `Origin` Cloudflare Challenge on Direct CDN Requests**: In Electron, requests from iframes to `https://storage.googleapiscdn.com` sent default `Referer: http://127.0.0.1:<port>/`. Cloudflare's bot shield flagged this cross-origin localhost referrer and blocked chunk requests with HTTP 403 / 429 (`{"error":"Bot detected"}` or `{"error":"Missing segment token"}`).
     2. **Encrypted Placeholder Segments & `_avsDomains` Referrer Whitelist**: AnimeVietSub M3U8 files contain placeholder segment URLs (`storage.googleapiscdn.com/chunks/.../seg000.html`). `avs-loader.js` intercepts these and decrypts them into genuine Google Photos CDN URLs (`https://lh3.googleusercontent.com/...`). However, `avs-loader.js` verifies `document.referrer` against `window._avsDomains = [..., [108,111,99,97,108,104,111,115,116]]` (`localhost`). When the app loaded on `http://127.0.0.1:18650`, `document.referrer` was `127.0.0.1` (NOT in whitelist), causing `avs-loader.js` to abort decryption and JWPlayer to fallback to raw placeholder URLs which failed with 403.
     3. **Electron Navigation Interception**: In `electron/main.js`, `contents.on('will-navigate')` intercepted all navigations without checking `isMainFrame`, blocking iframe embedded players from loading.
     4. **Stale Running Process**: Electron DEV was running since 10:04 AM without restart, executing old Python code that lacked `X-Envelope` forwarding.
   - **Solutions**:
     1. In [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js):
        - Added `session.defaultSession.webRequest.onBeforeSendHeaders` intercepting `*googleapiscdn.com*` to inject `Referer: https://animevietsub.love/` and `Origin: https://storage.googleapiscdn.com`.
        - Changed `mainWindow.loadURL` to `http://localhost:${serverPort}/` so `document.referrer` matches `localhost` in `window._avsDomains`.
        - Updated `will-navigate` in `web-contents-created` to only intercept top-level main frame navigations (`isMainFrame`), permitting iframe subframe player navigations.
     2. In [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
        - In `triggerPreview`, when `window.electronAPI` is present and `streamUrl.startsWith('http')`, set `previewWebpageIframe.src = streamUrl` directly. This enables `avs-loader.js` to run on its native origin with full WebCrypto access.
     3. Verification:
        - Confirmed via Electron headless runner that JWPlayer loads M3U8, resolves duration (1420s), decrypts segments to `lh3.googleusercontent.com`, and plays fluidly (`currentTime > 0`, `readyState: 4`, exit code 0).
        - Ran test suite: `.\venv\Scripts\python.exe -m unittest discover tests` (Ran 28 tests, all passed, Exit Code 0).
1. **AnimeVietSub Iframe Player Black Screen & Browser Incompatibility Notice Fix**:
   - **Root Causes**:
     1. In [`extractors/generic.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/generic.py), `clean_iframe = iframe_link.split("?")[0]` stripped query parameter `?isFinal=1`. In Google CDN player HTML, this caused `const isFinal = ""` instead of `"1"`.
     2. In [`app.py`](file:///d:/JOB/DEV/EveryThingDownloader/app.py), the 404 proxy fallback intercepted `/static/avs-fingerprint.min.js` and returned a dummy `console.log(...)`. Because `avs-fingerprint.min.js` defines essential crypto hashing objects on `window` required by `init.min.js` and `avs-loader.min.js`, the player boot sequence threw an uncaught error.
     3. In [`routes/build.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/build.py), `navigator.serviceWorker.register` was mocked to return `Promise.resolve()`. In `init.min.js`, `.then(function(reg) { reg.active... })` threw a TypeError on `undefined`, triggering the `.catch()` block that called `_runCompatBootstrap()`.
     4. `_runCompatBootstrap()` called `_avsShowBrowserUpgradeNotice()`, which rendered the orange card: *"Trình duyệt của bạn hỗ trợ chưa tốt — hãy dùng Chrome, Firefox hoặc Edge để xem mượt hơn."* and bypassed JWPlayer setup, leaving the video container pitch black.
   - **Solutions**:
     1. In [`extractors/generic.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/generic.py): Preserved essential query parameters (especially `?isFinal=1`), stripping only tracking parameters `nextName` and `nextUrl`.
     2. In [`routes/build.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/build.py):
        - Enforced `isFinal=1` query parameter on Google CDN player URLs if missing.
        - Neutralized `_avsShowBrowserUpgradeNotice` and replaced `_runCompatBootstrap` to invoke `startPlayer()` directly.
        - Spoofed `navigator.userAgent` and `navigator.appVersion` inside the iframe to standard Chrome 128 string, preventing Electron detection.
        - Mocked `navigator.serviceWorker.register` to return a complete mock registration object (`{ active: { postMessage: function() {}, state: 'activated' }, installing: null, waiting: null, scope: '/', addEventListener: function() {}, removeEventListener: function() {} }`).
        - Enhanced CSS suppression covering all variants of the warning element: `#avs-compat-fallback, .avs-warning, .browser-warning, [id*="compat-fallback"], .quality-notice, [style*="245, 158, 11"], [style*="245,158,11"], [style*="rgb(245, 158, 11)"], [style*="rgb(245,158,11)"], [style*="#f59e0b"]`.
        - Added periodic DOM scrubber (250ms) to immediately remove any banner element containing warning text (`Trình duyệt của bạn`, `Không thể phát video`, `hỗ trợ chưa tốt`).
        - Added auto-play polling trigger for JWPlayer once initialized.
     3. In [`app.py`](file:///d:/JOB/DEV/EveryThingDownloader/app.py):
        - Removed `"avs-fingerprint"` from neutralization filter so the hashing library passes through to CDN intact.
        - Patched `init.min.js` on-the-fly to neutralize `_avsShowBrowserUpgradeNotice` and force `startPlayer()`.
     4. Verification:
        - Created unit test [`tests/test_avs_preview.py`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_avs_preview.py) verifying query parameter preservation, JS patching, and URL enforcement.
        - All 26 Python unit tests passing (Exit Code 0).

## Summary of Accomplishments (Sprint v28 - Streaming Extraction, Universal Preview & UI Audit)
1. **Downloads Manager Badge & Dark/Light Theme Contrast Fix (Yêu cầu #2)**:
   - **Nguyên nhân**: `.downloads-count-badge` trong [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css) sử dụng biến chưa từng được khai báo `background: var(--cyan-gradient)` kèm `color: #000`. Khiến badge bị trong suốt và chữ đen chìm hoàn toàn vào nền tối của panel. Ngoài ra, panel Downloads Manager thiếu toàn bộ style override cho `.light-theme`.
   - **Giải pháp**:
     - Thay thế bằng `background: var(--cyan); color: #fff;` với font-weight 700 và box-shadow chuẩn theme.
     - Bổ sung toàn diện bộ style `.light-theme .downloads-manager`, `.downloads-manager-header`, `.downloads-count-badge`, `.downloads-manager-spinner`, `.download-task-card`, `.download-task-track`, `.btn-task-clear`.

2. **LuPhim.com Extraction & Moviking M3U8 Stream Parsing (Yêu cầu #5)**:
   - **Nguyên nhân**: Moviking cập nhật cấu trúc mới, nhúng `iframe` trỏ tới `cdn.codexa.fun/streaming3rd`. Extractor cũ gọi API POST không còn hoạt động, rơi vào fallback `Download Webpage (HTML / Text)`. Khi recursive iframe harvester quét trang, URL iframe bị lỗi `&amp;` (chưa unescape) khiến `web=&lang=` bị rỗng và CDN từ chối cấp stream.
   - **Giải pháp**:
     - Trong [`extractors/generic.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/generic.py): Nâng cấp LuPhim extractor tự động phát hiện `iframe` lồng nhau từ Moviking sang `cdn.codexa.fun`, bóc tách trực tiếp link HLS `.m3u8` (`Server: LuPhim [M3U8 Direct]`), tự động tính toán kích thước tệp video (1.5 GB) thay vì trả về webpage HTML.
     - Thêm `html_lib.unescape(src)` trong toàn bộ đệ quy iframe harvesting để triệt tiêu lỗi `&amp;` cho mọi trang web lồng iframe.

3. **RoPhim.soy Extraction & Bypass Trailer Detection (Yêu cầu #4)**:
   - **Nguyên nhân**: `rophim.soy` sử dụng Next.js App Router (Streaming Server Components). Trong trang HTML có metadata `video_preview` chứa link trailer từ IMDb (`https://imdb-video.media-imdb.com/...mp4`). yt-dlp nhận diện nhầm đây là video chính và chỉ lấy về trailer 88.5 MB.
   - **Giải pháp**:
     - Thêm RoPhim Extractor chuyên dụng trong [`extractors/generic.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/generic.py): Phân giải `public_id` từ URL phim, gọi API RoPhim (`/api/v1/player/getLink` và `/api/v1/movie/seasons`), trích xuất chính xác trình phát phim đầy đủ (`Server: RoPhim [Player]`) cho từng tập và cả bản full movie.
     - Trong [`routes/info.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/info.py): Mở rộng `should_bypass_ytdl` với danh sách heuristics các trang streaming/movie (`rophim`, `luphim`, `guphim`, `animevietsub`, `motphim`, `/xem-phim/`...). Bỏ qua yt-dlp ngay lập tức để tiết kiệm 15-30s timeout và không bao giờ bị bẫy bởi trailer IMDb.

4. **AnimeVietSub Iframe Sandbox & Anti-Tamper Bypass (Yêu cầu #3)**:
   - **Nguyên nhân**: Trình phát nhúng của AnimeVietSub chạy trong iframe Electron nhưng thẻ iframe thiếu các quyền `allow="autoplay; encrypted-media; fullscreen; picture-in-picture"` và thuộc tính `sandbox`, kích hoạt cơ chế cảnh báo tương thích trình duyệt (`#avs-compat-fallback`).
   - **Giải pháp**:
     - Trong [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html): Cấu hình đầy đủ quyền `allow="autoplay *; encrypted-media *; fullscreen *; picture-in-picture *"` và `sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation allow-downloads"` cho `#preview-webpage-iframe`.
     - Trong [`routes/build.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/build.py): Nâng cấp bộ tiêm mã chống kiểm tra môi trường (`window.createShield`), ẩn toàn bộ các biểu ngữ cảnh báo trình duyệt (`#avs-compat-fallback`, `.quality-notice`...) bằng CSS tiêm cưỡng chế.

5. **Xem trước tệp nội bộ Torrent & Tệp văn bản cục bộ (Yêu cầu #1)**:
   - **Nguyên nhân**: Khi tệp con torrent đã tải về máy (`opt["is_local"] = True`), nếu người dùng xem trước tệp phụ đề hoặc tệp văn bản (`.nfo`, `.txt`), endpoint `/api/system/proxy-sub` trước đây chỉ xử lý link HTTP hoặc thư mục tạm, dẫn đến lỗi khi đọc đường dẫn tuyệt đối trên ổ đĩa. Ngoài ra, `startServerSidePreview` trên frontend thiếu tiền tố `torrent_content_` trong danh sách whitelist chuyển tiếp `customUrl`.
   - **Giải pháp**:
     - Trong [`routes/build.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/build.py): Bổ sung nhánh xử lý trực tiếp tệp ổ đĩa cục bộ `os.path.isabs(url) and os.path.isfile(url)` trong `proxy_subtitle_endpoint`.
     - Trong [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js): Thêm `formatId.startsWith("torrent_content_")` vào payload whitelist để gửi đúng đường dẫn tệp đĩa / webseed URL lên server-side preview converter. Nâng cấp thông báo giao diện đồ họa đẹp mắt khi tệp torrent chưa tải về máy.

6. **Mở rộng đa định dạng xem trước & Xem PDF trực tiếp (Yêu cầu #6)**:
   - **PDF Viewer**: Tích hợp luồng xem trước PDF qua `previewWebpageIframe`, hỗ trợ cả PDF trực tuyến và PDF lưu cục bộ trên máy.
   - **Code & Text Formats**: Mở rộng `isRawTextFile` và `textPreviewExts` trong [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js) hỗ trợ đầy đủ các định dạng mã nguồn: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.rs`, `.go`, `.rb`, `.php`, `.pl`, `.swift`, `.kt`, `.r`, `.scala`, `.lua`, `.toml`, `.sh`, `.bat`, `.sql`, `.nfo`, `.env`, `.gitignore`, `.dockerfile`.

7. **Trí thông minh phân tích trang web lạ (Universal Smart Crawler) (Yêu cầu #7 & #8)**:
   - Trong [`extractors/generic.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/generic.py):
     - Phát hiện thông minh các trang SPA hiện đại dựa trên `__NEXT_DATA__`, `self.__next_f`, `jwplayer`, `videojs`, `plyr`, `artplayer`, `dplayer`.
     - Tìm kiếm luồng phát `.m3u8` và `.mp4` được định nghĩa trong các biến script JS (`var url =`, `file:`, `source:`, `stream:`).
     - Tự động bỏ qua lỗi giải mã ký tự HTML `&amp;` trong các liên kết nhúng iframe đệ quy.

8. **Kiểm thử tự động & Xác minh chất lượng (Yêu cầu #8, #9, #10)**:
   - Thêm 3 test case tự động mới vào [`tests/test_proxy_and_preview.py`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_proxy_and_preview.py):
     - `test_proxy_subtitle_local_file`
     - `test_should_bypass_ytdl_streaming_sites`
     - `test_downloads_count_badge_css`
   - Toàn bộ 25 bài unit test Python đạt kết quả: `Ran 25 tests in 0.243s - OK`.
   - Kiểm tra cú pháp JavaScript: `node -c static/js/main.js` đạt Exit Code 0.
   - Kiểm tra tính năng chuyển trang & lọc trùng URL: `test_navigation_history.js` và `test_url_deduplication.js` toàn bộ passed.
1. **Xử lý triệt để lỗi 403 Meta/Facebook/Instagram CDN (`/api/proxy/image`)**:
   - **Nguyên nhân**: Link ảnh Facebook/Instagram CDN (`*.fbcdn.net`) chứa tham số chữ ký hết hạn `oe=<hex_timestamp>`. Khi gọi quá thời gian cho phép, CDN trả về `HTTP 403 Forbidden` (`URL signature expired`). Header `Referer` trước đó bị thiếu cấu hình cho `fbcdn.net`, và `routes/download.py` hardcode đường dẫn cookie mà không fallback cookie từ Chrome Extension.
   - **Giải pháp**:
     - Trong [`utils/helpers.py`](file:///d:/JOB/DEV/EveryThingDownloader/utils/helpers.py): Bổ sung quy tắc phân giải Referer cho `fbcdn.net`, `facebook.com`, `fbsbx.com` (`https://www.facebook.com/` hoặc `https://www.instagram.com/`).
     - Trong [`utils/cookies.py`](file:///d:/JOB/DEV/EveryThingDownloader/utils/cookies.py): Cho phép `get_cookie_file_path()` tự động fallback sang `cookies_chrome-extension.txt` hoặc tệp cookie mới nhất khi `client_id` không khớp hoặc bị thiếu.
     - Trong [`routes/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/download.py):
       - Thay thế toàn bộ hardcode `cookies_{client_id}.txt` bằng hàm dùng chung `get_cookie_file_path(client_id)`.
       - Nâng cấp `User-Agent` lên `DEFAULT_MEDIA_USER_AGENT` (`Chrome/147.0.0.0`).
       - Trong `proxy_image`: Khi CDN upstream trả mã `403` (signature expired), `404`, hoặc anti-bot HTML block, chuyển cấp độ log xuống `INFO` và trả về ngay ảnh vector SVG placeholder chuẩn dark-mode (`FALLBACK_IMAGE_PLACEHOLDER_SVG`, `mimetype="image/svg+xml"`). Ngăn chặn hoàn toàn lỗi 403 làm đỏ console trình duyệt và sinh log cảnh báo `[WARN ] [Flask]` trên terminal.
   - **Unit Tests**:
     - Thêm `test_proxy_image_403_fallback_svg` và `test_proxy_image_success` vào [`tests/test_proxy_and_preview.py`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_proxy_and_preview.py).
     - Mock `os.startfile` trong `test_sys_import_in_download_task` để tránh chặn luồng desktop khi chạy bộ test tự động.

2. **Phân nhóm định dạng tệp đa phương tiện & dữ liệu (File Format Grouping)**:
   - Trong [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js) (hàm `displayMetadata`), phân tách độc lập các danh mục tệp:
     - **Torrent / Magnet Package (`torrentPackages`)**: Nhóm gói swarm hiển thị trên đầu, icon package, chỉ cung cấp nút **GET** để tải về máy hoặc mở client BitTorrent/uTorrent, loại bỏ hoàn toàn nút Preview.
     - **Video Options (`videos`)**: Nhóm tệp video thật sự (`.mp4`, `.mkv`...) với nút **PREVIEW** và **GET**, hỗ trợ gom nhóm theo Server nếu có.
     - **Audio Options (`audios`)**: Tự động gom tệp âm thanh từ cả `data.audio_options` và `data.video_options` (`.mp3`, `.m4a`...) với đầy đủ nút Preview & Get.
     - **Photo Options (`photos`)**: Hình ảnh (`.jpg`, `.png`, `.webp`...) với Preview & Get.
     - **Document & Text Files (`documents`)**: Tệp văn bản (`.xml`, `.json`, `.txt`, `.md`...) có nút **PREVIEW** (mở xem text) và **GET**; tệp tài liệu nhị phân (`.pdf`, `.doc`) chỉ có nút **GET**.
     - **Subtitle Options (`subFiles`)**: Phụ đề (`.vtt`, `.srt`...) với Preview & Get.
     - **Other / Data Files (`others`)**: Tệp dữ liệu / nhị phân / nén (`.sqlite`, `.db`, `.zip`, `.iso`, `.exe`, `.bin`...) chỉ cung cấp nút **GET**, tuyệt đối không hiển thị nút PREVIEW gây lỗi.
   - Trong [`extractors/torrent.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/torrent.py), hoàn thiện bộ phân loại extension: `VIDEO_EXTS`, `AUDIO_EXTS`, `IMAGE_EXTS`, `SUB_EXTS`, `TEXT_EXTS`, `DOC_EXTS`, `DATA_EXTS`, `ARCHIVE_EXTS`. Gán trường `type` chuẩn xác cho từng tệp.

2. **Khắc phục lỗi xem trước & Tích hợp BEP 19 WebSeeds (Torrent Preview Fix)**:
   - Loại bỏ nút PREVIEW ở các định dạng tệp không thể preview (gói torrent `.torrent`, tệp cơ sở dữ liệu `.sqlite`, tệp nén `.zip`, disk image `.iso`).
   - Tích hợp chuẩn BitTorrent BEP 19 WebSeeds (`url-list`): Đối với các torrent từ Internet Archive (`archive.org`) hoặc có WebSeeds HTTP, backend tự động phân giải URL HTTP trực tiếp vào `opt["url"]`. Nhờ đó người dùng có thể bấm PREVIEW và xem phim trực tiếp trên trình phát HTML5 mà không cần đợi tải toàn bộ torrent.
   - Trong [`tasks/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/tasks/download.py):
     - Phân định rõ tác vụ gói torrent (`is_torrent_package_task`) và tác vụ tải tệp con (`torrent_content_`).
     - Tệp con có URL HTTP WebSeed được tải trực tiếp tốc độ cao qua HTTP CDN stream và tự động bỏ qua hậu xử lý FFmpeg nếu là file dữ liệu non-media (`.sqlite`, `.xml`).
     - Tệp con đã có trên đĩa cứng cục bộ được sao chép trực tiếp.

3. **Sửa lỗi hiển thị mã HTML thô trong thông báo Preview**:
   - Trong [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js#L1357) (`showPreviewLoader`), đổi `previewLoaderText.textContent = text;` thành `previewLoaderText.innerHTML = text;`.
   - Các thông báo chứa thẻ định dạng `<br>` và `<strong>GET</strong>` giờ được hiển thị sạch đẹp, chuyên nghiệp, không còn bị lộ thẻ HTML thô.
1. **Quoted Path Input Sanitization ("Copy as path" Fix)**:
   - When copying paths on Windows via "Copy as path", surrounding quotes (`"E:\Downloads\xyz.torrent"`) caused regex validation failures and file lookups to fail (`os.path.exists` returning False).
   - Created `sanitizeInputUrl()` in [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js) and applied it on paste, input, `isValidUrl()`, `normalizeMediaUrl()`, and `performAnalysis()`.
   - Updated [`routes/info.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/info.py), [`extractors/torrent.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/torrent.py), and [`tasks/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/tasks/download.py) to strip surrounding single/double quotes across all endpoints.

2. **Direct File and Folder Browse Buttons in Search Bar**:
   - Added `#browse-file-btn` (file icon) and `#browse-folder-btn` (folder icon) inside `.search-input-wrap` in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html).
   - Implemented native Electron dialog IPC channels (`select-file`, `select-folder`) in [`electron/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/main.js) and [`electron/preload.js`](file:///d:/JOB/DEV/EveryThingDownloader/electron/preload.js) using `dialog.showOpenDialog`.
   - Added browser fallback via hidden `<input type="file">` and `webkitdirectory` with multipart upload support to `/api/info`.
   - Updated `updateUrlInputButtons()` in [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js) to smoothly hide paste & browse buttons when input is non-empty and display the clear button.

3. **Stale Metadata & Analysis Error Reset**:
   - Fixed bug where previous video metadata and download format cards remained visible below error alerts when analyzing a new invalid or failed link.
   - Implemented `clearActiveAnalysisUI()` in [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js). Whenever analysis begins or an error occurs in `performAnalysis()` or `showError()`, `activeMetadata` is cleared, `optionsContainer.innerHTML = ""`, video thumbnails are reset, and `resultGrid` is set to `welcome-mode`.

4. **Torrent Preview & Missing `sys` Import Fix**:
   - Fixed `NameError: name 'sys' is not defined` in [`tasks/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/tasks/download.py) by importing `sys`.
   - In [`extractors/torrent.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/torrent.py), added local sibling file detection for `.torrent` inputs so already-downloaded media files are marked with `opt["is_local"] = True` and streamed directly via `/api/proxy/stream`.
   - In [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js), added guard for non-downloaded torrent items in `triggerPreview()` to guide users to use the GET button or open in their BitTorrent client.

## Summary of Accomplishments
1. **Backend Streaming & Byte-Range 206 Passthrough Integrity**:
   - In [`routes/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/download.py#L841), added `direct_passthrough=True` to the Flask generator `Response` in `/api/proxy/stream`. This prevents Werkzeug from stripping `Content-Length` on 206 Partial Content responses, ensuring browsers accurately compute buffer ranges and video duration.
   - Added unit test `test_proxy_stream_partial_content_range_headers` in [`tests/test_proxy_and_preview.py`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_proxy_and_preview.py), verifying status 206, `Content-Range`, `Content-Length`, and `Accept-Ranges`.

2. **Web Audio Routing & Equalizer Support for Video**:
   - In [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js#L2300), routed `videoSourceNode` into `eqBassNode` instead of directly into `analyser`. Video playback audio now benefits from the full 4-band EQ and voice filter chain.
   - Added `previewVideoPlayer.crossOrigin = "anonymous"` before connecting to Web Audio API.

3. **A-B Loop Visualizer & Two-Way Trimmer Synchronization**:
   - Added `#video-loop-range-bar`, `#video-loop-marker-a`, and `#video-loop-marker-b` to the video timeline seekbar in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html#L2190) and [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css#L3685).
   - Implemented real-time visual positioning with dynamic percentages and translucent cyan accent glow.
   - Implemented two-way sync: When opening preview modal, any active trim range on the main page (`#trim-checkbox`, `#trim-start`, `#trim-end`) is automatically populated into the A-B loop and rendered on the timeline.

4. **Media Library Quick Retry & History Single-Item Deletion**:
   - Added a "Retry" (`btn-lib-retry`) button on incomplete (`error`/`cancelled`) download cards in Media Library, allowing 1-click re-download without re-entering the URL.
   - Added an inline delete button (`&times;`) per item in the Recent History list so users can remove individual links.

5. **WCAG 2.1 AA Keyboard Accessibility & Shortcuts**:
   - Added a global `:focus-visible` system in [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css) with high-contrast `var(--cyan)` focus rings for keyboard tabbing without mouse click outlines.
   - Added keyboard shortcuts: `R` (Toggle Repeat), `P` (Picture-in-Picture), `T` (Transcript Sidebar).
   - Added `aria-label` and hotkey indicators to all video controls in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html).

6. **Root Cause Analysis (Frozen at `[0%] Queued. Starting download...` on MP3 & Video)**:
   - **`UnboundLocalError: cannot access local variable 're'` in `tasks/download.py`**:
     Inside `bg_download_task` at line 930, there was a local statement `import re`. In Python semantics, importing or assigning to a variable anywhere in a function makes it a local variable across the entire function scope. At line 691, `url = re.sub(r'&list=RD[^&]*', '', url)` attempted to access `re` before the local import was reached, causing an immediate `UnboundLocalError`.
   - **Uncaught Exception in Background Thread**:
     Because line 691 was located before the `try:` block (which previously started at line 802), the `UnboundLocalError` killed the background worker thread immediately upon start. The status in `downloads_status[download_id]` was never updated and remained permanently at `status: "pending"`, `progress: 0`, `message: "Queued. Starting download..."`.
   - **Werkzeug Reloader File-Watch Interruptions**:
     In `app.py`, `app.run(..., debug=not is_prod)` ran with `use_reloader=True` by default in dev mode (`FLASK_ENV=development`). Whenever yt-dlp or SQLite wrote chunks to `downloads/` or `downloads.db`, the Werkzeug reloader detected file changes and abruptly restarted Flask in the middle of active downloads, marking tasks as `"Server restarted. Task interrupted."` and leaving orphan processes on port 18650.
   - **Orphan Zombie Processes on Port 18650**:
     When the reloader or previous dev process was stopped via Ctrl+C, child processes remained alive listening on port 18650. When `electron` launched a new instance, `findFreePort` selected 18651, while browser tabs at `http://127.0.0.1:18650` interacted with the dead orphan process.

2. **Resolution of Preview & Progressive Streaming ("Load tới đâu chiếu tới đó")**:
   - **Why Preview was Downloading to 100% instead of Streaming On-the-Fly**:
     In [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js), `isYouTubeMedia` and `isConvertedAudio` were previously hardcoded to disable direct streaming (`isDirectStream = false`) for all YouTube formats and all MP3 formats. This bypassed the progressive streaming proxies (`/api/proxy/stream` and `/api/proxy/stream_adaptive` - FR-35) and forced every preview into `startServerSidePreview`, which queued a full background download to 100% before playing.
   - **Audio Preview Instant Streaming**:
     Removed `isConvertedAudio` blocking. When previewing MP3/M4A/Audio, the frontend now extracts the direct audio stream from `activeMetadata.audio_options` and feeds it directly into HTML5 `<audio>` via `/api/proxy/stream`. Playback starts in ~0.5s without any server-side download or conversion.
   - **Adaptive Stream Proxy Header Alignment**:
     In [`routes/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/download.py), replaced outdated Chrome 120 User-Agent with modern `DEFAULT_MEDIA_USER_AGENT` matching `yt-dlp` (`Chrome/147.0.0.0`) in both `proxy_stream` and `proxy_stream_adaptive` to prevent Google Video CDN 403 Forbidden errors.
   - **Preventing Flask Lockups via Threading**:
     Added `threaded=True` to `app.run` in [`app.py`](file:///d:/JOB/DEV/EveryThingDownloader/app.py) to guarantee that SSE connections (`/api/download/progress/<id>`) never block subsequent HTTP API requests.

3. **Slim Sleek Scrollbar Styling (Resolved Thick Scrollbar with Arrows)**:
   - **Root Cause**: In [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css), `.card` previously had `scrollbar-width: thin;` and `scrollbar-color: rgba(...) transparent;`. In modern Chromium (Chrome 121+ / Electron 28+), specifying `scrollbar-color` completely disables `::-webkit-scrollbar` pseudo-elements on that container, causing Chromium to fall back to the default Windows OS scrollbar (16px thick bar with `▲`/`▼` arrow buttons).
   - **Fix**: Removed `scrollbar-color` and `scrollbar-width: thin;` from `.card`. Updated `::-webkit-scrollbar` globally and on `.card` / `.format-list` to a 4px ultra-slim floating pill with `::-webkit-scrollbar-button { display: none; width: 0; height: 0; }` to eliminate arrow buttons completely.

4. **Ambient Light Glow Advanced Fine-Tuning System & Collapsible Accordion Fix**:
   - **Root Cause of Overlap**: `#ambient-glow-wrapper` previously included the shared class `.collapsible-settings-wrapper`. Later in [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css#L7485), `.collapsible-settings-wrapper.expanded` clamped `max-height: 250px; overflow: visible;`. Because the ambient drawer content requires ~340px, the bottom 90px overflowed visibly and caused subsequent flex siblings (`A-B Loop (Trim)`) to overlap directly on top of the Performance/FPS select dropdown.
   - **Fix & Accordion Grouping**:
     - Removed `.collapsible-settings-wrapper` from `#ambient-glow-wrapper`.
     - Set `.ambient-glow-wrapper.expanded { max-height: 600px !important; margin-bottom: 12px; }` to allow full natural height and spacious margin separation.
     - Added an interactive Accordion trigger in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html#L1815-L1825): users can click the Ambient Light Glow header or chevron button `[▼] / [▶]` to fold or unfold the entire tuning drawer at any time.
     - Added dynamic preset tag badge (`Standard`, `Vibrant`, `Subtle`, `Dreamy`, `Custom`) next to the title.
     - Persisted drawer open/collapse preference in `localStorage` under `video-ambient-glow-drawer-open`.
   - **Deep Customization Parameters**:
     - **Brightness / Opacity**: 10% - 100% (CSS `--ambient-opacity`).
     - **Blur Diffusion**: 10px - 120px (CSS `--ambient-blur`).
     - **Color Vibrance / Saturation**: 100% - 250% (CSS `--ambient-saturate`).
     - **Glow Spread / Scale**: 100% - 125% (CSS `--ambient-size-x`, `--ambient-size-y`).
     - **Framerate / Performance Throttle**: 60 FPS (Ultra Smooth), 30 FPS (Balanced default, saving 50% CPU/GPU draw calls), 15 FPS (Eco Mode).
   - **Curated Presets**: Standard, Vibrant, Subtle, Dreamy, and Instant Reset button.
   - **Real-time Live Preview & Aspect Ratio Adaptation**: Sliders update CSS variables and canvas frame immediately even while video is paused. Dynamic aspect ratio downsampling matches video dimensions.
   - **State Persistence**: Saved to `localStorage` under `video-ambient-glow-config` and `video-ambient-glow-enabled`.

5. **YouTube-style Video Buffering & Timeline Progress Bar Fix**:
   - **Root Cause of Missing Buffer Bar**:
     - In [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js#L2118), `totalDuration` evaluated to `previewVideoPlayer.duration` whenever `previewIsAdaptive` was false. For HTTP proxy streams without `Content-Length`, `previewVideoPlayer.duration` returned `Infinity` or `NaN`, causing `pct_buffered = (bufferedEnd / Infinity) * 100 = 0`, collapsing the buffer bar width to 0% and producing invalid CSS.
     - Buffer range lookup only checked strict `start <= curTime && end >= curTime` without tolerance, failing when PTS time codes had slight offsets.
     - Media elements (`<video id="preview-video-player">`, `<audio id="preview-audio-player">`) lacked `preload="auto"` in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html), allowing browsers to conservatively halt buffering when paused.
     - `bufferedColor` had low opacity (`rgba(255, 255, 255, 0.4)`), rendering invisible beside the glowing 14px seek thumb.
   - **Fixes Applied**:
     - Added `preload="auto"` to both video and audio player elements.
     - Updated `updateSliderBackground` with robust `totalDuration` fallback (`isFinite(previewVideoPlayer.duration)` -> fallback to `activeMetadata.duration_raw`).
     - Added `0.5s` tolerance interval window to locate active buffer range across seek jumps.
     - Upgraded buffer fill color to match the theme accent color with soft glow opacity (`rgba(var(--cyan-rgb), 0.45)` on dark theme, `rgba(var(--cyan-rgb), 0.35)` on light theme), ensuring instant visual recognition across all themes (Rose, Emerald, Cyan, Orchid, Orange, etc.).
     - Centralized duration calculations into `getVideoTotalDuration()` across timeline slider, timeupdate, durationchange, loadedmetadata, thumbnail previews, and keyboard seek shortcuts.
     - Hooked buffer update triggers across all key media lifecycle events: `progress`, `canplay`, `seeked`, `playing`, `pause`, `loadeddata`.

6. **Timeline Hover Thumbnail Lag & Stale Frame Elimination**:
   - **Root Cause**: `seekThumbCanvas` retained stale pixel data across hover sessions. When hovering at a new timestamp (e.g. 54:17 vs 11:53), the tooltip popped up showing the old frame until the background video finished seeking (100-400ms), giving a jarring flash of outdated scenes.
   - **Fixes Applied**:
     - Implemented in-memory `thumbCache` (up to 120 `ImageBitmap` frames) for instant 0ms recall when scrubbing or revisiting timeline positions.
     - Upgraded video seeking to hardware keyframe `fastSeek` (`thumbPreviewVideo.fastSeek()`), cutting seek delay by 5-10x.
     - Added `.seek-thumb-tooltip canvas.is-seeking` with CSS ease transition (`0.18s`), dimming (`opacity: 0.45`) and blurring (`blur(2px)`) when seeking distant or uncached timestamps.
     - Handled `mouseleave` by marking `is-seeking` and clearing `thumbLastDrawnTime`, guaranteeing stale frames are never displayed as current timestamps upon re-entry.

8. **URL Navigation History Back/Forward Controls (`[ ← ] [ → ]`) Activation**:
   - **Root Cause**:
     - `navigationHistory` previously initialized as an empty array (`[]`) with `navigationIndex = -1`.
     - When the user analyzed their first link (e.g. YouTube video), `pushToNavigationHistory(url)` set `navigationIndex = 0`.
     - The state evaluator `updateNavigationButtons()` computed:
       - `navBackBtn.disabled = (navigationIndex <= 0)` -> `0 <= 0` was `true` (`disabled`).
       - `navForwardBtn.disabled = (navigationIndex >= length - 1)` -> `0 >= 0` was `true` (`disabled`).
     - Both buttons were permanently locked in disabled state (`opacity: 0.2`, `pointer-events: none`), preventing the user from returning to the Welcome/Home screen.
     - Furthermore, `pushToNavigationHistory` explicitly rejected empty strings (`if (!url) return;`), meaning the Home / Welcome state was never represented in the navigation stack.
   - **Fixes Applied**:
     - Initialized `navigationHistory = [""]` and `navigationIndex = 0`, treating the Welcome Dashboard as the root home page.
     - When analyzing any link, `navigationIndex` advances to `1+`, immediately enabling the Back button `[ ← ]` with tooltip `Go back to Welcome Screen`.
     - In `navigateHistoryBack()` and `navigateHistoryForward()`, navigating back to index 0 (`""`) cleanly resets to the Welcome screen via newly extracted `resetToWelcomeDashboard()`.
     - Added sequential duplicate deduplication and branch truncation (`splice`) matching web browser history specs.
     - Added WCAG 2.1 AA keyboard `:focus-visible` styling (`var(--cyan)`) in [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css#L9609).
     - Added support for mouse thumb buttons 3 & 4 (hardware Back/Forward mouse buttons).
     - Created standalone runnable test suite [`tests/test_navigation_history.js`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_navigation_history.js) with 7 assertion checks passing 100%.
     - Bumped cache busters in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html) to `?v=25.0`.

9. **Media URL Normalization & Smart History Deduplication**:
   - **Root Cause**:
     - `saveToHistory()` previously performed raw string comparison (`item.url !== url`).
     - A video accessed via playlist parameters (e.g. `&list=RDDzOF3gUEqkY&start_radio=1`), timestamp (`&t=...`), or tracking parameters (`&si=...`, `&fbclid=...`) was treated as a completely different entry from the clean canonical URL (`https://www.youtube.com/watch?v=DzOF3gUEqkY`).
     - Consequently, analyzing the same video at different times produced duplicate rows in "Recent Analyzed" history (e.g. `NØIR/SIDE | Elegy - EP` appearing at both 21:13:41 and 23:26:29).
   - **Fixes Applied**:
     - Implemented `normalizeMediaUrl(url)`:
       - Canonicalizes YouTube formats (watch, youtu.be, shorts, live, embed, music) to `https://www.youtube.com/watch?v=VIDEO_ID`.
       - Strips query tracking parameters (`fbclid`, `igshid`, `si`, `utm_*`, `ref`, `feature`, `start_radio`, `t`, `list=RD*`).
     - Implemented `isSameMediaItem(itemA, itemB)`:
       - Multi-tier matching: normalized URL match, media `id` match, or exact title + platform match.
     - Implemented `deduplicateHistory(history)`:
       - Auto-cleans legacy duplicate records from `localStorage` whenever `renderHistory()` runs, immediately merging existing duplicate cards into a single latest entry.
     - Added `id` and `webpage_url` to `/api/info` response in [`routes/info.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/info.py#L1885).
     - Created runnable unit test [`tests/test_url_deduplication.js`](file:///d:/JOB/DEV/EveryThingDownloader/tests/test_url_deduplication.js): 5/5 assertions passed.
     - Bumped cache busters in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html) to `?v=26.0`.

10. **uTorrent & BitTorrent Full Analysis & Handoff Support**:
   - **Feature Scope**:
     - Analyze Magnet links (`magnet:?xt=urn:btih:...`).
     - Analyze local and remote `.torrent` files.
     - Accept raw 40-character SHA1 and 32-character base32 torrent info-hashes.
   - **Implementation Details**:
     - Created [`extractors/torrent.py`](file:///d:/JOB/DEV/EveryThingDownloader/extractors/torrent.py):
       - Built pure Python zero-dependency Bencode decoder (`bdecode_torrent`) extracting exact `info` dict bytes to compute SHA-1 `info_hash`.
       - Structured file inspection: parses multi-file and single-file torrents, extracting file paths, individual sizes, and categorized options (video, audio, image, general files).
       - Magnet link parser: extracts `xt` (BTIH hash), `dn` (display name), `tr` (trackers), `xl` (file length).
     - Integrated into [`routes/info.py`](file:///d:/JOB/DEV/EveryThingDownloader/routes/info.py):
       - Added `is_torrent_input(url)` check to route magnet links and torrent files to `extract_torrent_info()`.
     - Integrated into [`tasks/download.py`](file:///d:/JOB/DEV/EveryThingDownloader/tasks/download.py):
       - On download request, writes `.magnet` or downloads `.torrent` file to sandbox, and dispatches to Windows default BitTorrent client (uTorrent, qBittorrent, etc.) via `os.startfile()`.
     - Frontend updates in [`static/js/main.js`](file:///d:/JOB/DEV/EveryThingDownloader/static/js/main.js):
       - Updated `isValidUrl()` to accept `magnet:` links and raw 40/32-character torrent hashes.
       - Added `torrent` and `utorrent` theme colors (`#25c276`, `#00e676`).
       - Canonicalized Magnet links in `normalizeMediaUrl()`.
     - UI additions in [`templates/index.html`](file:///d:/JOB/DEV/EveryThingDownloader/templates/index.html) and [`static/css/styles.css`](file:///d:/JOB/DEV/EveryThingDownloader/static/css/styles.css):
       - Added `uTorrent / Magnet` platform badge on the Welcome dashboard with 1-click sample magnet link.
       - Added `.platform-badge.tag-torrent` uTorrent green styling.
       - Bumped cache busters to `?v=27.0`.

11. **Verification**:
   - Ran `.\venv\Scripts\python.exe -m unittest tests/test_torrent_extractor.py`: 5/5 unit & integration tests passed (Exit Code 0).
   - Ran `node tests/test_url_deduplication.js`: 5/5 assertions passed (Exit Code 0).
   - Ran `node tests/test_navigation_history.js`: 7/7 assertions passed (Exit Code 0).
   - Ran `node -c static/js/main.js`: Syntax OK (Exit Code 0).
   - Ran `venv/Scripts/python.exe -m unittest discover tests`: All unit tests passed with Exit Code 0.

8. **Running the Application**:
   - To run in Desktop App mode:
     ```powershell
     cd electron
     npm run dev
     ```
     Or double click `run_desktop.bat` (or shortcut `EveryThingDownloader Dev.lnk` on Desktop).
   - Backend runs on `http://127.0.0.1:18650`.

## Notes & Technical Warnings
- If rebuilding the standalone installer `.exe`, execute `venv\Scripts\python.exe build_tool/builder_cli.py` to compile the latest code into `dist/server.exe`.
