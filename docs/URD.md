# User Requirements Document (URD) - EveryThingDownloader

## 1. Executive Summary & Scope
EveryThingDownloader is a self-hosted, universal media download utility designed to extract, convert, and package video, audio, image, and subtitle assets from major online social and media platforms. The application operates in three distinct delivery models:
1. **Self-Hosted Web Application**: A lightweight, multi-client web utility accessible from local and network browsers.
2. **Standalone Desktop Application**: A high-fidelity, packaged desktop shell wrapping the core server on **Windows, macOS, and Linux**, requiring zero external runtime dependencies (Python/Node.js) or command-line execution from the end-user.
3. **Docker Container**: A containerized deployment option for headless web-server operation and build-tool access without local environment setup.

This document details the user needs, target user personas, functional and non-functional requirement mappings, and UI/UX design systems to align developers and stakeholders on the project's behavioral specifications.

---

## 2. Target Audience & User Personas

### 2.1 Content Creators & Video Editors
- **Core Needs**: High-fidelity video downloads (1080p, 2K, 4K), lossless audio extractions, and clipping specific ranges (trimming) to import segments directly into video editing suites (e.g. Adobe Premiere, DaVinci Resolve) without downloading huge source files.
- **Pain Points**: Ad-heavy, malware-prone generic downloader websites that throttle download speeds, restrict high resolutions, or inject watermarks.

### 2.2 Archivists & Collectors
- **Core Needs**: Batch downloading entire collections (e.g. YouTube playlists, Facebook photo albums), extracting captions/subtitles in multiple languages, and preserving original metadata.
- **Pain Points**: Platform geo-blocking, age-gates, and anti-bot IP rate-limiting that break long-running batch operations.

### 2.3 Software Distributors & Resellers
- **Core Needs**: Packaging the downloader into custom-branded standalone executables, applying usage restrictions (expiry dates, IP locks, hardware locks) to control and monetize distribution.
- **Pain Points**: Decompilation of Python code, license bypassing, and configuration tampering.

---

## 3. Prioritized Requirement Matrix

