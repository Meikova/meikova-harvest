document.addEventListener("DOMContentLoaded", async () => {
  const loaderSection = document.getElementById("loader-section");
  const loaderText = document.getElementById("loader-text");
  const metaSection = document.getElementById("meta-section");
  const progressSection = document.getElementById("progress-section");
  const errorSection = document.getElementById("error-section");

  const metaThumb = document.getElementById("meta-thumb");
  const durationBadge = document.getElementById("duration-badge");
  const videoTitleEl = document.getElementById("video-title");
  const videoUploaderEl = document.getElementById("video-uploader");
  const platformBadge = document.getElementById("platform-badge");
  const formatsContainer = document.getElementById("formats-container");

  const progressTargetTitle = document.getElementById("progress-target-title");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");
  const progressMsg = document.getElementById("progress-msg");
  const progressSpeed = document.getElementById("progress-speed");
  const progressActions = document.getElementById("progress-actions");

  const errorMsgEl = document.getElementById("error-msg");
  const fallbackBtn = document.getElementById("fallback-btn");
  const settingsToggle = document.getElementById("settings-toggle");
  const settingsPanel = document.getElementById("settings-panel");
  const serverUrlInput = document.getElementById("server-url-input");

  let currentTab = null;
  let targetServerUrl = localStorage.getItem("etd_server_url") || "http://127.0.0.1:18650";
  let activeMetadata = null;
  let activeSse = null;
  let activeDownloadId = null;

  serverUrlInput.value = targetServerUrl;

  const CACHE_EXPIRATION_MS = 60 * 60 * 1000; // 1 hour expiration window

  const colorAccents = {
    video: { hex: "#8b5cf6", rgb: "139, 92, 246" },
    audio: { hex: "#00e5ff", rgb: "0, 229, 255" },
    subtitle: { hex: "#f59e0b", rgb: "245, 158, 11" },
    image: { hex: "#10b981", rgb: "16, 185, 129" }
  };

  const SVGIcons = {
    video: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
    audio: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`,
    subtitle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
    image: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
    download: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="11" height="11"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`
  };

  // Run cache garbage collection on load
  cleanupExpiredCache();

  // 1. Get current active tab details
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs[0]) {
      currentTab = tabs[0];
      const urlLower = (currentTab.url || "").toLowerCase();
      if (!urlLower.startsWith("http://") && !urlLower.startsWith("https://")) {
        showErrorState("Vui lòng mở một trang web chứa video hoặc nhạc (YouTube, Facebook, v.v.) để sử dụng.");
        return;
      }
    } else {
      showErrorState("Không tìm thấy tab trình duyệt đang hoạt động.");
      return;
    }
  } catch (err) {
    console.error("Error reading tab:", err);
    showErrorState("Không thể đọc thông tin tab trình duyệt.");
    return;
  }

  // 2. Auto-detect running port by checking open tabs
  try {
    const allTabs = await chrome.tabs.query({});
    for (const tab of allTabs) {
      if (tab.url) {
        const match = tab.url.match(/^https?:\/\/(?:127\.0\.0\.1|localhost):(\d+)/);
        if (match) {
          const port = match[1];
          try {
            const res = await fetch(`http://127.0.0.1:${port}/api/extension/stream`, { method: "HEAD" });
            targetServerUrl = `http://127.0.0.1:${port}`;
            serverUrlInput.value = targetServerUrl;
            localStorage.setItem("etd_server_url", targetServerUrl);
            break;
          } catch (e) {
            // port not responding, skip
          }
        }
      }
    }
  } catch (e) {
    console.warn("Could not auto-detect port:", e);
  }

  // 3. Initiate page analysis (checking local storage cache first)
  analyzeTabLink();

  async function analyzeTabLink() {
    if (!currentTab || !currentTab.url) return;

    // Check time-bound localStorage cache
    const cachedData = getCachedData(currentTab.url);
    if (cachedData) {
      activeMetadata = cachedData;
      console.log("Loading analysis metadata from time-bound localStorage cache.");
      renderMetadataAndOptions(activeMetadata);
      return;
    }

    showSection(loaderSection);
    loaderText.textContent = "Đang phân tích liên kết...";

    const infoUrl = `${targetServerUrl.replace(/\/$/, "")}/api/info`;

    try {
      const response = await fetch(infoUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: currentTab.url, client_id: "chrome-extension" })
      });
      
      let data;
      try {
        data = await response.json();
      } catch (jsonErr) {
        showErrorState("Phản hồi từ máy chủ không hợp lệ.");
        return;
      }

      if (response.ok && data.status === "success") {
        activeMetadata = data;
        // Save to cache
        setCachedData(currentTab.url, data);
        renderMetadataAndOptions(data);
      } else {
        const errMsg = data.message || "Phân tích thất bại.";
        console.warn("Server analysis returned error:", errMsg);
        showErrorState(errMsg);
      }
    } catch (err) {
      console.warn("Analysis connection failed:", err);
      showErrorState("Không thể kết nối đến ứng dụng EveryThingDownloader. Vui lòng đảm bảo ứng dụng đang chạy ở máy tính.");
    }
  }

  function renderMetadataAndOptions(data) {
    showSection(metaSection);
    
    // Set platform badge
    platformBadge.textContent = data.platform_label || "Link";
    platformBadge.className = `platform-badge badge-${data.platform_class || 'default'}`;

    // Set thumbnail with local proxy fallback
    const thumbUrl = data.thumbnail || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=150";
    if (thumbUrl.startsWith("http")) {
      metaThumb.src = `${targetServerUrl.replace(/\/$/, "")}/api/proxy/image?url=${encodeURIComponent(thumbUrl)}`;
    } else {
      metaThumb.src = thumbUrl;
    }
    
    // Duration
    if (data.duration && data.duration !== "Unknown" && data.duration !== "N/A" && data.duration !== "0:00") {
      durationBadge.textContent = data.duration;
      durationBadge.style.display = "block";
    } else {
      durationBadge.style.display = "none";
    }

    videoTitleEl.textContent = data.title || "Untitled Video";
    videoUploaderEl.textContent = data.uploader || "Unknown Platform";

    formatsContainer.innerHTML = "";

    const imageExts = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "heic", "heif", "tiff", "tif", "svg", "ico", "avif"];
    const htmlExts = ["html", "htm"];
    const docExts = ["txt", "xml", "json", "csv", "log", "md", "css", "js", "py", "yaml", "yml", "ini", "cfg", "conf"];
    const subExts = ["vtt", "srt", "ass", "ssa", "sub", "idx", "lrc"];

    // 1. Video Options
    const videos = (data.video_options || []).filter(opt => {
      if (opt.type) return opt.type === "video";
      const ext = (opt.ext || "").toLowerCase();
      return !imageExts.includes(ext) && !htmlExts.includes(ext) && !docExts.includes(ext) && !subExts.includes(ext);
    });

    // 2. Audio Options (including data.audio_options)
    const audios = data.audio_options || (data.video_options || []).filter(opt => {
      if (opt.type) return opt.type === "audio";
      const ext = (opt.ext || "").toLowerCase();
      return ["mp3", "m4a", "wav", "flac", "ogg", "aac", "wma", "opus"].includes(ext);
    });

    // 3. Subtitle Options
    const subtitles = data.subtitles || (data.video_options || []).filter(opt => {
      if (opt.type) return opt.type === "subtitle";
      const ext = (opt.ext || "").toLowerCase();
      return subExts.includes(ext);
    });

    // 4. Image Options
    const images = data.images || (data.video_options || []).filter(opt => {
      if (opt.type) return opt.type === "image";
      const ext = (opt.ext || "").toLowerCase();
      return imageExts.includes(ext);
    });

    let renderedCount = 0;

    // Render Video
    if (videos.length > 0) {
      const rowEls = [];
      videos.forEach(opt => {
        rowEls.push(createFormatRow(opt, "video"));
      });
      const groupEl = createFormatGroup("Video Resolutions", SVGIcons.video, rowEls, "video");
      if (groupEl) formatsContainer.appendChild(groupEl);
      renderedCount++;
    }

    // Render Audio
    if (audios.length > 0) {
      const rowEls = [];
      audios.forEach(opt => {
        rowEls.push(createFormatRow(opt, "audio"));
      });
      const groupEl = createFormatGroup("Audio Options", SVGIcons.audio, rowEls, "audio");
      if (groupEl) formatsContainer.appendChild(groupEl);
      renderedCount++;
    }

    // Render Subtitles
    if (subtitles.length > 0) {
      const rowEls = [];
      subtitles.forEach(opt => {
        rowEls.push(createFormatRow({
          format_id: opt.format_id || "subtitle",
          ext: opt.ext || "vtt",
          label: opt.name || opt.label || `Subtitle ${opt.lang || "Unknown"}`,
          quality: opt.lang || "",
          size: opt.size || "",
          url: opt.url || ""
        }, "subtitle"));
      });
      const groupEl = createFormatGroup("Subtitle Options", SVGIcons.subtitle, rowEls, "subtitle");
      if (groupEl) formatsContainer.appendChild(groupEl);
      renderedCount++;
    }

    // Render Images
    if (images.length > 0) {
      const rowEls = [];
      images.forEach((opt, idx) => {
        rowEls.push(createFormatRow({
          format_id: opt.format_id || "image",
          ext: opt.ext || "jpg",
          label: opt.label || `Photo ${idx + 1}`,
          quality: opt.quality || "",
          size: opt.size || "",
          url: opt.url || opt
        }, "image"));
      });
      const groupEl = createFormatGroup("Image Options", SVGIcons.image, rowEls, "image");
      if (groupEl) formatsContainer.appendChild(groupEl);
      renderedCount++;
    }

    if (renderedCount === 0) {
      formatsContainer.innerHTML = `<div style="text-align: center; padding: 20px; font-size: 11px; color: var(--text-muted);">Không tìm thấy tùy chọn tải cho liên kết này.</div>`;
    }
  }

  function createFormatGroup(titleText, iconSvg, elements, type) {
    if (!elements || elements.length === 0) return null;
    
    const groupDiv = document.createElement("div");
    groupDiv.className = "format-group";

    const header = document.createElement("div");
    header.className = "options-group-title";
    const accent = colorAccents[type] || colorAccents.video;
    header.style.setProperty("--color-accent", accent.hex);
    
    header.innerHTML = `
      <div class="options-group-title-left">
        ${iconSvg}
        <span>${titleText}</span>
      </div>
      <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10">
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    `;

    const contentDiv = document.createElement("div");
    contentDiv.className = "format-group-content";
    elements.forEach(el => contentDiv.appendChild(el));

    groupDiv.appendChild(header);
    groupDiv.appendChild(contentDiv);

    header.addEventListener("click", () => {
      const isCollapsed = contentDiv.classList.toggle("collapsed");
      header.classList.toggle("collapsed", isCollapsed);
    });

    return groupDiv;
  }

  function createFormatRow(opt, type) {
    const row = document.createElement("div");
    row.className = "format-row";
    
    const accent = colorAccents[type] || colorAccents.video;
    row.style.setProperty("--color-accent", accent.hex);
    row.style.setProperty("--color-accent-rgb", accent.rgb);

    const labelText = opt.label || (type === "video" ? `Video ${opt.quality || "Default"}` : type === "audio" ? `Audio ${opt.quality || "Default"}` : `Media File`);
    const ext = opt.ext || "mp4";
    const sizeStr = opt.size ? ` • ${opt.size}` : "";

    row.innerHTML = `
      <div class="format-left">
        <div class="format-icon-wrap">
          ${SVGIcons[type]}
        </div>
        <div class="format-details">
          <div class="format-label" title="${labelText}">${labelText}</div>
          <div class="format-meta">
            <span class="badge-ext">${ext}</span>
            <span>${sizeStr}</span>
          </div>
        </div>
      </div>
      <button class="btn-get">
        ${SVGIcons.download}
        <span>Get</span>
      </button>
    `;

    row.querySelector(".btn-get").addEventListener("click", () => {
      startDownloadTask(opt, labelText, type);
    });

    return row;
  }

  async function startDownloadTask(opt, labelText, type) {
    showSection(progressSection);
    progressTargetTitle.textContent = activeMetadata.title || "Downloading...";
    progressPercent.textContent = "0%";
    progressFill.style.width = "0%";
    progressMsg.textContent = "Đang khởi tạo tác vụ...";
    progressSpeed.textContent = "-- KB/s";
    
    progressActions.innerHTML = `<button id="cancel-btn" class="btn-cancel">Hủy tải xuống</button>`;
    
    document.getElementById("cancel-btn").onclick = cancelActiveDownload;

    const downloadUrl = `${targetServerUrl.replace(/\/$/, "")}/api/download`;
    
    const formatId = type === "subtitle" || type === "image" ? "local_file" : opt.format_id;
    const downloadPayload = {
      url: opt.url || currentTab.url,
      format_id: formatId,
      ext: opt.ext,
      quality: opt.quality || "",
      title: type === "subtitle" || type === "image" ? labelText : (activeMetadata.title || labelText),
      thumbnail: activeMetadata.thumbnail || "",
      client_id: "chrome-extension"
    };

    try {
      const response = await fetch(downloadUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(downloadPayload)
      });
      const data = await response.json();

      if (response.ok && data.status === "success") {
        activeDownloadId = data.download_id;
        connectProgressSse(activeDownloadId);
      } else {
        throw new Error(data.message || "Tạo tác vụ thất bại.");
      }
    } catch (err) {
      console.error("Start download task failed:", err);
      progressMsg.textContent = "Lỗi khởi động: " + err.message;
      progressActions.innerHTML = `<button class="btn-back">Quay lại</button>`;
      progressActions.querySelector(".btn-back").onclick = () => renderMetadataAndOptions(activeMetadata);
    }
  }

  function connectProgressSse(downloadId) {
    const sseUrl = `${targetServerUrl.replace(/\/$/, "")}/api/download/progress/${downloadId}`;
    activeSse = new EventSource(sseUrl);

    activeSse.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        
        if (data.progress !== undefined) {
          const pct = Math.round(data.progress);
          progressPercent.textContent = `${pct}%`;
          progressFill.style.width = `${pct}%`;
        }

        if (data.message) {
          progressMsg.textContent = data.message;
        }

        if (data.speed) {
          progressSpeed.textContent = data.speed;
        }

        if (data.status === "complete") {
          completeDownloadFlow(downloadId);
        } else if (data.status === "error") {
          throw new Error(data.error || "Tải xuống thất bại.");
        }
      } catch (err) {
        handleProgressError(err.message);
      }
    };

    activeSse.onerror = () => {
      // sse error event
    };
  }

  function completeDownloadFlow(downloadId) {
    if (activeSse) {
      activeSse.close();
      activeSse = null;
    }
    progressPercent.textContent = "100%";
    progressFill.style.width = "100%";
    progressMsg.textContent = "Tải về hoàn tất!";
    progressSpeed.textContent = "Xong";

    const fileUrl = `${targetServerUrl.replace(/\/$/, "")}/api/download/file/${downloadId}`;

    chrome.tabs.create({ url: fileUrl, active: false });

    progressActions.innerHTML = `
      <button id="save-btn" class="btn-save">
        ${SVGIcons.download}
        <span>Lưu lại tệp tin</span>
      </button>
      <button class="btn-back">Quay lại danh sách</button>
    `;

    document.getElementById("save-btn").onclick = () => {
      chrome.tabs.create({ url: fileUrl, active: true });
    };
    progressActions.querySelector(".btn-back").onclick = () => {
      renderMetadataAndOptions(activeMetadata);
    };
  }

  async function cancelActiveDownload() {
    if (activeSse) {
      activeSse.close();
      activeSse = null;
    }
    
    if (activeDownloadId) {
      const cancelUrl = `${targetServerUrl.replace(/\/$/, "")}/api/download/cancel/${activeDownloadId}`;
      try {
        await fetch(cancelUrl, { method: "POST" });
      } catch (e) {
        console.error("Cancel API call failed:", e);
      }
    }
    
    renderMetadataAndOptions(activeMetadata);
  }

  function handleProgressError(msg) {
    if (activeSse) {
      activeSse.close();
      activeSse = null;
    }
    progressMsg.textContent = msg || "Có lỗi xảy ra khi tải.";
    progressActions.innerHTML = `<button class="btn-back">Quay lại danh sách</button>`;
    progressActions.querySelector(".btn-back").onclick = () => {
      renderMetadataAndOptions(activeMetadata);
    };
  }

  function showErrorState(msg) {
    showSection(errorSection);
    errorMsgEl.textContent = msg;
  }

  function showSection(section) {
    [loaderSection, metaSection, progressSection, errorSection].forEach(sec => {
      sec.classList.remove("active");
    });
    section.classList.add("active");
  }

  // 4. Manual Fallback Button (Opens Main Web App page)
  fallbackBtn.addEventListener("click", () => {
    if (!currentTab || !currentTab.url) return;
    const launchUrl = `${targetServerUrl.replace(/\/$/, "")}/?url=${encodeURIComponent(currentTab.url)}`;
    chrome.tabs.create({ url: launchUrl });
  });

  // 5. Settings toggle
  settingsToggle.addEventListener("click", () => {
    settingsPanel.classList.toggle("visible");
    const arrow = settingsToggle.querySelector("svg");
    if (settingsPanel.classList.contains("visible")) {
      arrow.style.transform = "rotate(180deg)";
    } else {
      arrow.style.transform = "none";
    }
  });

  serverUrlInput.addEventListener("change", () => {
    let val = serverUrlInput.value.trim();
    if (val) {
      if (!val.startsWith("http://") && !val.startsWith("https://")) {
        val = "http://" + val;
      }
      targetServerUrl = val;
      serverUrlInput.value = val;
      localStorage.setItem("etd_server_url", val);

      // Clear localStorage cache entries on server switch
      clearAllCache();

      analyzeTabLink(); // Re-analyze using the new target server
    }
  });

  // --- Caching helpers (Time-bound localStorage cache: 1 hour expiration) ---
  function getCachedData(url) {
    const cacheKey = `etd_cache_${url}`;
    const cachedStr = localStorage.getItem(cacheKey);
    if (!cachedStr) return null;
    try {
      const cached = JSON.parse(cachedStr);
      if (Date.now() - cached.timestamp < CACHE_EXPIRATION_MS) {
        return cached.data;
      }
      // Expired cache
      localStorage.removeItem(cacheKey);
    } catch (e) {
      localStorage.removeItem(cacheKey);
    }
    return null;
  }

  function setCachedData(url, data) {
    const cacheKey = `etd_cache_${url}`;
    const payload = {
      timestamp: Date.now(),
      data: data
    };
    try {
      localStorage.setItem(cacheKey, JSON.stringify(payload));
    } catch (e) {
      console.warn("localStorage quota exceeded or failed:", e);
    }
  }

  function clearAllCache() {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith("etd_cache_")) {
        localStorage.removeItem(key);
      }
    });
  }

  function cleanupExpiredCache() {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith("etd_cache_")) {
        try {
          const cached = JSON.parse(localStorage.getItem(key));
          if (!cached.timestamp || Date.now() - cached.timestamp > CACHE_EXPIRATION_MS) {
            localStorage.removeItem(key);
          }
        } catch (e) {
          localStorage.removeItem(key);
        }
      }
    });
  }
});
