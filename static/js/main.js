// --- JavaScript Logic for EveryThingDownloader ---

document.addEventListener("DOMContentLoaded", () => {
    // Theme Toggle Logic
    const themeToggle = document.getElementById("theme-toggle");
    const currentTheme = localStorage.getItem("theme");
    
    if (currentTheme === "light") {
        document.body.classList.add("light-theme");
        document.documentElement.classList.add("light-theme");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const isLight = document.body.classList.toggle("light-theme");
            document.documentElement.classList.toggle("light-theme", isLight);
            localStorage.setItem("theme", isLight ? "light" : "dark");
        });
    }

    // Unique Client ID Management
    let clientId = localStorage.getItem("client_id");
    if (!clientId) {
        clientId = "client_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem("client_id", clientId);
    }

    // Cookies UI Elements
    const activeCookiesBadge = document.getElementById("active-cookies-badge");
    const clearCookiesBtn = document.getElementById("clear-cookies-btn");
    const cookiesSection = document.getElementById("cookies-section");
    const cookieFileInput = document.getElementById("cookie-file-input");
    const cookieDropzone = document.getElementById("cookie-dropzone");

    // Check cookie status on load
    checkCookieStatus();

    async function checkCookieStatus() {
        try {
            const res = await fetch(`/api/cookies/status/${clientId}`);
            const data = await res.json();
            if (data.has_cookies) {
                activeCookiesBadge.classList.remove("hidden");
                const textSpan = activeCookiesBadge.querySelector("span:not(.pulse-dot)");
                if (textSpan) {
                    if (data.domains && data.domains.length > 0) {
                        textSpan.textContent = `Active session cookies loaded (${data.domains.join(", ")})`;
                    } else {
                        textSpan.textContent = "Active session cookies loaded";
                    }
                }
            } else {
                activeCookiesBadge.classList.add("hidden");
            }
        } catch (err) {
            console.error("Failed to check cookie status:", err);
        }
    }

    if (clearCookiesBtn) {
        clearCookiesBtn.addEventListener("click", async () => {
            try {
                const res = await fetch(`/api/cookies/clear/${clientId}`, { method: "POST" });
                const data = await res.json();
                if (data.status === "success") {
                    checkCookieStatus();
                    cookiesSection.classList.add("hidden");
                }
            } catch (err) {
                console.error("Failed to clear cookies:", err);
            }
        });
    }

    // Cookie Dropzone Drag and Drop Handlers
    if (cookieDropzone && cookieFileInput) {
        cookieDropzone.addEventListener("click", () => {
            cookieFileInput.click();
        });

        cookieFileInput.addEventListener("change", (e) => {
            if (cookieFileInput.files.length > 0) {
                handleCookieUpload(cookieFileInput.files[0]);
            }
        });

        cookieDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            cookieDropzone.classList.add("dragover");
        });

        cookieDropzone.addEventListener("dragleave", () => {
            cookieDropzone.classList.remove("dragover");
        });

        cookieDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            cookieDropzone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                handleCookieUpload(e.dataTransfer.files[0]);
            }
        });
    }

    async function handleCookieUpload(file) {
        const nameLower = file.name.toLowerCase();
        if (!nameLower.endsWith(".txt") && !nameLower.endsWith(".json")) {
            showError("Invalid file type. Please upload a cookies.txt or cookies.json file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        formData.append("client_id", clientId);

        try {
            loaderSection.classList.remove("hidden");
            loaderText.textContent = "Uploading cookies to server...";
            cookiesSection.classList.add("hidden");

            const res = await fetch("/api/cookies/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (res.ok && data.status === "success") {
                checkCookieStatus();
                // Automatically re-run analysis now that cookies are uploaded!
                loaderText.textContent = "Cookies saved! Retrying analysis...";
                setTimeout(() => {
                    performAnalysis();
                }, 1000);
            } else {
                showError(data.message || "Failed to upload cookies file.");
                cookiesSection.classList.remove("hidden");
            }
        } catch (err) {
            console.error(err);
            showError("Error uploading cookies file to server.");
            cookiesSection.classList.remove("hidden");
        } finally {
            loaderSection.classList.add("hidden");
        }
    }

    // UI Elements
    const urlInput = document.getElementById("url-input");
    const pasteBtn = document.getElementById("paste-btn");
    const analyzeBtn = document.getElementById("analyze-btn");
    
    const loaderSection = document.getElementById("loader");
    const loaderText = document.getElementById("loader-text");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    
    const resultSection = document.getElementById("result-section");
    const videoThumbnail = document.getElementById("video-thumbnail");
    const videoTitle = document.getElementById("video-title");
    const videoUploader = document.getElementById("video-uploader");
    const videoDuration = document.getElementById("video-duration-badge");
    const mediaBadge = document.getElementById("media-badge");
    const optionsContainer = document.getElementById("options-container");
    
    const downloadProgress = document.getElementById("download-progress");
    const progressPercent = document.getElementById("progress-percent");
    const progressBarFill = document.getElementById("progress-fill");
    const downloadStatusTitle = document.getElementById("download-status-title");
    const downloadStatusMessage = document.getElementById("download-status-message");
    const downloadFormatLabel = document.getElementById("download-format-label");

    // Global state
    let activeUrl = "";
    let pollingInterval = null;
    let extractedImages = [];

    // Preview Modal DOM Elements
    const previewModal = document.getElementById("preview-modal");
    const previewModalCloseBtn = document.getElementById("preview-modal-close-btn");
    const previewTitle = document.getElementById("preview-title");
    const previewLoader = document.getElementById("preview-loader");
    const previewLoaderText = document.getElementById("preview-loader-text");
    const previewVideoContainer = document.getElementById("preview-video-container");
    const previewVideoPlayer = document.getElementById("preview-video-player");
    const previewAudioContainer = document.getElementById("preview-audio-container");
    const previewAudioPlayer = document.getElementById("preview-audio-player");
    const previewImageContainer = document.getElementById("preview-image-container");
    const previewImageElement = document.getElementById("preview-image-element");
    const previewSubtitleContainer = document.getElementById("preview-subtitle-container");
    const previewSubLang = document.getElementById("preview-sub-lang");
    const previewSubText = document.getElementById("preview-sub-text");
    const btnCopySub = document.getElementById("btn-copy-sub");
    const previewMetaInfo = document.getElementById("preview-meta-info");
    const previewDownloadBtn = document.getElementById("preview-download-btn");
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomOut = document.getElementById("btn-zoom-out");
    const btnRotate = document.getElementById("btn-rotate");

    // Preview state variables
    let previewZoomLevel = 1;
    let previewRotation = 0;
    let previewActiveDownloadId = null;
    let previewActiveUrl = "";
    let previewActiveExt = "";
    let previewActiveFilename = "";

    // Close preview modal behavior
    if (previewModal && previewModalCloseBtn) {
        const closePreviewModal = () => {
            previewModal.classList.add("hidden");
            document.body.classList.remove("modal-open");
            
            // Stop player playback on close
            if (previewVideoPlayer) {
                previewVideoPlayer.pause();
                previewVideoPlayer.src = "";
            }
            if (previewAudioPlayer) {
                previewAudioPlayer.pause();
                previewAudioPlayer.src = "";
            }
        };

        previewModalCloseBtn.onclick = closePreviewModal;

        previewModal.onclick = (e) => {
            if (e.target === previewModal) {
                closePreviewModal();
            }
        };

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !previewModal.classList.contains("hidden")) {
                closePreviewModal();
            }
        });
    }

    // Image preview transform controls
    function updateImageTransform() {
        if (previewImageElement) {
            previewImageElement.style.transform = `scale(${previewZoomLevel}) rotate(${previewRotation}deg)`;
        }
    }

    if (btnZoomIn && previewImageElement) {
        btnZoomIn.onclick = () => {
            previewZoomLevel = Math.min(3, previewZoomLevel + 0.2);
            updateImageTransform();
        };
    }
    if (btnZoomOut && previewImageElement) {
        btnZoomOut.onclick = () => {
            previewZoomLevel = Math.max(0.5, previewZoomLevel - 0.2);
            updateImageTransform();
        };
    }
    if (btnRotate && previewImageElement) {
        btnRotate.onclick = () => {
            previewRotation = (previewRotation + 90) % 360;
            updateImageTransform();
        };
    }

    // Copy subtitles clipboard helper
    if (btnCopySub && previewSubText) {
        btnCopySub.onclick = () => {
            navigator.clipboard.writeText(previewSubText.textContent).then(() => {
                const originalText = btnCopySub.textContent;
                btnCopySub.textContent = "Copied!";
                setTimeout(() => {
                    btnCopySub.textContent = originalText;
                }, 1500);
            });
        };
    }

    // Preview modal footer download trigger
    if (previewDownloadBtn) {
        previewDownloadBtn.onclick = () => {
            if (previewActiveDownloadId) {
                window.location.href = `/api/download/file/${previewActiveDownloadId}`;
            } else if (previewActiveUrl) {
                const a = document.createElement("a");
                a.href = previewActiveUrl;
                a.download = previewActiveFilename || "download";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        };
    }

    // 1. Paste Button Clipboard Interaction
    pasteBtn.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text;
                urlInput.focus();
                triggerGlowEffect();
            }
        } catch (err) {
            console.log("Unable to read from clipboard via API. Fallback to manual pasting.");
        }
    });

    // Style helper for input glow
    function triggerGlowEffect() {
        const container = urlInput.parentElement;
        container.style.borderColor = "var(--cyan)";
        container.style.boxShadow = "0 0 15px rgba(99, 179, 237, 0.4)";
        setTimeout(() => {
            container.style.borderColor = "";
            container.style.boxShadow = "";
        }, 1000);
    }

    // 2. Link Analysis
    analyzeBtn.addEventListener("click", performAnalysis);
    urlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            performAnalysis();
        }
    });

    function isValidUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?([a-z0-9-]+\.)?(youtube\.com|youtu\.be|youtubekids\.com|youtube-nocookie\.com)/i;
        const facebookRegex = /^(https?:\/\/)?([a-z0-9-]+\.)?(facebook\.com|fb\.com|fb\.watch|fb\.gg|messenger\.com)/i;
        const instagramRegex = /^(https?:\/\/)?([a-z0-9-]+\.)?(instagram\.com|instagr\.am)/i;
        const threadsRegex = /^(https?:\/\/)?([a-z0-9-]+\.)?(threads\.net|threads\.com)/i;
        return youtubeRegex.test(url) || facebookRegex.test(url) || instagramRegex.test(url) || threadsRegex.test(url);
    }

    const themeColors = {
        "youtube": {
            cyan: "#ff0000", purple: "#ff4d4d",
            cyanRgb: "255, 0, 0", purpleRgb: "255, 77, 77"
        },
        "youtube-kids": {
            cyan: "#ffbb00", purple: "#00ff66",
            cyanRgb: "255, 187, 0", purpleRgb: "0, 255, 102"
        },
        "youtube-music": {
            cyan: "#00ffd0", purple: "#0088ff",
            cyanRgb: "0, 255, 208", purpleRgb: "0, 136, 255"
        },
        "youtube-shorts": {
            cyan: "#ff3e3e", purple: "#ff8a00",
            cyanRgb: "255, 62, 62", purpleRgb: "255, 138, 0"
        },
        "youtube-live": {
            cyan: "#ff003c", purple: "#ff00a0",
            cyanRgb: "255, 0, 60", purpleRgb: "255, 0, 160"
        },
        "youtube-clip": {
            cyan: "#e62117", purple: "#ff6e6e",
            cyanRgb: "230, 33, 23", purpleRgb: "255, 110, 110"
        },
        "facebook": {
            cyan: "#1877f2", purple: "#00c6ff",
            cyanRgb: "24, 119, 242", purpleRgb: "0, 198, 255"
        },
        "facebook-reel": {
            cyan: "#2ecc71", purple: "#00e5ff",
            cyanRgb: "46, 204, 113", purpleRgb: "0, 229, 255"
        },
        "facebook-group": {
            cyan: "#20b2aa", purple: "#48d1cc",
            cyanRgb: "32, 178, 170", purpleRgb: "72, 209, 204"
        },
        "facebook-live": {
            cyan: "#ff4500", purple: "#ff8c00",
            cyanRgb: "255, 69, 0", purpleRgb: "255, 140, 0"
        },
        "facebook-watch": {
            cyan: "#4267b2", purple: "#898f9c",
            cyanRgb: "66, 103, 178", purpleRgb: "137, 143, 156"
        },
        "facebook-story": {
            cyan: "#7b1fa2", purple: "#e91e63",
            cyanRgb: "123, 31, 162", purpleRgb: "233, 30, 99"
        },
        "facebook-gaming": {
            cyan: "#00bcd4", purple: "#3f51b5",
            cyanRgb: "0, 188, 212", purpleRgb: "63, 81, 181"
        },
        "instagram": {
            cyan: "#e1306c", purple: "#f77737",
            cyanRgb: "225, 48, 108", purpleRgb: "247, 119, 55"
        },
        "instagram-reel": {
            cyan: "#ff8a00", purple: "#da00ff",
            cyanRgb: "255, 138, 0", purpleRgb: "218, 0, 255"
        },
        "instagram-story": {
            cyan: "#8a3ab9", purple: "#e95950",
            cyanRgb: "138, 58, 185", purpleRgb: "233, 89, 80"
        },
        "instagram-tv": {
            cyan: "#5851db", purple: "#c13584",
            cyanRgb: "88, 81, 219", purpleRgb: "193, 53, 132"
        },
        "instagram-post": {
            cyan: "#fd1d1d", purple: "#fccc63",
            cyanRgb: "253, 29, 29", purpleRgb: "252, 204, 99"
        },
        "threads": {
            cyan: "#a855f7", purple: "#ec4899",
            cyanRgb: "168, 85, 247", purpleRgb: "236, 72, 153"
        },
        "tiktok": {
            cyan: "#00f2fe", purple: "#fe0979",
            cyanRgb: "0, 242, 254", purpleRgb: "254, 9, 121"
        }
    };

    function setPlatformTheme(platformClass) {
        // Remove existing theme classes
        const classes = Array.from(document.body.classList);
        classes.forEach(c => {
            if (c.startsWith("theme-")) {
                document.body.classList.remove(c);
            }
        });
        
        // Add new theme class and dynamic styles if present
        if (platformClass) {
            document.body.classList.add(`theme-${platformClass}`);
            
            const colors = themeColors[platformClass];
            if (colors) {
                document.documentElement.style.setProperty('--cyan', colors.cyan);
                document.documentElement.style.setProperty('--purple', colors.purple);
                document.documentElement.style.setProperty('--cyan-rgb', colors.cyanRgb);
                document.documentElement.style.setProperty('--purple-rgb', colors.purpleRgb);
            }
        } else {
            // Reset to defaults
            document.documentElement.style.removeProperty('--cyan');
            document.documentElement.style.removeProperty('--purple');
            document.documentElement.style.removeProperty('--cyan-rgb');
            document.documentElement.style.removeProperty('--purple-rgb');
        }
    }

    async function performAnalysis() {
        const url = urlInput.value.trim();
        
        if (!url) {
            showError("Please enter a link first.");
            return;
        }

        if (!isValidUrl(url)) {
            showError("Invalid URL. Please make sure it is a valid YouTube, Facebook, Instagram, or Threads link.");
            return;
        }

        // Reset UI States
        setPlatformTheme(null);
        errorCard.classList.add("hidden");
        resultSection.classList.add("hidden");
        downloadProgress.classList.add("hidden");
        cookiesSection.classList.add("hidden");
        
        // Show Loading
        loaderSection.classList.remove("hidden");
        loaderText.textContent = "Connecting to interface & extracting stream protocols...";
        analyzeBtn.disabled = true;
        analyzeBtn.style.opacity = "0.7";

        try {
            const response = await fetch("/api/info", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ url: url, client_id: clientId })
            });

            const data = await response.json();

            if (response.ok && data.status === "success") {
                activeUrl = url;
                setPlatformTheme(data.platform_class);
                displayMetadata(data);
            } else {
                setPlatformTheme(null);
                showError(data.message || "Unable to extract media information from this URL.");
                const msg = (data.message || "").toLowerCase();
                const authKeywords = ["private", "log in", "login", "sign in", "signin", "invalid", "cookie", "confirm", "subscriber", "membership", "member"];
                if (authKeywords.some(keyword => msg.includes(keyword))) {
                    cookiesSection.classList.remove("hidden");
                }
            }
        } catch (err) {
            console.error(err);
            setPlatformTheme(null);
            showError("Connection lost. Unable to contact local Python downloader server.");
        } finally {
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
        }
    }

    // Display parsed metadata
    function displayMetadata(data) {
        // Thumbnail & Title
        videoThumbnail.src = data.thumbnail || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600";
        videoTitle.textContent = data.title;
        videoUploader.textContent = data.uploader;
        videoDuration.textContent = data.duration;

        // Badges
        if (mediaBadge) {
            mediaBadge.textContent = data.platform_label || "Video";
            mediaBadge.className = "tag";
            mediaBadge.classList.add(`tag-${data.platform_class || 'default'}`);
        }

        // Rich Stats
        const viewsEl = document.getElementById("video-views");
        const likesEl = document.getElementById("video-likes");
        const dateEl = document.getElementById("video-date");
        const categoryEl = document.getElementById("video-category");
        
        if (viewsEl) viewsEl.textContent = data.views || "Unknown";
        if (likesEl) likesEl.textContent = data.likes || "Unknown";
        if (dateEl) dateEl.textContent = data.upload_date || "Unknown";
        if (categoryEl) {
            if (data.category) {
                categoryEl.textContent = data.category;
                categoryEl.classList.remove("hidden");
            } else {
                categoryEl.classList.add("hidden");
            }
        }

        // Tags
        const tagsContainer = document.getElementById("video-tags-container");
        if (tagsContainer) {
            tagsContainer.innerHTML = "";
            if (data.tags && data.tags.length > 0) {
                data.tags.forEach(tag => {
                    const tagPill = document.createElement("span");
                    tagPill.className = "tag-pill";
                    tagPill.textContent = `#${tag}`;
                    tagsContainer.appendChild(tagPill);
                });
            }
        }

        // Description Modal Logic
        const descToggleBtn = document.getElementById("desc-toggle-btn");
        const descModal = document.getElementById("desc-modal");
        const modalDescContent = document.getElementById("modal-desc-content");
        const modalCloseBtn = document.getElementById("modal-close-btn");

        if (descToggleBtn && descModal && modalDescContent && modalCloseBtn) {
            modalDescContent.textContent = data.description || "No description available.";
            
            descToggleBtn.onclick = () => {
                descModal.classList.remove("hidden");
                document.body.classList.add("modal-open");
            };

            const closeModal = () => {
                descModal.classList.add("hidden");
                document.body.classList.remove("modal-open");
            };

            modalCloseBtn.onclick = closeModal;

            // Close on click outside card
            descModal.onclick = (e) => {
                if (e.target === descModal) {
                    closeModal();
                }
            };

            // Close on ESC key
            const escHandler = (e) => {
                if (e.key === "Escape" && !descModal.classList.contains("hidden")) {
                    closeModal();
                }
            };
            document.addEventListener("keydown", escHandler);
        }

        // Images Modal Logic
        extractedImages = data.images || [];
        const imagesToggleBtn = document.getElementById("images-toggle-btn");
        const imagesModal = document.getElementById("images-modal");
        const imagesModalCloseBtn = document.getElementById("images-modal-close-btn");
        const modalImagesGrid = document.getElementById("modal-images-grid");
        const selectAllCheckbox = document.getElementById("images-select-all");
        const downloadSelectedBtn = document.getElementById("images-download-selected");

        if (imagesToggleBtn) {
            if (extractedImages.length > 0) {
                imagesToggleBtn.classList.remove("hidden");
            } else {
                imagesToggleBtn.classList.add("hidden");
            }
        }

        if (imagesToggleBtn && imagesModal && imagesModalCloseBtn && modalImagesGrid) {
            imagesToggleBtn.onclick = () => {
                renderImagesGrid();
                imagesModal.classList.remove("hidden");
                document.body.classList.add("modal-open");
            };

            const closeImagesModal = () => {
                imagesModal.classList.add("hidden");
                document.body.classList.remove("modal-open");
            };

            imagesModalCloseBtn.onclick = closeImagesModal;

            // Close on click outside card
            imagesModal.onclick = (e) => {
                if (e.target === imagesModal) {
                    closeImagesModal();
                }
            };

            // Close on ESC key
            const escImagesHandler = (e) => {
                if (e.key === "Escape" && !imagesModal.classList.contains("hidden")) {
                    closeImagesModal();
                }
            };
            document.addEventListener("keydown", escImagesHandler);
        }

        function renderImagesGrid() {
            modalImagesGrid.innerHTML = "";
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
            
            extractedImages.forEach((img, idx) => {
                const card = document.createElement("div");
                card.className = "image-card";
                
                let imgLabel, imgUrl, imgExt;
                if (typeof img === "string") {
                    imgUrl = img;
                    imgLabel = `Photo ${idx + 1}`;
                    imgExt = "jpg";
                } else if (img && typeof img === "object") {
                    imgUrl = img.url || "";
                    imgLabel = img.label || `Photo ${idx + 1}`;
                    imgExt = img.ext || "jpg";
                } else {
                    return; // Skip invalid entries
                }
                
                // Extract resolution label from name if present
                const resMatch = imgLabel.match(/\((\d+x\d+)\)/);
                const resLabel = resMatch ? resMatch[1] : (imgExt ? imgExt.toUpperCase() : "Image");
                const cleanLabel = imgLabel.replace(/\s*\(\d+x\d+\)/, "");
                
                const safeTitle = data.title || "image";
                const cleanTitle = safeTitle.replace(/[\\/*?:"<>|]/g, "").substring(0, 50).trim();
                const filename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${imgExt}`;
                const proxyDownloadUrl = `/api/download/image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(filename)}&client_id=${encodeURIComponent(clientId)}`;

                card.innerHTML = `
                    <div class="image-checkbox-container">
                        <input type="checkbox" class="image-select-check custom-checkbox" data-url="${imgUrl}" data-label="${cleanLabel}" data-ext="${imgExt}" data-filename="${filename}">
                    </div>
                    <div class="image-preview-wrap">
                        <img src="${imgUrl}" alt="${imgLabel}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600'">
                    </div>
                    <div class="image-info-bar">
                        <div class="image-label" title="${imgLabel}">${cleanLabel}</div>
                        <div class="image-actions">
                            <span class="image-res">${resLabel}</span>
                            <div class="image-card-buttons-group">
                                <button class="image-card-preview-btn" title="Preview Image" type="button">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                    <span>Preview</span>
                                </button>
                                <a href="${proxyDownloadUrl}" class="image-card-download-btn" title="Download Image" target="_blank">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                    <span>Get</span>
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                
                // Bind preview button click
                const prevBtn = card.querySelector(".image-card-preview-btn");
                prevBtn.onclick = (e) => {
                    e.stopPropagation(); // Prevent toggling checkbox
                    triggerPreview(prevBtn, "image_preview", "jpg", cleanLabel, "", img.url);
                };
                
                // Add click listener on preview to toggle checkbox
                const preview = card.querySelector(".image-preview-wrap");
                const checkbox = card.querySelector(".image-select-check");
                preview.onclick = (e) => {
                    if (e.target !== checkbox) {
                        checkbox.checked = !checkbox.checked;
                        updateSelectAllState();
                    }
                };
                checkbox.onchange = () => {
                    updateSelectAllState();
                };

                modalImagesGrid.appendChild(card);
            });
        }

        function updateSelectAllState() {
            if (!selectAllCheckbox) return;
            const checkboxes = modalImagesGrid.querySelectorAll(".image-select-check");
            const checked = modalImagesGrid.querySelectorAll(".image-select-check:checked");
            
            if (checkboxes.length > 0 && checked.length === checkboxes.length) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else if (checked.length > 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
        }

        if (selectAllCheckbox) {
            selectAllCheckbox.onclick = () => {
                const checkboxes = modalImagesGrid.querySelectorAll(".image-select-check");
                checkboxes.forEach(cb => {
                    cb.checked = selectAllCheckbox.checked;
                });
            };
        }

        if (downloadSelectedBtn) {
            downloadSelectedBtn.onclick = async () => {
                const checkedCheckboxes = modalImagesGrid.querySelectorAll(".image-select-check:checked");
                if (checkedCheckboxes.length === 0) {
                    alert("Please select at least one image to download.");
                    return;
                }
                
                const selectedItems = [];
                checkedCheckboxes.forEach(cb => {
                    selectedItems.push({
                        url: cb.getAttribute("data-url"),
                        label: cb.getAttribute("data-label"),
                        ext: cb.getAttribute("data-ext") || "jpg",
                        filename: cb.getAttribute("data-filename")
                    });
                });
                
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                
                if (isMobile) {
                    // Mobile flow: Download sequentially with a delay to prevent browser block
                    downloadSelectedBtn.disabled = true;
                    const originalText = downloadSelectedBtn.innerHTML;
                    
                    for (let i = 0; i < selectedItems.length; i++) {
                        const item = selectedItems[i];
                        downloadSelectedBtn.innerHTML = `<span>Downloading ${i+1}/${selectedItems.length}...</span>`;
                        
                        const proxyUrl = `/api/download/image?url=${encodeURIComponent(item.url)}&filename=${encodeURIComponent(item.filename)}&client_id=${encodeURIComponent(clientId)}`;
                        const link = document.createElement("a");
                        link.href = proxyUrl;
                        link.target = "_blank";
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        // Wait 600ms before next download
                        await new Promise(resolve => setTimeout(resolve, 600));
                    }
                    
                    downloadSelectedBtn.disabled = false;
                    downloadSelectedBtn.innerHTML = originalText;
                } else {
                    // Desktop flow: Download packed ZIP file
                    try {
                        downloadSelectedBtn.disabled = true;
                        const originalText = downloadSelectedBtn.innerHTML;
                        downloadSelectedBtn.innerHTML = `<span>Creating ZIP...</span>`;
                        
                        const response = await fetch("/api/download/images/zip", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                urls: selectedItems.map(item => ({ url: item.url, label: item.label, ext: item.ext })),
                                title: data.title ? data.title.replace(/[\\/*?:"<>|]/g, "").substring(0, 50).trim() : "images",
                                client_id: clientId
                            })
                        });
                        
                        if (!response.ok) {
                            throw new Error("Server error creating ZIP file.");
                        }
                        
                        const blob = await response.blob();
                        const blobUrl = URL.createObjectURL(blob);
                        const downloadAnchor = document.createElement("a");
                        downloadAnchor.href = blobUrl;
                        downloadAnchor.download = `${data.title ? data.title.replace(/[\\/*?:"<>|]/g, "").substring(0, 50).trim() : "images"}_images.zip`;
                        document.body.appendChild(downloadAnchor);
                        downloadAnchor.click();
                        document.body.removeChild(downloadAnchor);
                        URL.revokeObjectURL(blobUrl);
                        
                        downloadSelectedBtn.disabled = false;
                        downloadSelectedBtn.innerHTML = originalText;
                    } catch (err) {
                        alert("Failed to download images: " + err.message);
                        downloadSelectedBtn.disabled = false;
                        downloadSelectedBtn.innerHTML = `<span>Download Selected</span>`;
                    }
                }
            };
        }

        // Render options list
        optionsContainer.innerHTML = "";
        
        const videoSvg = `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`;
        const audioSvg = `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;
        const downloadSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;

        // Render Video options if present
        if (data.video_options && data.video_options.length > 0) {
            const videos = data.video_options.filter(opt => opt.ext !== "jpg");
            const photos = data.video_options.filter(opt => opt.ext === "jpg");

            if (videos.length > 0) {
                const videoGroupLabel = document.createElement("div");
                videoGroupLabel.className = "format-group-label";
                videoGroupLabel.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                    <span>Video Options</span>
                `;
                optionsContainer.appendChild(videoGroupLabel);

                videos.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row video-row";
                    
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            ${videoSvg}
                            <span class="format-name">${option.label}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <span>Preview</span>
                            </button>
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    optionsContainer.appendChild(row);
                });
            }

            if (photos.length > 0) {
                const photoGroupLabel = document.createElement("div");
                photoGroupLabel.className = "format-group-label";
                photoGroupLabel.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                    <span>Photo Options</span>
                `;
                optionsContainer.appendChild(photoGroupLabel);

                photos.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row photo-row";
                    
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                            <span class="format-name">${option.label}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <span>Preview</span>
                            </button>
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    optionsContainer.appendChild(row);
                });
            }
        }

        // Render Audio options if present
        if (data.audio_options && data.audio_options.length > 0) {
            const audioGroupLabel = document.createElement("div");
            audioGroupLabel.className = "format-group-label";
            audioGroupLabel.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                <span>Audio Options</span>
            `;
            optionsContainer.appendChild(audioGroupLabel);

            data.audio_options.forEach(option => {
                const row = document.createElement("div");
                row.className = "format-row audio-row";
                
                const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                row.innerHTML = `
                    <div class="format-left">
                        ${audioSvg}
                        <span class="format-name">${option.label}</span>
                        ${sizeBadge}
                    </div>
                    <div class="format-actions">
                        <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                        <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                            ${downloadSvg}
                            <span>Get</span>
                        </button>
                    </div>
                `;
                optionsContainer.appendChild(row);
            });
        }

        // Render Subtitle options if present
        if (data.subtitles && data.subtitles.length > 0) {
            const subGroupLabel = document.createElement("div");
            subGroupLabel.className = "format-group-label";
            subGroupLabel.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>Subtitles Options</span>
            `;
            optionsContainer.appendChild(subGroupLabel);

            data.subtitles.forEach(option => {
                const row = document.createElement("div");
                row.className = "format-row subtitle-row";
                
                const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                row.innerHTML = `
                    <div class="format-left">
                        <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan);"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <span class="format-name">${option.name}</span>
                        ${sizeBadge}
                    </div>
                    <div class="format-actions">
                        <button class="btn-preview" data-id="${option.lang_code}" data-ext="vtt" data-label="Subtitles - ${option.name}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                        <button class="btn-get" data-id="${option.lang_code}" data-ext="vtt" data-label="Subtitles - ${option.name}">
                            ${downloadSvg}
                            <span>Get VTT</span>
                        </button>
                    </div>
                `;
                optionsContainer.appendChild(row);
            });
        }

        // Render photo options from data.images if no video or audio options are available at all
        const hasVideoOptions = data.video_options && data.video_options.length > 0;
        const hasAudioOptions = data.audio_options && data.audio_options.length > 0;
        
        if (!hasVideoOptions && !hasAudioOptions && data.images && data.images.length > 0) {
            const photoGroupLabel = document.createElement("div");
            photoGroupLabel.className = "format-group-label";
            photoGroupLabel.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                <span>Photo Options</span>
            `;
            optionsContainer.appendChild(photoGroupLabel);

            data.images.forEach((img, idx) => {
                const row = document.createElement("div");
                row.className = "format-row photo-row";
                
                let imgLabel, imgUrl, imgExt;
                if (typeof img === "string") {
                    imgUrl = img;
                    imgLabel = `Photo ${idx + 1}`;
                    imgExt = "jpg";
                } else if (img && typeof img === "object") {
                    imgUrl = img.url || "";
                    imgLabel = img.label || `Photo ${idx + 1}`;
                    imgExt = img.ext || "jpg";
                } else {
                    return; // Skip invalid entries
                }
                
                const cleanLabel = imgLabel.replace(/\s*\(\d+x\d+\)/, "");
                const safeTitle = data.title || "image";
                const cleanTitle = safeTitle.replace(/[\\/*?:"<>|]/g, "").substring(0, 50).trim();
                const filename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${imgExt}`;
                const proxyDownloadUrl = `/api/download/image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(filename)}&client_id=${encodeURIComponent(clientId)}`;

                row.innerHTML = `
                    <div class="format-left">
                        <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                        <span class="format-name">${imgLabel}</span>
                    </div>
                    <div class="format-actions">
                        <button class="btn-preview" data-id="image_preview" data-ext="${imgExt}" data-label="${cleanLabel}" data-quality="" data-url="${imgUrl}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                        <button class="btn-get" data-id="image_download" data-ext="${imgExt}" data-label="${cleanLabel}" data-quality="" data-url="${proxyDownloadUrl}">
                            ${downloadSvg}
                            <span>Get</span>
                        </button>
                    </div>
                `;
                optionsContainer.appendChild(row);
            });
        }

        // Bind download actions
        const downloadButtons = optionsContainer.querySelectorAll(".btn-get");
        downloadButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const formatId = btn.getAttribute("data-id");
                const ext = btn.getAttribute("data-ext");
                const label = btn.getAttribute("data-label");
                const quality = btn.getAttribute("data-quality");
                const customUrl = btn.getAttribute("data-url");
                if (formatId === "image_download") {
                    window.open(customUrl, "_blank");
                    return;
                }
                triggerDownload(btn, formatId, ext, label, quality, customUrl);
            });
        });

        // Bind preview actions
        const previewButtons = optionsContainer.querySelectorAll(".btn-preview");
        previewButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const formatId = btn.getAttribute("data-id");
                const ext = btn.getAttribute("data-ext");
                const label = btn.getAttribute("data-label");
                const quality = btn.getAttribute("data-quality");
                const customUrl = btn.getAttribute("data-url");
                triggerPreview(btn, formatId, ext, label, quality, customUrl);
            });
        });

        // Show result section
        resultSection.classList.remove("hidden");
        resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 3. Download Execution via Asynchronous Server Task & Polling
    async function triggerDownload(btn, formatId, ext, label, quality, customUrl) {
        // Reset previous polling if running
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        // Clear status states in progress panel
        downloadProgress.className = "progress-panel";
        downloadProgress.classList.remove("hidden");
        
        progressBarFill.classList.add("striped");
        progressBarFill.style.width = "5%";
        progressPercent.textContent = "0%";
        
        downloadStatusTitle.textContent = "Initializing queue...";
        downloadStatusMessage.textContent = "Adding download request to local Python server...";
        downloadFormatLabel.textContent = label;
        
        downloadProgress.scrollIntoView({ behavior: "smooth", block: "nearest" });

        // Disable input panel to prevent interruptions
        analyzeBtn.disabled = true;
        urlInput.disabled = true;

        // Disable all get buttons and highlight active downloading row
        const allButtons = optionsContainer.querySelectorAll(".btn-get");
        allButtons.forEach(b => b.disabled = true);

        const allRows = optionsContainer.querySelectorAll(".format-row");
        allRows.forEach(r => r.classList.remove("is-downloading"));
        
        const activeRow = btn.closest(".format-row");
        if (activeRow) {
            activeRow.classList.add("is-downloading");
        }

        try {
            // Step A: Request the server to start the download task in the background
            const response = await fetch("/api/download", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    url: customUrl || activeUrl,
                    format_id: formatId,
                    ext: ext,
                    quality: quality,
                    title: videoTitle.textContent,
                    client_id: clientId
                })
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Failed to enqueue download task on server.");
            }

            const downloadId = data.download_id;
            console.log(`Download enqueued. ID: ${downloadId}`);

            // Step B: Set up polling to fetch status progress
            pollingInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`/api/download/status/${downloadId}`);
                    if (!statusRes.ok) {
                        throw new Error("Unable to fetch download status from server.");
                    }

                    const statusData = await statusRes.json();
                    
                    if (statusData.status === "pending") {
                        progressBarFill.classList.add("striped");
                        progressBarFill.style.width = "5%";
                        progressPercent.textContent = "0%";
                        downloadStatusTitle.textContent = "Queued...";
                        downloadStatusMessage.textContent = statusData.message || "Waiting in line...";
                    }
                    else if (statusData.status === "downloading") {
                        progressBarFill.classList.remove("striped");
                        progressBarFill.style.width = `${statusData.progress}%`;
                        progressPercent.textContent = `${statusData.progress}%`;
                        const platform = mediaBadge ? mediaBadge.textContent : "YouTube";
                        downloadStatusTitle.textContent = `Downloading from ${platform}...`;
                        downloadStatusMessage.textContent = statusData.message;
                    } 
                    else if (statusData.status === "merging" || statusData.status === "processing") {
                        progressBarFill.classList.add("striped");
                        progressBarFill.style.width = `${statusData.progress}%`;
                        progressPercent.textContent = `${statusData.progress}%`;
                        downloadStatusTitle.textContent = statusData.status === "merging" ? "Merging streams..." : "Processing audio...";
                        downloadStatusMessage.textContent = statusData.message;
                    } 
                    else if (statusData.status === "complete") {
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                        
                        progressBarFill.classList.remove("striped");
                        progressBarFill.style.width = "100%";
                        progressPercent.textContent = "Done!";
                        
                        downloadProgress.classList.add("state-complete");
                        downloadStatusTitle.textContent = "Download complete!";
                        downloadStatusMessage.innerHTML = `File downloaded successfully. <a href="/api/download/file/${downloadId}" class="download-again-btn" target="_blank" style="color: var(--cyan); text-decoration: underline; font-weight: 500; margin-left: 5px;">Click here</a> if the download did not start automatically.`;

                        // Re-enable inputs & restore format buttons
                        analyzeBtn.disabled = false;
                        urlInput.disabled = false;
                        allButtons.forEach(b => b.disabled = false);
                        if (activeRow) {
                            activeRow.classList.remove("is-downloading");
                        }

                        // Trigger file download
                        const downloadAnchor = document.createElement("a");
                        downloadAnchor.href = `/api/download/file/${downloadId}`;
                        document.body.appendChild(downloadAnchor);
                        downloadAnchor.click();
                        downloadAnchor.remove();
                    } 
                    else if (statusData.status === "error") {
                        throw new Error(statusData.error || statusData.message || "An error occurred on the downloader backend.");
                    }
                } catch (pollErr) {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    handleDownloadFailure(pollErr.message, activeRow, allButtons);
                }
            }, 1000); // Poll every second

        } catch (err) {
            handleDownloadFailure(err.message, activeRow, allButtons);
        }
    }

    function handleDownloadFailure(errorMessageText, activeRow, allButtons) {
        progressBarFill.classList.remove("striped");
        progressBarFill.style.width = "0%";
        progressPercent.textContent = "Error";
        
        downloadProgress.classList.add("state-error");
        downloadStatusTitle.textContent = "Download failed";
        downloadStatusMessage.textContent = errorMessageText || "An error occurred while initializing download queue.";
        
        analyzeBtn.disabled = false;
        urlInput.disabled = false;
        allButtons.forEach(b => b.disabled = false);
        if (activeRow) {
            activeRow.classList.remove("is-downloading");
        }
    }

    // Error helper for analysis
    function showError(message) {
        errorMessage.textContent = message;
        errorCard.classList.remove("hidden");
        errorCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // Dynamic Media Preview Orchestrator
    async function triggerPreview(btn, formatId, ext, label, quality, customUrl) {
        if (!previewModal) return;

        // Reset zoom & rotations
        previewZoomLevel = 1;
        previewRotation = 0;
        updateImageTransform();
        previewActiveDownloadId = null;
        previewActiveUrl = "";
        previewActiveExt = ext;
        previewActiveFilename = label;

        // Open modal & lock background scrolling
        previewModal.classList.remove("hidden");
        document.body.classList.add("modal-open");

        // Reset views
        previewVideoContainer.classList.add("hidden");
        previewAudioContainer.classList.add("hidden");
        previewImageContainer.classList.add("hidden");
        previewSubtitleContainer.classList.add("hidden");
        previewLoader.classList.remove("hidden");
        previewLoaderText.textContent = "Connecting to source & preparing stream...";
        
        previewTitle.textContent = label;
        previewMetaInfo.textContent = `Type: ${ext.toUpperCase()} ${quality ? `| Quality: ${quality}` : ""}`;

        // Stop current playbacks
        if (previewVideoPlayer) {
            previewVideoPlayer.pause();
            previewVideoPlayer.src = "";
        }
        if (previewAudioPlayer) {
            previewAudioPlayer.pause();
            previewAudioPlayer.src = "";
        }

        // Image Preview Flow
        if (ext === "jpg" || ext === "png" || ext === "jpeg" || formatId === "image_preview") {
            const finalUrl = formatId === "image_preview" 
                ? `/api/download/image?url=${encodeURIComponent(customUrl)}&client_id=${encodeURIComponent(clientId)}` 
                : customUrl;
            
            previewActiveUrl = finalUrl;
            previewActiveFilename = label;
            
            if (previewImageElement) {
                previewImageElement.src = finalUrl;
                previewImageElement.onload = () => {
                    previewLoader.classList.add("hidden");
                    previewImageContainer.classList.remove("hidden");
                };
                previewImageElement.onerror = () => {
                    previewLoaderText.textContent = "Failed to load image preview.";
                };
            }
            return;
        }

        // Audio, Video, Subtitle Preview Flow (Downloads to server & streams)
        try {
            const payload = {
                url: customUrl || activeUrl,
                format_id: formatId,
                ext: ext,
                quality: quality || "192",
                title: label,
                client_id: clientId
            };

            const response = await fetch("/api/download", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || data.status === "error") {
                previewLoaderText.textContent = `Error: ${data.message || "Failed to start preview task."}`;
                return;
            }

            const downloadId = data.download_id;
            previewActiveDownloadId = downloadId;

            // Poll the status progress
            const pollInterval = setInterval(async () => {
                if (previewModal.classList.contains("hidden")) {
                    clearInterval(pollInterval);
                    return;
                }

                try {
                    const statusRes = await fetch(`/api/download/status/${downloadId}`);
                    const statusData = await statusRes.json();

                    if (statusData.status === "complete") {
                        clearInterval(pollInterval);
                        previewLoader.classList.add("hidden");

                        const previewStreamUrl = `/api/download/file/${downloadId}?preview=true`;

                        if (ext === "mp3" || ext === "m4a") {
                            if (previewAudioPlayer) {
                                previewAudioPlayer.src = previewStreamUrl;
                                previewAudioPlayer.load();
                                previewAudioContainer.classList.remove("hidden");
                                previewAudioPlayer.play().catch(e => console.log("Playback blocked"));
                            }
                        } else if (ext === "vtt") {
                            if (previewSubText) {
                                previewSubLang.textContent = label;
                                previewSubtitleContainer.classList.remove("hidden");
                                previewSubText.textContent = "Loading subtitle text...";
                                
                                const textRes = await fetch(previewStreamUrl);
                                const text = await textRes.text();
                                previewSubText.textContent = text || "No content found in subtitle file.";
                            }
                        } else {
                            if (previewVideoPlayer) {
                                previewVideoPlayer.src = previewStreamUrl;
                                previewVideoPlayer.load();
                                previewVideoContainer.classList.remove("hidden");
                                previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                            }
                        }
                    } else if (statusData.status === "error") {
                        clearInterval(pollInterval);
                        previewLoaderText.textContent = `Preview failed: ${statusData.error || "Unknown server error."}`;
                    } else {
                        const progress = statusData.progress || 0;
                        const msg = statusData.message || "Downloading stream components...";
                        previewLoaderText.textContent = `[${progress}%] ${msg}`;
                    }
                } catch (err) {
                    console.error("Error polling preview status:", err);
                }
            }, 1000);

        } catch (err) {
            console.error(err);
            previewLoaderText.textContent = "Connection failed. Unable to start preview.";
        }
    }
});