| ID | Category | Requirement Description | Priority |
| :--- | :--- | :--- | :--- |
| **FR-01** | Extraction | Support YouTube standard videos, YouTube Shorts, and complete Playlists. | High |
| **FR-02** | Extraction | Support social platforms: Facebook (post, watch, albums), Instagram (reels, IGTV), TikTok, Twitter/X, Threads, Reddit, Pinterest, SoundCloud, and movie sites (MotChill, GhienPhim, LuPhim — WordPress DooPlay / Moviking sites). | High |
| **FR-03** | Processing | Extract separate video/audio streams and merge (mux) them into a single MP4/MKV. | High |
| **FR-04** | Trimming | Provide a visual timeline slider to crop start/end timestamps before downloading. | High |
| **FR-05** | Image Extraction | Detect and extract individual images from galleries/albums with multi-select batch downloads. | Medium |
| **FR-06** | Subtitles | Download or copy subtitle tracks as raw text or VTT format. | Medium |
| **FR-07** | Session Bypass | Upload Netscape-formatted cookie files to bypass age restrictions and login walls. | High |
| **FR-08** | Packaging | Compile server and Electron shell into single-file binaries, installers, app bundles, and portables for **Windows, macOS, and Linux**. Specific outputs: NSIS Setup + Portable + MSI + ZIP (Windows), DMG + ZIP + PKG (macOS), AppImage + tar.gz + DEB + RPM (Linux). | High |
| **FR-09** | Obfuscation | AST code scrambling, string literal encryption, dead code injection, anti-debugging, and binary shielding via PyArmor. | High |
| **FR-10** | Licensing | Apply IP whitelist locks, date-based expiry limits, and Machine ID hardware locks (CSPRODUCT UUID on Windows, SHA256 fingerprint on macOS, `/etc/machine-id` on Linux). | High |
| **FR-11** | Preview | Render fallback webpage (HTML) formats inside an interactive sandbox/iframe using a CORS-safe proxy instead of displaying raw text. | Medium |
| **FR-12** | Fullscreen | Enable a 3-mode preview fullscreen layout (Normal, Web Fullscreen, Native Fullscreen) for all formats with 3s mouse-inactivity auto-hiding for header/controls/cursor. | High |
| **FR-13** | Session Bypass | Bypass IP blocks and Cloudflare protection on webpage preview/download using curl_cffi Chrome impersonator and whitelisted cookies. | High |
| **FR-14** | Subtitles | Batch translate subtitle cues to target language using Google Translate API in 4000-char chunks to bypass rate limits. | Medium |
| **FR-15** | Subtitles | Aggressively deduplicate and collapse rolling subtitles (YouTube-style captions) by matching sequences and containment. | High |
| **FR-16** | Subtitles | Align and shift subtitle timestamps automatically when downloading a trimmed video segment. | High |
| **FR-17** | Subtitles | Automatically split long sentences in translated subtitles into shorter blocks of max 10 words per slide. | Medium |
| **FR-18** | Auto-Update | Desktop app checks for updates from public GitHub `update.json`, downloads platform-specific format (.exe for Windows, .dmg per architecture arm64/x64 for macOS, .AppImage for Linux), and performs native installation. Platform keys in `update.json`: `win32`, `darwin_arm64`, `darwin_x64`, `linux_x64`. | High |
| **FR-19** | CI/CD | GitHub Actions workflow builds for all 3 platforms (Windows, macOS, Linux) in parallel, publishes releases with SHA-256 checksums, and updates `update.json` automatically. | High |
| **FR-20** | Docker | Support Docker/Docker Compose deployment for the web server and build tool GUI without local environment setup. | Medium |
| **FR-21** | Subtitles | Support hardsub burn-in with customizable styles (font family, size, text color, background box, outlines, opacity, and positioning). | High |
| **FR-22** | Subtitles | Support softsub muxing with proper stream mapping and default active track configuration (auto-load disposition). | High |
| **FR-23** | Post-Processing | Apply cinematic color filters (Cyberpunk, Vintage, Noir, Enhance) to video via FFmpeg color grading presets. | Medium |
| **FR-24** | Post-Processing | Export video segments as animated GIF (palettegen) or convert horizontal video to vertical 9:16 Shorts with blurred background padding. | Medium |
| **FR-25** | Audio | 4-band audio equalizer (Bass 60Hz, Low-Mid 500Hz, High-Mid 2kHz, Treble 10kHz) with presets (Flat, Bass Boost, Vocal, Acoustic, Electronic, Lo-Fi). | Medium |
| **FR-26** | Audio | Playback speed control (0.25x–3x) with chained atempo filter for out-of-range values. | Low |
| **FR-27** | Audio | Voice effect presets (8 modes: Normal, Deep, Bright, Hall, Studio, Lo-Fi, Telephone, Underwater) via FFmpeg audio filters. | Low |
| **FR-28** | AI | AI voiceover dubbing via `edge-tts` — parallel TTS synthesis (15 concurrent), sequential scheduling, PCM mixing with original audio (8% original, 150% voiceover). | High |
| **FR-29** | Cloud | Upload completed downloads to Telegram Chat/Group/Channel via Bot API (sendVideo, sendAnimation, sendDocument). | Medium |
| **FR-30** | History | Persist all download tasks in SQLite database with review, re-download, and per-item deletion capabilities. | High |
| **FR-31** | UX | Dark/Light theme toggle with View Transitions API circular clip-path animation. | Low |
| **FR-32** | UX | UI Customizer with 10+ accent themes, glass blur, typography scale, font family, grid effects, sparkles, and gravity modes. | Low |
| **FR-33** | Extraction | Support SoundCloud audio and Vimeo video downloading via yt-dlp. | Medium |
| **FR-34** | Preview | Image viewer with zoom (0.5x–5x), 90° rotation, drag-to-pan, and arrow key navigation. | Medium |
| **FR-35** | Preview | DASH Adaptive Streaming preview — FFmpeg on-the-fly muxing of separate video-only + audio-only streams via `/api/proxy/stream_adaptive`. | High |
| **FR-36** | Network | DNS-over-HTTPS bypass (Cloudflare, Google, AdGuard, OpenDNS) to circumvent ISP-level DNS blocks on Vietnamese streaming sites. | High |
| **FR-37** | Session | Smart browser cookie auto-detection from 6+ installed browsers (Chrome, Edge, Firefox, Opera, Vivaldi, Brave) with domain-aware prioritization. | Medium |
| **FR-38** | UX | 20+ keyboard shortcuts for Video Player, Audio Player, Image Viewer, and Subtitle/Text Viewer. | Medium |
| **FR-39** | Build | Git Release Publisher — create tags, commits, and push directly from Build GUI to trigger GitHub Actions CI/CD pipeline. | Medium |
| **FR-40** | Progress | Real-time download progress reporting via Server-Sent Events (SSE) stream at `/api/download/progress/<id>`. | High |
| **NFR-01** | Clean-up | Automatically delete temporary files immediately after completion or cancellation (5-minute delayed cleanup timer). | High |
| **NFR-02** | Performance | Dynamic multi-threaded download segments (5 concurrent fragment downloads) to maximize bandwidth utilization. | High |

