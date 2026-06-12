// --- JavaScript Logic for EveryThingDownloader ---

// Global settings for Star Grid Canvas & UI Customizer
window.canvasSettings = {
    spacing: 54,
    maxDist: 180,
    gravityMode: 'pull',
    gravityDepth: 130,
    sparkleShape: 'star',
    springCoeffZ: 0.07,
    springCoeffXY: 0.06,
    gridEnabled: true,
    ripplesEnabled: true,
    sparklesEnabled: true
};

document.addEventListener("DOMContentLoaded", () => {
    // Theme Toggle Logic
    const themeToggle = document.getElementById("theme-toggle");
    const currentTheme = localStorage.getItem("theme");
    
    if (currentTheme === "light") {
        document.body.classList.add("light-theme");
        document.documentElement.classList.add("light-theme");
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", (e) => {
            const changeTheme = () => {
                document.documentElement.classList.add("no-transitions");
                const isLight = document.body.classList.toggle("light-theme");
                document.documentElement.classList.toggle("light-theme", isLight);
                localStorage.setItem("theme", isLight ? "light" : "dark");
                
                // Force layout reflow to apply the theme immediately
                document.documentElement.offsetHeight;
                document.documentElement.classList.remove("no-transitions");

                // Update background canvas colors instantly
                if (window.updateCanvasColors) {
                    window.updateCanvasColors();
                }
            };

            // Fallback for browsers that do not support the View Transitions API
            if (!document.startViewTransition) {
                changeTheme();
                return;
            }

            // Get click coordinates, fallback to center of the button if not triggered by cursor
            let x = window.innerWidth / 2;
            let y = window.innerHeight / 2;
            if (e && typeof e.clientX === "number" && typeof e.clientY === "number") {
                x = e.clientX;
                y = e.clientY;
            } else {
                const rect = themeToggle.getBoundingClientRect();
                x = rect.left + rect.width / 2;
                y = rect.top + rect.height / 2;
            }

            // Calculate distance to the furthest corner to set the final radius
            const endRadius = Math.hypot(
                Math.max(x, window.innerWidth - x),
                Math.max(y, window.innerHeight - y)
            );

            // Trigger circular clip-path transition
            const transition = document.startViewTransition(() => {
                changeTheme();
            });

            transition.ready.then(() => {
                document.documentElement.animate(
                    {
                        clipPath: [
                            `circle(0px at ${x}px ${y}px)`,
                            `circle(${endRadius}px at ${x}px ${y}px)`
                        ]
                    },
                    {
                        duration: 450,
                        easing: "ease-out",
                        pseudoElement: "::view-transition-new(root)"
                    }
                );
            });
        });
    }

    // Settings & Customizer Dropdown Toggle
    const settingsToggle = document.getElementById("settings-toggle");
    const settingsDropdown = document.getElementById("settings-dropdown");
    const customizerToggle = document.getElementById("customizer-toggle");
    const customizerDropdown = document.getElementById("customizer-dropdown");

    if (settingsToggle && settingsDropdown) {
        settingsToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            if (customizerDropdown) {
                customizerDropdown.classList.add("hidden");
                customizerToggle.classList.remove("active");
            }
            const isHidden = settingsDropdown.classList.contains("hidden");
            if (isHidden) {
                settingsDropdown.classList.remove("hidden");
                settingsToggle.classList.add("active");
            } else {
                settingsDropdown.classList.add("hidden");
                settingsToggle.classList.remove("active");
            }
        });
    }

    if (customizerToggle && customizerDropdown) {
        customizerToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            if (settingsDropdown) {
                settingsDropdown.classList.add("hidden");
                settingsToggle.classList.remove("active");
            }
            const isHidden = customizerDropdown.classList.contains("hidden");
            if (isHidden) {
                customizerDropdown.classList.remove("hidden");
                customizerToggle.classList.add("active");
            } else {
                customizerDropdown.classList.add("hidden");
                customizerToggle.classList.remove("active");
            }
        });
    }

    // Close both on click outside
    document.addEventListener("click", (e) => {
        if (settingsDropdown && settingsToggle) {
            if (!settingsDropdown.contains(e.target) && !settingsToggle.contains(e.target)) {
                settingsDropdown.classList.add("hidden");
                settingsToggle.classList.remove("active");
            }
        }
        if (customizerDropdown && customizerToggle) {
            if (!customizerDropdown.contains(e.target) && !customizerToggle.contains(e.target)) {
                customizerDropdown.classList.add("hidden");
                customizerToggle.classList.remove("active");
            }
        }
    });

    // --- UI CUSTOMIZER LOGIC ---
    const customizerAccent = document.getElementById("customizer-accent");
    const customizerRadius = document.getElementById("customizer-radius");
    const customizerBlur = document.getElementById("customizer-blur");
    const customizerBlurVal = document.getElementById("customizer-blur-val");
    const customizerFontSize = document.getElementById("customizer-fontsize");
    
    const customizerGridEnable = document.getElementById("customizer-grid-enable");
    const customizerRipplesEnable = document.getElementById("customizer-ripples-enable");
    const customizerSparklesEnable = document.getElementById("customizer-sparkles-enable");
    
    const customizerSpacing = document.getElementById("customizer-spacing");
    const customizerSpacingVal = document.getElementById("customizer-spacing-val");
    const customizerGravity = document.getElementById("customizer-gravity");
    const customizerGravityVal = document.getElementById("customizer-gravity-val");
    const customizerGravityMode = document.getElementById("customizer-gravity-mode");
    const customizerGravityDepth = document.getElementById("customizer-gravity-depth");
    const customizerGravityDepthVal = document.getElementById("customizer-gravity-depth-val");
    const customizerSparkleShape = document.getElementById("customizer-sparkle-shape");
    const customizerResetBtn = document.getElementById("customizer-reset-btn");

    function applyAccent(accentVal) {
        Array.from(document.documentElement.classList).forEach(cls => {
            if (cls.startsWith("accent-theme-")) {
                document.documentElement.classList.remove(cls);
            }
        });
        if (accentVal !== "default") {
            document.documentElement.classList.add("accent-theme-" + accentVal);
        }
        if (customizerAccent) customizerAccent.value = accentVal;
        localStorage.setItem("customizer-accent", accentVal);
    }

    function applyRadius(radiusVal) {
        let borderVal = "16px";
        if (radiusVal === "sharp") borderVal = "4px";
        else if (radiusVal === "rounded") borderVal = "16px";
        else if (radiusVal === "pill") borderVal = "30px";
        document.documentElement.style.setProperty("--radius", borderVal);
        if (customizerRadius) customizerRadius.value = radiusVal;
        localStorage.setItem("customizer-radius", radiusVal);
    }

    function applyBlur(blurVal, persist = false) {
        document.documentElement.style.setProperty("--glass-blur", blurVal + "px");
        if (customizerBlur) customizerBlur.value = blurVal;
        if (customizerBlurVal) customizerBlurVal.textContent = blurVal + "px";
        if (persist) {
            localStorage.setItem("customizer-blur", blurVal);
        }
    }

    function applyFontSize(sizeVal) {
        let htmlSize = "16px";
        if (sizeVal === "small") htmlSize = "14.4px";
        else if (sizeVal === "medium") htmlSize = "16px";
        else if (sizeVal === "large") htmlSize = "17.6px";
        document.documentElement.style.fontSize = htmlSize;
        if (customizerFontSize) customizerFontSize.value = sizeVal;
        localStorage.setItem("customizer-fontsize", sizeVal);
    }

    function updateCanvasOption(key, value) {
        window.canvasSettings[key] = value;
        localStorage.setItem("customizer-" + key, value);
    }

    if (customizerAccent) {
        customizerAccent.addEventListener("change", (e) => applyAccent(e.target.value));
    }
    if (customizerRadius) {
        customizerRadius.addEventListener("change", (e) => applyRadius(e.target.value));
    }
    if (customizerBlur) {
        customizerBlur.addEventListener("input", (e) => applyBlur(e.target.value, false));
        customizerBlur.addEventListener("change", (e) => applyBlur(e.target.value, true));
    }
    if (customizerFontSize) {
        customizerFontSize.addEventListener("change", (e) => applyFontSize(e.target.value));
    }

    if (customizerGridEnable) {
        customizerGridEnable.addEventListener("change", (e) => {
            updateCanvasOption("gridEnabled", e.target.checked);
            const gridContainer = document.getElementById("grid-spacing-container");
            const gravityContainer = document.getElementById("grid-gravity-container");
            const modeContainer = document.getElementById("customizer-gravity-mode") ? document.getElementById("customizer-gravity-mode").parentElement : null;
            const depthContainer = document.getElementById("grid-gravity-depth-container");
            if (e.target.checked) {
                if (gridContainer) gridContainer.style.display = "block";
                if (gravityContainer) gravityContainer.style.display = "block";
                if (modeContainer) modeContainer.style.display = "block";
                if (depthContainer && window.canvasSettings.gravityMode !== "none") depthContainer.style.display = "block";
            } else {
                if (gridContainer) gridContainer.style.display = "none";
                if (gravityContainer) gravityContainer.style.display = "none";
                if (modeContainer) modeContainer.style.display = "none";
                if (depthContainer) depthContainer.style.display = "none";
            }
        });
    }
    if (customizerRipplesEnable) {
        customizerRipplesEnable.addEventListener("change", (e) => updateCanvasOption("ripplesEnabled", e.target.checked));
    }
    if (customizerSparklesEnable) {
        customizerSparklesEnable.addEventListener("change", (e) => updateCanvasOption("sparklesEnabled", e.target.checked));
    }

    if (customizerSpacing) {
        customizerSpacing.addEventListener("input", (e) => {
            const val = parseInt(e.target.value);
            if (customizerSpacingVal) customizerSpacingVal.textContent = val + "px";
            window.canvasSettings.spacing = val;
        });
        customizerSpacing.addEventListener("change", (e) => {
            const val = parseInt(e.target.value);
            localStorage.setItem("customizer-spacing", val);
        });
    }
    if (customizerGravity) {
        customizerGravity.addEventListener("input", (e) => {
            const val = parseInt(e.target.value);
            if (customizerGravityVal) customizerGravityVal.textContent = val + "px";
            window.canvasSettings.maxDist = val;
        });
        customizerGravity.addEventListener("change", (e) => {
            const val = parseInt(e.target.value);
            localStorage.setItem("customizer-maxDist", val);
        });
    }
    if (customizerGravityMode) {
        customizerGravityMode.addEventListener("change", (e) => {
            updateCanvasOption("gravityMode", e.target.value);
            const depthContainer = document.getElementById("grid-gravity-depth-container");
            if (e.target.value === "none") {
                if (depthContainer) depthContainer.style.display = "none";
            } else {
                if (depthContainer) depthContainer.style.display = "block";
            }
        });
    }
    if (customizerGravityDepth) {
        customizerGravityDepth.addEventListener("input", (e) => {
            const val = parseInt(e.target.value);
            if (customizerGravityDepthVal) customizerGravityDepthVal.textContent = val + "px";
            window.canvasSettings.gravityDepth = val;
        });
        customizerGravityDepth.addEventListener("change", (e) => {
            const val = parseInt(e.target.value);
            localStorage.setItem("customizer-gravityDepth", val);
        });
    }
    if (customizerSparkleShape) {
        customizerSparkleShape.addEventListener("change", (e) => {
            updateCanvasOption("sparkleShape", e.target.value);
        });
    }

    if (customizerResetBtn) {
        customizerResetBtn.addEventListener("click", () => {
            applyAccent("default");
            applyRadius("rounded");
            applyBlur(24);
            applyFontSize("medium");

            if (customizerGridEnable) {
                customizerGridEnable.checked = true;
                updateCanvasOption("gridEnabled", true);
                const gridContainer = document.getElementById("grid-spacing-container");
                const gravityContainer = document.getElementById("grid-gravity-container");
                const modeContainer = document.getElementById("customizer-gravity-mode") ? document.getElementById("customizer-gravity-mode").parentElement : null;
                const depthContainer = document.getElementById("grid-gravity-depth-container");
                if (gridContainer) gridContainer.style.display = "block";
                if (gravityContainer) gravityContainer.style.display = "block";
                if (modeContainer) modeContainer.style.display = "block";
                if (depthContainer) depthContainer.style.display = "block";
            }
            if (customizerRipplesEnable) {
                customizerRipplesEnable.checked = true;
                updateCanvasOption("ripplesEnabled", true);
            }
            if (customizerSparklesEnable) {
                customizerSparklesEnable.checked = true;
                updateCanvasOption("sparklesEnabled", true);
            }
            if (customizerSpacing) {
                customizerSpacing.value = 54;
                if (customizerSpacingVal) customizerSpacingVal.textContent = "54px";
                updateCanvasOption("spacing", 54);
            }
            if (customizerGravity) {
                customizerGravity.value = 180;
                if (customizerGravityVal) customizerGravityVal.textContent = "180px";
                updateCanvasOption("maxDist", 180);
            }
            if (customizerGravityMode) {
                customizerGravityMode.value = "pull";
                updateCanvasOption("gravityMode", "pull");
            }
            if (customizerGravityDepth) {
                customizerGravityDepth.value = 130;
                if (customizerGravityDepthVal) customizerGravityDepthVal.textContent = "130px";
                updateCanvasOption("gravityDepth", 130);
            }
            if (customizerSparkleShape) {
                customizerSparkleShape.value = "star";
                updateCanvasOption("sparkleShape", "star");
            }
        });
    }

    const savedAccent = localStorage.getItem("customizer-accent") || "default";
    applyAccent(savedAccent);

    const savedRadius = localStorage.getItem("customizer-radius") || "rounded";
    applyRadius(savedRadius);

    const savedBlur = localStorage.getItem("customizer-blur") !== null ? parseInt(localStorage.getItem("customizer-blur")) : 24;
    applyBlur(savedBlur);

    const savedFontSize = localStorage.getItem("customizer-fontsize") || "medium";
    applyFontSize(savedFontSize);

    const savedGrid = localStorage.getItem("customizer-gridEnabled") !== null ? localStorage.getItem("customizer-gridEnabled") === "true" : true;
    const savedGravityMode = localStorage.getItem("customizer-gravityMode") || "pull";

    if (customizerGridEnable) {
        customizerGridEnable.checked = savedGrid;
        window.canvasSettings.gridEnabled = savedGrid;
        const gridContainer = document.getElementById("grid-spacing-container");
        const gravityContainer = document.getElementById("grid-gravity-container");
        const modeContainer = document.getElementById("customizer-gravity-mode") ? document.getElementById("customizer-gravity-mode").parentElement : null;
        const depthContainer = document.getElementById("grid-gravity-depth-container");
        if (savedGrid) {
            if (gridContainer) gridContainer.style.display = "block";
            if (gravityContainer) gravityContainer.style.display = "block";
            if (modeContainer) modeContainer.style.display = "block";
            if (depthContainer && savedGravityMode !== "none") depthContainer.style.display = "block";
        } else {
            if (gridContainer) gridContainer.style.display = "none";
            if (gravityContainer) gravityContainer.style.display = "none";
            if (modeContainer) modeContainer.style.display = "none";
            if (depthContainer) depthContainer.style.display = "none";
        }
    }

    if (customizerGravityMode) {
        customizerGravityMode.value = savedGravityMode;
        window.canvasSettings.gravityMode = savedGravityMode;
        const depthContainer = document.getElementById("grid-gravity-depth-container");
        if (savedGrid && savedGravityMode !== "none") {
            if (depthContainer) depthContainer.style.display = "block";
        } else {
            if (depthContainer) depthContainer.style.display = "none";
        }
    }

    const savedGravityDepth = localStorage.getItem("customizer-gravityDepth") !== null ? parseInt(localStorage.getItem("customizer-gravityDepth")) : 130;
    if (customizerGravityDepth) {
        customizerGravityDepth.value = savedGravityDepth;
        if (customizerGravityDepthVal) customizerGravityDepthVal.textContent = savedGravityDepth + "px";
        window.canvasSettings.gravityDepth = savedGravityDepth;
    }

    const savedSparkleShape = localStorage.getItem("customizer-sparkleShape") || "star";
    if (customizerSparkleShape) {
        customizerSparkleShape.value = savedSparkleShape;
        window.canvasSettings.sparkleShape = savedSparkleShape;
    }

    const savedRipples = localStorage.getItem("customizer-ripplesEnabled") !== null ? localStorage.getItem("customizer-ripplesEnabled") === "true" : true;
    if (customizerRipplesEnable) {
        customizerRipplesEnable.checked = savedRipples;
        window.canvasSettings.ripplesEnabled = savedRipples;
    }

    const savedSparkles = localStorage.getItem("customizer-sparklesEnabled") !== null ? localStorage.getItem("customizer-sparklesEnabled") === "true" : true;
    if (customizerSparklesEnable) {
        customizerSparklesEnable.checked = savedSparkles;
        window.canvasSettings.sparklesEnabled = savedSparkles;
    }

    const savedSpacing = localStorage.getItem("customizer-spacing") !== null ? parseInt(localStorage.getItem("customizer-spacing")) : 54;
    if (customizerSpacing) {
        customizerSpacing.value = savedSpacing;
        if (customizerSpacingVal) customizerSpacingVal.textContent = savedSpacing + "px";
        window.canvasSettings.spacing = savedSpacing;
    }

    const savedGravity = localStorage.getItem("customizer-maxDist") !== null ? parseInt(localStorage.getItem("customizer-maxDist")) : 180;
    if (customizerGravity) {
        customizerGravity.value = savedGravity;
        if (customizerGravityVal) customizerGravityVal.textContent = savedGravity + "px";
        window.canvasSettings.maxDist = savedGravity;
    }
        // Wire up trim checkbox toggle inside dropdown
        const trimCb = document.getElementById("trim-checkbox");
        const trimContainer = document.getElementById("trim-inputs-container");
        const trimSliderContainer = document.getElementById("trim-slider-container");
        const trimPreviewPlayer = document.getElementById("trim-preview-player");
        if (trimCb && trimContainer) {
            trimCb.addEventListener("change", () => {
                if (trimCb.checked) {
                    trimContainer.classList.remove("hidden");
                    if (trimSliderContainer) {
                        trimSliderContainer.classList.remove("hidden");
                    }
                } else {
                    trimContainer.classList.add("hidden");
                    if (trimSliderContainer) {
                        trimSliderContainer.classList.add("hidden");
                    }
                }
            });
        }

        // Voiceover checkbox toggle
        const voiceoverCb = document.getElementById("voiceover-checkbox");
        const voiceoverSelectContainer = document.getElementById("voiceover-select-container");
        if (voiceoverCb && voiceoverSelectContainer) {
            voiceoverCb.addEventListener("change", () => {
                if (voiceoverCb.checked) {
                    voiceoverSelectContainer.classList.remove("hidden");
                } else {
                    voiceoverSelectContainer.classList.add("hidden");
                }
            });
        }

        // Cloud sync select change
        const cloudSyncSelect = document.getElementById("cloud-sync-select");
        const telegramConfigInputs = document.getElementById("telegram-config-inputs");
        const tgBotTokenInput = document.getElementById("tg-bot-token");
        const tgChatIdInput = document.getElementById("tg-chat-id");

        // Load saved Telegram credentials if any
        if (tgBotTokenInput && tgChatIdInput) {
            tgBotTokenInput.value = localStorage.getItem("tg_bot_token") || "";
            tgChatIdInput.value = localStorage.getItem("tg_chat_id") || "";
            
            // Save on change
            tgBotTokenInput.addEventListener("input", () => {
                localStorage.setItem("tg_bot_token", tgBotTokenInput.value.trim());
            });
            tgChatIdInput.addEventListener("input", () => {
                localStorage.setItem("tg_chat_id", tgChatIdInput.value.trim());
            });
        }

        if (cloudSyncSelect && telegramConfigInputs) {
            cloudSyncSelect.addEventListener("change", () => {
                if (cloudSyncSelect.value === "telegram") {
                    telegramConfigInputs.classList.remove("hidden");
                } else {
                    telegramConfigInputs.classList.add("hidden");
                }
            });
        }

        // Color filter preview application
        const colorFilterSelect = document.getElementById("color-filter-select");
        if (colorFilterSelect) {
            colorFilterSelect.addEventListener("change", () => {
                const filterVal = colorFilterSelect.value;
                if (trimPreviewPlayer) {
                    if (filterVal === "cyberpunk") {
                        trimPreviewPlayer.style.filter = "hue-rotate(-10deg) saturate(1.5) contrast(1.1) brightness(0.95)";
                    } else if (filterVal === "vintage") {
                        trimPreviewPlayer.style.filter = "sepia(0.4) saturate(1.2) contrast(0.9) hue-rotate(5deg)";
                    } else if (filterVal === "noir") {
                        trimPreviewPlayer.style.filter = "grayscale(1) contrast(1.4) brightness(0.9)";
                    } else if (filterVal === "enhance") {
                        trimPreviewPlayer.style.filter = "contrast(1.05) saturate(1.1)";
                    } else {
                        trimPreviewPlayer.style.filter = "none";
                    }
                }
            });
        }

    // Unique Client ID Management
    let clientId = localStorage.getItem("client_id");
    if (!clientId) {
        clientId = "client_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem("client_id", clientId);
    }

    // UI Elements
    const urlInput = document.getElementById("url-input");
    const pasteBtn = document.getElementById("paste-btn");
    const clearUrlBtn = document.getElementById("clear-url-btn");
    const analyzeBtn = document.getElementById("analyze-btn");
    
    const loaderSection = document.getElementById("loader");
    const loaderText = document.getElementById("loader-text");
    const cancelAnalyzeBtn = document.getElementById("cancel-analyze-btn");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");
    
    let analysisAbortController = null;
    
    const resultSection = document.getElementById("result-section");
    const videoThumbnail = document.getElementById("video-thumbnail");
    if (videoThumbnail) {
        videoThumbnail.addEventListener("load", function() {
            videoThumbnail.style.opacity = "1";
        });
        videoThumbnail.addEventListener("error", function() {
            // If the proxied URL failed, try loading the original direct URL as fallback
            const currentSrc = videoThumbnail.src || "";
            const originalUrl = videoThumbnail.getAttribute("data-original-url");
            if (currentSrc.includes("/api/proxy/image") && originalUrl) {
                console.warn("Proxy image failed, falling back to direct URL:", originalUrl);
                videoThumbnail.removeAttribute("data-original-url"); // prevent infinite loop
                videoThumbnail.src = originalUrl;
                return;
            }
            // Final fallback: show a styled placeholder
            videoThumbnail.style.opacity = "1";
            videoThumbnail.alt = "Thumbnail unavailable";
        });
    }
    const videoTitle = document.getElementById("video-title");
    const videoUploader = document.getElementById("video-uploader");
    const videoDuration = document.getElementById("video-duration-badge");
    const mediaBadge = document.getElementById("media-badge");
    const optionsContainer = document.getElementById("options-container");
    if (optionsContainer) {
        optionsContainer.addEventListener("mouseover", (e) => {
            const formatLeft = e.target.closest(".format-left");
            if (formatLeft && !formatLeft.hasAttribute("title")) {
                formatLeft.setAttribute("title", "Click to expand/collapse full name");
            }
        });
        optionsContainer.addEventListener("click", (e) => {
            const formatLeft = e.target.closest(".format-left");
            if (formatLeft) {
                const row = formatLeft.closest(".format-row");
                if (row) {
                    row.classList.toggle("expanded");
                }
            }
        });
    }
    
    const downloadProgress = document.getElementById("download-progress");
    const progressPercent = document.getElementById("progress-percent");
    const progressBarFill = document.getElementById("progress-fill");
    const downloadStatusTitle = document.getElementById("download-status-title");
    const downloadStatusMessage = document.getElementById("download-status-message");
    const downloadFormatLabel = document.getElementById("download-format-label");

    // Preview Modal DOM Elements
    const previewModal = document.getElementById("preview-modal");
    const previewModalCloseBtn = document.getElementById("preview-modal-close-btn");

    // Confirm Modal DOM Elements
    const confirmModal = document.getElementById("confirm-modal");
    const confirmModalTitle = document.getElementById("confirm-modal-title");
    const confirmModalMessage = document.getElementById("confirm-modal-message");
    const confirmModalBtnYes = document.getElementById("confirm-modal-btn-yes");
    const confirmModalBtnNo = document.getElementById("confirm-modal-btn-no");
    const confirmCloseBtn = document.getElementById("confirm-close-btn");
    let confirmYesCallback = null;
    let confirmNoCallback = null;
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

    function getProxiedImageUrl(url) {
        if (!url) return "";
        // Reject Reddit placeholder strings like 'image', 'self', 'default', 'nsfw', 'spoiler'
        if (!url.startsWith("http")) return "";
        // Reddit CDN (redd.it, redditmedia.com, redditstatic.com) blocks server-side
        // requests via TLS fingerprinting / anti-bot, but allows direct browser loading.
        // So we do NOT proxy Reddit image URLs — let the browser fetch them directly.
        if (url.includes("twimg.com") || url.includes("instagram.com") || url.includes("cdninstagram.com") || url.includes("fbcdn.net") || url.includes("pinimg.com")) {
            return `/api/proxy/image?url=${encodeURIComponent(url)}${clientId ? `&client_id=${clientId}` : ''}`;
        }
        return url;
    }

    function getSafeTitle(title, defaultVal = "image") {
        if (!title) return defaultVal;
        let clean = String(title);
        // Remove common branding/suffixes
        const brandingPatterns = [
            /-?\s*Motchill\s*$/i, /-?\s*Motchilli\s*$/i, /-?\s*PhimMoi\s*$/i,
            /Vietsub\s*$/i, /Thuyết Minh\s*$/i, /Lồng Tiếng\s*$/i,
            /\(\d{4}\)/i, /Full\s*$/i
        ];
        brandingPatterns.forEach(pattern => {
            clean = clean.replace(pattern, "");
        });
        const cleaned = clean.replace(/[\\/*?:"<>|#]/g, "").replace(/\s+/g, " ").trim();
        return [...cleaned].slice(0, 80).join("").trim() || defaultVal;
    }

    // Cookies UI Elements
    const activeCookiesBadge = document.getElementById("active-cookies-badge");
    const clearCookiesBtn = document.getElementById("clear-cookies-btn");
    const cookiesSection = document.getElementById("cookies-section");
    const cookieFileInput = document.getElementById("cookie-file-input");
    const cookieDropzone = document.getElementById("cookie-dropzone");

    // Check cookie status on load
    checkCookieStatus();

    // Initialize welcome dashboard and render history
    showWelcomeDashboard();

    // Wire up platform badge example URL clicks
    const platformBadges = document.querySelectorAll(".platform-badge");
    platformBadges.forEach(badge => {
        badge.addEventListener("click", () => {
            const hintUrl = badge.getAttribute("data-url-hint");
            if (hintUrl) {
                urlInput.value = hintUrl;
                urlInput.focus();
                triggerGlowEffect();
            }
        });
    });

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

    // Toggle Cookies Section
    const toggleCookiesBtn = document.getElementById("toggle-cookies-btn");
    if (toggleCookiesBtn && cookiesSection) {
        toggleCookiesBtn.addEventListener("click", () => {
            const isHidden = cookiesSection.classList.toggle("hidden");
            const btnSpan = toggleCookiesBtn.querySelector("span");
            if (btnSpan) {
                btnSpan.textContent = isHidden ? "Manage Cookies" : "Close Cookie Panel";
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

    // Cookies Tabs Toggle Logic
    const tabUploadBtn = document.getElementById("cookie-tab-upload");
    const tabPasteBtn = document.getElementById("cookie-tab-paste");
    const tabUploadContent = document.getElementById("cookie-tab-content-upload");
    const tabPasteContent = document.getElementById("cookie-tab-content-paste");

    if (tabUploadBtn && tabPasteBtn && tabUploadContent && tabPasteContent) {
        tabUploadBtn.addEventListener("click", () => {
            tabUploadBtn.classList.add("active");
            tabPasteBtn.classList.remove("active");
            tabUploadContent.classList.remove("hidden");
            tabPasteContent.classList.add("hidden");
        });

        tabPasteBtn.addEventListener("click", () => {
            tabPasteBtn.classList.add("active");
            tabUploadBtn.classList.remove("active");
            tabPasteContent.classList.remove("hidden");
            tabUploadContent.classList.add("hidden");
        });
    }

    // Pasted Cookies Saving
    const cookieTextInput = document.getElementById("cookie-text-input");
    const cookieSaveTextBtn = document.getElementById("cookie-save-text-btn");

    if (cookieSaveTextBtn && cookieTextInput) {
        cookieSaveTextBtn.addEventListener("click", async () => {
            const content = cookieTextInput.value.trim();
            if (!content) {
                showError("Vui lòng dán nội dung cookies trước.");
                return;
            }

            try {
                loaderSection.classList.remove("hidden");
                loaderText.textContent = "Đang lưu cookies...";
                cookiesSection.classList.add("hidden");

                const res = await fetch("/api/cookies/paste", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        client_id: clientId,
                        content: content
                    })
                });
                const data = await res.json();

                if (res.ok && data.status === "success") {
                    cookieTextInput.value = "";
                    checkCookieStatus();
                    loaderText.textContent = "Cookies saved! Retrying analysis...";
                    setTimeout(() => {
                        performAnalysis();
                    }, 1000);
                } else {
                    showError(data.message || "Failed to save cookies.");
                    cookiesSection.classList.remove("hidden");
                }
            } catch (err) {
                console.error(err);
                showError("Connection lost. Failed to contact cookies paste API.");
                cookiesSection.classList.remove("hidden");
            } finally {
                loaderSection.classList.add("hidden");
            }
        });
    }

    // Global state
    let activeUrl = "";
    let pollingInterval = null;
    let activeDownloadId = null;
    let extractedImages = [];

    // Preview state variables
    let previewZoomLevel = 1;
    let previewRotation = 0;
    let previewActiveDownloadId = null;
    let previewActiveUrl = "";
    let previewActiveExt = "";
    let previewActiveFilename = "";
    let previewActivePollInterval = null;

    // Helper to stop all preview playbacks and destroy Hls instances
    function stopAllPreviewPlaybacks() {
        if (previewActivePollInterval) {
            previewActivePollInterval.close();
            previewActivePollInterval = null;
        }
        if (previewVideoPlayer) {
            previewVideoPlayer.pause();
            if (previewVideoPlayer.hlsInstance) {
                previewVideoPlayer.hlsInstance.destroy();
                delete previewVideoPlayer.hlsInstance;
            }
            previewVideoPlayer.src = "";
        }
        if (previewAudioPlayer) {
            previewAudioPlayer.pause();
            previewAudioPlayer.src = "";
        }
    }

    // Close preview modal behavior
    if (previewModal && previewModalCloseBtn) {
        const closePreviewModal = () => {
            previewModal.classList.add("hidden");
            document.body.classList.remove("modal-open");
            stopAllPreviewPlaybacks();
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

    // Confirm Modal Behavior
    function showConfirm(options = {}) {
        if (!confirmModal) return;
        confirmModalTitle.textContent = options.title || "Xác nhận";
        confirmModalMessage.textContent = options.message || "Bạn có chắc chắn?";
        confirmModalBtnYes.textContent = options.yesText || "Đồng ý";
        confirmModalBtnNo.textContent = options.noText || "Hủy";

        confirmYesCallback = options.onYes || null;
        confirmNoCallback = options.onNo || null;

        confirmModal.classList.remove("hidden");
        document.body.classList.add("modal-open");
    }

    function hideConfirm() {
        if (!confirmModal) return;
        confirmModal.classList.add("hidden");
        const anyVisible = Array.from(document.querySelectorAll(".modal-overlay")).some(el => !el.classList.contains("hidden"));
        if (!anyVisible) {
            document.body.classList.remove("modal-open");
        }
    }

    if (confirmModalBtnYes) {
        confirmModalBtnYes.onclick = () => {
            hideConfirm();
            if (confirmYesCallback) confirmYesCallback();
        };
    }

    if (confirmModalBtnNo) {
        confirmModalBtnNo.onclick = () => {
            hideConfirm();
            if (confirmNoCallback) confirmNoCallback();
        };
    }

    if (confirmCloseBtn) {
        confirmCloseBtn.onclick = () => {
            hideConfirm();
            if (confirmNoCallback) confirmNoCallback();
        };
    }

    if (confirmModal) {
        confirmModal.onclick = (e) => {
            if (e.target === confirmModal) {
                hideConfirm();
                if (confirmNoCallback) confirmNoCallback();
            }
        };

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !confirmModal.classList.contains("hidden")) {
                hideConfirm();
                if (confirmNoCallback) confirmNoCallback();
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
                updateUrlInputButtons();
                urlInput.focus();
                triggerGlowEffect();
            }
        } catch (err) {
            console.log("Unable to read from clipboard via API. Fallback to manual pasting.");
        }
    });

    // Helper to toggle paste/clear button in input box
    function updateUrlInputButtons() {
        if (urlInput.value.trim() === "") {
            pasteBtn.classList.remove("hidden");
            if (clearUrlBtn) clearUrlBtn.classList.add("hidden");
        } else {
            pasteBtn.classList.add("hidden");
            if (clearUrlBtn) clearUrlBtn.classList.remove("hidden");
        }
    }

    urlInput.addEventListener("input", updateUrlInputButtons);

    // Clear URL input and return to welcome mode
    if (clearUrlBtn) {
        clearUrlBtn.addEventListener("click", () => {
            urlInput.value = "";
            updateUrlInputButtons();
            urlInput.focus();
            
            if (analysisAbortController) {
                analysisAbortController.abort();
                analysisAbortController = null;
            }
            
            errorCard.classList.add("hidden");
            resultSection.classList.add("hidden");
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            
            setPlatformTheme(null);
            showWelcomeDashboard();
        });
    }

    // Cancel active analysis and return to welcome mode
    if (cancelAnalyzeBtn) {
        cancelAnalyzeBtn.addEventListener("click", () => {
            if (analysisAbortController) {
                analysisAbortController.abort();
                analysisAbortController = null;
            }
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            showWelcomeDashboard();
        });
    }

    // Logo click reset (Return to welcome dashboard without page reload)
    const logoEl = document.querySelector(".logo");
    if (logoEl) {
        logoEl.addEventListener("click", () => {
            // Reset input and update buttons
            urlInput.value = "";
            updateUrlInputButtons();
            
            // Abort active analysis if any
            if (analysisAbortController) {
                analysisAbortController.abort();
                analysisAbortController = null;
            }
            
            // Abort active download if any
            if (activeDownloadId) {
                try {
                    fetch(`/api/download/cancel/${activeDownloadId}`, { method: "POST" });
                } catch (e) {
                    console.error("Failed to cancel download on logo click:", e);
                }
                activeDownloadId = null;
            }
            
            if (pollingInterval) {
                pollingInterval.close();
                pollingInterval = null;
            }
            
            // Hide all dynamic panels
            errorCard.classList.add("hidden");
            resultSection.classList.add("hidden");
            loaderSection.classList.add("hidden");
            downloadProgress.classList.add("hidden");
            downloadProgress.classList.remove("state-complete", "state-error");
            cookiesSection.classList.add("hidden");
            
            // Enable buttons
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            urlInput.disabled = false;
            
            // Reset theme
            setPlatformTheme(null);
            
            // Show welcome dashboard
            showWelcomeDashboard();
        });
    }

    // Cancel active download and return to format options
    const cancelDownloadBtn = document.getElementById("cancel-download-btn");
    if (cancelDownloadBtn) {
        cancelDownloadBtn.addEventListener("click", () => {
            if (activeDownloadId) {
                try {
                    fetch(`/api/download/cancel/${activeDownloadId}`, { method: "POST" });
                } catch (e) {
                    console.error("Failed to call cancel download API:", e);
                }
            }
            
            // Close SSE
            if (pollingInterval) {
                pollingInterval.close();
                pollingInterval = null;
            }
            
            // Hide progress panel
            downloadProgress.classList.add("hidden");
            downloadProgress.classList.remove("state-complete", "state-error");
            
            // Enable inputs & buttons
            analyzeBtn.disabled = false;
            urlInput.disabled = false;
            
            // Re-enable format buttons
            const formatRows = document.querySelectorAll(".format-row");
            formatRows.forEach(row => {
                row.classList.remove("is-downloading");
                const btns = row.querySelectorAll("button");
                btns.forEach(b => b.disabled = false);
            });
            
            const allPrimaryBtns = document.querySelectorAll(".format-btn");
            allPrimaryBtns.forEach(b => b.disabled = false);
            
            activeDownloadId = null;
        });
    }

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
    
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", () => {
            showConfirm({
                title: "Xác nhận xóa lịch sử",
                message: "Bạn có chắc chắn muốn xóa toàn bộ lịch sử phân tích không?",
                yesText: "Đồng ý",
                noText: "Hủy",
                onYes: () => {
                    localStorage.removeItem("downloader_history");
                    renderHistory();
                }
            });
        });
    }

    urlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            performAnalysis();
        }
    });

    function isValidUrl(url) {
        try {
            const parsed = new URL(url);
            return parsed.protocol === "http:" || parsed.protocol === "https:";
        } catch (_) {
            return false;
        }
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
        },
        "tiktok-video": {
            cyan: "#00f2fe", purple: "#fe0979",
            cyanRgb: "0, 242, 254", purpleRgb: "254, 9, 121"
        },
        "tiktok-slideshow": {
            cyan: "#00f2fe", purple: "#fe0979",
            cyanRgb: "0, 242, 254", purpleRgb: "254, 9, 121"
        },
        "tiktok-story": {
            cyan: "#00f2fe", purple: "#fe0979",
            cyanRgb: "0, 242, 254", purpleRgb: "254, 9, 121"
        },
        "twitter-x": {
            cyan: "#1d9bf0", purple: "#ffffff",
            cyanRgb: "29, 155, 240", purpleRgb: "255, 255, 255"
        },
        "reddit": {
            cyan: "#ff4500", purple: "#ffb700",
            cyanRgb: "255, 69, 0", purpleRgb: "255, 183, 0"
        },
        "soundcloud": {
            cyan: "#ff5500", purple: "#ffaa00",
            cyanRgb: "255, 85, 0", purpleRgb: "255, 170, 0"
        },
        "pinterest": {
            cyan: "#bd081c", purple: "#e60023",
            cyanRgb: "189, 8, 28", purpleRgb: "230, 0, 35"
        },
        "vimeo": {
            cyan: "#1ab7ea", purple: "#86d9f8",
            cyanRgb: "26, 183, 234", purpleRgb: "134, 217, 248"
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

    function showWelcomeDashboard() {
        const resultGrid = resultSection.querySelector(".result-grid");
        if (resultGrid) {
            resultGrid.classList.add("welcome-mode");
        }
        resultSection.classList.remove("hidden");
        renderHistory();
    }

    function saveToHistory(url, data) {
        try {
            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            
            const existingItem = history.find(item => item.url === url);
            let savedSettings = existingItem ? existingItem.settings : null;
            if (!savedSettings) {
                const trimCheckbox = document.getElementById("trim-checkbox");
                const trimStart = document.getElementById("trim-start");
                const trimEnd = document.getElementById("trim-end");
                const translateSubsCheckbox = document.getElementById("translate-subs-checkbox");
                const exportTypeSelect = document.getElementById("export-type-select");
                const colorFilterSelect = document.getElementById("color-filter-select");
                const voiceoverCheckbox = document.getElementById("voiceover-checkbox");
                const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
                const cloudSyncSelect = document.getElementById("cloud-sync-select");

                savedSettings = {
                    trim_active: trimCheckbox ? trimCheckbox.checked : false,
                    trim_start: trimStart ? trimStart.value : "00:00:00",
                    trim_end: trimEnd ? trimEnd.value : "00:00:10",
                    translate_subs: translateSubsCheckbox ? translateSubsCheckbox.checked : false,
                    export_type: exportTypeSelect ? exportTypeSelect.value : "default",
                    color_filter: colorFilterSelect ? colorFilterSelect.value : "none",
                    voiceover_active: voiceoverCheckbox ? voiceoverCheckbox.checked : false,
                    voiceover_voice: voiceoverVoiceSelect ? voiceoverVoiceSelect.value : "vi-VN-HoaiMyNeural",
                    cloud_sync: cloudSyncSelect ? cloudSyncSelect.value : "local"
                };
            }

            // Remove duplicate of the same URL if exists
            history = history.filter(item => item.url !== url);
            
            // Add to the beginning
            history.unshift({
                url: url,
                title: data.title || "Untitled Media",
                thumbnail: data.thumbnail || "",
                platform_label: data.platform_label || "Video",
                platform_class: data.platform_class || "default",
                timestamp: Date.now(),
                settings: savedSettings
            });
            
            // Keep at most 10 items
            if (history.length > 10) {
                history.pop();
            }
            
            localStorage.setItem("downloader_history", JSON.stringify(history));
        } catch (e) {
            console.error("Error saving history:", e);
        }
    }

    function renderHistory() {
        const historyList = document.getElementById("history-list");
        const historySection = document.getElementById("welcome-history-section");
        if (!historyList || !historySection) return;
        
        try {
            const history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            if (history.length === 0) {
                historySection.classList.add("hidden");
                return;
            }
            
            historySection.classList.remove("hidden");
            historyList.innerHTML = "";
            
            history.forEach(item => {
                const row = document.createElement("div");
                row.className = "history-item";
                row.setAttribute("data-url", item.url);
                
                const thumbUrl = getProxiedImageUrl(item.thumbnail) || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=120";
                
                row.innerHTML = `
                    <div class="history-item-left">
                        <img class="history-thumb" src="${thumbUrl}" alt="Thumb">
                        <div class="history-details">
                            <span class="history-title">${item.title}</span>
                            <div class="history-meta">
                                <span class="history-platform-tag ${item.platform_class}">${item.platform_label}</span>
                                <span>${new Date(item.timestamp).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </div>
                    <svg class="history-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                `;
                
                row.addEventListener("click", () => {
                    urlInput.value = item.url;
                    performAnalysis();
                });
                
                historyList.appendChild(row);
            });
        } catch (e) {
            console.error("Error rendering history:", e);
        }
    }

    async function performAnalysis() {
        const url = urlInput.value.trim();
        
        if (!url) {
            showError("Please enter a link first.");
            return;
        }

        if (!isValidUrl(url)) {
            showError("Invalid URL. Please enter a valid HTTP or HTTPS link.");
            return;
        }

        // Initialize AbortController to support cancellation
        if (analysisAbortController) {
            analysisAbortController.abort();
        }
        analysisAbortController = new AbortController();

        // Reset UI States
        setPlatformTheme(null);
        errorCard.classList.add("hidden");
        resultSection.classList.add("hidden");
        downloadProgress.classList.add("hidden");
        cookiesSection.classList.add("hidden");

        // Reset stale metadata from previous analysis
        videoThumbnail.src = "";
        videoThumbnail.style.opacity = "0";
        videoThumbnail.alt = "Thumbnail";
        videoTitle.textContent = "Đang phân tích...";
        videoUploader.textContent = "";
        videoDuration.textContent = "0:00";
        videoDuration.style.display = "none";
        if (mediaBadge) {
            mediaBadge.textContent = "Video";
            mediaBadge.className = "tag tag-default";
        }
        const viewsEl_reset = document.getElementById("video-views");
        const likesEl_reset = document.getElementById("video-likes");
        const dateEl_reset = document.getElementById("video-date");
        if (viewsEl_reset) viewsEl_reset.textContent = "—";
        if (likesEl_reset) likesEl_reset.textContent = "—";
        if (dateEl_reset) dateEl_reset.textContent = "—";
        const tagsReset = document.getElementById("video-tags-container");
        if (tagsReset) tagsReset.innerHTML = "";
        optionsContainer.innerHTML = "";
        
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
                body: JSON.stringify({ url: url, client_id: clientId }),
                signal: analysisAbortController.signal
            });

            const data = await response.json();

            if (response.ok && data.status === "success") {
                activeUrl = url;
                setPlatformTheme(data.platform_class);
                displayMetadata(data);
                
                try {
                    const history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
                    const item = history.find(it => it.url === url);
                    if (item) {
                        restoreSettingsForUrl(item);
                    }
                } catch (e) {
                    console.error("Error restoring settings:", e);
                }

                saveToHistory(url, data);
            } else {
                setPlatformTheme(null);
                showError(data.message || "Unable to extract media information from this URL.");
                const msg = (data.message || "").toLowerCase();
                const authKeywords = ["private", "log in", "login", "sign in", "signin", "invalid", "cookie", "confirm", "subscriber", "membership", "member"];
                if (authKeywords.some(keyword => msg.includes(keyword))) {
                    cookiesSection.classList.remove("hidden");
                }
                showWelcomeDashboard();
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                console.log("Analysis aborted by user.");
                showWelcomeDashboard();
                return;
            }
            console.error(err);
            setPlatformTheme(null);
            showError("Connection lost. Unable to contact local Python downloader server.");
            showWelcomeDashboard();
        } finally {
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            analysisAbortController = null;
        }
    }

    // Display parsed metadata
    function displayMetadata(data) {
        const resultGrid = resultSection.querySelector(".result-grid");
        if (resultGrid) {
            resultGrid.classList.remove("welcome-mode");
        }
        
        // Thumbnail & Title
        videoThumbnail.style.opacity = "0";
        // Store original URL for fallback if proxy fails
        if (data.thumbnail) {
            videoThumbnail.setAttribute("data-original-url", data.thumbnail);
        }
        videoThumbnail.src = getProxiedImageUrl(data.thumbnail) || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600";
        videoTitle.textContent = data.title;
        videoUploader.textContent = data.uploader;
        if (data.duration && data.duration !== "Unknown" && data.duration !== "N/A" && data.duration !== "0:00") {
            videoDuration.textContent = data.duration;
            videoDuration.style.display = "inline-block";
        } else {
            videoDuration.style.display = "none";
        }

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
                
                const cleanTitle = getSafeTitle(data.title, "image");
                const filename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${imgExt}`;
                const proxyDownloadUrl = `/api/download/image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(filename)}&client_id=${encodeURIComponent(clientId)}`;

                card.innerHTML = `
                    <div class="image-checkbox-container">
                        <input type="checkbox" class="image-select-check custom-checkbox" data-url="${imgUrl}" data-label="${cleanLabel}" data-ext="${imgExt}" data-filename="${filename}">
                    </div>
                    <div class="image-preview-wrap">
                        <img src="${getProxiedImageUrl(imgUrl)}" alt="${imgLabel}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600'">
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
                                title: getSafeTitle(data.title, "images"),
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
                        downloadAnchor.download = `${getSafeTitle(data.title, "images")}_images.zip`;
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
                // Group videos by server
                const serverOrder = [];
                const grouped = {};
                const noGroup = [];

                videos.forEach(option => {
                    const server = option.server || "";
                    if (server) {
                        if (!grouped[server]) {
                            grouped[server] = [];
                            serverOrder.push(server);
                        }
                        grouped[server].push(option);
                    } else {
                        noGroup.push(option);
                    }
                });

                // Sort options inside each server group by episode name/number naturally
                serverOrder.forEach(server => {
                    grouped[server].sort((a, b) => {
                        const epA = a.episode || "";
                        const epB = b.episode || "";
                        return epA.localeCompare(epB, undefined, { numeric: true, sensitivity: 'base' });
                    });
                });

                // Render ungrouped videos first (if any)
                if (noGroup.length > 0) {
                    const videoGroupLabel = document.createElement("div");
                    videoGroupLabel.className = "format-group-label";
                    videoGroupLabel.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                        <span>Video Options</span>
                    `;
                    optionsContainer.appendChild(videoGroupLabel);

                    noGroup.forEach(option => {
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

                // Render grouped videos by server
                serverOrder.forEach(server => {
                    const serverGroupLabel = document.createElement("div");
                    serverGroupLabel.className = "format-group-label server-group-label";
                    
                    serverGroupLabel.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                        <span>${server}</span>
                    `;
                    optionsContainer.appendChild(serverGroupLabel);

                    grouped[server].forEach(option => {
                        const row = document.createElement("div");
                        row.className = "format-row video-row";
                        const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                        
                        // Formulate the display label using episode, fall back to option.label
                        let displayLabel = option.label;
                        if (option.episode) {
                            const ep = option.episode;
                            if (ep.toLowerCase().startsWith("episode") || ep.toLowerCase().startsWith("ep") || ep.toLowerCase().startsWith("tập") || ep.toLowerCase().startsWith("tap")) {
                                displayLabel = ep;
                            } else {
                                displayLabel = `Episode ${ep}`;
                            }
                        } else {
                            if (displayLabel.includes("(Episode ")) {
                                displayLabel = displayLabel.replace(/\s*\(Episode\s+[^)]+\)/g, "");
                            }
                        }
                        
                        row.innerHTML = `
                            <div class="format-left">
                                ${videoSvg}
                                <span class="format-name">${displayLabel}</span>
                                ${sizeBadge}
                            </div>
                            <div class="format-actions">
                                <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-episode="${option.episode || ''}" data-server="${option.server || ''}">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                    <span>Preview</span>
                                </button>
                                <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-episode="${option.episode || ''}" data-server="${option.server || ''}">
                                    ${downloadSvg}
                                    <span>Get</span>
                                </button>
                            </div>
                        `;
                        optionsContainer.appendChild(row);
                    });
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
                const cleanTitle = getSafeTitle(data.title, "image");
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
                const episode = btn.getAttribute("data-episode") || "";
                const server = btn.getAttribute("data-server") || "";
                if (formatId === "image_download") {
                    window.open(customUrl, "_blank");
                    return;
                }
                triggerDownload(btn, formatId, ext, label, quality, customUrl, episode, server);
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
                const episode = btn.getAttribute("data-episode") || "";
                const server = btn.getAttribute("data-server") || "";
                triggerPreview(btn, formatId, ext, label, quality, customUrl, episode, server);
            });
        });

        // Setup Advanced Options panel state for the new media
        const trimCheckbox = document.getElementById("trim-checkbox");
        const trimInputsContainer = document.getElementById("trim-inputs-container");
        const trimSliderContainer = document.getElementById("trim-slider-container");
        const trimStartInput = document.getElementById("trim-start");
        const trimEndInput = document.getElementById("trim-end");
        const trimPreviewContainer = document.getElementById("trim-preview-container");
        const trimPreviewPlayer = document.getElementById("trim-preview-player");
        const trimRangeSlider = document.getElementById("trim-range-slider");
        const subTranslateContainer = document.getElementById("sub-translate-container");
        const translateCheckbox = document.getElementById("translate-subs-checkbox");

        if (trimCheckbox) {
            trimCheckbox.checked = false;
            if (trimInputsContainer) trimInputsContainer.classList.add("hidden");
            if (trimSliderContainer) trimSliderContainer.classList.add("hidden");
            if (trimPreviewContainer) trimPreviewContainer.classList.add("hidden");
            if (trimStartInput) trimStartInput.value = "00:00:00";
            if (trimEndInput) {
                let dur = data.duration || "00:00:10";
                if (dur.split(":").length === 2) {
                    dur = "00:" + dur;
                }
                trimEndInput.value = dur;
            }

            // Clean up old preview player state
            if (trimPreviewPlayer) {
                trimPreviewPlayer.removeAttribute("src");
                trimPreviewPlayer.load();
            }

            // Visual trimmer logic: setup noUiSlider
            const durationSeconds = parseFloat(data.duration_raw) || 0;
            const hasVideo = data.video_options && data.video_options.some(opt => opt.ext !== "jpg");
            
            if (durationSeconds > 0 && hasVideo && trimRangeSlider) {
                // Determine a valid video format URL to load in background preview
                const previewVideoOption = data.video_options.find(opt => opt.ext !== "jpg" && opt.url);
                const previewVideoUrl = previewVideoOption ? previewVideoOption.url : null;
                
                if (previewVideoUrl && trimPreviewPlayer) {
                    trimPreviewPlayer.src = previewVideoUrl;
                    trimPreviewPlayer.load();
                }

                // Show preview area automatically when media has video
                if (trimPreviewContainer && previewVideoUrl) {
                    trimPreviewContainer.classList.remove("hidden");
                    trimPreviewContainer.classList.remove("force-hidden");
                }

                // Destroy any existing slider
                if (trimRangeSlider.noUiSlider) {
                    trimRangeSlider.noUiSlider.destroy();
                }

                // Initialize noUiSlider
                noUiSlider.create(trimRangeSlider, {
                    start: [0, durationSeconds],
                    connect: true,
                    step: 1,
                    range: {
                        'min': 0,
                        'max': durationSeconds
                    }
                });

                // Helper to format seconds to time string hh:mm:ss
                function formatSecsToTime(secs) {
                    const h = Math.floor(secs / 3600);
                    const m = Math.floor((secs % 3600) / 60);
                    const s = Math.floor(secs % 60);
                    const pad = (n) => String(n).padStart(2, '0');
                    return `${pad(h)}:${pad(m)}:${pad(s)}`;
                }

                // Helper to parse time string hh:mm:ss to seconds
                function parseTimeToSecs(timeStr) {
                    const parts = timeStr.split(':').map(Number);
                    if (parts.length === 3) {
                        return parts[0] * 3600 + parts[1] * 60 + parts[2];
                    } else if (parts.length === 2) {
                        return parts[0] * 60 + parts[1];
                    } else if (parts.length === 1) {
                        return parts[0];
                    }
                    return 0;
                }

                // Update text inputs on slider change
                trimRangeSlider.noUiSlider.on('update', (values) => {
                    const startVal = Math.round(parseFloat(values[0]));
                    const endVal = Math.round(parseFloat(values[1]));
                    if (trimStartInput) trimStartInput.value = formatSecsToTime(startVal);
                    if (trimEndInput) trimEndInput.value = formatSecsToTime(endVal);
                });

                // Seek preview video player to the handle being dragged/interacted with in real-time
                const seekToHandle = (values, handle) => {
                    const seekVal = Math.round(parseFloat(values[handle]));
                    if (trimPreviewPlayer) {
                        trimPreviewPlayer.currentTime = seekVal;
                    }
                };
                trimRangeSlider.noUiSlider.on('slide', seekToHandle);
                trimRangeSlider.noUiSlider.on('change', seekToHandle);

                // Two-way sync: manual changes to input text update the slider
                if (trimStartInput) {
                    trimStartInput.onchange = () => {
                        const sec = parseTimeToSecs(trimStartInput.value);
                        trimRangeSlider.noUiSlider.set([sec, null]);
                        if (trimPreviewPlayer) trimPreviewPlayer.currentTime = sec;
                    };
                }
                if (trimEndInput) {
                    trimEndInput.onchange = () => {
                        const sec = parseTimeToSecs(trimEndInput.value);
                        trimRangeSlider.noUiSlider.set([null, sec]);
                        if (trimPreviewPlayer) trimPreviewPlayer.currentTime = sec;
                    };
                }

                // Scene Detector API call
                if (previewVideoUrl) {
                    fetch(`/api/video/analyze-scenes?url=${encodeURIComponent(previewVideoUrl)}`)
                        .then(res => res.json())
                        .then(sceneData => {
                            if (sceneData.status === "success" && sceneData.scenes && sceneData.scenes.length > 0) {
                                renderSceneMarkers(sceneData.scenes, durationSeconds, trimRangeSlider);
                            }
                        })
                        .catch(err => console.log("Failed to load scene highlights:", err));
                }

                // Render markers inside the noUiSlider
                function renderSceneMarkers(scenes, totalDuration, sliderElement) {
                    const noUiBase = sliderElement.querySelector('.noUi-base');
                    if (!noUiBase) return;
                    
                    // Remove existing scene markers if any
                    noUiBase.querySelectorAll('.scene-marker').forEach(el => el.remove());
                    
                    scenes.forEach(timeSec => {
                        const pct = (timeSec / totalDuration) * 100;
                        if (pct > 0 && pct < 100) {
                            const marker = document.createElement('div');
                            marker.className = 'scene-marker';
                            marker.style.left = `${pct}%`;
                            marker.title = `Scene change at ${formatSecsToTime(timeSec)}`;
                            
                            // On click seek player and snap slider handle
                            marker.onclick = (e) => {
                                e.stopPropagation();
                                if (trimPreviewPlayer) {
                                    trimPreviewPlayer.currentTime = timeSec;
                                }
                                const currentVals = sliderElement.noUiSlider.get().map(parseFloat);
                                const distStart = Math.abs(currentVals[0] - timeSec);
                                const distEnd = Math.abs(currentVals[1] - timeSec);
                                if (distStart < distEnd) {
                                    sliderElement.noUiSlider.set([timeSec, null]);
                                } else {
                                    sliderElement.noUiSlider.set([null, timeSec]);
                                }
                            };
                            noUiBase.appendChild(marker);
                        }
                    });
                }

            } else {
                // If it is a photo post or has no valid duration, force hide preview player & slider
                if (trimPreviewContainer) {
                    trimPreviewContainer.classList.add("force-hidden");
                    trimPreviewContainer.classList.add("hidden");
                }
            }
        }

        if (subTranslateContainer) {
            if (data.subtitles && data.subtitles.length > 0) {
                subTranslateContainer.classList.remove("hidden");
            } else {
                subTranslateContainer.classList.add("hidden");
            }
        }
        if (translateCheckbox) {
            translateCheckbox.checked = false;
        }

        // Show result section
        resultSection.classList.remove("hidden");
        resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 3. Download Execution via Asynchronous Server Task & Polling
    async function triggerDownload(btn, formatId, ext, label, quality, customUrl, episode = "", server = "") {
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
            const requestBody = {
                url: (formatId.startsWith("direct_") || formatId === "image_preview" || formatId === "image_download") ? (customUrl || activeUrl) : activeUrl,
                format_id: formatId,
                ext: ext,
                quality: quality,
                title: videoTitle.textContent,
                episode: episode,
                server: server,
                client_id: clientId
            };

            const trimCheckbox = document.getElementById("trim-checkbox");
            if (trimCheckbox && trimCheckbox.checked) {
                requestBody.trim_start = document.getElementById("trim-start").value.trim();
                requestBody.trim_end = document.getElementById("trim-end").value.trim();
            }

            const translateCheckbox = document.getElementById("translate-subs-checkbox");
            const subTranslateContainer = document.getElementById("sub-translate-container");
            if (translateCheckbox && translateCheckbox.checked && subTranslateContainer && !subTranslateContainer.classList.contains("hidden")) {
                requestBody.translate_subs = "vi";
            }

            // Export Format Type
            const exportTypeSelect = document.getElementById("export-type-select");
            if (exportTypeSelect) {
                requestBody.export_type = exportTypeSelect.value;
            }

            // Cinematic color filter preset
            const colorFilterSelect = document.getElementById("color-filter-select");
            if (colorFilterSelect) {
                requestBody.color_filter = colorFilterSelect.value;
            }

            // AI Voiceover settings
            const voiceoverCb = document.getElementById("voiceover-checkbox");
            const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
            if (voiceoverCb && voiceoverCb.checked) {
                requestBody.voiceover_active = true;
                if (voiceoverVoiceSelect) {
                    requestBody.voiceover_voice = voiceoverVoiceSelect.value;
                }
            }

            // Cloud sync upload settings
            const cloudSyncSelect = document.getElementById("cloud-sync-select");
            if (cloudSyncSelect) {
                requestBody.cloud_destination = cloudSyncSelect.value;
                if (cloudSyncSelect.value === "telegram") {
                    const tgBotToken = document.getElementById("tg-bot-token");
                    const tgChatId = document.getElementById("tg-chat-id");
                    if (tgBotToken && tgChatId) {
                        requestBody.tg_bot_token = tgBotToken.value.trim();
                        requestBody.tg_chat_id = tgChatId.value.trim();
                    }
                }
            }

            // Step A: Request the server to start the download task in the background
            const response = await fetch("/api/download", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Failed to enqueue download task on server.");
            }

            const downloadId = data.download_id;
            activeDownloadId = downloadId;
            console.log(`Download enqueued. ID: ${downloadId}`);

            // Step B: Set up Server-Sent Events (SSE) to fetch status progress
            pollingInterval = new EventSource(`/api/download/progress/${downloadId}`);
            
            pollingInterval.onmessage = (event) => {
                try {
                    const statusData = JSON.parse(event.data);
                    
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
                        
                        let msg = statusData.message;
                        if (statusData.speed && statusData.eta) {
                            msg += ` | Speed: ${statusData.speed} | ETA: ${statusData.eta}`;
                        } else if (statusData.speed) {
                            msg += ` | Speed: ${statusData.speed}`;
                        } else if (statusData.eta) {
                            msg += ` | ETA: ${statusData.eta}`;
                        }
                        downloadStatusMessage.textContent = msg;
                    } 
                    else if (statusData.status === "merging" || statusData.status === "processing") {
                        progressBarFill.classList.add("striped");
                        progressBarFill.style.width = `${statusData.progress}%`;
                        progressPercent.textContent = `${statusData.progress}%`;
                        downloadStatusTitle.textContent = statusData.status === "merging" ? "Merging streams..." : "Processing audio...";
                        downloadStatusMessage.textContent = statusData.message;
                    } 
                    else if (statusData.status === "complete") {
                        if (pollingInterval) {
                            pollingInterval.close();
                            pollingInterval = null;
                        }
                        
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

                        // Trigger file download only if not cloud sync upload
                        const cloudSyncSelect = document.getElementById("cloud-sync-select");
                        const isCloudUpload = cloudSyncSelect && cloudSyncSelect.value !== "local";

                        if (isCloudUpload) {
                            downloadStatusMessage.textContent = "File uploaded successfully to your Cloud storage!";
                        } else {
                            const downloadAnchor = document.createElement("a");
                            downloadAnchor.href = `/api/download/file/${downloadId}`;
                            document.body.appendChild(downloadAnchor);
                            downloadAnchor.click();
                            downloadAnchor.remove();
                        }
                    } 
                    else if (statusData.status === "error") {
                        throw new Error(statusData.error || statusData.message || "An error occurred on the downloader backend.");
                    }
                } catch (pollErr) {
                    if (pollingInterval) {
                        pollingInterval.close();
                        pollingInterval = null;
                    }
                    handleDownloadFailure(pollErr.message, activeRow, allButtons);
                }
            };

            pollingInterval.onerror = (err) => {
                if (pollingInterval) {
                    pollingInterval.close();
                    pollingInterval = null;
                }
                handleDownloadFailure("Loss of SSE connection to server progress handler.", activeRow, allButtons);
            };

        } catch (err) {
            handleDownloadFailure(err.message, activeRow, allButtons);
        }
    }

    function escapeHTML(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;")
                  .replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;")
                  .replace(/"/g, "&quot;")
                  .replace(/'/g, "&#039;");
    }

    function handleDownloadFailure(errorMessageText, activeRow, allButtons) {
        progressBarFill.classList.remove("striped");
        progressBarFill.style.width = "0%";
        progressPercent.textContent = "Error";
        
        downloadProgress.classList.add("state-error");
        downloadStatusTitle.textContent = "Download failed";
        
        let rawError = errorMessageText || "Đã xảy ra lỗi trong quá trình xếp hàng tải xuống.";
        let friendlyMessage = rawError;
        const lowerErr = rawError.toLowerCase();
        
        if (lowerErr.includes("fallback download also failed") || lowerErr.includes("returned non-zero code")) {
            friendlyMessage = "Không thể tải về từ nguồn phát này. Nguồn phát có thể đã bị nhà cung cấp mã hóa hoặc chặn lượt tải. Bạn vui lòng chọn Server khác (ví dụ Server #1) hoặc thử lại sau.";
        } else if (lowerErr.includes("429") || lowerErr.includes("too many requests") || lowerErr.includes("rate limit") || lowerErr.includes("rate-limit")) {
            friendlyMessage = "Yêu cầu bị giới hạn tần suất từ IP này (Lỗi 429 - Too Many Requests). Bạn vui lòng đợi vài phút rồi thử lại, hoặc cập nhật Cookie/đổi kết nối mạng.";
        } else if (lowerErr.includes("403") || lowerErr.includes("forbidden") || lowerErr.includes("access denied")) {
            friendlyMessage = "Truy cập bị từ chối (Lỗi 403 - Forbidden). Nguồn phát có thể yêu cầu Cookie đăng nhập hợp lệ hoặc đang chặn IP máy chủ.";
        } else if (lowerErr.includes("404") || lowerErr.includes("not found")) {
            friendlyMessage = "Không tìm thấy tài nguyên (Lỗi 404 - Not Found). Vui lòng kiểm tra lại đường dẫn xem bài viết/video có còn tồn tại không.";
        } else if (lowerErr.includes("sign in to confirm you're not a bot") || lowerErr.includes("confirm you're not a bot") || lowerErr.includes("confirm you are not a bot")) {
            friendlyMessage = "Tải về bị chặn do yêu cầu xác minh robot (Confirm you are not a bot). Hãy thử lại sau hoặc cập nhật Cookie trong mục 'Cài đặt Cookies'.";
        } else if (lowerErr.includes("login") || lowerErr.includes("logged-in") || lowerErr.includes("cookie") || lowerErr.includes("private")) {
            friendlyMessage = "Nội dung này yêu cầu đăng nhập hoặc cookie tài khoản để truy cập. Vui lòng đăng nhập trên trình duyệt, xuất cookie và cập nhật trong mục 'Cài đặt Cookies'.";
        } else if (lowerErr.includes("unsupported url")) {
            friendlyMessage = "Đường dẫn không được hỗ trợ tải về trực tiếp. Hãy kiểm tra lại đường dẫn.";
        } else if (lowerErr.includes("connection refused") || lowerErr.includes("timeout") || lowerErr.includes("timed out")) {
            friendlyMessage = "Lỗi kết nối tới máy chủ nguồn. Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.";
        }

        let htmlContent = `<span>${friendlyMessage}</span>`;
        if (errorMessageText) {
            htmlContent += `<details class="error-details">
                <summary class="error-summary">Chi tiết lỗi (Technical details)</summary>
                <pre class="error-pre">${escapeHTML(errorMessageText)}</pre>
            </details>`;
        }
        
        downloadStatusMessage.innerHTML = htmlContent;
        
        analyzeBtn.disabled = false;
        urlInput.disabled = false;
        allButtons.forEach(b => b.disabled = false);
        if (activeRow) {
            activeRow.classList.remove("is-downloading");
        }
    }

    // Error helper for analysis
    function showError(message) {
        const lowerMsg = (message || "").toLowerCase();
        let friendly = "Không thể trích xuất thông tin media từ đường dẫn này. Nguồn phát có thể đang chặn kết nối hoặc yêu cầu Cookie.";
        let technical = message;
        
        if (lowerMsg.includes("429") || lowerMsg.includes("too many requests") || lowerMsg.includes("rate limit") || lowerMsg.includes("rate-limit")) {
            friendly = "Yêu cầu trích xuất thông tin bị chặn do tần suất quá cao (Lỗi 429 - Too Many Requests). Vui lòng đổi kết nối mạng (Wifi/4G/VPN) hoặc thử lại sau ít phút.";
        } else if (lowerMsg.includes("403") || lowerMsg.includes("forbidden") || lowerMsg.includes("access denied")) {
            friendly = "Truy cập bị từ chối (Lỗi 403 - Forbidden). Nguồn phát có thể chặn kết nối hoặc cần Cookie đăng nhập hợp lệ.";
        } else if (lowerMsg.includes("404") || lowerMsg.includes("not found")) {
            friendly = "Không tìm thấy nội dung (Lỗi 404 - Not Found). Vui lòng kiểm tra lại đường dẫn bài viết/video.";
        } else if (lowerMsg.includes("sign in to confirm you're not a bot") || lowerMsg.includes("confirm you're not a bot") || lowerMsg.includes("confirm you are not a bot")) {
            friendly = "Trích xuất bị chặn do yêu cầu xác minh robot (Confirm you are not a bot). Hãy thử lại sau hoặc cập nhật Cookie trong mục 'Cài đặt Cookies'.";
        } else if (lowerMsg.includes("login") || lowerMsg.includes("logged-in") || lowerMsg.includes("cookie") || lowerMsg.includes("private") || lowerMsg.includes("sign in")) {
            friendly = "Nội dung này yêu cầu đăng nhập hoặc cookie tài khoản để truy cập. Vui lòng đăng nhập trên trình duyệt, xuất và tải lên file cookie J2TEAM (Netscape/JSON) trong mục 'Cài đặt Cookies'.";
        } else if (lowerMsg.includes("unsupported url")) {
            friendly = "Đường dẫn không được hỗ trợ tải về trực tiếp. Hãy kiểm tra lại đường dẫn.";
        } else if (lowerMsg.includes("connection refused") || lowerMsg.includes("timeout") || lowerMsg.includes("timed out")) {
            friendly = "Lỗi kết nối tới máy chủ nguồn. Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.";
        } else if (message.startsWith("Unable to extract media metadata: ")) {
            const rawErr = message.replace("Unable to extract media metadata: ", "");
            friendly = "Không thể trích xuất thông tin media từ đường dẫn này. Chi tiết: " + rawErr;
        }

        let htmlContent = `<span>${friendly}</span>`;
        if (technical && technical !== friendly) {
            htmlContent += `<details class="error-details">
                <summary class="error-summary">Chi tiết lỗi kỹ thuật</summary>
                <pre class="error-pre">${escapeHTML(technical)}</pre>
            </details>`;
        }
        
        errorMessage.innerHTML = htmlContent;
        errorCard.classList.remove("hidden");
        errorCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // Dynamic Media Preview Orchestrator
    async function triggerPreview(btn, formatId, ext, label, quality, customUrl, episode = "", server = "") {
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
        stopAllPreviewPlaybacks();

        // Image Preview Flow
        if (ext === "jpg" || ext === "png" || ext === "jpeg" || formatId === "image_preview") {
            const finalUrl = formatId === "image_preview" 
                ? `/api/download/image?url=${encodeURIComponent(customUrl)}&client_id=${encodeURIComponent(clientId)}` 
                : customUrl;
            
            previewActiveUrl = finalUrl;
            const cleanTitle = getSafeTitle(videoTitle.textContent, "image");
            const cleanLabel = label.replace(/\s*\(\d+x\d+\)/, "");
            previewActiveFilename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${ext}`;
            
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

        // Direct stream preview (stream-on-demand)
        const isYouTube = activeUrl.includes("youtube.com") || activeUrl.includes("youtu.be") || activeUrl.includes("googlevideo.com");
        const isDirectStream = formatId.startsWith("direct_") || 
                               (customUrl && customUrl.startsWith("http") && !isYouTube);
        
        if (isDirectStream) {
            const streamUrl = customUrl || activeUrl;
            previewActiveUrl = streamUrl;
            previewActiveDownloadId = null;
            const cleanTitle = getSafeTitle(videoTitle.textContent, "video");
            previewActiveFilename = `${cleanTitle}_Episode_${episode || 1}_${server || "Server"}.${ext}`;

            const proxyStreamUrl = `/api/proxy/stream?url=${encodeURIComponent(streamUrl)}&client_id=${encodeURIComponent(clientId)}`;

            previewLoader.classList.add("hidden");
            
            if (ext === "mp3" || ext === "m4a") {
                if (previewAudioPlayer) {
                    previewAudioPlayer.src = proxyStreamUrl;
                    previewAudioPlayer.load();
                    previewAudioContainer.classList.remove("hidden");
                    previewAudioPlayer.play().catch(e => console.log("Playback blocked"));
                }
            } else {
                if (previewVideoPlayer) {
                    previewVideoContainer.classList.remove("hidden");
                    const isM3u8 = ext === "m3u8" || streamUrl.includes(".m3u8");
                    
                    previewVideoPlayer.onerror = () => {
                        console.warn("HTML5 Video Error");
                        previewLoaderText.textContent = "Không thể phát nguồn này trực tiếp. Vui lòng chọn Server khác (như Server #1) hoặc bấm nút Tải về bên dưới.";
                        previewLoader.classList.remove("hidden");
                        previewVideoContainer.classList.add("hidden");
                        stopAllPreviewPlaybacks();
                    };
                    
                    if (isM3u8 && typeof Hls !== "undefined" && Hls.isSupported()) {
                        const hls = new Hls({
                            maxBufferSize: 30 * 1024 * 1024, // 30MB buffer max
                            maxBufferLength: 30 // 30 seconds max buffer ahead
                        });
                        hls.loadSource(proxyStreamUrl);
                        hls.attachMedia(previewVideoPlayer);
                        hls.on(Hls.Events.MANIFEST_PARSED, () => {
                            previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                        });
                        hls.on(Hls.Events.ERROR, function(event, data) {
                            if (data.fatal) {
                                console.warn("HLS fatal error:", data.type);
                                previewLoaderText.textContent = "Server này bị nhà cung cấp mã hóa nguồn phát, không thể xem trước trực tiếp. Bạn vui lòng chọn Server khác (ví dụ Server #1) hoặc bấm nút Tải về bên dưới.";
                                previewLoader.classList.remove("hidden");
                                previewVideoContainer.classList.add("hidden");
                                stopAllPreviewPlaybacks();
                            }
                        });
                        previewVideoPlayer.hlsInstance = hls;
                    } else {
                        previewVideoPlayer.src = proxyStreamUrl;
                        previewVideoPlayer.load();
                        previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                    }
                }
            }
            return;
        }

        // Audio, Video, Subtitle Preview Flow (Downloads to server & streams)
        try {
            const payload = {
                url: (formatId.startsWith("direct_") || formatId === "image_preview" || formatId === "image_download") ? (customUrl || activeUrl) : activeUrl,
                format_id: formatId,
                ext: ext,
                quality: quality || "192",
                title: videoTitle.textContent,
                episode: episode,
                server: server,
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

            // Step B: Set up Server-Sent Events (SSE) to fetch status progress
            let pollInterval = new EventSource(`/api/download/progress/${downloadId}`);
            previewActivePollInterval = pollInterval;
            
            // Periodically check if preview modal was closed
            const modalCheckTimer = setInterval(() => {
                if (previewModal.classList.contains("hidden")) {
                    if (previewActivePollInterval) {
                        previewActivePollInterval.close();
                        previewActivePollInterval = null;
                    }
                    clearInterval(modalCheckTimer);
                }
            }, 500);

            pollInterval.onmessage = async (event) => {
                try {
                    const statusData = JSON.parse(event.data);

                    if (statusData.status === "complete") {
                        if (previewActivePollInterval) {
                            previewActivePollInterval.close();
                            previewActivePollInterval = null;
                        }
                        clearInterval(modalCheckTimer);
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
                        if (previewActivePollInterval) {
                            previewActivePollInterval.close();
                            previewActivePollInterval = null;
                        }
                        clearInterval(modalCheckTimer);
                        previewLoaderText.textContent = `Preview failed: ${statusData.error || "Unknown server error."}`;
                    } else {
                        const progress = statusData.progress || 0;
                        let msg = statusData.message || "Downloading stream components...";
                        if (statusData.speed && statusData.eta) {
                            msg += ` | Speed: ${statusData.speed} | ETA: ${statusData.eta}`;
                        } else if (statusData.speed) {
                            msg += ` | Speed: ${statusData.speed}`;
                        }
                        previewLoaderText.textContent = `[${progress}%] ${msg}`;
                    }
                } catch (err) {
                    console.error("Error handling preview SSE progress:", err);
                }
            };

            pollInterval.onerror = (err) => {
                if (previewActivePollInterval) {
                    previewActivePollInterval.close();
                    previewActivePollInterval = null;
                }
                clearInterval(modalCheckTimer);
                previewLoaderText.textContent = "Connection to preview progress server lost.";
            };

        } catch (err) {
            console.error(err);
                        previewLoaderText.textContent = "Connection failed. Unable to start preview.";
        }
    }

    // Advanced Settings Persistence Helpers
    function saveCurrentSettingsToHistory() {
        if (!activeUrl) return;
        try {
            const trimCheckbox = document.getElementById("trim-checkbox");
            const trimStart = document.getElementById("trim-start");
            const trimEnd = document.getElementById("trim-end");
            const translateSubsCheckbox = document.getElementById("translate-subs-checkbox");
            const exportTypeSelect = document.getElementById("export-type-select");
            const colorFilterSelect = document.getElementById("color-filter-select");
            const voiceoverCheckbox = document.getElementById("voiceover-checkbox");
            const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
            const cloudSyncSelect = document.getElementById("cloud-sync-select");

            const settings = {
                trim_active: trimCheckbox ? trimCheckbox.checked : false,
                trim_start: trimStart ? trimStart.value : "00:00:00",
                trim_end: trimEnd ? trimEnd.value : "00:00:10",
                translate_subs: translateSubsCheckbox ? translateSubsCheckbox.checked : false,
                export_type: exportTypeSelect ? exportTypeSelect.value : "default",
                color_filter: colorFilterSelect ? colorFilterSelect.value : "none",
                voiceover_active: voiceoverCheckbox ? voiceoverCheckbox.checked : false,
                voiceover_voice: voiceoverVoiceSelect ? voiceoverVoiceSelect.value : "vi-VN-HoaiMyNeural",
                cloud_sync: cloudSyncSelect ? cloudSyncSelect.value : "local"
            };

            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            const item = history.find(it => it.url === activeUrl);
            if (item) {
                item.settings = settings;
                localStorage.setItem("downloader_history", JSON.stringify(history));
            }
        } catch (e) {
            console.error("Error saving current settings to history:", e);
        }
    }

    function restoreSettingsForUrl(item) {
        if (!item) return;
        if (!item.settings) {
            resetAdvancedSettingsToDefaults();
            return;
        }
        try {
            const s = item.settings;
            const trimCheckbox = document.getElementById("trim-checkbox");
            const trimStart = document.getElementById("trim-start");
            const trimEnd = document.getElementById("trim-end");
            const translateSubsCheckbox = document.getElementById("translate-subs-checkbox");
            const exportTypeSelect = document.getElementById("export-type-select");
            const colorFilterSelect = document.getElementById("color-filter-select");
            const voiceoverCheckbox = document.getElementById("voiceover-checkbox");
            const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
            const cloudSyncSelect = document.getElementById("cloud-sync-select");

            // Disable save listener temporary during restoration to avoid loops
            isRestoringSettings = true;

            if (trimCheckbox) {
                trimCheckbox.checked = !!s.trim_active;
                trimCheckbox.dispatchEvent(new Event("change"));
            }
            if (trimStart) trimStart.value = s.trim_start || "00:00:00";
            if (trimEnd) trimEnd.value = s.trim_end || "00:00:10";
            if (translateSubsCheckbox) translateSubsCheckbox.checked = !!s.translate_subs;
            if (exportTypeSelect) exportTypeSelect.value = s.export_type || "default";
            if (colorFilterSelect) {
                colorFilterSelect.value = s.color_filter || "none";
                colorFilterSelect.dispatchEvent(new Event("change"));
            }
            if (voiceoverCheckbox) {
                voiceoverCheckbox.checked = !!s.voiceover_active;
                voiceoverCheckbox.dispatchEvent(new Event("change"));
            }
            if (voiceoverVoiceSelect) voiceoverVoiceSelect.value = s.voiceover_voice || "vi-VN-HoaiMyNeural";
            if (cloudSyncSelect) {
                cloudSyncSelect.value = s.cloud_sync || "local";
                cloudSyncSelect.dispatchEvent(new Event("change"));
            }

            isRestoringSettings = false;
        } catch (e) {
            console.error("Error restoring settings for URL:", e);
            isRestoringSettings = false;
        }
    }

    function resetAdvancedSettingsToDefaults() {
        try {
            const trimCheckbox = document.getElementById("trim-checkbox");
            const trimStart = document.getElementById("trim-start");
            const trimEnd = document.getElementById("trim-end");
            const translateSubsCheckbox = document.getElementById("translate-subs-checkbox");
            const exportTypeSelect = document.getElementById("export-type-select");
            const colorFilterSelect = document.getElementById("color-filter-select");
            const voiceoverCheckbox = document.getElementById("voiceover-checkbox");
            const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
            const cloudSyncSelect = document.getElementById("cloud-sync-select");

            isRestoringSettings = true;

            if (trimCheckbox) {
                trimCheckbox.checked = false;
                trimCheckbox.dispatchEvent(new Event("change"));
            }
            if (trimStart) trimStart.value = "00:00:00";
            if (trimEnd) trimEnd.value = "00:00:10";
            if (translateSubsCheckbox) translateSubsCheckbox.checked = false;
            if (exportTypeSelect) exportTypeSelect.value = "default";
            if (colorFilterSelect) {
                colorFilterSelect.value = "none";
                colorFilterSelect.dispatchEvent(new Event("change"));
            }
            if (voiceoverCheckbox) {
                voiceoverCheckbox.checked = false;
                voiceoverCheckbox.dispatchEvent(new Event("change"));
            }
            if (voiceoverVoiceSelect) voiceoverVoiceSelect.value = "vi-VN-HoaiMyNeural";
            if (cloudSyncSelect) {
                cloudSyncSelect.value = "local";
                cloudSyncSelect.dispatchEvent(new Event("change"));
            }

            isRestoringSettings = false;
        } catch (e) {
            console.error("Error resetting settings to defaults:", e);
            isRestoringSettings = false;
        }
    }

    // Attach Change Listeners
    let isRestoringSettings = false;
    const settingsControls = [
        { id: "trim-checkbox", event: "change" },
        { id: "trim-start", event: "input" },
        { id: "trim-end", event: "input" },
        { id: "translate-subs-checkbox", event: "change" },
        { id: "export-type-select", event: "change" },
        { id: "color-filter-select", event: "change" },
        { id: "voiceover-checkbox", event: "change" },
        { id: "voiceover-voice-select", event: "change" },
        { id: "cloud-sync-select", event: "change" }
    ];

    settingsControls.forEach(ctrl => {
        const el = document.getElementById(ctrl.id);
        if (el) {
            el.addEventListener(ctrl.event, () => {
                if (!isRestoringSettings) {
                    saveCurrentSettingsToHistory();
                }
            });
        }
    });
});

// --- Star Grid Mesh (3D Gravity Well & Elastic Net) Effect ---
document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("cursor-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let grid = [];
    let particles = [];
    let sparkles = [];
    let rippleBuffer1 = [];
    let rippleBuffer2 = [];
    let cols = 0;
    let rows = 0;
    let currentSpacing = 54; // Dynamically bound to window.canvasSettings.spacing
    
    let mouse = { x: 0, y: 0, active: false, inactivityTimeout: null };
    let lastMouse = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

    // Resize canvas and recreate the grid mesh
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        initGrid();
    }
    window.addEventListener("resize", resizeCanvas);

    // Track mouse speed and touch events for ripple propagation
    let mouseSpeed = 0;
    let prevMouseX = window.innerWidth / 2;
    let prevMouseY = window.innerHeight / 2;

    function handleMouseMove(x, y) {
        let dx = x - prevMouseX;
        let dy = y - prevMouseY;
        mouseSpeed = Math.sqrt(dx*dx + dy*dy);
        prevMouseX = x;
        prevMouseY = y;

        mouse.x = x;
        mouse.y = y;
        mouse.active = true;
        
        lastMouse.x = x;
        lastMouse.y = y;

        // Disturb the ripple buffer at the grid node nearest to the mouse
        if (window.canvasSettings.ripplesEnabled && cols > 0 && rows > 0) {
            let col = Math.round((x + 0.5 * currentSpacing) / currentSpacing);
            let row = Math.round((y + 0.5 * currentSpacing) / currentSpacing);
            
            // Disturb a small 3x3 region around the mouse
            for (let c = col - 1; c <= col + 1; c++) {
                for (let r = row - 1; r <= row + 1; r++) {
                    if (c >= 0 && c < cols && r >= 0 && r < rows) {
                        // Disturb proportional to mouse speed
                        rippleBuffer1[c][r] = -Math.min(100, mouseSpeed * 1.5);
                    }
                }
            }
        }

        // Spawn glowing stardust vortex particles at the mouse tip
        if (window.canvasSettings.sparklesEnabled) {
            const currentMaxDist = window.canvasSettings.maxDist || 180;
            let spawnCount = Math.floor(Math.random() * (currentMaxDist / 80)) + 1;
            spawnCount = Math.min(5, spawnCount); // Cap per tick

            if (sparkles.length < 250) {
                for (let i = 0; i < spawnCount; i++) {
                    sparkles.push(new Sparkle(x, y));
                }
            }
        }

        clearTimeout(mouse.inactivityTimeout);
        mouse.inactivityTimeout = setTimeout(() => {
            mouse.active = false;
            mouseSpeed = 0;
        }, 1200); // return to normal shape after 1.2s of inactivity
    }

    window.addEventListener("mousemove", (e) => {
        handleMouseMove(e.clientX, e.clientY);
    });

    window.addEventListener("mouseleave", () => {
        mouse.active = false;
        mouseSpeed = 0;
    });

    window.addEventListener("touchmove", (e) => {
        if (e.touches.length > 0) {
            handleMouseMove(e.touches[0].clientX, e.touches[0].clientY);
        }
    }, { passive: true });

    window.addEventListener("touchend", () => {
        mouse.active = false;
        mouseSpeed = 0;
    });

    window.addEventListener("click", (e) => {
        if (!window.canvasSettings.ripplesEnabled) return;
        let x = e.clientX;
        let y = e.clientY;
        if (cols > 0 && rows > 0) {
            let col = Math.round((x + 0.5 * currentSpacing) / currentSpacing);
            let row = Math.round((y + 0.5 * currentSpacing) / currentSpacing);
            
            // Inject a much larger force field in a 5x5 region to propagate a big mechanical wave
            for (let c = col - 2; c <= col + 2; c++) {
                for (let r = row - 2; r <= row + 2; r++) {
                    if (c >= 0 && c < cols && r >= 0 && r < rows) {
                        let distFromCenter = Math.sqrt((c - col) * (c - col) + (r - row) * (r - row));
                        let strength = (1 - distFromCenter / 3) * -180;
                        if (strength < 0) {
                            rippleBuffer1[c][r] = strength;
                        }
                    }
                }
            }
        }
    });

    // Get theme colors from CSS variables
    let activeColors = ['#00f2fe', '#fe0979'];
    let isLightTheme = false;
    function updateColors() {
        isLightTheme = document.body.classList.contains("light-theme");
        const style = getComputedStyle(document.body);
        const cyan = style.getPropertyValue('--cyan').trim() || '#00f2fe';
        const purple = style.getPropertyValue('--purple').trim() || '#fe0979';
        activeColors = [cyan, purple];
    }
    updateColors();
    window.updateCanvasColors = updateColors;

    // Helper to blend two colors dynamically based on tension/displacement ratio
    function blendColors(c1, c2, ratio) {
        if (ratio <= 0) return c1;
        if (ratio >= 1) return c2;
        
        let r1 = parseInt(c1.substring(1, 3), 16);
        let g1 = parseInt(c1.substring(3, 5), 16);
        let b1 = parseInt(c1.substring(5, 7), 16);
        
        let r2 = parseInt(c2.substring(1, 3), 16);
        let g2 = parseInt(c2.substring(3, 5), 16);
        let b2 = parseInt(c2.substring(5, 7), 16);
        
        let r = Math.round(r1 + (r2 - r1) * ratio);
        let g = Math.round(g1 + (g2 - g1) * ratio);
        let b = Math.round(b1 + (b2 - b1) * ratio);
        
        return `rgb(${r}, ${g}, ${b})`;
    }

    class Sparkle {
        constructor(x, y) {
            const currentMaxDist = window.canvasSettings.maxDist || 180;
            const scaleFactor = currentMaxDist / 180.0;

            // Scatter the spawn origin slightly based on gravity radius
            let startRadius = Math.random() * 6 * scaleFactor;
            let startAngle = Math.random() * Math.PI * 2;
            this.x = x + Math.cos(startAngle) * startRadius;
            this.y = y + Math.sin(startAngle) * startRadius;

            let angle = Math.random() * Math.PI * 2;
            let speed = (Math.random() * 2.5 + 1.5) * scaleFactor;
            this.vx = Math.cos(angle) * speed;
            this.vy = Math.sin(angle) * speed - 0.4 * scaleFactor; // slight upward drift
            this.size = (Math.random() * 4.0 + 2.5) * scaleFactor; // scales with gravity radius
            this.life = Math.random() * 25 + 25;
            this.maxLife = this.life;
            this.color = activeColors[Math.floor(Math.random() * 2)];
            this.rotation = Math.random() * Math.PI;
            this.rotSpeed = (Math.random() - 0.5) * 0.1;
        }
        update() {
            // Gravitational pull & spiral vortex towards mouse
            if (mouse.active) {
                let dx = mouse.x - this.x;
                let dy = mouse.y - this.y;
                let dist = Math.sqrt(dx*dx + dy*dy);
                const currentMaxDist = window.canvasSettings.maxDist || 180;
                if (dist > 8 && dist < currentMaxDist) {
                    let force = (1 - dist / currentMaxDist); // stronger pull closer to mouse
                    // Pull strength (gravitational attraction)
                    let pull = force * force * 0.28;
                    this.vx += (dx / dist) * pull;
                    this.vy += (dy / dist) * pull;

                    // Tangential swirl (orbital velocity)
                    let swirl = force * 0.45;
                    this.vx += (-dy / dist) * swirl;
                    this.vy += (dx / dist) * swirl;
                }
            }

            this.x += this.vx;
            this.y += this.vy;
            this.vx *= 0.94; // slightly damp speed to spiral in
            this.vy *= 0.94;
            this.rotation += this.rotSpeed;
            this.life--;
        }
        draw(ctx) {
            let alpha = this.life / this.maxLife;
            let size = this.size * alpha;
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.rotation);
            ctx.beginPath();
            
            const shape = window.canvasSettings.sparkleShape || 'star';
            if (shape === 'star') {
                let inner = size * 0.35;
                ctx.moveTo(0, -size);
                for (let i = 0; i < 4; i++) {
                    let rot = -Math.PI / 2 + (Math.PI / 2) * i;
                    ctx.lineTo(Math.cos(rot) * size, Math.sin(rot) * size);
                    rot += Math.PI / 4;
                    ctx.lineTo(Math.cos(rot) * inner, Math.sin(rot) * inner);
                }
            } else if (shape === 'circle') {
                ctx.arc(0, 0, size * 0.8, 0, Math.PI * 2);
            } else if (shape === 'diamond') {
                ctx.moveTo(0, -size);
                ctx.lineTo(size * 0.8, 0);
                ctx.lineTo(0, size * 0.8);
                ctx.lineTo(-size * 0.8, 0);
            } else if (shape === 'square') {
                ctx.rect(-size * 0.7, -size * 0.7, size * 1.4, size * 1.4);
            } else if (shape === 'heart') {
                ctx.moveTo(0, size * 0.7);
                ctx.bezierCurveTo(-size * 0.8, size * 0.2, -size * 0.8, -size * 0.6, 0, -size * 0.3);
                ctx.bezierCurveTo(size * 0.8, -size * 0.6, size * 0.8, size * 0.2, 0, size * 0.7);
            }
            
            ctx.closePath();
            ctx.fillStyle = this.color;
            ctx.globalAlpha = alpha;
            ctx.shadowBlur = 8;
            ctx.shadowColor = this.color;
            ctx.fill();
            ctx.restore();
        }
    }

    class Particle {
        constructor(baseX, baseY, col, row) {
            this.baseX = baseX;
            this.baseY = baseY;
            this.col = col;
            this.row = row;

            this.x = baseX;
            this.y = baseY;
            this.z = 0; // 3D depth displacement

            this.vx = 0;
            this.vy = 0;
            this.vz = 0;

            this.baseSize = Math.random() * 2 + 2.5; // Elegant star size
            this.spikes = 4;
            this.colorIndex = (col + row) % 2; // checkerboard theme coloring
            
            this.rotation = Math.random() * Math.PI;
            this.rotationSpeed = (Math.random() - 0.5) * 0.02;
            
            // Screen projected positions
            this.px = this.x;
            this.py = this.y;
            this.scale = 1;

            // Anchor factor for physical net behavior: boundary nodes are locked to 0
            let distCol = Math.min(col, cols - 1 - col);
            let distRow = Math.min(row, rows - 1 - row);
            this.anchorFactor = Math.min(1.0, distCol / 2.0) * Math.min(1.0, distRow / 2.0);
        }

        update(mouse) {
            this.rotation += this.rotationSpeed;

            // 1. Slow wave movement for the floating effect (superimposed organic wave)
            let time = Date.now() * 0.0005;
            let waveX = Math.sin(time * 1.3 + (this.col * 0.22) + (this.row * 0.15)) * 10 + Math.cos(time * 0.7 + (this.row * 0.35)) * 4;
            let waveY = Math.cos(time * 1.1 + (this.col * 0.15) + (this.row * 0.22)) * 10 + Math.sin(time * 0.6 + (this.col * 0.35)) * 4;

            // Keep grid coordinate stable globally
            let currentOrigX = this.baseX + waveX * this.anchorFactor;
            let currentOrigY = this.baseY + waveY * this.anchorFactor;

            // Fetch wave height from the 2D ripple buffer
            let targetZ = 0;
            if (window.canvasSettings.ripplesEnabled && rippleBuffer1[this.col] && rippleBuffer1[this.col][this.row] !== undefined) {
                targetZ = rippleBuffer1[this.col][this.row] * this.anchorFactor;
            }

            // Calculate constant mouse indentation (funnel effect) centered under the cursor
            let dx = mouse.x - this.x;
            let dy = mouse.y - this.y;
            let dist = Math.sqrt(dx*dx + dy*dy);
            let indentZ = 0;

            const currentMaxDist = window.canvasSettings.maxDist || 180;

            if (mouse.active && dist < currentMaxDist) {
                const gravityMode = window.canvasSettings.gravityMode || 'pull';
                if (gravityMode !== 'none') {
                    // Cubic smoothstep for smooth gravity well
                    let t = dist / currentMaxDist;
                    let force = 1 - (3 * t * t - 2 * t * t * t);
                    const depth = window.canvasSettings.gravityDepth !== undefined ? window.canvasSettings.gravityDepth : 130;
                    const sign = gravityMode === 'push' ? 1 : -1;

                    // Push or pull Z based on gravity mode, scaled by anchorFactor
                    indentZ = sign * depth * force * this.anchorFactor;
                }
            }

            // 2. Spring physics for Z depth (combine ripple height and funnel indentation)
            let combinedTargetZ = targetZ + indentZ;
            this.vz += (combinedTargetZ - this.z) * 0.07; // physical spring coefficient
            this.vz *= 0.91; // damping
            this.z += this.vz;

            // 3. Horizontal coordinate restoration (let 3D perspective projection handle the funnel shift naturally)
            let targetX = currentOrigX;
            let targetY = currentOrigY;

            // 4. Spring physics for X and Y coordinate restoration
            this.vx += (targetX - this.x) * 0.06;
            this.vy += (targetY - this.y) * 0.06;
            this.vx *= 0.91;
            this.vy *= 0.91;

            this.x += this.vx;
            this.y += this.vy;
        }

        project(projX, projY, fov) {
            // Perspective projection relative to the indentation center (mouse position)
            // This ensures the funnel is mathematically centered exactly at the cursor!
            let scale = fov / (fov - this.z);
            this.scale = scale;
            this.px = projX + (this.x - projX) * scale;
            this.py = projY + (this.y - projY) * scale;
        }

        draw(ctx) {
            // Breathing size oscillation + high-frequency twinkle for a lifelike organic pulse
            let twinkle = Math.sin(Date.now() * 0.016 + this.col * 1.7 + this.row * 1.3) * 0.4;
            let breathe = Math.sin(Date.now() * 0.0025 + this.col * 0.5 + this.row * 0.3) * 0.55 + twinkle;
            
            // Tension increases brightness and size of the knot
            let tension = Math.min(1.5, Math.abs(this.z) / 80);
            let size = (this.baseSize + (isLightTheme ? 0.5 : 0) + breathe + tension * 1.5) * this.scale;
            if (size < 1) size = 1;

            let alpha = isLightTheme ? 0.45 + (this.scale * 0.45) : 0.2 + (this.scale * 0.6); // Deeper points fade away
            alpha += tension * 0.3;
            if (alpha < 0.1) alpha = 0.1;
            if (alpha > 1) alpha = 1;

            const color = activeColors[this.colorIndex];
            const innerRadius = size * 0.35;

            ctx.save();
            ctx.translate(this.px, this.py);

            // Draw a subtle outer glow circle at each knot (reduced size and alpha for delicate look)
            ctx.beginPath();
            ctx.arc(0, 0, size * 1.5, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.globalAlpha = alpha * 0.08;
            ctx.fill();

            // Draw the central 4-pointed knot star
            ctx.rotate(this.rotation);
            ctx.beginPath();

            let rot = -Math.PI / 2;
            let step = Math.PI / this.spikes;

            ctx.moveTo(0, -size);
            for (let i = 0; i < this.spikes; i++) {
                let x = Math.cos(rot) * size;
                let y = Math.sin(rot) * size;
                ctx.lineTo(x, y);
                rot += step;

                x = Math.cos(rot) * innerRadius;
                y = Math.sin(rot) * innerRadius;
                ctx.lineTo(x, y);
                rot += step;
            }
            ctx.lineTo(0, -size);
            ctx.closePath();

            ctx.fillStyle = color;
            ctx.globalAlpha = alpha;
            ctx.fill();
            ctx.restore();
        }
    }

    function initGrid() {
        // Read spacing from global settings
        currentSpacing = window.canvasSettings.spacing || 54;
        grid = [];
        particles = [];
        rippleBuffer1 = [];
        rippleBuffer2 = [];
        
        cols = Math.ceil(window.innerWidth / currentSpacing) + 2;
        rows = Math.ceil(window.innerHeight / currentSpacing) + 2;

        for (let c = 0; c < cols; c++) {
            grid[c] = [];
            rippleBuffer1[c] = new Float32Array(rows);
            rippleBuffer2[c] = new Float32Array(rows);
            for (let r = 0; r < rows; r++) {
                // Symmetrical grid offset
                let baseX = (c - 0.5) * currentSpacing;
                let baseY = (r - 0.5) * currentSpacing;

                let p = new Particle(baseX, baseY, c, r);
                grid[c][r] = p;
                particles.push(p);
            }
        }
    }

    // Initialize
    initGrid();
    resizeCanvas();

    // Loop
    let frameCount = 0;
    function animate() {
        frameCount++;
        if (frameCount % 60 === 0) {
            updateColors();
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Check if spacing has changed and re-initialize grid if needed
        if (window.canvasSettings.spacing !== currentSpacing) {
            initGrid();
        }

        const currentMaxDist = window.canvasSettings.maxDist || 180;

        // Center projection relative to active or last mouse coordinates
        let projX = mouse.active ? mouse.x : lastMouse.x;
        let projY = mouse.active ? mouse.y : lastMouse.y;
        let fov = 400; // perspective focal length

        // 0. Radial Gravity Well Glow (under the grid lines for layered depth)
        if (window.canvasSettings.gridEnabled && mouse.active) {
            let glowGrad = ctx.createRadialGradient(projX, projY, 0, projX, projY, currentMaxDist * 1.2);
            glowGrad.addColorStop(0, blendColors(activeColors[0], activeColors[1], 0.5));
            glowGrad.addColorStop(0.2, activeColors[0]);
            glowGrad.addColorStop(0.5, activeColors[1]);
            glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

            ctx.save();
            ctx.globalCompositeOperation = 'screen';
            ctx.globalAlpha = isLightTheme ? 0.14 : 0.08;
            ctx.fillStyle = glowGrad;
            ctx.beginPath();
            ctx.arc(projX, projY, currentMaxDist * 1.2, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        // 1. 2D Discrete Wave Equation Simulation (Water Ripple Propagation)
        if (window.canvasSettings.ripplesEnabled && cols > 0 && rows > 0 && rippleBuffer1.length > 0 && rippleBuffer2.length > 0) {
            for (let c = 1; c < cols - 1; c++) {
                for (let r = 1; r < rows - 1; r++) {
                    rippleBuffer2[c][r] = (
                        rippleBuffer1[c - 1][r] +
                        rippleBuffer1[c + 1][r] +
                        rippleBuffer1[c][r - 1] +
                        rippleBuffer1[c][r + 1]
                    ) / 2 - rippleBuffer2[c][r];
                    // Damping factor: keeps wave bouncing but dissipates energy slowly
                    rippleBuffer2[c][r] *= 0.975;
                }
            }

            // Swap ripple buffers
            let temp = rippleBuffer1;
            rippleBuffer1 = rippleBuffer2;
            rippleBuffer2 = temp;
        }

        // 2. Update and Project all grid nodes
        particles.forEach(p => {
            p.update(mouse);
            p.project(projX, projY, fov);
        });

        // 3. Draw connecting grid lines (mesh structure)
        if (window.canvasSettings.gridEnabled) {
            for (let c = 0; c < cols; c++) {
                for (let r = 0; r < rows; r++) {
                    let p1 = grid[c][r];
                    if (!p1) continue;

                    // Draw line to right neighbor
                    if (c + 1 < cols && grid[c + 1][r]) {
                        let p2 = grid[c + 1][r];
                        let baseAlpha = isLightTheme ? 0.32 : 0.08;
                        let lineAlpha = baseAlpha * ((p1.scale + p2.scale) / 2); // baseline alpha
                        
                        // Tension displacement calculation
                        let displacement = Math.max(Math.abs(p1.z), Math.abs(p2.z));
                        lineAlpha += (displacement / 150) * 0.22;

                        // Blend horizontal color: from cyan (rest) to purple (stressed)
                        let strokeColor = blendColors(activeColors[0], activeColors[1], displacement / 140);

                        // Outer Glow Envelope
                        ctx.strokeStyle = strokeColor;
                        ctx.globalAlpha = lineAlpha * 0.35;
                        ctx.lineWidth = 1.6;
                        ctx.beginPath();
                        ctx.moveTo(p1.px, p1.py);
                        ctx.lineTo(p2.px, p2.py);
                        ctx.stroke();

                        // Core Filament
                        ctx.globalAlpha = lineAlpha;
                        ctx.lineWidth = 0.6;
                        ctx.beginPath();
                        ctx.moveTo(p1.px, p1.py);
                        ctx.lineTo(p2.px, p2.py);
                        ctx.stroke();
                    }

                    // Draw line to bottom neighbor
                    if (r + 1 < rows && grid[c][r + 1]) {
                        let p2 = grid[c][r + 1];
                        let baseAlpha = isLightTheme ? 0.32 : 0.08;
                        let lineAlpha = baseAlpha * ((p1.scale + p2.scale) / 2);
                        
                        // Tension displacement calculation
                        let displacement = Math.max(Math.abs(p1.z), Math.abs(p2.z));
                        lineAlpha += (displacement / 150) * 0.22;

                        // Blend vertical color: from purple (rest) to cyan (stressed)
                        let strokeColor = blendColors(activeColors[1], activeColors[0], displacement / 140);

                        // Outer Glow Envelope
                        ctx.strokeStyle = strokeColor;
                        ctx.globalAlpha = lineAlpha * 0.35;
                        ctx.lineWidth = 1.6;
                        ctx.beginPath();
                        ctx.moveTo(p1.px, p1.py);
                        ctx.lineTo(p2.px, p2.py);
                        ctx.stroke();

                        // Core Filament
                        ctx.globalAlpha = lineAlpha;
                        ctx.lineWidth = 0.6;
                        ctx.beginPath();
                        ctx.moveTo(p1.px, p1.py);
                        ctx.lineTo(p2.px, p2.py);
                        ctx.stroke();
                    }
                }
            }

            // 4. Draw grid stars (knots)
            particles.forEach(p => {
                p.draw(ctx);
            });
        }

        // 5. Update and Draw active sparkler particles (stardust vortex)
        if (window.canvasSettings.sparklesEnabled) {
            for (let i = sparkles.length - 1; i >= 0; i--) {
                let s = sparkles[i];
                s.update();
                if (s.life <= 0) {
                    sparkles.splice(i, 1);
                } else {
                    s.draw(ctx);
                }
            }
        } else {
            sparkles = [];
        }

        requestAnimationFrame(animate);
    }
    animate();
});