---

## 4. UI/UX Design System Guidelines

To achieve the premium, state-of-the-art visual standard requested for this project, the interface must follow the strict design token system below.

### 4.1 Dark-Neon Color Palette
- **Background Base**: Deep rich black-blue (`#0a0f1d` / `rgba(10, 15, 29, 1)`)
- **Card Background**: Glassmorphic slate (`rgba(20, 26, 45, 0.6)`)
- **Primary Accent (Cyan)**: `#00f2fe` (used for standard status, links, and system indicators)
- **Secondary Accent (Purple)**: `#9b51e0` (used for advanced features, settings, and badges)
- **Success Glow (Green)**: `#00ffd0` (used for successful operations and completion indicators)
- **Warning Glow (Orange/Yellow)**: `#ffb000` (used for notices and alerts)
- **Error Glow (Red)**: `#ff4b4b` (used for system failures and input errors)

### 4.2 Typography
- **Font Stack**:
  - Headers & Brand Title: `"Space Grotesk"`, sans-serif (delivers a structured, futuristic appearance).
  - Body & Input Fields: `"Outfit"`, sans-serif (highly readable, clean).
- **Text Sizes**: Brand Header (`28px`), Card Titles (`18px`), Body Text (`14px`), Form Labels (`12px`).

### 4.3 Glassmorphism CSS Parameters
All layout cards, dialogs, and panels must employ the following glassmorphic properties to ensure high visual depth:
```css
background: rgba(20, 26, 45, 0.55);
backdrop-filter: blur(12px);
-webkit-backdrop-filter: blur(12px);
border: 1px solid rgba(255, 255, 255, 0.08);
box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
border-radius: 12px;
```

### 4.4 Scrollbars
Scrollbars must be styled to match the dark-neon aesthetics:
- **Track**: Transparent or deep blue-black (`rgba(10, 15, 29, 0.5)`)
- **Thumb**: Thin 5px width, rounded, utilizing a linear gradient of `#00f2fe` to `#9b51e0` with a glow effect on hover.

### 4.5 Custom Dialogs
All confirmation and alert dialogs use a custom-built glassmorphic modal system (`showConfirm()`) instead of native browser `confirm()`/`alert()` dialogs, ensuring visual consistency with the dark-neon design language across all platforms.

---

## 5. User Scenarios & Error Recovery

### 5.1 Scenario A: Age-Gated / Member-Only Video Extraction
1. **User Action**: User inputs a member-only YouTube URL.
2. **System Behavior**: Analysis fails because guest tokens cannot view the content. An error card slides down.
3. **Recovery Flow**:
   - The system displays a friendly warning: *"Authentication Required. Please upload valid cookies for youtube.com."*
   - User clicks **Manage Cookies** and uploads their exported Netscape cookies file for YouTube.
   - User re-analyzes the link. The system extracts the format choices successfully.

### 5.2 Scenario B: Video Trimming Muxing Failures
1. **User Action**: User specifies a crop range that exceeds the video duration (e.g. trimming from 00:05:00 to 00:10:00 on a 3-minute video).
2. **System Behavior**: Frontend validates range inputs before submission to prevent unnecessary processing.
3. **Recovery Flow**:
   - The UI blocks the download trigger and highlights the slider track in red.
   - A tooltip displays: *"Trim range must be within the video duration (00:03:00)."*
   - Slider endpoints are automatically clamped to the video duration limit.

### 5.3 Scenario C: Auto-Update Flow (Desktop App)
1. **System Behavior**: On startup, the Electron app fetches `update.json` from the public GitHub repository.
2. **Update Available**: A dialog appears showing the new version and changelog with three options: *Update Automatically (Recommended)*, *Download Manually*, or *Later*.
3. **Auto-Install**: If the user selects automatic update, the app resolves the platform-specific download URL (under the `platforms` key: `win32`, `darwin`, or `linux`) and shows a progress window displaying percentages and download size.
4. **Platform Execution**: Once the download completes, the app quits and installs the update:
   - **Windows**: Executes the downloaded `.exe` setup installer in a separate process.
   - **macOS**: Automatically mounts the `.dmg` installer using `shell.openPath` and quits so the user can drag-and-drop the application into the Applications folder.
   - **Linux**: Applies `chmod +x` to the downloaded `.AppImage` file and spawns it, or opens the downloads directory for other packages.
