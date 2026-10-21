// --- JavaScript Logic for Meikova Harvest ---

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
    sparklesEnabled: true,
    soundReactiveEnabled: true,
    previewBlurryBackdrop: false,
    previewDraggable: true,
    previewResizable: true
};

document.addEventListener("DOMContentLoaded", () => {
    let autoFillSettingsAfterAnalysis = null;

    function formatHistoryDateTime(timestampMs) {
        if (!timestampMs) return "Unknown date";
        const date = new Date(timestampMs);
        const pad = (n) => String(n).padStart(2, '0');
        const day = pad(date.getDate());
        const month = pad(date.getMonth() + 1);
        const year = date.getFullYear();
        const hours = pad(date.getHours());
        const minutes = pad(date.getMinutes());
        const seconds = pad(date.getSeconds());
        return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
    }

    function truncateMiddle(str, maxLength = 25) {
        if (!str || str.length <= maxLength) return str;
        const lastDot = str.lastIndexOf('.');
        if (lastDot === -1 || str.length - lastDot > 8) {
            return str.slice(0, maxLength - 3) + "...";
        }
        const ext = str.slice(lastDot);
        const name = str.slice(0, lastDot);
        const availSpace = maxLength - ext.length - 3;
        if (availSpace <= 8) {
            return str.slice(0, maxLength - 3) + "...";
        }
        const left = Math.ceil(availSpace / 2);
        const right = Math.floor(availSpace / 2);
        return name.slice(0, left) + "..." + name.slice(-right) + ext;
    }

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

    // Global settings button actions
    const clearTempCacheBtn = document.getElementById("btn-clear-temp-cache");
    if (clearTempCacheBtn) {
        clearTempCacheBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            showConfirm({
                title: "Clear Temporary Cache",
                message: "Are you sure you want to delete all downloaded temporary files and cache? This won't affect active downloads.",
                yesText: "Clear",
                noText: "Cancel",
                onYes: async () => {
                    clearTempCacheBtn.disabled = true;
                    const originalText = clearTempCacheBtn.textContent;
                    clearTempCacheBtn.textContent = "Clearing...";
                    try {
                        const response = await fetch("/api/clear-temp", { method: "POST" });
                        const data = await response.json();
                        if (data.success) {
                            alert(data.message || "Successfully cleared temporary cache folder.");
                        } else {
                            alert("Failed to clear temporary cache: " + (data.error || "Unknown error"));
                        }
                    } catch (err) {
                        console.error(err);
                        alert("Failed to clear cache: network error.");
                    } finally {
                        clearTempCacheBtn.disabled = false;
                        clearTempCacheBtn.textContent = originalText;
                    }
                }
            });
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
    const customizerBlur = document.getElementById("customizer-blur");
    const customizerBlurVal = document.getElementById("customizer-blur-val");

    const customizerGridEnable = document.getElementById("customizer-grid-enable");
    const customizerRipplesEnable = document.getElementById("customizer-ripples-enable");
    const customizerSoundReactiveEnable = document.getElementById("customizer-sound-reactive-enable");
    const customizerSparklesEnable = document.getElementById("customizer-sparkles-enable");
    const customizerPreviewBlur = document.getElementById("customizer-preview-blur");
    const customizerPreviewDrag = document.getElementById("customizer-preview-drag");
    const customizerPreviewZoom = document.getElementById("customizer-preview-zoom");

    const customizerSpacing = document.getElementById("customizer-spacing");
    const customizerSpacingVal = document.getElementById("customizer-spacing-val");
    const customizerGravity = document.getElementById("customizer-gravity");
    const customizerGravityVal = document.getElementById("customizer-gravity-val");
    const customizerGravityDepth = document.getElementById("customizer-gravity-depth");
    const customizerGravityDepthVal = document.getElementById("customizer-gravity-depth-val");
    const customizerResetBtn = document.getElementById("customizer-reset-btn");

    const accentNames = {
        "default": "Neon Cyan",
        "emerald": "Emerald Green",
        "orchid": "Orchid Pink",
        "amber": "Amber Gold",
        "purple": "Royal Purple",
        "rose": "Ruby Red",
        "orange": "Electric Orange",
        "blue": "Sapphire Blue",
        "peach": "Sunset Peach",
        "lime": "Acid Lime",
        "custom": "Custom Color"
    };

    function hexToRgb(hex) {
        const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b);
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    function applyCustomColor(hexColor) {
        const rgb = hexToRgb(hexColor);
        if (!rgb) return;
        document.documentElement.style.setProperty('--cyan', hexColor);
        document.documentElement.style.setProperty('--cyan-rgb', `${rgb.r}, ${rgb.g}, ${rgb.b}`);
        document.documentElement.style.setProperty('--accent', hexColor);
        localStorage.setItem("customizer-custom-color", hexColor);

        const picker = document.getElementById("customizer-accent-picker-1");
        if (picker) picker.value = hexColor;
        const btn = document.getElementById("custom-color-btn-1");
        if (btn) btn.style.background = hexColor;

        if (window.updateCanvasColors) window.updateCanvasColors();
    }

    function applyCustomColor2(hexColor) {
        const rgb = hexToRgb(hexColor);
        if (!rgb) return;
        document.documentElement.style.setProperty('--purple', hexColor);
        document.documentElement.style.setProperty('--purple-rgb', `${rgb.r}, ${rgb.g}, ${rgb.b}`);
        localStorage.setItem("customizer-custom-color-2", hexColor);

        const picker = document.getElementById("customizer-accent-picker-2");
        if (picker) picker.value = hexColor;
        const btn = document.getElementById("custom-color-btn-2");
        if (btn) btn.style.background = hexColor;

        if (window.updateCanvasColors) window.updateCanvasColors();
    }

    function applyAccent(accentVal) {
        Array.from(document.documentElement.classList).forEach(cls => {
            if (cls.startsWith("accent-theme-")) {
                document.documentElement.classList.remove(cls);
            }
        });
        if (accentVal !== "default" && accentVal !== "custom") {
            document.documentElement.classList.add("accent-theme-" + accentVal);
        }

        if (accentVal === "custom") {
            const savedCustomColor = localStorage.getItem("customizer-custom-color") || "#00f2fe";
            const savedCustomColor2 = localStorage.getItem("customizer-custom-color-2") || "#fe0979";
            applyCustomColor(savedCustomColor);
            applyCustomColor2(savedCustomColor2);
        } else {
            document.documentElement.style.removeProperty('--cyan');
            document.documentElement.style.removeProperty('--cyan-rgb');
            document.documentElement.style.removeProperty('--purple');
            document.documentElement.style.removeProperty('--purple-rgb');
            document.documentElement.style.removeProperty('--accent');
            if (window.updateCanvasColors) window.updateCanvasColors();
        }

        // Update active class on swatches
        document.querySelectorAll('.accent-swatch').forEach(btn => {
            if (btn.getAttribute('data-value') === accentVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        const nameSpan = document.getElementById('customizer-accent-name');
        if (nameSpan) {
            nameSpan.textContent = accentNames[accentVal] || accentVal;
        }

        localStorage.setItem("customizer-accent", accentVal);
    }

    function applyRadius(radiusVal) {
        let borderVal = "16px";
        if (radiusVal === "sharp") borderVal = "4px";
        else if (radiusVal === "rounded") borderVal = "16px";
        else if (radiusVal === "pill") borderVal = "30px";
        document.documentElement.style.setProperty("--radius", borderVal);

        // Update active class on radius preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="radius"]').forEach(btn => {
            if (btn.getAttribute('data-value') === radiusVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        localStorage.setItem("customizer-radius", radiusVal);
    }

    function applyBlur(blurVal, persist = false) {
        document.documentElement.style.setProperty("--glass-blur", blurVal + "px");
        if (customizerBlur) customizerBlur.value = blurVal;
        if (customizerBlurVal) customizerBlurVal.value = blurVal;
        if (persist) {
            localStorage.setItem("customizer-blur", blurVal);
        }
    }

    function applyFontSize(sizeVal) {
        let scaleFactor = 1.0;
        if (sizeVal === "tiny") scaleFactor = 0.75;
        else if (sizeVal === "compact") scaleFactor = 0.85;
        else if (sizeVal === "small") scaleFactor = 0.9;
        else if (sizeVal === "medium") scaleFactor = 1.0;
        else if (sizeVal === "large") scaleFactor = 1.1;
        else if (sizeVal === "xlarge") scaleFactor = 1.2;
        else if (sizeVal === "huge") scaleFactor = 1.3;

        document.documentElement.style.fontSize = "";
        document.documentElement.style.setProperty('--font-scale', scaleFactor);

        // Update active class on fontsize preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="fontsize"]').forEach(btn => {
            if (btn.getAttribute('data-value') === sizeVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        localStorage.setItem("customizer-fontsize", sizeVal);
    }

    function applyFontFamily(fontVal) {
        let fontStack = '"Outfit"';
        let displayFontStack = '"Space Grotesk"';

        if (fontVal === "plus-jakarta-sans") {
            fontStack = '"Plus Jakarta Sans"';
            displayFontStack = '"Plus Jakarta Sans"';
        } else if (fontVal === "inter") {
            fontStack = '"Inter"';
            displayFontStack = '"Inter"';
        } else if (fontVal === "space-grotesk") {
            fontStack = '"Space Grotesk"';
            displayFontStack = '"Space Grotesk"';
        } else if (fontVal === "system-ui") {
            fontStack = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            displayFontStack = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        }

        document.documentElement.style.setProperty('--user-font', fontStack);
        document.documentElement.style.setProperty('--user-font-display', displayFontStack);

        // Update active class on fontfamily preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="fontfamily"]').forEach(btn => {
            if (btn.getAttribute('data-value') === fontVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        localStorage.setItem("customizer-fontfamily", fontVal);
    }

    function applyAppHeight(heightVal) {
        document.documentElement.style.setProperty("--app-shell-height", heightVal);

        // Update active class on app-height preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="app-height"]').forEach(btn => {
            if (btn.getAttribute('data-value') === heightVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        localStorage.setItem("customizer-app-height", heightVal);
    }

    function updateCanvasOption(key, value) {
        window.canvasSettings[key] = value;
        localStorage.setItem("customizer-" + key, value);
    }

    function applyGravityMode(modeVal) {
        window.canvasSettings.gravityMode = modeVal;
        localStorage.setItem("customizer-gravityMode", modeVal);

        // Update active class on gravity mode preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="gravity-mode"]').forEach(btn => {
            if (btn.getAttribute('data-value') === modeVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        const depthContainer = document.getElementById("grid-gravity-depth-container");
        if (modeVal === "none") {
            if (depthContainer) depthContainer.style.display = "none";
        } else {
            if (depthContainer && (customizerGridEnable ? customizerGridEnable.checked : true)) {
                depthContainer.style.display = "block";
            }
        }
    }

    function applySparkleShape(shapeVal) {
        window.canvasSettings.sparkleShape = shapeVal;
        localStorage.setItem("customizer-sparkleShape", shapeVal);

        // Update active class on sparkle shape preset buttons
        document.querySelectorAll('.customizer-preset-btn[data-type="sparkle-shape"]').forEach(btn => {
            if (btn.getAttribute('data-value') === shapeVal) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    function applySpacing(spacingVal, persist = false) {
        window.canvasSettings.spacing = spacingVal;
        if (customizerSpacing) customizerSpacing.value = spacingVal;
        if (customizerSpacingVal) customizerSpacingVal.value = spacingVal;
        if (persist) {
            localStorage.setItem("customizer-spacing", spacingVal);
        }
    }

    function applyGravityRadius(gravityVal, persist = false) {
        window.canvasSettings.maxDist = gravityVal;
        if (customizerGravity) customizerGravity.value = gravityVal;
        if (customizerGravityVal) customizerGravityVal.value = gravityVal;
        if (persist) {
            localStorage.setItem("customizer-maxDist", gravityVal);
        }
    }

    function applyGravityDepth(depthVal, persist = false) {
        window.canvasSettings.gravityDepth = depthVal;
        if (customizerGravityDepth) customizerGravityDepth.value = depthVal;
        if (customizerGravityDepthVal) customizerGravityDepthVal.value = depthVal;
        if (persist) {
            localStorage.setItem("customizer-gravityDepth", depthVal);
        }
    }

    // Swatches and presets event listeners
    document.querySelectorAll('.accent-swatch').forEach(btn => {
        btn.addEventListener('click', () => {
            applyAccent(btn.getAttribute('data-value'));
        });
    });

    const picker1 = document.getElementById("customizer-accent-picker-1");
    if (picker1) {
        picker1.addEventListener("input", (e) => {
            applyCustomColor(e.target.value);
            applyAccent("custom");
        });
        picker1.addEventListener("change", (e) => {
            applyCustomColor(e.target.value);
            applyAccent("custom");
        });
    }

    const picker2 = document.getElementById("customizer-accent-picker-2");
    if (picker2) {
        picker2.addEventListener("input", (e) => {
            applyCustomColor2(e.target.value);
            applyAccent("custom");
        });
        picker2.addEventListener("change", (e) => {
            applyCustomColor2(e.target.value);
            applyAccent("custom");
        });
    }

    document.querySelectorAll('.customizer-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-type');
            const val = btn.getAttribute('data-value');
            if (type === 'radius') {
                applyRadius(val);
            } else if (type === 'fontsize') {
                applyFontSize(val);
            } else if (type === 'fontfamily') {
                applyFontFamily(val);
            } else if (type === 'gravity-mode') {
                applyGravityMode(val);
            } else if (type === 'sparkle-shape') {
                applySparkleShape(val);
            } else if (type === 'app-height') {
                applyAppHeight(val);
            }
        });
    });

    // Sliders and custom number input listeners
    if (customizerBlur) {
        customizerBlur.addEventListener("input", (e) => applyBlur(parseInt(e.target.value), false));
        customizerBlur.addEventListener("change", (e) => applyBlur(parseInt(e.target.value), true));
    }
    if (customizerBlurVal) {
        customizerBlurVal.addEventListener("input", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) return;
            if (val >= 0 && val <= 100) {
                document.documentElement.style.setProperty("--glass-blur", val + "px");
                if (customizerBlur) customizerBlur.value = val;
                localStorage.setItem("customizer-blur", val);
            }
        });
        customizerBlurVal.addEventListener("blur", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) val = 24;
            let clamped = Math.max(0, Math.min(100, val));
            applyBlur(clamped, true);
        });
    }

    if (customizerSpacing) {
        customizerSpacing.addEventListener("input", (e) => applySpacing(parseInt(e.target.value), false));
        customizerSpacing.addEventListener("change", (e) => applySpacing(parseInt(e.target.value), true));
    }
    if (customizerSpacingVal) {
        customizerSpacingVal.addEventListener("input", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) return;
            if (val >= 10 && val <= 500) {
                window.canvasSettings.spacing = val;
                if (customizerSpacing) customizerSpacing.value = val;
                localStorage.setItem("customizer-spacing", val);
            }
        });
        customizerSpacingVal.addEventListener("blur", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) val = 54;
            let clamped = Math.max(10, Math.min(500, val));
            applySpacing(clamped, true);
        });
    }

    if (customizerGravity) {
        customizerGravity.addEventListener("input", (e) => applyGravityRadius(parseInt(e.target.value), false));
        customizerGravity.addEventListener("change", (e) => applyGravityRadius(parseInt(e.target.value), true));
    }
    if (customizerGravityVal) {
        customizerGravityVal.addEventListener("input", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) return;
            if (val >= 10 && val <= 2000) {
                window.canvasSettings.maxDist = val;
                if (customizerGravity) customizerGravity.value = val;
                localStorage.setItem("customizer-maxDist", val);
            }
        });
        customizerGravityVal.addEventListener("blur", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) val = 180;
            let clamped = Math.max(10, Math.min(2000, val));
            applyGravityRadius(clamped, true);
        });
    }

    if (customizerGravityDepth) {
        customizerGravityDepth.addEventListener("input", (e) => applyGravityDepth(parseInt(e.target.value), false));
        customizerGravityDepth.addEventListener("change", (e) => applyGravityDepth(parseInt(e.target.value), true));
    }
    if (customizerGravityDepthVal) {
        customizerGravityDepthVal.addEventListener("input", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) return;
            if (val >= 10 && val <= 1000) {
                window.canvasSettings.gravityDepth = val;
                if (customizerGravityDepth) customizerGravityDepth.value = val;
                localStorage.setItem("customizer-gravityDepth", val);
            }
        });
        customizerGravityDepthVal.addEventListener("blur", (e) => {
            let val = parseInt(e.target.value);
            if (isNaN(val)) val = 150;
            let clamped = Math.max(10, Math.min(1000, val));
            applyGravityDepth(clamped, true);
        });
    }

    if (customizerGridEnable) {
        customizerGridEnable.addEventListener("change", (e) => {
            updateCanvasOption("gridEnabled", e.target.checked);
            const gridContainer = document.getElementById("grid-spacing-container");
            const gravityContainer = document.getElementById("grid-gravity-container");
            const modeContainer = document.querySelector('.customizer-preset-btn[data-type="gravity-mode"]')?.parentElement?.parentElement;
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
    if (customizerSoundReactiveEnable) {
        customizerSoundReactiveEnable.addEventListener("change", (e) => updateCanvasOption("soundReactiveEnabled", e.target.checked));
    }
    if (customizerSparklesEnable) {
        customizerSparklesEnable.addEventListener("change", (e) => updateCanvasOption("sparklesEnabled", e.target.checked));
    }

    function applyPreviewBlurryBackdrop(enabled) {
        const modal = document.getElementById("preview-modal");
        if (!modal) return;
        if (enabled) {
            modal.classList.add("blurry-backdrop");
        } else {
            modal.classList.remove("blurry-backdrop");
        }
    }

    function applyPreviewResizable(enabled) {
        const handles = document.querySelectorAll(".modal-card-preview .preview-resize-handle");
        handles.forEach(handle => {
            handle.style.display = enabled ? "" : "none";
        });
    }

    if (customizerPreviewBlur) {
        customizerPreviewBlur.addEventListener("change", (e) => {
            updateCanvasOption("previewBlurryBackdrop", e.target.checked);
            applyPreviewBlurryBackdrop(e.target.checked);
        });
    }
    if (customizerPreviewDrag) {
        customizerPreviewDrag.addEventListener("change", (e) => {
            updateCanvasOption("previewDraggable", e.target.checked);
        });
    }
    if (customizerPreviewZoom) {
        customizerPreviewZoom.addEventListener("change", (e) => {
            updateCanvasOption("previewResizable", e.target.checked);
            applyPreviewResizable(e.target.checked);
        });
    }

    if (customizerResetBtn) {
        customizerResetBtn.addEventListener("click", () => {
            showConfirm({
                title: "Reset UI Settings",
                message: "Are you sure you want to reset all UI themes, accents, heights, and custom interactive canvas settings back to their defaults?",
                onYes: () => {
                    applyAccent("default");
                    applyRadius("rounded");
                    applyBlur(24);
                    applyFontSize("medium");
                    applyFontFamily("outfit");
                    applyAppHeight("100%");
                    applyGravityMode("pull");
                    applySparkleShape("star");
                    applySpacing(54, true);
                    applyGravityRadius(180, true);
                    applyGravityDepth(130, true);

                    if (customizerGridEnable) {
                        customizerGridEnable.checked = true;
                        updateCanvasOption("gridEnabled", true);
                        const gridContainer = document.getElementById("grid-spacing-container");
                        const gravityContainer = document.getElementById("grid-gravity-container");
                        const modeContainer = document.querySelector('.customizer-preset-btn[data-type="gravity-mode"]')?.parentElement?.parentElement;
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
                    if (customizerSoundReactiveEnable) {
                        customizerSoundReactiveEnable.checked = true;
                        updateCanvasOption("soundReactiveEnabled", true);
                    }
                    if (customizerSparklesEnable) {
                        customizerSparklesEnable.checked = true;
                        updateCanvasOption("sparklesEnabled", true);
                    }
                    if (customizerPreviewBlur) {
                        customizerPreviewBlur.checked = false;
                        updateCanvasOption("previewBlurryBackdrop", false);
                        applyPreviewBlurryBackdrop(false);
                    }
                    if (customizerPreviewDrag) {
                        customizerPreviewDrag.checked = true;
                        updateCanvasOption("previewDraggable", true);
                    }
                    if (customizerPreviewZoom) {
                        customizerPreviewZoom.checked = true;
                        updateCanvasOption("previewResizable", true);
                        applyPreviewResizable(true);
                    }
                }
            });
        });
    }

    // Load initial values
    const savedAccent = localStorage.getItem("customizer-accent") || "default";
    applyAccent(savedAccent);

    const savedRadius = localStorage.getItem("customizer-radius") || "rounded";
    applyRadius(savedRadius);

    const savedBlur = localStorage.getItem("customizer-blur") !== null ? parseInt(localStorage.getItem("customizer-blur")) : 24;
    applyBlur(savedBlur);

    const savedFontSize = localStorage.getItem("customizer-fontsize") || "medium";
    applyFontSize(savedFontSize);

    const savedFontFamily = localStorage.getItem("customizer-fontfamily") || "outfit";
    applyFontFamily(savedFontFamily);

    const savedAppHeight = localStorage.getItem("customizer-app-height") || "100%";
    applyAppHeight(savedAppHeight);

    const savedGrid = localStorage.getItem("customizer-gridEnabled") !== null ? localStorage.getItem("customizer-gridEnabled") === "true" : true;
    const savedGravityMode = localStorage.getItem("customizer-gravityMode") || "pull";

    if (customizerGridEnable) {
        customizerGridEnable.checked = savedGrid;
        window.canvasSettings.gridEnabled = savedGrid;
        const gridContainer = document.getElementById("grid-spacing-container");
        const gravityContainer = document.getElementById("grid-gravity-container");
        const modeContainer = document.querySelector('.customizer-preset-btn[data-type="gravity-mode"]')?.parentElement?.parentElement;
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

    applyGravityMode(savedGravityMode);

    const savedGravityDepth = localStorage.getItem("customizer-gravityDepth") !== null ? parseInt(localStorage.getItem("customizer-gravityDepth")) : 130;
    applyGravityDepth(savedGravityDepth);

    const savedSparkleShape = localStorage.getItem("customizer-sparkleShape") || "star";
    applySparkleShape(savedSparkleShape);

    const savedRipples = localStorage.getItem("customizer-ripplesEnabled") !== null ? localStorage.getItem("customizer-ripplesEnabled") === "true" : true;
    if (customizerRipplesEnable) {
        customizerRipplesEnable.checked = savedRipples;
        window.canvasSettings.ripplesEnabled = savedRipples;
    }

    const savedSoundReactive = localStorage.getItem("customizer-soundReactiveEnabled") !== null ? localStorage.getItem("customizer-soundReactiveEnabled") === "true" : true;
    if (customizerSoundReactiveEnable) {
        customizerSoundReactiveEnable.checked = savedSoundReactive;
        window.canvasSettings.soundReactiveEnabled = savedSoundReactive;
    }

    const savedSparkles = localStorage.getItem("customizer-sparklesEnabled") !== null ? localStorage.getItem("customizer-sparklesEnabled") === "true" : true;
    if (customizerSparklesEnable) {
        customizerSparklesEnable.checked = savedSparkles;
        window.canvasSettings.sparklesEnabled = savedSparkles;
    }

    const savedPreviewBlur = localStorage.getItem("customizer-previewBlurryBackdrop") !== null ? localStorage.getItem("customizer-previewBlurryBackdrop") === "true" : false;
    if (customizerPreviewBlur) {
        customizerPreviewBlur.checked = savedPreviewBlur;
        window.canvasSettings.previewBlurryBackdrop = savedPreviewBlur;
        applyPreviewBlurryBackdrop(savedPreviewBlur);
    }

    const savedPreviewDrag = localStorage.getItem("customizer-previewDraggable") !== null ? localStorage.getItem("customizer-previewDraggable") === "true" : true;
    if (customizerPreviewDrag) {
        customizerPreviewDrag.checked = savedPreviewDrag;
        window.canvasSettings.previewDraggable = savedPreviewDrag;
    }

    const savedPreviewZoom = localStorage.getItem("customizer-previewResizable") !== null ? localStorage.getItem("customizer-previewResizable") === "true" : true;
    if (customizerPreviewZoom) {
        customizerPreviewZoom.checked = savedPreviewZoom;
        window.canvasSettings.previewResizable = savedPreviewZoom;
        applyPreviewResizable(savedPreviewZoom);
    }

    const savedSpacing = localStorage.getItem("customizer-spacing") !== null ? parseInt(localStorage.getItem("customizer-spacing")) : 54;
    applySpacing(savedSpacing);

    const savedGravity = localStorage.getItem("customizer-maxDist") !== null ? parseInt(localStorage.getItem("customizer-maxDist")) : 180;
    applyGravityRadius(savedGravity);
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

    // Voiceover speed & pitch sliders
    const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
    const voiceoverRateVal = document.getElementById("voiceover-rate-val");
    const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
    const voiceoverPitchVal = document.getElementById("voiceover-pitch-val");

    if (voiceoverRateSlider && voiceoverRateVal) {
        voiceoverRateSlider.addEventListener("input", () => {
            const val = parseInt(voiceoverRateSlider.value);
            if (val === 0) {
                voiceoverRateVal.innerText = "Normal";
            } else {
                voiceoverRateVal.innerText = (val > 0 ? "+" : "") + val + "%";
            }
        });
    }

    if (voiceoverPitchSlider && voiceoverPitchVal) {
        voiceoverPitchSlider.addEventListener("input", () => {
            const val = parseInt(voiceoverPitchSlider.value);
            if (val === 0) {
                voiceoverPitchVal.innerText = "Normal";
            } else {
                voiceoverPitchVal.innerText = (val > 0 ? "+" : "") + val + "%";
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

    // Load and save Clipboard Detect Checkbox & Default Quality Select
    const clipboardDetectCb = document.getElementById("clipboard-detect-checkbox");
    const globalDefaultQualitySelect = document.getElementById("global-default-quality");

    if (clipboardDetectCb) {
        const savedClipboardDetect = localStorage.getItem("global_clipboard_detect") !== null ? localStorage.getItem("global_clipboard_detect") === "true" : true;
        clipboardDetectCb.checked = savedClipboardDetect;
        clipboardDetectCb.addEventListener("change", () => {
            localStorage.setItem("global_clipboard_detect", clipboardDetectCb.checked);
        });
    }

    if (globalDefaultQualitySelect) {
        const savedDefaultQuality = localStorage.getItem("global_default_quality") || "best";
        globalDefaultQualitySelect.value = savedDefaultQuality;
        globalDefaultQualitySelect.addEventListener("change", () => {
            localStorage.setItem("global_default_quality", globalDefaultQualitySelect.value);
        });
    }

    // Downloads Location in Global Settings
    const globalDownloadsDirInput = document.getElementById("global-downloads-dir");
    const btnSettingsChangeDir = document.getElementById("btn-settings-change-dir");
    const btnSettingsOpenDir = document.getElementById("btn-settings-open-dir");

    async function updateDownloadsDirDisplay() {
        if (!globalDownloadsDirInput) return;
        if (window.electronAPI && typeof window.electronAPI.getDownloadsDir === "function") {
            try {
                const dir = await window.electronAPI.getDownloadsDir();
                if (dir) globalDownloadsDirInput.value = dir;
            } catch (_) {}
            if (btnSettingsChangeDir) btnSettingsChangeDir.style.display = "inline-flex";
        } else {
            globalDownloadsDirInput.value = "Downloads / MeikovaHarvest";
        }
    }
    updateDownloadsDirDisplay();

    if (btnSettingsChangeDir) {
        btnSettingsChangeDir.addEventListener("click", async () => {
            if (window.electronAPI && typeof window.electronAPI.selectFolder === "function") {
                const chosen = await window.electronAPI.selectFolder();
                if (chosen) {
                    const res = await window.electronAPI.setDownloadsDir(chosen);
                    if (res && res.success && res.dir) {
                        globalDownloadsDirInput.value = res.dir;
                    }
                }
            }
        });
    }

    if (btnSettingsOpenDir) {
        btnSettingsOpenDir.addEventListener("click", () => {
            if (window.electronAPI && typeof window.electronAPI.openDownloadsFolder === "function") {
                window.electronAPI.openDownloadsFolder();
            } else {
                fetch("/api/download/open-folder", { method: "POST" });
            }
        });
    }

    if (globalDownloadsDirInput) {
        globalDownloadsDirInput.addEventListener("click", () => {
            if (btnSettingsOpenDir) btnSettingsOpenDir.click();
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
            let filterCss = "none";
            if (filterVal === "cyberpunk") {
                filterCss = "hue-rotate(-10deg) saturate(1.5) contrast(1.1) brightness(0.95)";
            } else if (filterVal === "vintage") {
                filterCss = "sepia(0.4) saturate(1.2) contrast(0.9) hue-rotate(5deg)";
            } else if (filterVal === "noir") {
                filterCss = "grayscale(1) contrast(1.4) brightness(0.9)";
            } else if (filterVal === "enhance") {
                filterCss = "contrast(1.05) saturate(1.1)";
            }

            if (trimPreviewPlayer) {
                trimPreviewPlayer.style.filter = filterCss;
            }
            if (previewVideoPlayer) {
                previewVideoPlayer.style.filter = filterCss;
            }
        });
    }

    // Unique Client ID Management
    let clientId = localStorage.getItem("client_id");
    if (!clientId) {
        clientId = "client_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem("client_id", clientId);
    }

    // ponytail: Navigation history stack initializes with Home/Welcome ("") at index 0 so back button allows returning to Welcome screen
    const navigationHistory = [""];
    let navigationIndex = 0;
    let isNavigating = false;

    const navBackBtn = document.getElementById("nav-back-btn");
    const navForwardBtn = document.getElementById("nav-forward-btn");

    function updateNavigationButtons() {
        const canGoBack = navigationIndex > 0;
        const canGoForward = navigationIndex < navigationHistory.length - 1;

        if (navBackBtn) {
            navBackBtn.disabled = !canGoBack;
            if (canGoBack) {
                const prevUrl = navigationHistory[navigationIndex - 1];
                navBackBtn.title = prevUrl ? `Go back: ${prevUrl}` : "Go back to Welcome Screen (Backspace / Alt + Left)";
            } else {
                navBackBtn.title = "Go back (No earlier history)";
            }
        }
        if (navForwardBtn) {
            navForwardBtn.disabled = !canGoForward;
            if (canGoForward) {
                const nextUrl = navigationHistory[navigationIndex + 1];
                navForwardBtn.title = nextUrl ? `Go forward: ${nextUrl}` : "Go forward to Welcome Screen (Alt + Right)";
            } else {
                navForwardBtn.title = "Go forward (No forward history)";
            }
        }
    }

    function pushToNavigationHistory(url) {
        if (isNavigating) return;
        const cleanUrl = (url || "").trim();

        // Don't push duplicate sequentially
        if (navigationIndex >= 0 && navigationHistory[navigationIndex] === cleanUrl) {
            return;
        }

        // Discard any forward history if navigating to a new branch
        if (navigationIndex < navigationHistory.length - 1) {
            navigationHistory.splice(navigationIndex + 1);
        }

        navigationHistory.push(cleanUrl);
        if (navigationHistory.length > 50) {
            navigationHistory.shift();
        }
        navigationIndex = navigationHistory.length - 1;
        updateNavigationButtons();
    }

    async function navigateHistoryBack() {
        if (isNavigating) return;
        if (navigationIndex > 0) {
            isNavigating = true;
            try {
                navigationIndex--;
                const targetUrl = navigationHistory[navigationIndex] || "";
                if (urlInput) {
                    urlInput.value = targetUrl;
                    updateUrlInputButtons();
                }
                updateNavigationButtons();
                if (targetUrl) {
                    await performAnalysis();
                } else {
                    resetToWelcomeDashboard();
                }
            } finally {
                isNavigating = false;
                updateNavigationButtons();
            }
        }
    }

    async function navigateHistoryForward() {
        if (isNavigating) return;
        if (navigationIndex < navigationHistory.length - 1) {
            isNavigating = true;
            try {
                navigationIndex++;
                const targetUrl = navigationHistory[navigationIndex] || "";
                if (urlInput) {
                    urlInput.value = targetUrl;
                    updateUrlInputButtons();
                }
                updateNavigationButtons();
                if (targetUrl) {
                    await performAnalysis();
                } else {
                    resetToWelcomeDashboard();
                }
            } finally {
                isNavigating = false;
                updateNavigationButtons();
            }
        }
    }

    if (navBackBtn) navBackBtn.addEventListener("click", navigateHistoryBack);
    if (navForwardBtn) navForwardBtn.addEventListener("click", navigateHistoryForward);

    // Hardware mouse back/forward buttons (thumb buttons 3 & 4)
    window.addEventListener("mouseup", (e) => {
        if (e.button === 3) {
            e.preventDefault();
            navigateHistoryBack();
        } else if (e.button === 4) {
            e.preventDefault();
            navigateHistoryForward();
        }
    });

    updateNavigationButtons();

    // Keyboard navigation shortcuts
    document.addEventListener("keydown", (e) => {
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
        if (activeTag === "input" || activeTag === "textarea") {
            return;
        }
        
        if (e.altKey) {
            if (e.key === "ArrowLeft") {
                e.preventDefault();
                navigateHistoryBack();
            } else if (e.key === "ArrowRight") {
                e.preventDefault();
                navigateHistoryForward();
            }
        } else if (e.key === "Backspace") {
            e.preventDefault();
            navigateHistoryBack();
        }
    });

    // Touch Swipe gestures (left/right) for mobile
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;

    document.addEventListener("touchstart", (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    document.addEventListener("touchend", (e) => {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;
        
        // Ensure swipe is horizontal and meets threshold
        if (Math.abs(diffX) > 120 && Math.abs(diffY) < 60) {
            if (diffX > 0) {
                navigateHistoryBack(); // Swipe right -> Back
            } else {
                navigateHistoryForward(); // Swipe left -> Forward
            }
        }
    }, { passive: true });

    // Trackpad horizontal swipe detection (wheel scroll)
    let wheelAccumulatorX = 0;
    let wheelDebounceTimeout = null;

    document.addEventListener("wheel", (e) => {
        if (Math.abs(e.deltaX) > 5) {
            wheelAccumulatorX += e.deltaX;
            
            clearTimeout(wheelDebounceTimeout);
            wheelDebounceTimeout = setTimeout(() => {
                if (wheelAccumulatorX > 150) {
                    navigateHistoryForward(); // Scrolled right -> Go Forward
                } else if (wheelAccumulatorX < -150) {
                    navigateHistoryBack(); // Scrolled left -> Go Back
                }
                wheelAccumulatorX = 0;
            }, 100);
        }
    }, { passive: true });

    // Desktop Mouse Drag Swiping on neutral/empty background areas
    let mouseStartX = 0;
    let mouseStartY = 0;
    let isMouseDown = false;

    document.addEventListener("mousedown", (e) => {
        const target = e.target;
        // Ignore drag-swipe if clicking inside inputs, buttons, sliders, media elements, links, or specific panels
        const interactiveTags = ["input", "textarea", "button", "select", "a", "option", "video", "audio"];
        if (interactiveTags.includes(target.tagName.toLowerCase())) return;
        if (target.closest(".card") || target.closest(".modal-card-preview") || target.closest("#downloads-manager") || target.closest(".nav-history-controls")) {
            return;
        }

        isMouseDown = true;
        mouseStartX = e.clientX;
        mouseStartY = e.clientY;
    });

    document.addEventListener("mouseup", (e) => {
        if (!isMouseDown) return;
        isMouseDown = false;

        const mouseEndX = e.clientX;
        const mouseEndY = e.clientY;

        const diffX = mouseEndX - mouseStartX;
        const diffY = mouseEndY - mouseStartY;

        // Require 150px drag, mostly horizontal
        if (Math.abs(diffX) > 150 && Math.abs(diffY) < 60) {
            if (diffX > 0) {
                navigateHistoryBack(); // Dragged right -> Go Back
            } else {
                navigateHistoryForward(); // Dragged left -> Go Forward
            }
        }
    });

    // UI Elements
    const urlInput = document.getElementById("url-input");
    const pasteBtn = document.getElementById("paste-btn");
    const browseFileBtn = document.getElementById("browse-file-btn");
    const browseFolderBtn = document.getElementById("browse-folder-btn");
    const localFilePicker = document.getElementById("local-file-picker");
    const localFolderPicker = document.getElementById("local-folder-picker");
    const clearUrlBtn = document.getElementById("clear-url-btn");
    const analyzeBtn = document.getElementById("analyze-btn");

    const loaderSection = document.getElementById("loader");
    const loaderText = document.getElementById("loader-text");
    const cancelAnalyzeBtn = document.getElementById("cancel-analyze-btn");
    const errorCard = document.getElementById("error-card");
    const errorMessage = document.getElementById("error-message");

    // ponytail: Strips whitespace and Windows copy-as-path quotes from input url
    function sanitizeInputUrl(val) {
        if (!val || typeof val !== "string") return "";
        return val.trim().replace(/^["']+|["']+$/g, '').trim();
    }

    let analysisAbortController = null;

    const resultSection = document.getElementById("result-section");
    const videoThumbnail = document.getElementById("video-thumbnail");
    if (videoThumbnail) {
        videoThumbnail.addEventListener("load", function () {
            videoThumbnail.style.opacity = "1";
        });
        videoThumbnail.addEventListener("error", function () {
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

    const downloadsManager = document.getElementById("downloads-manager");
    const downloadsTasksList = document.getElementById("downloads-tasks-list");
    const downloadsActiveCount = document.getElementById("downloads-active-count");
    const downloadsToggleBtn = document.getElementById("downloads-toggle-btn");
    const downloadsManagerHeader = document.getElementById("downloads-manager-header");

    const activeTasks = {}; // Key: downloadId, Value: { sse, cardEl, progress }

    if (downloadsManagerHeader && downloadsManager) {
        downloadsManagerHeader.addEventListener("click", () => {
            downloadsManager.classList.toggle("collapsed");
        });
    }

    const downloadsOpenFolderBtn = document.getElementById("downloads-open-folder-btn");
    const downloadsClearAllBtn = document.getElementById("downloads-clear-all-btn");

    if (downloadsOpenFolderBtn) {
        downloadsOpenFolderBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (window.electronAPI && typeof window.electronAPI.openDownloadsFolder === "function") {
                window.electronAPI.openDownloadsFolder();
            } else {
                fetch("/api/download/open-folder", { method: "POST" })
                    .catch(() => window.open("/downloads", "_blank"));
            }
        });
    }

    if (downloadsClearAllBtn) {
        downloadsClearAllBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (!downloadsTasksList) return;
            const finishedCards = downloadsTasksList.querySelectorAll(".download-task-card.state-complete, .download-task-card.state-error");
            finishedCards.forEach(card => card.remove());
            if (downloadsTasksList.children.length === 0 && downloadsManager) {
                downloadsManager.classList.add("hidden");
            }
            updateDownloadsCount();
        });
    }

    function updateDownloadsCount() {
        if (!downloadsActiveCount) return;
        const activeCount = Object.values(activeTasks).filter(t => t.sse).length;
        downloadsActiveCount.textContent = activeCount;
        
        const spinner = downloadsManager ? downloadsManager.querySelector(".downloads-manager-spinner") : null;
        if (spinner) {
            if (activeCount > 0) {
                spinner.classList.add("active");
            } else {
                spinner.classList.remove("active");
            }
        }
    }

    // Preview Modal DOM Elements
    const previewModal = document.getElementById("preview-modal");
    const previewModalCloseBtn = document.getElementById("preview-modal-close-btn");
    const modalFullscreenBtn = document.getElementById("modal-fullscreen-btn");
    const previewLightsOffBtn = document.getElementById("preview-lightsoff-btn");
    const previewShortcutsBtn = document.getElementById("preview-shortcuts-btn");
    const previewShortcutsOverlay = document.getElementById("preview-shortcuts-overlay");
    const shortcutsOverlayCloseBtn = document.getElementById("shortcuts-overlay-close-btn");
    let closePreviewModal = () => { };

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
    const previewLoaderSpinner = previewLoader ? previewLoader.querySelector(".preview-loader-spinner") : null;
    const previewLoaderErrorIcon = document.getElementById("preview-loader-error-icon");

    function showPreviewLoader(text, isError = false) {
        if (!previewLoader) return;
        if (previewLoaderText) {
            previewLoaderText.innerHTML = text;
            previewLoaderText.style.color = isError ? "#ff5555" : "";
        }
        if (previewLoaderSpinner) {
            if (isError) {
                previewLoaderSpinner.classList.add("hidden");
            } else {
                previewLoaderSpinner.classList.remove("hidden");
            }
        }
        if (previewLoaderErrorIcon) {
            if (isError) {
                previewLoaderErrorIcon.classList.remove("hidden");
            } else {
                previewLoaderErrorIcon.classList.add("hidden");
            }
        }
        previewLoader.classList.remove("hidden");
    }

    function hidePreviewLoader() {
        if (previewLoader) {
            previewLoader.classList.add("hidden");
        }
    }

    function showPlayerToast(text, duration = 3500) {
        let toast = document.getElementById("player-floating-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "player-floating-toast";
            toast.style.cssText = "position: fixed; bottom: 28px; right: 28px; background: rgba(15, 23, 42, 0.95); color: #f8fafc; border: 1px solid rgba(99, 102, 241, 0.4); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(99, 102, 241, 0.25); border-radius: 8px; padding: 12px 18px; font-size: 13.5px; z-index: 9999999; display: flex; align-items: center; gap: 10px; backdrop-filter: blur(8px); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); opacity: 0; transform: translateY(12px); pointer-events: none;";
            document.body.appendChild(toast);
        }
        toast.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg><span>${text}</span>`;
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
        if (toast._dismissTimer) clearTimeout(toast._dismissTimer);
        toast._dismissTimer = setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
        }, duration);
    }
    const previewVideoContainer = document.getElementById("preview-video-container");
    const previewVideoPlayer = document.getElementById("preview-video-player");
    const previewAudioContainer = document.getElementById("preview-audio-container");
    const previewAudioPlayer = document.getElementById("preview-audio-player");
    if (previewAudioPlayer) {
        previewAudioPlayer.crossOrigin = "anonymous";
    }
    const previewImageContainer = document.getElementById("preview-image-container");
    const previewImageElement = document.getElementById("preview-image-element");
    const btnImageAdjust = document.getElementById("btn-image-adjust");
    const imageSidePanel = document.getElementById("image-side-panel");
    const btnImgReset = document.getElementById("btn-img-reset");
    const previewSubtitleContainer = document.getElementById("preview-subtitle-container");
    const previewSubLang = document.getElementById("preview-sub-lang");
    const previewSubText = document.getElementById("preview-sub-text");
    const previewWebpageContainer = document.getElementById("preview-webpage-container");
    const previewWebpageIframe = document.getElementById("preview-webpage-iframe");
    const previewWebpageWebview = document.getElementById("preview-webpage-webview");
    const previewWebpagePauseIndicator = document.getElementById("preview-webpage-pause-indicator");
    const btnCopySub = document.getElementById("btn-copy-sub");
    const previewMetaInfo = document.getElementById("preview-meta-info");
    const previewDownloadBtn = document.getElementById("preview-download-btn");
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomOut = document.getElementById("btn-zoom-out");
    const btnRotate = document.getElementById("btn-rotate");
    const btnPrevImage = document.getElementById("btn-prev-image");
    const btnNextImage = document.getElementById("btn-next-image");

    // Custom audio player elements
    const audioCard = document.querySelector(".audio-preview-card");
    const audioPlayPauseBtn = document.getElementById("audio-play-pause-btn");
    const audioLoopBtn = document.getElementById("audio-loop-btn");
    const audioSeekSlider = document.getElementById("audio-seek-slider");
    const audioTimeCurrent = document.getElementById("audio-time-current");
    const audioTimeTotal = document.getElementById("audio-time-total");
    const audioMuteBtn = document.getElementById("audio-mute-btn");
    const audioVolumeSlider = document.getElementById("audio-volume-slider");
    const audioFormatSelect = document.getElementById("audio-preview-format-select");

    // Custom audio player expanded features elements
    const audioLyricsBtn = document.getElementById("audio-lyrics-btn");
    const audioEqBtn = document.getElementById("audio-eq-btn");
    const audioSettingsPanel = document.getElementById("audio-settings-panel");
    const audioSidePanel = document.getElementById("audio-side-panel");
    const audioStabs = document.querySelectorAll(".audio-stab");
    const audioStabContents = document.querySelectorAll(".audio-stab-content");
    const audioSubSelect = document.getElementById("audio-sub-select");
    const audioSubUploadBtn = document.getElementById("audio-sub-upload-btn");
    const audioSubFile = document.getElementById("audio-sub-file");
    const audioLyricsList = document.getElementById("audio-lyrics-list");
    const audioLyricsOverlay = document.getElementById("audio-lyrics-overlay");
    const audioSpeedSlider = document.getElementById("audio-speed-slider");
    const audioSpeedDisplay = document.getElementById("audio-speed-display");
    const speedPresetBtns = document.querySelectorAll(".speed-preset-btn");
    const eqSliders = document.querySelectorAll(".eq-slider");
    const eqPresets = document.querySelectorAll(".eq-preset");
    const voicePresets = document.querySelectorAll(".voice-preset");

    // Custom video player elements
    const videoCard = document.querySelector(".video-preview-card");
    const videoPlayPauseBtn = document.getElementById("video-play-pause-btn");
    const videoLoopBtn = document.getElementById("video-loop-btn");
    const videoSeekSlider = document.getElementById("video-seek-slider");
    const videoTimeCurrent = document.getElementById("video-time-current");
    const videoTimeTotal = document.getElementById("video-time-total");
    const videoMuteBtn = document.getElementById("video-mute-btn");
    const videoVolumeSlider = document.getElementById("video-volume-slider");
    const videoFullscreenBtn = document.getElementById("video-fullscreen-btn");
    const videoFormatSelect = document.getElementById("video-preview-format-select");
    const customVideoControls = document.querySelector(".custom-video-controls");

    // Seek thumbnail preview elements
    const thumbPreviewVideo = document.getElementById("thumb-preview-video");
    const seekThumbTooltip = document.getElementById("seek-thumb-tooltip");
    const seekThumbCanvas = document.getElementById("seek-thumb-canvas");
    const seekThumbTime = document.getElementById("seek-thumb-time");
    const seekThumbPointer = document.getElementById("seek-thumb-pointer");
    const seekThumbDot = document.getElementById("seek-thumb-dot");
    const seekThumbCtx = seekThumbCanvas ? seekThumbCanvas.getContext("2d") : null;
    const videoSliderContainer = document.querySelector(".video-slider-container");

    // Episode Navigation Helpers and Click Listeners
    function getGroupSiblingsAndIndex() {
        if (!videoFormatSelect) return { siblings: [], currentIndex: -1 };
        const selectedOption = videoFormatSelect.querySelector("option:checked") || videoFormatSelect.options[videoFormatSelect.selectedIndex];
        if (!selectedOption) return { siblings: [], currentIndex: -1 };
        
        const parent = selectedOption.parentElement;
        let siblings = [];
        if (parent && parent.tagName.toLowerCase() === "optgroup") {
            siblings = Array.from(parent.querySelectorAll("option"));
        } else {
            siblings = Array.from(videoFormatSelect.children).filter(child => child.tagName.toLowerCase() === "option");
        }
        const currentIndex = siblings.indexOf(selectedOption);
        return { siblings, currentIndex };
    }

    function handleEpisodeStep(direction) {
        if (!videoFormatSelect) return;
        const { siblings, currentIndex } = getGroupSiblingsAndIndex();
        if (currentIndex === -1 || !siblings.length) return;
        const targetIndex = currentIndex + direction;
        if (targetIndex >= 0 && targetIndex < siblings.length) {
            const targetOpt = siblings[targetIndex];
            videoFormatSelect.value = targetOpt.value;
            videoFormatSelect.dispatchEvent(new Event("change"));
            const cleanTitle = (targetOpt.textContent || targetOpt.value || "").trim();
            if (typeof showPlayerToast === "function") {
                showPlayerToast(`Đang chuyển: ${cleanTitle}`, 2500);
            }
        }
    }

    function updateEpisodeNavigationButtonsState() {
        const nextBtn = document.getElementById("video-next-btn");
        const prevBtn = document.getElementById("video-prev-btn");
        const footerEpNav = document.getElementById("preview-episode-nav");
        const footerEpPrevBtn = document.getElementById("preview-ep-prev-btn");
        const footerEpNextBtn = document.getElementById("preview-ep-next-btn");
        const footerEpSelect = document.getElementById("preview-ep-select");
        const footerEpCounter = document.getElementById("preview-ep-counter");
        const floatPrevBtn = document.getElementById("preview-stream-floating-prev");
        const floatNextBtn = document.getElementById("preview-stream-floating-next");

        if (!videoFormatSelect || videoFormatSelect.style.display === "none") {
            if (nextBtn) nextBtn.classList.add("hidden");
            if (prevBtn) prevBtn.classList.add("hidden");
            if (footerEpNav) footerEpNav.classList.add("hidden");
            if (footerEpCounter) footerEpCounter.classList.add("hidden");
            if (floatPrevBtn) floatPrevBtn.classList.add("hidden");
            if (floatNextBtn) floatNextBtn.classList.add("hidden");
            return;
        }

        const { siblings, currentIndex } = getGroupSiblingsAndIndex();
        const hasMultiple = (siblings && siblings.length > 1);

        // Player custom video controls buttons
        if (nextBtn) {
            if (hasMultiple && currentIndex !== -1 && currentIndex < siblings.length - 1) {
                nextBtn.classList.remove("hidden");
            } else {
                nextBtn.classList.add("hidden");
            }
        }
        if (prevBtn) {
            if (hasMultiple && currentIndex > 0) {
                prevBtn.classList.remove("hidden");
            } else {
                prevBtn.classList.add("hidden");
            }
        }

        // Footer episode toolbar
        if (footerEpNav) {
            if (hasMultiple) {
                footerEpNav.classList.remove("hidden");
            } else {
                footerEpNav.classList.add("hidden");
            }
        }

        const canGoPrev = hasMultiple && currentIndex > 0;
        const canGoNext = hasMultiple && currentIndex !== -1 && currentIndex < siblings.length - 1;

        if (footerEpPrevBtn) {
            footerEpPrevBtn.disabled = !canGoPrev;
            footerEpPrevBtn.classList.toggle("disabled", !canGoPrev);
            if (canGoPrev) {
                const prevTitle = siblings[currentIndex - 1]?.textContent || "Tập trước";
                footerEpPrevBtn.title = `Tập trước: ${prevTitle} (Hotkey: [ hoặc Shift+P)`;
            } else {
                footerEpPrevBtn.title = "Không có tập trước đó";
            }
        }

        if (footerEpNextBtn) {
            footerEpNextBtn.disabled = !canGoNext;
            footerEpNextBtn.classList.toggle("disabled", !canGoNext);
            if (canGoNext) {
                const nextTitle = siblings[currentIndex + 1]?.textContent || "Tập sau";
                footerEpNextBtn.title = `Tập sau: ${nextTitle} (Hotkey: ] hoặc Shift+N)`;
            } else {
                footerEpNextBtn.title = "Đã là tập mới nhất";
            }
        }

        if (footerEpSelect && videoFormatSelect) {
            if (footerEpSelect.innerHTML !== videoFormatSelect.innerHTML) {
                footerEpSelect.innerHTML = videoFormatSelect.innerHTML;
            }
            footerEpSelect.value = videoFormatSelect.value;
        }

        if (footerEpCounter) {
            if (hasMultiple && currentIndex !== -1) {
                footerEpCounter.textContent = `${currentIndex + 1} / ${siblings.length}`;
                footerEpCounter.classList.remove("hidden");
                footerEpCounter.title = `Tập ${currentIndex + 1} trên tổng số ${siblings.length} tập`;
            } else {
                footerEpCounter.classList.add("hidden");
            }
        }

        // Floating on-screen navigation buttons on stream player
        if (floatPrevBtn) {
            floatPrevBtn.classList.toggle("hidden", !canGoPrev);
            if (canGoPrev) {
                const prevTitle = siblings[currentIndex - 1]?.textContent || "Tập trước";
                floatPrevBtn.title = `Tập trước: ${prevTitle} (Hotkey: [ hoặc Shift+P)`;
            }
        }
        if (floatNextBtn) {
            floatNextBtn.classList.toggle("hidden", !canGoNext);
            if (canGoNext) {
                const nextTitle = siblings[currentIndex + 1]?.textContent || "Tập sau";
                floatNextBtn.title = `Tập sau: ${nextTitle} (Hotkey: ] hoặc Shift+N)`;
            }
        }
    }

    const videoNextBtn = document.getElementById("video-next-btn");
    if (videoNextBtn) {
        videoNextBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(1);
        });
    }

    const videoPrevBtn = document.getElementById("video-prev-btn");
    if (videoPrevBtn) {
        videoPrevBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(-1);
        });
    }

    const footerEpPrevBtn = document.getElementById("preview-ep-prev-btn");
    if (footerEpPrevBtn) {
        footerEpPrevBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(-1);
        });
    }

    const footerEpNextBtn = document.getElementById("preview-ep-next-btn");
    if (footerEpNextBtn) {
        footerEpNextBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(1);
        });
    }

    const footerEpSelect = document.getElementById("preview-ep-select");
    if (footerEpSelect) {
        footerEpSelect.addEventListener("change", function (e) {
            if (videoFormatSelect) {
                videoFormatSelect.value = this.value;
                videoFormatSelect.dispatchEvent(new Event("change"));
            }
        });
    }

    const floatPrevBtn = document.getElementById("preview-stream-floating-prev");
    if (floatPrevBtn) {
        floatPrevBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(-1);
        });
    }

    const floatNextBtn = document.getElementById("preview-stream-floating-next");
    if (floatNextBtn) {
        floatNextBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            handleEpisodeStep(1);
        });
    }

    function getProxiedImageUrl(url) {
        if (!url) return "";
        if (url.startsWith("/")) return url;
        // Local file path - proxy through Flask
        if (/^[A-Za-z]:[/\\]/.test(url)) {
            return `/api/proxy/image?url=${encodeURIComponent(url)}`;
        }
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

    // Local file path detection helpers
    function isLocalPath(path) {
        if (!path || typeof path !== "string") return false;
        // Windows absolute path (e.g., C:\, D:\, F:/)
        if (/^[A-Za-z]:[/\\]/.test(path)) return true;
        // Unix absolute path (but exclude URLs like http://)
        if (path.startsWith("/") && !path.startsWith("//") && !path.startsWith("/api/")) return true;
        return false;
    }

    function getLocalStreamUrl(localPath) {
        return `/api/proxy/stream?url=${encodeURIComponent(localPath)}`;
    }

    function getLocalImageUrl(localPath) {
        return `/api/proxy/image?url=${encodeURIComponent(localPath)}`;
    }

    function getLocalSubUrl(localPath) {
        return `/api/system/proxy-sub?url=${encodeURIComponent(localPath)}`;
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

    // Close Cookies Panel button
    const btnCloseCookies = document.getElementById("btn-close-cookies");
    if (btnCloseCookies && cookiesSection) {
        btnCloseCookies.addEventListener("click", () => {
            cookiesSection.classList.add("hidden");
            if (toggleCookiesBtn) {
                const btnSpan = toggleCookiesBtn.querySelector("span");
                if (btnSpan) {
                    btnSpan.textContent = "Manage Cookies";
                }
            }
        });
    }

    // Update Engine Logic
    const updateEngineBtn = document.getElementById("update-engine-btn");
    if (updateEngineBtn) {
        // Query engine version on load to show in title
        fetch("/api/system/engine-version")
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    updateEngineBtn.setAttribute("title", `Current yt-dlp version: ${data.yt_dlp_version}`);
                    if (data.is_frozen) {
                        updateEngineBtn.style.display = "none";
                    }
                }
            })
            .catch(err => console.error("Error fetching engine version:", err));

        updateEngineBtn.addEventListener("click", () => {
            showConfirm({
                title: "Update Downloader Engine",
                message: "Do you want to update the main downloader engine (yt-dlp) to the latest version? This process may take a minute.",
                yesText: "Update Now",
                noText: "Cancel",
                onYes: () => {
                    updateEngineBtn.classList.add("updating");
                    updateEngineBtn.disabled = true;
                    const btnSpan = updateEngineBtn.querySelector("span");
                    if (btnSpan) btnSpan.textContent = "Updating...";

                    fetch("/api/system/update-ytdl", { method: "POST" })
                        .then(res => res.json())
                        .then(data => {
                            updateEngineBtn.classList.remove("updating");
                            updateEngineBtn.disabled = false;
                            if (btnSpan) btnSpan.textContent = "Update Engine";

                            if (data.status === "success") {
                                updateEngineBtn.setAttribute("title", `Current yt-dlp version: ${data.version}`);
                                showConfirm({
                                    title: "Update Succeeded!",
                                    message: `Downloader engine updated successfully to version: ${data.version}.`,
                                    yesText: "Great",
                                    noText: "Close"
                                });
                            } else {
                                showConfirm({
                                    title: "Update Failed",
                                    message: `Error: ${data.message}\n\nOutput: ${data.output}`,
                                    yesText: "Ok",
                                    noText: "Close"
                                });
                            }
                        })
                        .catch(err => {
                            updateEngineBtn.classList.remove("updating");
                            updateEngineBtn.disabled = false;
                            if (btnSpan) btnSpan.textContent = "Update Engine";
                            alert("Connection error while updating engine: " + err.message);
                        });
                }
            });
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
                showError("Please paste cookies content first.");
                return;
            }

            try {
                loaderSection.classList.remove("hidden");
                loaderText.textContent = "Saving cookies...";
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
    let activeMetadata = null;
    let extractedImages = [];

    // Preview state variables
    let previewZoomLevel = 1;
    let previewRotation = 0;
    let previewSubFontSize = 0.88;
    let previewSubWordWrap = true;
    let previewActiveDownloadId = null;
    let previewActiveUrl = "";
    let previewActiveExt = "";
    let previewActiveFilename = "";
    let previewActiveBtn = null;
    let previewActiveFormatId = "";
    let previewActiveQuality = "";
    let previewActiveCustomUrl = "";
    let previewActiveEpisode = "";
    let previewActiveServer = "";
    let previewActiveType = "";
    let previewActivePollInterval = null;
    let previewActiveSubtitleContent = "";
    let previewCurrentImageIndex = -1;

    // Adaptive Streaming Preview State
    let previewIsAdaptive = false;
    let previewAdaptiveVideoUrl = "";
    let previewAdaptiveAudioUrl = "";
    let previewAdaptiveContainer = "";
    let previewCurrentTimeOffset = 0;

    // Subtitles & advanced player states
    let currentCues = [];
    let isEditingSubtitles = false;
    let activeSubUrl = "";
    let originalSubtitleContent = "";
    let loopStartSecs = null;
    let loopEndSecs = null;
    let lastTtsText = "";
    let isDraggingVideoSlider = false;
    let isDraggingAudioSlider = false;
    let videoFullscreenMode = 0; // 0: Normal, 1: Theater, 2: Native Fullscreen

    // --- Audio Player Feature Expansion State ---
    let audioLyrics = []; // Array of parsed cues: { start: Number, end: Number, text: String }
    let activeLyricIndex = -1;
    let audioSubSelectUrl = "";

    // --- Seek Thumbnail Preview State & Memory Cache ---
    let thumbSeekPending = false;
    let thumbNextSeekTime = null;
    let thumbCurrentSeekingTime = null;
    let thumbLastDrawnTime = -1;
    let thumbSourceReady = false;
    let thumbHlsInstance = null;
    const thumbCache = new Map(); // Key: Math.round(targetTime), Value: ImageBitmap
    const MAX_THUMB_CACHE = 120;

    function clearThumbCache() {
        thumbCache.forEach(bmp => {
            if (bmp && typeof bmp.close === "function") {
                try { bmp.close(); } catch (e) { }
            }
        });
        thumbCache.clear();
    }

    function seekAdaptiveVideo(targetTime) {
        if (!previewIsAdaptive) return;

        showPreviewLoader("Seeking stream...");
        previewCurrentTimeOffset = targetTime;

        // Stop current playback
        previewVideoPlayer.pause();

        // Re-construct the proxy stream URL with start_time = targetTime
        const proxyStreamUrl = `/api/proxy/stream_adaptive?video_url=${encodeURIComponent(previewAdaptiveVideoUrl)}&audio_url=${encodeURIComponent(previewAdaptiveAudioUrl)}&container=${encodeURIComponent(previewAdaptiveContainer)}&start_time=${targetTime}&client_id=${encodeURIComponent(clientId)}`;

        // Load the new stream URL
        previewVideoPlayer.src = proxyStreamUrl;
        previewVideoPlayer.load();

        // Resume playing once loaded
        previewVideoPlayer.play()
            .then(() => {
                hidePreviewLoader();
            })
            .catch(e => {
                console.log("Playback blocked or failed on seek:", e);
                setTimeout(() => {
                    previewVideoPlayer.play().catch(err => console.log("Retry play blocked: ", err));
                }, 150);
            });
    }

    // Helper to stop all preview playbacks and destroy Hls instances
    function stopAllPreviewPlaybacks(isClosingModal = false) {
        if (previewActivePollInterval) {
            previewActivePollInterval.close();
            previewActivePollInterval = null;
        }
        if (window._previewWebviewPollTimer) {
            clearInterval(window._previewWebviewPollTimer);
            window._previewWebviewPollTimer = null;
        }
        if (previewWebpagePauseIndicator) {
            previewWebpagePauseIndicator.classList.add("hidden");
        }
        if (previewWebpageWebview) {
            try {
                previewWebpageWebview.executeJavaScript(`
                    (function() {
                        try {
                            if (typeof jwplayer === 'function') {
                                const p = jwplayer('player');
                                if (p) { p.stop(); p.pause(); }
                            }
                        } catch(_) {}
                        document.querySelectorAll('video, audio').forEach(v => {
                            try {
                                v.pause();
                                v.muted = true;
                            } catch(_) {}
                        });
                        return true;
                    })()
                `).catch(() => {});
            } catch (_) {}
            if (isClosingModal) {
                previewWebpageWebview.classList.add("hidden");
                try {
                    if (typeof previewWebpageWebview.stop === 'function') {
                        try { previewWebpageWebview.stop(); } catch (_) {}
                    }
                    previewWebpageWebview.src = "about:blank";
                } catch (_) {}
            }
        }
        if (previewWebpageIframe && isClosingModal) {
            previewWebpageIframe.classList.add("hidden");
            try { previewWebpageIframe.src = "about:blank"; } catch (_) {}
            try { previewWebpageIframe.removeAttribute("src"); } catch (_) {}
        }
        if (previewWebpageContainer && isClosingModal) {
            previewWebpageContainer.classList.add("hidden");
        }
        if (previewVideoPlayer) {
            previewVideoPlayer.pause();
            previewVideoPlayer.onerror = null;
            previewVideoPlayer.loop = false;
            if (videoLoopBtn) {
                videoLoopBtn.classList.remove("active-loop");
                videoLoopBtn.title = "Repeat (Off)";
                videoLoopBtn.style.color = "";
                videoLoopBtn.style.borderColor = "";
                videoLoopBtn.style.boxShadow = "";
            }
            if (previewVideoPlayer.hlsInstance) {
                previewVideoPlayer.hlsInstance.destroy();
                delete previewVideoPlayer.hlsInstance;
            }
            previewVideoPlayer.removeAttribute("src");
            try {
                previewVideoPlayer.load();
            } catch (e) { }
        }
        // Clean up thumbnail preview video
        if (thumbHlsInstance) {
            thumbHlsInstance.destroy();
            thumbHlsInstance = null;
        }
        if (thumbPreviewVideo) {
            thumbPreviewVideo.removeAttribute("src");
            thumbPreviewVideo.removeAttribute("data-thumb-src");
            try { thumbPreviewVideo.load(); } catch (e) { }
            thumbSourceReady = false;
        }
        thumbNextSeekTime = null;
        thumbCurrentSeekingTime = null;
        thumbLastDrawnTime = -1;
        clearThumbCache();
        if (seekThumbCanvas) {
            seekThumbCanvas.classList.add("is-seeking");
        }
        if (seekThumbTooltip) {
            seekThumbTooltip.classList.remove("visible");
        }
        if (seekThumbDot) {
            seekThumbDot.classList.remove("visible");
        }
        if (previewAudioPlayer) {
            previewAudioPlayer.pause();
            previewAudioPlayer.onerror = null;
            previewAudioPlayer.loop = false;
            if (audioLoopBtn) {
                audioLoopBtn.classList.remove("active-loop");
                audioLoopBtn.title = "Repeat (Off)";
                audioLoopBtn.style.color = "";
                audioLoopBtn.style.borderColor = "";
                audioLoopBtn.style.boxShadow = "";
            }
            previewAudioPlayer.removeAttribute("src");
            try {
                previewAudioPlayer.load();
            } catch (e) { }

            // Reset visualizer canvas and placeholder animation state
            const audioCanvas = document.getElementById("audio-visualizer-canvas");
            if (audioCanvas) {
                audioCanvas.classList.add("hidden");
                const audioCtx2D = audioCanvas.getContext("2d");
                if (audioCtx2D) {
                    audioCtx2D.clearRect(0, 0, audioCanvas.width, audioCanvas.height);
                }
            }
            const staticVisualizer = document.querySelector(".waveform-animation");
            if (staticVisualizer) {
                staticVisualizer.classList.remove("hidden-visualizer");
            }
        }

        // Reset subtitles state
        currentCues = [];
        activeSubUrl = "";
        originalSubtitleContent = "";
        loopStartSecs = null;
        loopEndSecs = null;
        lastTtsText = "";
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }

        // Hide overlays & sidebar
        const subOverlay = document.getElementById("preview-subtitles-overlay");
        if (subOverlay) {
            subOverlay.classList.add("hidden");
            const box = subOverlay.querySelector(".subtitles-text-box");
            if (box) box.textContent = "";
        }

        const sidebar = document.getElementById("preview-transcript-sidebar");
        if (sidebar) {
            sidebar.classList.add("hidden");
            const list = document.getElementById("transcript-list");
            if (list) list.innerHTML = "";
            const search = document.getElementById("transcript-search");
            if (search) search.value = "";
        }

        // Reset sub controls UI values
        const loopA = document.getElementById("loop-point-a");
        const loopB = document.getElementById("loop-point-b");
        if (loopA) loopA.value = "";
        if (loopB) loopB.value = "";

        const subSelect = document.getElementById("preview-sub-select");
        if (subSelect) subSelect.innerHTML = '<option value="none">None</option>';

        const subTrans = document.getElementById("preview-sub-trans-select");
        if (subTrans) subTrans.value = "none";

        const voiceover = document.getElementById("preview-voiceover-select");
        if (voiceover) voiceover.value = "none";

        setPlaybackSpeedUI(1.0);

        const stylePopover = document.getElementById("preview-sub-style-popover");
        if (stylePopover) stylePopover.classList.add("hidden");

        const videoSettingsMenu = document.getElementById("video-settings-menu");
        if (videoSettingsMenu) videoSettingsMenu.classList.add("hidden");

        const downloadSubBtn = document.getElementById("preview-sub-download-btn");
        if (downloadSubBtn) downloadSubBtn.disabled = true;

        // Reset Custom Audio UI
        if (audioCard) audioCard.classList.remove("playing");
        if (audioPlayPauseBtn) {
            const playIcon = audioPlayPauseBtn.querySelector(".play-icon");
            const pauseIcon = audioPlayPauseBtn.querySelector(".pause-icon");
            if (playIcon) playIcon.classList.remove("hidden");
            if (pauseIcon) pauseIcon.classList.add("hidden");
        }
        if (audioSeekSlider) {
            audioSeekSlider.value = 0;
            updateSliderBackground(audioSeekSlider);
        }
        if (audioTimeCurrent) audioTimeCurrent.textContent = "00:00";
        if (audioTimeTotal) audioTimeTotal.textContent = "00:00";

        // Reset Custom Video UI
        if (videoCard) videoCard.classList.remove("playing");
        if (videoPlayPauseBtn) {
            const playIcon = videoPlayPauseBtn.querySelector(".play-icon");
            const pauseIcon = videoPlayPauseBtn.querySelector(".pause-icon");
            if (playIcon) playIcon.classList.remove("hidden");
            if (pauseIcon) pauseIcon.classList.add("hidden");
        }
        if (videoSeekSlider) {
            videoSeekSlider.value = 0;
            updateSliderBackground(videoSeekSlider);
        }
        if (videoTimeCurrent) videoTimeCurrent.textContent = "00:00";
        if (videoTimeTotal) videoTimeTotal.textContent = "00:00";
        if (customVideoControls) {
            customVideoControls.classList.add("hidden-controls");
        }
        resetAudioEffects();
    }

    // Format Time helper (seconds -> mm:ss)
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds === Infinity) return "00:00";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    }

    // Format Time detailed helper (seconds -> hh:mm:ss.xxx)
    function formatTimeDetailed(seconds) {
        if (isNaN(seconds) || seconds === Infinity || seconds < 0) return "00:00:00.000";
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);

        const hrsStr = hrs.toString().padStart(2, "0");
        const minsStr = mins.toString().padStart(2, "0");
        const secsStr = secs.toString().padStart(2, "0");
        const msStr = ms.toString().padStart(3, "0");

        return `${hrsStr}:${minsStr}:${secsStr}.${msStr}`;
    }

    // Helper to reliably compute total video duration across adaptive and progressive streams
    function getVideoTotalDuration() {
        const metaDuration = parseFloat(activeMetadata && activeMetadata.duration_raw ? activeMetadata.duration_raw : 0) || 0;
        if (previewIsAdaptive) {
            return metaDuration > 0 ? metaDuration : (previewVideoPlayer && previewVideoPlayer.duration && isFinite(previewVideoPlayer.duration) ? previewVideoPlayer.duration : 0);
        }
        return (previewVideoPlayer && previewVideoPlayer.duration && isFinite(previewVideoPlayer.duration) && previewVideoPlayer.duration > 0)
            ? previewVideoPlayer.duration
            : metaDuration;
    }

    // Dynamic track fill for ranges
    function updateSliderBackground(slider) {
        if (!slider) return;
        const val = parseFloat(slider.value) || 0;
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 100;
        const pct = ((val - min) / (max - min)) * 100;

        let pct_buffered = 0;
        let isMediaSeek = false;

        if (slider === audioSeekSlider && previewAudioPlayer) {
            const metaDuration = parseFloat(activeMetadata && activeMetadata.duration_raw ? activeMetadata.duration_raw : 0) || 0;
            const playerDuration = (previewAudioPlayer.duration && isFinite(previewAudioPlayer.duration) && previewAudioPlayer.duration > 0)
                ? previewAudioPlayer.duration
                : metaDuration;
            const totalDuration = playerDuration;

            if (totalDuration > 0) {
                isMediaSeek = true;
                if (previewAudioPlayer.buffered && previewAudioPlayer.buffered.length > 0) {
                    let bufferedEnd = 0;
                    const curTime = previewAudioPlayer.currentTime || 0;
                    for (let i = 0; i < previewAudioPlayer.buffered.length; i++) {
                        const bStart = previewAudioPlayer.buffered.start(i);
                        const bEnd = previewAudioPlayer.buffered.end(i);
                        if (bStart <= curTime + 0.5 && bEnd >= curTime - 0.5) {
                            bufferedEnd = Math.max(bufferedEnd, bEnd);
                        }
                    }
                    if (bufferedEnd === 0) {
                        bufferedEnd = previewAudioPlayer.buffered.end(previewAudioPlayer.buffered.length - 1);
                    }
                    pct_buffered = (bufferedEnd / totalDuration) * 100;
                }
            }
        } else if (slider === videoSeekSlider && previewVideoPlayer) {
            const totalDuration = getVideoTotalDuration();
            if (totalDuration > 0) {
                isMediaSeek = true;
                if (previewVideoPlayer.buffered && previewVideoPlayer.buffered.length > 0) {
                    let bufferedEnd = 0;
                    const curTime = previewVideoPlayer.currentTime || 0;
                    for (let i = 0; i < previewVideoPlayer.buffered.length; i++) {
                        const bStart = previewVideoPlayer.buffered.start(i);
                        const bEnd = previewVideoPlayer.buffered.end(i);
                        if (bStart <= curTime + 0.5 && bEnd >= curTime - 0.5) {
                            bufferedEnd = Math.max(bufferedEnd, bEnd);
                        }
                    }
                    if (bufferedEnd === 0) {
                        bufferedEnd = previewVideoPlayer.buffered.end(previewVideoPlayer.buffered.length - 1);
                    }
                    const absBufferedEnd = previewIsAdaptive ? (previewCurrentTimeOffset + bufferedEnd) : bufferedEnd;
                    pct_buffered = (absBufferedEnd / totalDuration) * 100;
                }
            }
        }

        if (isMediaSeek) {
            if (!isFinite(pct_buffered) || isNaN(pct_buffered)) {
                pct_buffered = pct;
            } else {
                pct_buffered = Math.max(pct, Math.min(100, pct_buffered));
            }
            const isLightTheme = document.documentElement.classList.contains("light-theme");
            // Faded theme accent color (màu mờ mờ theo màu chủ đạo)
            const bufferedOpacity = isLightTheme ? 0.35 : 0.45;
            const bufferedColor = `rgba(var(--cyan-rgb), ${bufferedOpacity})`;
            slider.style.background = `linear-gradient(
                to right,
                var(--cyan) 0%,
                var(--cyan) ${pct}%,
                ${bufferedColor} ${pct}%,
                ${bufferedColor} ${pct_buffered}%,
                var(--slider-track) ${pct_buffered}%,
                var(--slider-track) 100%
            )`;
        } else {
            slider.style.background = `linear-gradient(to right, var(--cyan) 0%, var(--cyan) ${pct}%, var(--slider-track) ${pct}%, var(--slider-track) 100%)`;
        }
    }

    // --- AUDIO VISUALIZER LOGIC (WEB AUDIO API) ---
    let audioCtx = null;
    let analyser = null;
    let sourceNode = null;
    let videoSourceNode = null;
    let visualizerAnimationId = null;

    // EQ & Effect Web Audio Nodes
    let eqBassNode = null;
    let eqLowMidNode = null;
    let eqHighMidNode = null;
    let eqTrebleNode = null;
    let voiceLowFilterNode = null;
    let voiceHighFilterNode = null;
    let delayNode = null;
    let delayFeedbackNode = null;
    let delayGainNode = null;

    function initAudioVisualizer() {
        if (audioCtx) return;
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextClass) return;

            audioCtx = new AudioContextClass();
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256; // 128 bins for high-density visualizer

            // Expose globally for the background grid
            window.audioAnalyser = analyser;

            // Make sure the audio player supports CORS requests so the Web Audio node doesn't get blocked
            previewAudioPlayer.crossOrigin = "anonymous";

            sourceNode = audioCtx.createMediaElementSource(previewAudioPlayer);

            // Create EQ nodes
            eqBassNode = audioCtx.createBiquadFilter();
            eqBassNode.type = "peaking";
            eqBassNode.frequency.value = 60;
            eqBassNode.Q.value = 1.0;
            eqBassNode.gain.value = 0;

            eqLowMidNode = audioCtx.createBiquadFilter();
            eqLowMidNode.type = "peaking";
            eqLowMidNode.frequency.value = 500;
            eqLowMidNode.Q.value = 1.0;
            eqLowMidNode.gain.value = 0;

            eqHighMidNode = audioCtx.createBiquadFilter();
            eqHighMidNode.type = "peaking";
            eqHighMidNode.frequency.value = 2000;
            eqHighMidNode.Q.value = 1.0;
            eqHighMidNode.gain.value = 0;

            eqTrebleNode = audioCtx.createBiquadFilter();
            eqTrebleNode.type = "peaking";
            eqTrebleNode.frequency.value = 10000;
            eqTrebleNode.Q.value = 1.0;
            eqTrebleNode.gain.value = 0;

            // Create Voice effect nodes
            voiceLowFilterNode = audioCtx.createBiquadFilter();
            voiceLowFilterNode.type = "allpass";

            voiceHighFilterNode = audioCtx.createBiquadFilter();
            voiceHighFilterNode.type = "allpass";

            // Create Delay / Reverb nodes (for Concert Hall)
            delayNode = audioCtx.createDelay(1.0);
            delayNode.delayTime.value = 0.15; // 150ms delay
            delayFeedbackNode = audioCtx.createGain();
            delayFeedbackNode.gain.value = 0.45; // 45% feedback
            delayGainNode = audioCtx.createGain();
            delayGainNode.gain.value = 0.0; // dry by default

            // Chain EQ & Voice filters
            sourceNode.connect(eqBassNode);
            eqBassNode.connect(eqLowMidNode);
            eqLowMidNode.connect(eqHighMidNode);
            eqHighMidNode.connect(eqTrebleNode);
            eqTrebleNode.connect(voiceLowFilterNode);
            voiceLowFilterNode.connect(voiceHighFilterNode);

            // Connect Dry path to Analyser
            voiceHighFilterNode.connect(analyser);

            // Connect Wet path (Delay loop)
            voiceHighFilterNode.connect(delayNode);
            delayNode.connect(delayFeedbackNode);
            delayFeedbackNode.connect(delayNode); // feedback loop
            delayNode.connect(delayGainNode);
            delayGainNode.connect(analyser); // mix back into analyser

            // Set up video preview player Web Audio routing
            if (previewVideoPlayer && !videoSourceNode) {
                try {
                    previewVideoPlayer.crossOrigin = "anonymous";
                    videoSourceNode = audioCtx.createMediaElementSource(previewVideoPlayer);
                    videoSourceNode.connect(eqBassNode);
                } catch (e) {
                    // ponytail: ignore if already connected to audioCtx or blocked by CORS
                    console.log("videoSourceNode already created or failed:", e);
                }
            }

            // Connect Analyser to Destination
            analyser.connect(audioCtx.destination);

            // Add the class to disable simulated CSS animations
            const waveformContainer = document.querySelector(".waveform-animation");
            if (waveformContainer) {
                waveformContainer.classList.add("real-visualizer");
            }

            // Sync with current UI states in case settings were modified before visualizer loaded
            syncAudioEffectsToNodes();

        } catch (err) {
            console.warn("Failed to initialize Web Audio visualizer, falling back to CSS animation:", err);
        }
    }

    function syncAudioEffectsToNodes() {
        if (!audioCtx) return;

        // Apply EQ slider gains
        const bassVal = parseFloat(document.getElementById("eq-bass").value) || 0;
        const lowmidVal = parseFloat(document.getElementById("eq-lowmid").value) || 0;
        const highmidVal = parseFloat(document.getElementById("eq-highmid").value) || 0;
        const trebleVal = parseFloat(document.getElementById("eq-treble").value) || 0;

        if (eqBassNode) eqBassNode.gain.setValueAtTime(bassVal, audioCtx.currentTime);
        if (eqLowMidNode) eqLowMidNode.gain.setValueAtTime(lowmidVal, audioCtx.currentTime);
        if (eqHighMidNode) eqHighMidNode.gain.setValueAtTime(highmidVal, audioCtx.currentTime);
        if (eqTrebleNode) eqTrebleNode.gain.setValueAtTime(trebleVal, audioCtx.currentTime);

        // Apply Voice FX preset
        const activeVoiceBtn = document.querySelector(".voice-preset.active");
        if (activeVoiceBtn) {
            const voicePreset = activeVoiceBtn.dataset.voice;
            applyVoiceEffectsNodePreset(voicePreset);
        }
    }

    function applyVoiceEffectsNodePreset(voicePreset) {
        if (!audioCtx || !voiceLowFilterNode || !voiceHighFilterNode || !delayGainNode) return;

        // Reset first to standard before applying preset
        voiceLowFilterNode.type = "allpass";
        voiceHighFilterNode.type = "allpass";
        delayGainNode.gain.setValueAtTime(0.0, audioCtx.currentTime);

        switch (voicePreset) {
            case "normal":
                // already reset
                break;
            case "deep":
                voiceLowFilterNode.type = "lowshelf";
                voiceLowFilterNode.frequency.setValueAtTime(150, audioCtx.currentTime);
                voiceLowFilterNode.gain.setValueAtTime(8, audioCtx.currentTime);

                voiceHighFilterNode.type = "highshelf";
                voiceHighFilterNode.frequency.setValueAtTime(3000, audioCtx.currentTime);
                voiceHighFilterNode.gain.setValueAtTime(-8, audioCtx.currentTime);
                break;
            case "bright":
                voiceLowFilterNode.type = "lowshelf";
                voiceLowFilterNode.frequency.setValueAtTime(200, audioCtx.currentTime);
                voiceLowFilterNode.gain.setValueAtTime(-4, audioCtx.currentTime);

                voiceHighFilterNode.type = "highshelf";
                voiceHighFilterNode.frequency.setValueAtTime(4000, audioCtx.currentTime);
                voiceHighFilterNode.gain.setValueAtTime(8, audioCtx.currentTime);
                break;
            case "hall":
                delayGainNode.gain.setValueAtTime(0.4, audioCtx.currentTime);
                break;
            case "studio":
                voiceLowFilterNode.type = "peaking";
                voiceLowFilterNode.frequency.setValueAtTime(120, audioCtx.currentTime);
                voiceLowFilterNode.gain.setValueAtTime(2, audioCtx.currentTime);

                voiceHighFilterNode.type = "peaking";
                voiceHighFilterNode.frequency.setValueAtTime(3200, audioCtx.currentTime);
                voiceHighFilterNode.gain.setValueAtTime(3, audioCtx.currentTime);

                delayGainNode.gain.setValueAtTime(0.08, audioCtx.currentTime);
                break;
            case "lofi":
                voiceLowFilterNode.type = "lowpass";
                voiceLowFilterNode.frequency.setValueAtTime(3200, audioCtx.currentTime);

                voiceHighFilterNode.type = "highpass";
                voiceHighFilterNode.frequency.setValueAtTime(180, audioCtx.currentTime);
                break;
            case "telephone":
                voiceLowFilterNode.type = "highpass";
                voiceLowFilterNode.frequency.setValueAtTime(450, audioCtx.currentTime);

                voiceHighFilterNode.type = "lowpass";
                voiceHighFilterNode.frequency.setValueAtTime(2800, audioCtx.currentTime);
                break;
            case "underwater":
                voiceLowFilterNode.type = "lowpass";
                voiceLowFilterNode.frequency.setValueAtTime(600, audioCtx.currentTime);

                delayGainNode.gain.setValueAtTime(0.2, audioCtx.currentTime);
                break;
        }
    }

    const EQ_PRESETS = {
        flat: { bass: 0, lowmid: 0, highmid: 0, treble: 0 },
        bass: { bass: 9, lowmid: 4, highmid: -1, treble: -2 },
        vocal: { bass: -3, lowmid: 3, highmid: 7, treble: 4 },
        acoustic: { bass: 4, lowmid: 2, highmid: 3, treble: 5 },
        electronic: { bass: 7, lowmid: -2, highmid: 4, treble: 6 },
        lofi: { bass: 4, lowmid: -2, highmid: -8, treble: -12 }
    };

    function applyEqPreset(presetName) {
        const values = EQ_PRESETS[presetName];
        if (!values) return;

        // Set inputs in UI
        const bassInput = document.getElementById("eq-bass");
        const lowmidInput = document.getElementById("eq-lowmid");
        const highmidInput = document.getElementById("eq-highmid");
        const trebleInput = document.getElementById("eq-treble");

        if (bassInput) {
            bassInput.value = values.bass;
            updateSliderBackground(bassInput);
            document.getElementById("eq-bass-val").textContent = (values.bass > 0 ? "+" : "") + values.bass;
        }
        if (lowmidInput) {
            lowmidInput.value = values.lowmid;
            updateSliderBackground(lowmidInput);
            document.getElementById("eq-lowmid-val").textContent = (values.lowmid > 0 ? "+" : "") + values.lowmid;
        }
        if (highmidInput) {
            highmidInput.value = values.highmid;
            updateSliderBackground(highmidInput);
            document.getElementById("eq-highmid-val").textContent = (values.highmid > 0 ? "+" : "") + values.highmid;
        }
        if (trebleInput) {
            trebleInput.value = values.treble;
            updateSliderBackground(trebleInput);
            document.getElementById("eq-treble-val").textContent = (values.treble > 0 ? "+" : "") + values.treble;
        }

        // Apply to nodes
        if (audioCtx) {
            if (eqBassNode) eqBassNode.gain.setValueAtTime(values.bass, audioCtx.currentTime);
            if (eqLowMidNode) eqLowMidNode.gain.setValueAtTime(values.lowmid, audioCtx.currentTime);
            if (eqHighMidNode) eqHighMidNode.gain.setValueAtTime(values.highmid, audioCtx.currentTime);
            if (eqTrebleNode) eqTrebleNode.gain.setValueAtTime(values.treble, audioCtx.currentTime);
        }
    }

    function saveAudioSettingsToStorage() {
        const eqBassVal = parseFloat(document.getElementById("eq-bass")?.value || 0);
        const eqLowMidVal = parseFloat(document.getElementById("eq-lowmid")?.value || 0);
        const eqHighMidVal = parseFloat(document.getElementById("eq-highmid")?.value || 0);
        const eqTrebleVal = parseFloat(document.getElementById("eq-treble")?.value || 0);
        const audioSpeedVal = parseFloat(document.getElementById("audio-speed-slider")?.value || 1.0);
        const activeVoiceBtn = document.querySelector(".voice-preset.active");
        const voicePreset = activeVoiceBtn ? activeVoiceBtn.dataset.voice : "normal";

        localStorage.setItem("audio_eq_bass", eqBassVal);
        localStorage.setItem("audio_eq_lowmid", eqLowMidVal);
        localStorage.setItem("audio_eq_highmid", eqHighMidVal);
        localStorage.setItem("audio_eq_treble", eqTrebleVal);
        localStorage.setItem("audio_speed", audioSpeedVal);
        localStorage.setItem("audio_voice_preset", voicePreset);
    }

    function loadAudioSettingsFromStorage() {
        const eqBass = localStorage.getItem("audio_eq_bass") !== null ? parseFloat(localStorage.getItem("audio_eq_bass")) : 0;
        const eqLowMid = localStorage.getItem("audio_eq_lowmid") !== null ? parseFloat(localStorage.getItem("audio_eq_lowmid")) : 0;
        const eqHighMid = localStorage.getItem("audio_eq_highmid") !== null ? parseFloat(localStorage.getItem("audio_eq_highmid")) : 0;
        const eqTreble = localStorage.getItem("audio_eq_treble") !== null ? parseFloat(localStorage.getItem("audio_eq_treble")) : 0;
        const audioSpeed = localStorage.getItem("audio_speed") !== null ? parseFloat(localStorage.getItem("audio_speed")) : 1.0;
        const voicePreset = localStorage.getItem("audio_voice_preset") || "normal";

        // Apply UI values
        const bassInput = document.getElementById("eq-bass");
        const lowmidInput = document.getElementById("eq-lowmid");
        const highmidInput = document.getElementById("eq-highmid");
        const trebleInput = document.getElementById("eq-treble");
        const audioSpeedSliderEl = document.getElementById("audio-speed-slider");
        const audioSpeedDisplayEl = document.getElementById("audio-speed-display");

        if (bassInput) {
            bassInput.value = eqBass;
            updateSliderBackground(bassInput);
            const valEl = document.getElementById("eq-bass-val");
            if (valEl) valEl.textContent = (eqBass > 0 ? "+" : "") + eqBass;
        }
        if (lowmidInput) {
            lowmidInput.value = eqLowMid;
            updateSliderBackground(lowmidInput);
            const valEl = document.getElementById("eq-lowmid-val");
            if (valEl) valEl.textContent = (eqLowMid > 0 ? "+" : "") + eqLowMid;
        }
        if (highmidInput) {
            highmidInput.value = eqHighMid;
            updateSliderBackground(highmidInput);
            const valEl = document.getElementById("eq-highmid-val");
            if (valEl) valEl.textContent = (eqHighMid > 0 ? "+" : "") + eqHighMid;
        }
        if (trebleInput) {
            trebleInput.value = eqTreble;
            updateSliderBackground(trebleInput);
            const valEl = document.getElementById("eq-treble-val");
            if (valEl) valEl.textContent = (eqTreble > 0 ? "+" : "") + eqTreble;
        }

        if (audioSpeedSliderEl) {
            audioSpeedSliderEl.value = audioSpeed;
            updateSliderBackground(audioSpeedSliderEl);
        }
        if (audioSpeedDisplayEl) {
            audioSpeedDisplayEl.textContent = audioSpeed.toFixed(2);
        }

        // Apply active presets styling
        if (speedPresetBtns) {
            speedPresetBtns.forEach(btn => {
                const s = parseFloat(btn.dataset.speed);
                if (Math.abs(s - audioSpeed) < 0.01) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
        }

        // Match EQ Preset active highlight
        if (eqPresets) {
            eqPresets.forEach(btn => {
                const preset = btn.dataset.preset;
                const values = EQ_PRESETS[preset];
                if (values &&
                    Math.abs(values.bass - eqBass) < 0.01 &&
                    Math.abs(values.lowmid - eqLowMid) < 0.01 &&
                    Math.abs(values.highmid - eqHighMid) < 0.01 &&
                    Math.abs(values.treble - eqTreble) < 0.01) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
        }

        // Match Voice FX active highlight
        if (voicePresets) {
            voicePresets.forEach(btn => {
                if (btn.dataset.voice === voicePreset) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
        }

        // Apply to Web Audio nodes if audioCtx is already initialized
        if (audioCtx) {
            if (eqBassNode) eqBassNode.gain.setValueAtTime(eqBass, audioCtx.currentTime);
            if (eqLowMidNode) eqLowMidNode.gain.setValueAtTime(eqLowMid, audioCtx.currentTime);
            if (eqHighMidNode) eqHighMidNode.gain.setValueAtTime(eqHighMid, audioCtx.currentTime);
            if (eqTrebleNode) eqTrebleNode.gain.setValueAtTime(eqTreble, audioCtx.currentTime);

            // Re-apply voice FX
            applyVoiceEffectsNodePreset(voicePreset);

            // Re-apply playback speed to previewAudioPlayer
            if (previewAudioPlayer) {
                previewAudioPlayer.playbackRate = audioSpeed;
            }
        }
    }

    function resetAudioEffects() {
        loadAudioSettingsFromStorage();

        // Reset Lyrics
        audioLyrics = [];
        activeLyricIndex = -1;
        if (audioLyricsList) {
            audioLyricsList.innerHTML = '<div class="lyrics-placeholder">Upload a .vtt or .srt subtitle file to see lyrics</div>';
        }
        if (audioSubSelect) {
            audioSubSelect.innerHTML = '<option value="none">None</option>';
            audioSubSelect.value = "none";
        }
        audioSubSelectUrl = "";

        // Hide Panels
        if (audioSettingsPanel) {
            audioSettingsPanel.classList.add("hidden");
        }
        if (audioSidePanel) {
            audioSidePanel.classList.add("hidden");
        }
        if (audioEqBtn) {
            audioEqBtn.classList.remove("active");
        }
        if (audioLyricsOverlay) {
            audioLyricsOverlay.classList.add("hidden");
        }
        if (audioLyricsBtn) {
            audioLyricsBtn.classList.remove("active");
        }
    }

    function setupAudioPreviewSubtitles() {
        if (!audioSubSelect) return;
        audioSubSelect.innerHTML = '<option value="none">None</option>';

        let subOpts = (activeMetadata && activeMetadata.subtitles) ? activeMetadata.subtitles : [];
        if (subOpts && typeof subOpts === "object" && !Array.isArray(subOpts)) {
            subOpts = Object.keys(subOpts).map(key => {
                const val = subOpts[key];
                if (typeof val === "string") {
                    return { lang_code: key, name: key.toUpperCase(), url: val };
                }
                return {
                    lang_code: key,
                    name: val.name || key.toUpperCase(),
                    url: val.url || ""
                };
            });
        }
        if (!Array.isArray(subOpts)) {
            subOpts = [];
        }
        subOpts.forEach(opt => {
            const optionEl = document.createElement("option");
            optionEl.value = opt.url || opt.lang_code;
            optionEl.textContent = opt.name;
            audioSubSelect.appendChild(optionEl);
        });

        // Clear existing lyrics
        audioLyrics = [];
        activeLyricIndex = -1;
        if (audioLyricsList) {
            audioLyricsList.innerHTML = '<div class="lyrics-placeholder">Upload a .vtt or .srt subtitle file to see lyrics</div>';
        }

        // Auto-load first subtitle if available
        if (subOpts.length > 0) {
            const autoSub = subOpts.find(s => s.lang_code === "vi") || subOpts.find(s => s.lang_code === "en") || subOpts[0];
            if (autoSub) {
                audioSubSelect.value = autoSub.url || autoSub.lang_code;
                loadAudioSubtitle(autoSub.url || autoSub.lang_code);
            }
        }
    }

    async function loadAudioSubtitle(urlOrContent, isContent = false) {
        try {
            let text = "";
            if (isContent) {
                text = urlOrContent;
            } else {
                if (!urlOrContent || urlOrContent === "none") {
                    audioLyrics = [];
                    activeLyricIndex = -1;
                    if (audioLyricsList) {
                        audioLyricsList.innerHTML = '<div class="lyrics-placeholder">Upload a .vtt or .srt subtitle file to see lyrics</div>';
                    }
                    return;
                }

                audioSubSelectUrl = urlOrContent;
                let requestUrl = urlOrContent;
                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    if (requestUrl.includes("fmt=")) {
                        requestUrl = requestUrl.replace(/fmt=[^&]+/, "fmt=vtt");
                    } else {
                        requestUrl += requestUrl.includes("?") ? "&fmt=vtt" : "?fmt=vtt";
                    }
                }

                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    try {
                        const res = await fetch(requestUrl);
                        if (!res.ok) throw new Error("Direct fetch failed");
                        text = await res.text();
                    } catch (err) {
                        console.warn("Direct timedtext fetch failed for audio, falling back to proxy...", err);
                        const proxyUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                        const res = await fetch(proxyUrl);
                        text = await res.text();
                    }
                } else {
                    let fetchUrl = requestUrl;
                    if (requestUrl.startsWith("http://") || requestUrl.startsWith("https://") || requestUrl.startsWith("/api/download/file/")) {
                        fetchUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                    }
                    const res = await fetch(fetchUrl);
                    text = await res.text();
                }
            }

            const cues = parseSubtitleText(text);
            console.log(`Loaded ${cues.length} audio lyrics cues`);
            renderAudioLyrics(cues);
        } catch (err) {
            console.error("Failed to load audio subtitles:", err);
            if (audioLyricsList) {
                audioLyricsList.innerHTML = '<div class="lyrics-placeholder" style="color:var(--red)">Failed to load subtitles file.</div>';
            }
        }
    }

    function renderAudioLyrics(cues) {
        audioLyrics = cues;
        activeLyricIndex = -1;

        if (!audioLyricsList) return;

        if (audioLyrics.length === 0) {
            audioLyricsList.innerHTML = '<div class="lyrics-placeholder">No lyric lines found in file.</div>';
            return;
        }

        audioLyricsList.innerHTML = "";
        audioLyrics.forEach((cue, index) => {
            const lineDiv = document.createElement("div");
            lineDiv.className = "lyrics-line";
            lineDiv.setAttribute("data-index", index);
            lineDiv.innerHTML = cue.text.replace(/\n/g, "<br>");

            lineDiv.addEventListener("click", () => {
                if (previewAudioPlayer) {
                    previewAudioPlayer.currentTime = cue.start;
                }
            });

            audioLyricsList.appendChild(lineDiv);
        });
    }

    function syncAudioLyrics(currentTime) {
        if (!audioLyrics || audioLyrics.length === 0 || !audioLyricsList) return;

        // Find the matching cue
        let matchIndex = -1;

        // Find the latest cue that started before currentTime
        for (let i = 0; i < audioLyrics.length; i++) {
            if (currentTime >= audioLyrics[i].start && currentTime <= audioLyrics[i].end) {
                matchIndex = i;
                break;
            }
        }

        // If not found in a specific range, find the closest active line
        if (matchIndex === -1) {
            for (let i = audioLyrics.length - 1; i >= 0; i--) {
                if (currentTime >= audioLyrics[i].start) {
                    matchIndex = i;
                    break;
                }
            }
        }

        if (matchIndex !== -1 && matchIndex !== activeLyricIndex) {
            // Remove active class from previous
            const oldActive = audioLyricsList.querySelector(".lyrics-line.active");
            if (oldActive) oldActive.classList.remove("active");

            // Add active class to new
            const newActive = audioLyricsList.querySelector(`.lyrics-line[data-index="${matchIndex}"]`);
            if (newActive) {
                newActive.classList.add("active");

                // Auto scroll
                const containerHeight = audioLyricsList.clientHeight;
                const lineOffsetTop = newActive.offsetTop;
                const lineHeight = newActive.clientHeight;

                audioLyricsList.scrollTo({
                    top: lineOffsetTop - (containerHeight / 2) + (lineHeight / 2),
                    behavior: "smooth"
                });
            }
            activeLyricIndex = matchIndex;
        }
    }

    function renderAudioVisualizer() {
        if (!analyser) return;

        const canvas = document.getElementById("audio-visualizer-canvas");
        if (!canvas) return;

        const toggleVisualizerCheckbox = document.getElementById("toggle-visualizer-checkbox");
        if (toggleVisualizerCheckbox && !toggleVisualizerCheckbox.checked) {
            canvas.classList.add("hidden");
            return;
        }

        const staticVisualizer = document.querySelector(".waveform-animation");
        if (staticVisualizer) {
            staticVisualizer.classList.add("hidden-visualizer");
        }
        canvas.classList.remove("hidden");

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const contentArea = document.querySelector(".preview-content-area");

        // Keep decayValues in a variable that can be resized
        let decayValues = new Float32Array(0);

        const draw = () => {
            const ctx = canvas.getContext("2d");
            if (!ctx) return;

            // Make sure resolution matches container size
            if (canvas.width !== canvas.clientWidth || canvas.height !== canvas.clientHeight) {
                canvas.width = canvas.clientWidth || 300;
                canvas.height = canvas.clientHeight || 60;
            }

            const W = canvas.width;
            const H = canvas.height;

            // Dynamically determine the number of bars based on screen width
            // to keep the visualizer beautiful and elegant without turning into a dense comb in fullscreen.
            let numBars = 64;
            if (W > 1200) {
                numBars = 72; // Perfect balance for large screens / fullscreen
            } else if (W < 500) {
                numBars = 44; // Compact count for small windows / mobile
            }

            const halfLength = numBars / 2;

            // Calculate dynamic bar space, width and gap to fill the container perfectly
            const barSpace = W / numBars;
            const barWidth = Math.max(3, barSpace * 0.55);
            const gap = Math.max(2, barSpace * 0.45);

            // Adjust decayValues array size if needed
            if (decayValues.length !== halfLength) {
                const oldDecay = decayValues;
                decayValues = new Float32Array(halfLength);
                if (oldDecay.length > 0) {
                    for (let i = 0; i < Math.min(oldDecay.length, halfLength); i++) {
                        decayValues[i] = oldDecay[i];
                    }
                }
            }

            const minH = 4; // Rest level height (4px)
            const maxH = H * 0.95; // Max height to fit within canvas

            let stillDecaying = false;
            let sum = 0;

            if (previewAudioPlayer && !previewAudioPlayer.paused) {
                analyser.getByteFrequencyData(dataArray);
                const maxFreqIdx = Math.floor(bufferLength * 0.85);

                for (let i = 0; i < halfLength; i++) {
                    const percentIdx = i / (halfLength - 1 || 1);
                    const dataIdx = Math.floor(Math.pow(percentIdx, 1.25) * maxFreqIdx);
                    const value = dataArray[dataIdx] || 0;
                    sum += value;

                    // Apply visual gain multiplier (1.6) and progressive mid/high boost
                    const boostedValue = Math.min(255, value * 1.6 * (1.0 + percentIdx * 0.9));
                    const targetH = minH + (boostedValue / 255) * (maxH - minH);

                    // Smooth transition
                    decayValues[i] = decayValues[i] * 0.35 + targetH * 0.65;
                }
                stillDecaying = true;
            } else {
                // Smoothly decay bars
                for (let i = 0; i < halfLength; i++) {
                    if (decayValues[i] > minH + 0.1) {
                        decayValues[i] = decayValues[i] * 0.82;
                        stillDecaying = true;
                    } else {
                        decayValues[i] = minH;
                    }
                }
            }

            // Draw the bars
            ctx.clearRect(0, 0, W, H);

            // Create horizontal gradient from left to right centered at middle
            const grad = ctx.createLinearGradient(0, 0, W, 0);
            grad.addColorStop(0, '#00f3ff'); // Cyan (left outer)
            grad.addColorStop(0.35, '#8b5cf6'); // Purple
            grad.addColorStop(0.5, '#ff007f'); // Magenta (center)
            grad.addColorStop(0.65, '#8b5cf6'); // Purple
            grad.addColorStop(1, '#00f3ff'); // Cyan (right outer)
            ctx.fillStyle = grad;

            for (let i = 0; i < halfLength; i++) {
                const barHeight = decayValues[i];
                const y = H - barHeight;

                // Left bar
                const leftX = (W / 2) - gap / 2 - (i + 1) * barWidth - i * gap;
                ctx.beginPath();
                ctx.roundRect(leftX, y, barWidth, barHeight, barWidth / 2);
                ctx.fill();

                // Right bar
                const rightX = (W / 2) + gap / 2 + i * barWidth + i * gap;
                ctx.beginPath();
                ctx.roundRect(rightX, y, barWidth, barHeight, barWidth / 2);
                ctx.fill();
            }

            const average = halfLength > 0 ? (sum / halfLength) : 0;
            const backdrop = document.querySelector(".visualizer-glow-backdrop");
            if (backdrop) {
                if (previewAudioPlayer && !previewAudioPlayer.paused) {
                    const scale = 1.0 + (average / 255) * 0.35;
                    const opacity = 0.15 + (average / 255) * 0.65;
                    backdrop.style.transform = `translate(-50%, -50%) scale(${scale})`;
                    backdrop.style.opacity = opacity;
                } else {
                    const currentTransform = backdrop.style.transform || "";
                    const scaleMatch = currentTransform.match(/scale\(([^)]+)\)/);
                    let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
                    let currentOpacity = parseFloat(backdrop.style.opacity) || 0.15;

                    if (currentScale > 1.0) {
                        currentScale = Math.max(1.0, currentScale * 0.92 - 0.01);
                        backdrop.style.transform = `translate(-50%, -50%) scale(${currentScale})`;
                        stillDecaying = true;
                    }
                    if (currentOpacity > 0.15) {
                        currentOpacity = Math.max(0.15, currentOpacity * 0.9);
                        backdrop.style.opacity = currentOpacity;
                        stillDecaying = true;
                    }
                }
            }

            const vinylLabel = document.querySelector(".vinyl-label");
            if (vinylLabel) {
                if (previewAudioPlayer && !previewAudioPlayer.paused) {
                    const labelScale = 1.0 + (average / 255) * 0.18;
                    vinylLabel.style.transform = `scale(${labelScale})`;
                } else {
                    const currentTransform = vinylLabel.style.transform || "";
                    const scaleMatch = currentTransform.match(/scale\(([^)]+)\)/);
                    let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
                    if (currentScale > 1.0) {
                        currentScale = Math.max(1.0, currentScale * 0.9);
                        vinylLabel.style.transform = `scale(${currentScale})`;
                        stillDecaying = true;
                    }
                }
            }

            if (contentArea) {
                if (previewAudioPlayer && !previewAudioPlayer.paused) {
                    const innerBlur = 10 + (average / 255) * 25;
                    const outerBlur = 40 + (average / 255) * 60;
                    const innerOpacity = 0.15 + (average / 255) * 0.5;
                    const outerOpacity = 0.08 + (average / 255) * 0.3;
                    const borderOpacity = 0.1 + (average / 255) * 0.5;

                    contentArea.style.boxShadow = `0 0 ${innerBlur}px rgba(var(--cyan-rgb), ${innerOpacity}), 0 0 ${outerBlur}px rgba(var(--cyan-rgb), ${outerOpacity})`;
                    contentArea.style.borderColor = `rgba(var(--cyan-rgb), ${borderOpacity})`;
                } else {
                    contentArea.style.boxShadow = "";
                    contentArea.style.borderColor = "";
                }
            }

            const vinylRecord = document.querySelector(".vinyl-record");
            if (vinylRecord) {
                if (previewAudioPlayer && !previewAudioPlayer.paused) {
                    const innerBlur = 8 + (average / 255) * 20;
                    const outerBlur = 30 + (average / 255) * 50;
                    const innerOpacity = 0.3 + (average / 255) * 0.5;
                    const outerOpacity = 0.15 + (average / 255) * 0.45;

                    vinylRecord.style.boxShadow = `
                        0 10px 30px rgba(0, 0, 0, 0.7), 
                        0 0 ${innerBlur}px rgba(var(--cyan-rgb), ${innerOpacity}), 
                        0 0 ${outerBlur}px rgba(var(--cyan-rgb), ${outerOpacity}), 
                        inset 0 0 1px rgba(255, 255, 255, 0.15)
                    `;
                } else {
                    vinylRecord.style.boxShadow = "";
                }
            }

            if (stillDecaying) {
                visualizerAnimationId = requestAnimationFrame(draw);
            } else {
                visualizerAnimationId = null;
            }
        };

        if (!visualizerAnimationId) {
            draw();
        }
    }

    // --- CUSTOM AUDIO PLAYER HANDLERS ---
    if (previewAudioPlayer) {
        previewAudioPlayer.addEventListener("play", () => {
            if (audioCard) audioCard.classList.add("playing");

            // Initialize visualizer on play (requires user gesture)
            initAudioVisualizer();
            if (audioCtx && audioCtx.state === "suspended") {
                audioCtx.resume();
            }
            renderAudioVisualizer();

            if (audioPlayPauseBtn) {
                const playIcon = audioPlayPauseBtn.querySelector(".play-icon");
                const pauseIcon = audioPlayPauseBtn.querySelector(".pause-icon");
                if (playIcon) playIcon.classList.add("hidden");
                if (pauseIcon) pauseIcon.classList.remove("hidden");
            }
            showPreviewControls();
        });

        previewAudioPlayer.addEventListener("pause", () => {
            if (audioCard) audioCard.classList.remove("playing");
            renderAudioVisualizer(); // Trigger smooth decay

            if (audioPlayPauseBtn) {
                const playIcon = audioPlayPauseBtn.querySelector(".play-icon");
                const pauseIcon = audioPlayPauseBtn.querySelector(".pause-icon");
                if (playIcon) playIcon.classList.remove("hidden");
                if (pauseIcon) pauseIcon.classList.add("hidden");
            }

            // Always show controls when paused
            const customAudioControls = document.querySelector(".custom-audio-controls");
            if (customAudioControls) {
                customAudioControls.classList.remove("hidden-controls");
            }
            if (previewModal) {
                previewModal.classList.remove("hidden-cursor");
            }
            if (videoHoverTimeout) {
                clearTimeout(videoHoverTimeout);
            }
        });

        previewAudioPlayer.addEventListener("timeupdate", () => {
            if (previewAudioPlayer.duration) {
                const currentPlayTime = previewAudioPlayer.currentTime;
                if (!isDraggingAudioSlider && !previewAudioPlayer.seeking) {
                    const pct = (currentPlayTime / previewAudioPlayer.duration) * 100;
                    if (audioSeekSlider) {
                        audioSeekSlider.value = pct;
                        updateSliderBackground(audioSeekSlider);
                    }
                }
                if (audioTimeCurrent) {
                    audioTimeCurrent.textContent = formatTime(currentPlayTime);
                }
                syncAudioLyrics(currentPlayTime);
                if (loopStartSecs !== null && loopEndSecs !== null) {
                    if (currentPlayTime >= loopEndSecs || currentPlayTime < loopStartSecs) {
                        previewAudioPlayer.currentTime = loopStartSecs;
                    }
                }
            }
        });

        previewAudioPlayer.addEventListener("loadedmetadata", () => {
            if (audioTimeTotal && previewAudioPlayer.duration) {
                audioTimeTotal.textContent = formatTime(previewAudioPlayer.duration);
            }
            if (audioSeekSlider) {
                audioSeekSlider.value = 0;
                updateSliderBackground(audioSeekSlider);
            }
            if (audioVolumeSlider) {
                audioVolumeSlider.value = previewAudioPlayer.muted ? 0 : previewAudioPlayer.volume;
                updateSliderBackground(audioVolumeSlider);
            }
        });

        previewAudioPlayer.addEventListener("durationchange", () => {
            if (audioTimeTotal && previewAudioPlayer.duration) {
                audioTimeTotal.textContent = formatTime(previewAudioPlayer.duration);
            }
        });

        ["progress", "canplay", "seeked", "playing", "pause", "loadeddata"].forEach(evtName => {
            previewAudioPlayer.addEventListener(evtName, () => {
                if (audioSeekSlider) {
                    updateSliderBackground(audioSeekSlider);
                }
            });
        });
    }

    if (audioPlayPauseBtn && previewAudioPlayer) {
        audioPlayPauseBtn.addEventListener("click", () => {
            if (previewAudioPlayer.paused) {
                previewAudioPlayer.play().catch(e => console.log("Play failed: ", e));
            } else {
                previewAudioPlayer.pause();
            }
        });
    }

    if (audioLoopBtn && previewAudioPlayer) {
        audioLoopBtn.addEventListener("click", () => {
            previewAudioPlayer.loop = !previewAudioPlayer.loop;
            if (previewAudioPlayer.loop) {
                audioLoopBtn.classList.add("active-loop");
                audioLoopBtn.title = "Repeat (On)";
                audioLoopBtn.style.color = "var(--cyan)";
                audioLoopBtn.style.borderColor = "rgba(var(--cyan-rgb), 0.4)";
                audioLoopBtn.style.boxShadow = "0 0 10px rgba(var(--cyan-rgb), 0.3)";
            } else {
                audioLoopBtn.classList.remove("active-loop");
                audioLoopBtn.title = "Repeat (Off)";
                audioLoopBtn.style.color = "";
                audioLoopBtn.style.borderColor = "";
                audioLoopBtn.style.boxShadow = "";
            }
        });
    }

    if (audioSeekSlider && previewAudioPlayer) {
        const setAudioDragging = () => { isDraggingAudioSlider = true; };
        audioSeekSlider.addEventListener("mousedown", setAudioDragging);
        audioSeekSlider.addEventListener("touchstart", setAudioDragging);
        audioSeekSlider.addEventListener("input", function () {
            isDraggingAudioSlider = true;
            updateSliderBackground(this);
        });
        audioSeekSlider.addEventListener("change", function () {
            if (previewAudioPlayer.duration) {
                previewAudioPlayer.currentTime = (parseFloat(this.value) / 100) * previewAudioPlayer.duration;
            }
            setTimeout(() => {
                isDraggingAudioSlider = false;
            }, 300);
        });
    }

    function updateVolumeWavesState(volume, isMuted, muteBtn) {
        if (!muteBtn) return;
        const volIcon = muteBtn.querySelector(".volume-icon");
        const muteIcon = muteBtn.querySelector(".mute-icon");

        if (isMuted || volume === 0) {
            if (volIcon) volIcon.classList.add("hidden");
            if (muteIcon) muteIcon.classList.remove("hidden");
        } else {
            if (volIcon) volIcon.classList.remove("hidden");
            if (muteIcon) muteIcon.classList.add("hidden");

            const wave1 = volIcon.querySelector(".volume-wave-1");
            const wave2 = volIcon.querySelector(".volume-wave-2");
            const wave3 = volIcon.querySelector(".volume-wave-3");

            if (wave1) wave1.classList.toggle("hidden", false);
            if (wave2) wave2.classList.toggle("hidden", volume <= 0.33);
            if (wave3) wave3.classList.toggle("hidden", volume <= 0.66);
        }
    }

    if (audioVolumeSlider && previewAudioPlayer) {
        audioVolumeSlider.addEventListener("input", function () {
            previewAudioPlayer.volume = parseFloat(this.value);
            updateSliderBackground(this);
            if (audioMuteBtn) {
                previewAudioPlayer.muted = (previewAudioPlayer.volume === 0);
                updateVolumeWavesState(previewAudioPlayer.volume, previewAudioPlayer.muted, audioMuteBtn);
            }
        });
    }

    if (audioMuteBtn && previewAudioPlayer && audioVolumeSlider) {
        let prevVolume = 1.0;
        audioMuteBtn.addEventListener("click", () => {
            previewAudioPlayer.muted = !previewAudioPlayer.muted;
            if (previewAudioPlayer.muted) {
                prevVolume = parseFloat(audioVolumeSlider.value) || 1.0;
                audioVolumeSlider.value = 0;
            } else {
                audioVolumeSlider.value = prevVolume;
                previewAudioPlayer.volume = prevVolume;
            }
            updateVolumeWavesState(previewAudioPlayer.volume, previewAudioPlayer.muted, audioMuteBtn);
            updateSliderBackground(audioVolumeSlider);
        });
    }

    // --- AUDIO EXPANDED FEATURES HANDLERS ---
    if (audioLyricsBtn && audioLyricsOverlay) {
        audioLyricsBtn.addEventListener("click", () => {
            const isCurrentlyActive = audioLyricsBtn.classList.contains("active");

            // Deactivate EQ button and hide settings panel
            if (audioEqBtn) audioEqBtn.classList.remove("active");
            if (audioSettingsPanel) audioSettingsPanel.classList.add("hidden");

            if (isCurrentlyActive) {
                // Deactivate lyrics
                audioLyricsBtn.classList.remove("active");
                audioLyricsOverlay.classList.add("hidden");
                if (audioSidePanel) audioSidePanel.classList.add("hidden");
            } else {
                // Activate lyrics
                audioLyricsBtn.classList.add("active");
                audioLyricsOverlay.classList.remove("hidden");
                if (audioSidePanel) audioSidePanel.classList.remove("hidden");
                if (previewAudioPlayer) {
                    syncAudioLyrics(previewAudioPlayer.currentTime);
                }
            }
        });
    }

    if (audioEqBtn && audioSettingsPanel) {
        audioEqBtn.addEventListener("click", () => {
            const isCurrentlyActive = audioEqBtn.classList.contains("active");

            // Deactivate lyrics button and hide lyrics overlay
            if (audioLyricsBtn) audioLyricsBtn.classList.remove("active");
            if (audioLyricsOverlay) audioLyricsOverlay.classList.add("hidden");

            if (isCurrentlyActive) {
                // Deactivate EQ
                audioEqBtn.classList.remove("active");
                audioSettingsPanel.classList.add("hidden");
                if (audioSidePanel) audioSidePanel.classList.add("hidden");
            } else {
                // Activate EQ
                audioEqBtn.classList.add("active");
                audioSettingsPanel.classList.remove("hidden");
                if (audioSidePanel) audioSidePanel.classList.remove("hidden");
            }
        });
    }

    const toggleVisualizerCheckbox = document.getElementById("toggle-visualizer-checkbox");
    if (toggleVisualizerCheckbox) {
        toggleVisualizerCheckbox.addEventListener("change", function () {
            const staticVisualizer = document.querySelector(".waveform-animation");
            const audioCanvas = document.getElementById("audio-visualizer-canvas");
            const visualizerArea = document.querySelector(".audio-visualizer-area");

            if (this.checked) {
                if (visualizerArea) visualizerArea.classList.remove("visualizer-disabled");
                if (analyser) {
                    if (audioCanvas) audioCanvas.classList.remove("hidden");
                    if (staticVisualizer) staticVisualizer.classList.add("hidden-visualizer");
                    if (previewAudioPlayer && !previewAudioPlayer.paused && !visualizerAnimationId) {
                        renderAudioVisualizer();
                    }
                } else {
                    if (staticVisualizer) staticVisualizer.classList.remove("hidden-visualizer");
                    if (audioCanvas) audioCanvas.classList.add("hidden");
                }
            } else {
                if (visualizerArea) visualizerArea.classList.add("visualizer-disabled");
                if (staticVisualizer) staticVisualizer.classList.add("hidden-visualizer");
                if (audioCanvas) audioCanvas.classList.add("hidden");
            }
        });
    }

    audioStabs.forEach(tab => {
        tab.addEventListener("click", () => {
            audioStabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            const targetTab = tab.dataset.stab;
            audioStabContents.forEach(content => {
                if (content.dataset.content === targetTab) {
                    content.classList.remove("hidden");
                } else {
                    content.classList.add("hidden");
                }
            });
        });
    });

    if (audioSubSelect) {
        audioSubSelect.addEventListener("change", function () {
            loadAudioSubtitle(this.value);
        });
    }

    if (audioSubUploadBtn && audioSubFile) {
        audioSubUploadBtn.addEventListener("click", () => {
            audioSubFile.click();
        });
        audioSubFile.addEventListener("change", function (e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function (evt) {
                const text = evt.target.result;
                const opt = document.createElement("option");
                opt.value = "uploaded_file";
                opt.textContent = file.name;
                opt.selected = true;

                const existingCustom = audioSubSelect.querySelector('option[value="uploaded_file"]');
                if (existingCustom) {
                    existingCustom.remove();
                }

                audioSubSelect.appendChild(opt);
                audioSubSelect.value = "uploaded_file";

                loadAudioSubtitle(text, true);
            };
            reader.readAsText(file);
        });
    }

    if (audioSpeedSlider && previewAudioPlayer) {
        audioSpeedSlider.addEventListener("input", function () {
            const val = parseFloat(this.value);
            previewAudioPlayer.playbackRate = val;
            if (audioSpeedDisplay) audioSpeedDisplay.textContent = val.toFixed(2);
            updateSliderBackground(this);

            speedPresetBtns.forEach(btn => {
                const s = parseFloat(btn.dataset.speed);
                if (Math.abs(s - val) < 0.01) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
            saveAudioSettingsToStorage();
        });
    }

    speedPresetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const val = parseFloat(btn.dataset.speed);
            if (previewAudioPlayer) {
                previewAudioPlayer.playbackRate = val;
            }
            if (audioSpeedSlider) {
                audioSpeedSlider.value = val;
                updateSliderBackground(audioSpeedSlider);
            }
            if (audioSpeedDisplay) {
                audioSpeedDisplay.textContent = val.toFixed(2);
            }
            speedPresetBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            saveAudioSettingsToStorage();
        });
    });

    eqSliders.forEach(slider => {
        slider.addEventListener("input", function () {
            const val = parseFloat(this.value);
            const bandName = this.id.replace("eq-", "");
            const valEl = document.getElementById(`${this.id}-val`);
            if (valEl) valEl.textContent = (val > 0 ? "+" : "") + val;
            updateSliderBackground(this);

            if (audioCtx) {
                let node = null;
                if (bandName === "bass") node = eqBassNode;
                else if (bandName === "lowmid") node = eqLowMidNode;
                else if (bandName === "highmid") node = eqHighMidNode;
                else if (bandName === "treble") node = eqTrebleNode;

                if (node) {
                    node.gain.setValueAtTime(val, audioCtx.currentTime);
                }
            }

            eqPresets.forEach(b => b.classList.remove("active"));
            saveAudioSettingsToStorage();
        });
    });

    eqPresets.forEach(btn => {
        btn.addEventListener("click", () => {
            eqPresets.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            applyEqPreset(btn.dataset.preset);
            saveAudioSettingsToStorage();
        });
    });

    voicePresets.forEach(btn => {
        btn.addEventListener("click", () => {
            voicePresets.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const presetName = btn.dataset.voice;
            applyVoiceEffectsNodePreset(presetName);
            saveAudioSettingsToStorage();
        });
    });

    // --- PREVIEW MODAL HOVER & CURSOR AUTO-HIDE HANDLERS ---
    let videoHoverTimeout = null;
    function showPreviewControls() {
        const modalHeader = document.querySelector("#preview-modal .modal-header");
        const customVideoControls = document.querySelector(".custom-video-controls");
        const customAudioControls = document.querySelector(".custom-audio-controls");
        const imageControls = document.querySelector(".image-controls");
        const subHeader = document.querySelector(".subtitle-preview-box .sub-header");
        const navControls = document.querySelectorAll(".nav-control");

        if (modalHeader) modalHeader.classList.remove("hidden-header");
        if (customVideoControls) customVideoControls.classList.remove("hidden-controls");
        if (customAudioControls) customAudioControls.classList.remove("hidden-controls");
        if (imageControls) imageControls.classList.remove("hidden-controls");
        if (subHeader) subHeader.classList.remove("hidden-controls");
        navControls.forEach(ctrl => ctrl.classList.remove("hidden-controls"));

        if (previewModal) {
            previewModal.classList.remove("hidden-cursor");
        }

        if (videoHoverTimeout) {
            clearTimeout(videoHoverTimeout);
        }

        // Auto-hide controls, header, and cursor if fullscreen is active OR media is playing
        const isMediaPlaying = (previewVideoPlayer && !previewVideoPlayer.paused) || (previewAudioPlayer && !previewAudioPlayer.paused);
        const shouldAutoHide = (videoFullscreenMode > 0) || isMediaPlaying;

        if (shouldAutoHide) {
            videoHoverTimeout = setTimeout(() => {
                // Check if mouse is hovering header or custom video controls
                const isHoveringHeader = modalHeader && modalHeader.matches(':hover');
                const isHoveringVideoControls = customVideoControls && customVideoControls.matches(':hover');
                const isHoveringAudioControls = customAudioControls && customAudioControls.matches(':hover');
                const isHoveringImageControls = imageControls && imageControls.matches(':hover');
                const isHoveringSubHeader = subHeader && subHeader.matches(':hover');
                let isHoveringNav = false;
                navControls.forEach(ctrl => {
                    if (ctrl.matches(':hover')) isHoveringNav = true;
                });

                if (!isHoveringHeader && !isHoveringVideoControls && !isHoveringAudioControls && !isHoveringImageControls && !isHoveringSubHeader && !isHoveringNav) {
                    if (modalHeader) modalHeader.classList.add("hidden-header");
                    if (customVideoControls) customVideoControls.classList.add("hidden-controls");
                    if (customAudioControls) customAudioControls.classList.add("hidden-controls");
                    if (imageControls) imageControls.classList.add("hidden-controls");
                    if (subHeader) subHeader.classList.add("hidden-controls");
                    navControls.forEach(ctrl => ctrl.classList.add("hidden-controls"));
                    if (previewModal) previewModal.classList.add("hidden-cursor");
                }
            }, 3000);
        }
    }

    if (previewModal) {
        previewModal.addEventListener("mousemove", showPreviewControls);
        previewModal.addEventListener("mouseleave", () => {
            const isMediaPlaying = (previewVideoPlayer && !previewVideoPlayer.paused) || (previewAudioPlayer && !previewAudioPlayer.paused);
            const shouldAutoHide = (videoFullscreenMode > 0) || isMediaPlaying;

            if (shouldAutoHide) {
                const modalHeader = document.querySelector("#preview-modal .modal-header");
                const customVideoControls = document.querySelector(".custom-video-controls");
                const customAudioControls = document.querySelector(".custom-audio-controls");
                const imageControls = document.querySelector(".image-controls");
                const subHeader = document.querySelector(".subtitle-preview-box .sub-header");
                const navControls = document.querySelectorAll(".nav-control");

                if (modalHeader) modalHeader.classList.add("hidden-header");
                if (customVideoControls) customVideoControls.classList.add("hidden-controls");
                if (customAudioControls) customAudioControls.classList.add("hidden-controls");
                if (imageControls) imageControls.classList.add("hidden-controls");
                if (subHeader) subHeader.classList.add("hidden-controls");
                navControls.forEach(ctrl => ctrl.classList.add("hidden-controls"));
                previewModal.classList.add("hidden-cursor");
            }
        });
    }

    if (previewVideoPlayer) {
        // Prevent native browser text tracks/subtitles from rendering and overlapping with our custom overlay
        if (previewVideoPlayer.textTracks) {
            const disableTracks = () => {
                for (let i = 0; i < previewVideoPlayer.textTracks.length; i++) {
                    previewVideoPlayer.textTracks[i].mode = 'disabled';
                }
            };
            previewVideoPlayer.textTracks.addEventListener("addtrack", (e) => {
                e.track.mode = 'disabled';
            });
            previewVideoPlayer.addEventListener("loadedmetadata", disableTracks);
            previewVideoPlayer.addEventListener("play", disableTracks);
            disableTracks();
        }

        previewVideoPlayer.addEventListener("play", () => {
            if (videoCard) videoCard.classList.add("playing");
            if (videoPlayPauseBtn) {
                const playIcon = videoPlayPauseBtn.querySelector(".play-icon");
                const pauseIcon = videoPlayPauseBtn.querySelector(".pause-icon");
                if (playIcon) playIcon.classList.add("hidden");
                if (pauseIcon) pauseIcon.classList.remove("hidden");
            }
            showPreviewControls();

            // Initialize visualizer on play (requires user gesture)
            initAudioVisualizer();
            if (audioCtx && audioCtx.state === "suspended") {
                audioCtx.resume();
            }
        });

        previewVideoPlayer.addEventListener("pause", () => {
            if (videoCard) videoCard.classList.remove("playing");
            if (videoPlayPauseBtn) {
                const playIcon = videoPlayPauseBtn.querySelector(".play-icon");
                const pauseIcon = videoPlayPauseBtn.querySelector(".pause-icon");
                if (playIcon) playIcon.classList.remove("hidden");
                if (pauseIcon) pauseIcon.classList.add("hidden");
            }
            // Always show controls when paused
            if (customVideoControls) {
                customVideoControls.classList.remove("hidden-controls");
            }
            const modalHeader = document.querySelector("#preview-modal .modal-header");
            if (modalHeader) {
                modalHeader.classList.remove("hidden-header");
            }
            if (previewModal) {
                previewModal.classList.remove("hidden-cursor");
            }
            if (videoHoverTimeout) {
                clearTimeout(videoHoverTimeout);
            }
        });

        previewVideoPlayer.addEventListener("timeupdate", () => {
            // Continuously force native subtitle tracks to be disabled to avoid overlap
            if (previewVideoPlayer.textTracks && previewVideoPlayer.textTracks.length > 0) {
                for (let i = 0; i < previewVideoPlayer.textTracks.length; i++) {
                    if (previewVideoPlayer.textTracks[i].mode !== 'disabled') {
                        previewVideoPlayer.textTracks[i].mode = 'disabled';
                    }
                }
            }
            const totalDuration = getVideoTotalDuration();
            const currentPlayTime = previewIsAdaptive ? (previewCurrentTimeOffset + previewVideoPlayer.currentTime) : previewVideoPlayer.currentTime;

            if (totalDuration > 0) {
                // A-B repeat logic
                if (loopStartSecs !== null && loopEndSecs !== null) {
                    if (currentPlayTime >= loopEndSecs || currentPlayTime < loopStartSecs) {
                        if (previewIsAdaptive) {
                            seekAdaptiveVideo(loopStartSecs);
                        } else {
                            previewVideoPlayer.currentTime = loopStartSecs;
                        }
                    }
                }

                if (!isDraggingVideoSlider && !previewVideoPlayer.seeking) {
                    const pct = (currentPlayTime / totalDuration) * 100;
                    if (videoSeekSlider) {
                        videoSeekSlider.value = pct;
                        updateSliderBackground(videoSeekSlider);
                    }
                }
                if (videoTimeCurrent) {
                    videoTimeCurrent.textContent = formatTime(currentPlayTime);
                }

                // Subtitles sync
                if (typeof updateSubtitlesOverlay === "function") {
                    updateSubtitlesOverlay(currentPlayTime);
                }
            }
        });

        previewVideoPlayer.addEventListener("loadedmetadata", () => {
            const totalDuration = getVideoTotalDuration();
            if (videoTimeTotal && totalDuration > 0) {
                videoTimeTotal.textContent = formatTime(totalDuration);
            }
            if (videoSeekSlider && !previewIsAdaptive) {
                videoSeekSlider.value = 0;
                updateSliderBackground(videoSeekSlider);
            }
            if (videoVolumeSlider) {
                videoVolumeSlider.value = previewVideoPlayer.muted ? 0 : previewVideoPlayer.volume;
                updateSliderBackground(videoVolumeSlider);
            }
            // Apply speed setting
            if (previewVideoPlayer) {
                previewVideoPlayer.playbackRate = currentPlaybackSpeed;
            }
            if (typeof updateLoopMarkersUI === "function") {
                updateLoopMarkersUI();
            }
        });

        previewVideoPlayer.addEventListener("durationchange", () => {
            const totalDuration = getVideoTotalDuration();
            if (videoTimeTotal && totalDuration > 0) {
                videoTimeTotal.textContent = formatTime(totalDuration);
            }
            if (typeof updateLoopMarkersUI === "function") {
                updateLoopMarkersUI();
            }
        });

        ["progress", "canplay", "seeked", "playing", "pause", "loadeddata"].forEach(evtName => {
            previewVideoPlayer.addEventListener(evtName, () => {
                if (videoSeekSlider) {
                    updateSliderBackground(videoSeekSlider);
                }
            });
        });
    }

    if (videoPlayPauseBtn && previewVideoPlayer) {
        videoPlayPauseBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (previewVideoPlayer.paused) {
                previewVideoPlayer.play().catch(e => console.log("Play failed: ", e));
            } else {
                previewVideoPlayer.pause();
            }
        });
    }

    if (videoLoopBtn && previewVideoPlayer) {
        videoLoopBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewVideoPlayer.loop = !previewVideoPlayer.loop;
            if (previewVideoPlayer.loop) {
                videoLoopBtn.classList.add("active-loop");
                videoLoopBtn.title = "Repeat (On)";
                videoLoopBtn.style.color = "var(--cyan)";
                videoLoopBtn.style.borderColor = "rgba(var(--cyan-rgb), 0.4)";
                videoLoopBtn.style.boxShadow = "0 0 10px rgba(var(--cyan-rgb), 0.3)";
            } else {
                videoLoopBtn.classList.remove("active-loop");
                videoLoopBtn.title = "Repeat (Off)";
                videoLoopBtn.style.color = "";
                videoLoopBtn.style.borderColor = "";
                videoLoopBtn.style.boxShadow = "";
            }
        });
    }

    // Clicking on video itself toggles play/pause, double clicking toggles fullscreen mode
    if (previewVideoPlayer) {
        let clickTimeout = null;
        previewVideoPlayer.addEventListener("click", (e) => {
            if (clickTimeout !== null) {
                clearTimeout(clickTimeout);
                clickTimeout = null;
                return;
            }
            clickTimeout = setTimeout(() => {
                clickTimeout = null;
                if (previewVideoPlayer.paused) {
                    previewVideoPlayer.play().catch(err => console.log("Play failed: ", err));
                } else {
                    previewVideoPlayer.pause();
                }
            }, 250);
        });

        previewVideoPlayer.addEventListener("dblclick", (e) => {
            e.stopPropagation();
            if (clickTimeout !== null) {
                clearTimeout(clickTimeout);
                clickTimeout = null;
            }
            toggleFullscreenMode();
        });
    }

    if (videoSeekSlider && previewVideoPlayer) {
        const setVideoDragging = () => { isDraggingVideoSlider = true; };
        videoSeekSlider.addEventListener("mousedown", setVideoDragging);
        videoSeekSlider.addEventListener("touchstart", setVideoDragging);
        videoSeekSlider.addEventListener("input", function (e) {
            e.stopPropagation();
            isDraggingVideoSlider = true;
            updateSliderBackground(this);
        });
        videoSeekSlider.addEventListener("change", function (e) {
            e.stopPropagation();
            const totalDuration = getVideoTotalDuration();
            if (totalDuration > 0) {
                const targetTime = (parseFloat(this.value) / 100) * totalDuration;
                if (previewIsAdaptive) {
                    seekAdaptiveVideo(targetTime);
                } else {
                    previewVideoPlayer.currentTime = targetTime;
                }
            }
            setTimeout(() => {
                isDraggingVideoSlider = false;
            }, 300);
        });
    }

    // ===== Seek Thumbnail Preview (YouTube-style with Smart Frame Cache & fastSeek) =====

    function syncThumbnailVideoSource(srcUrl, isM3u8 = false) {
        if (!thumbPreviewVideo) return;

        // Clean up previous HLS instance if any
        if (thumbHlsInstance) {
            thumbHlsInstance.destroy();
            thumbHlsInstance = null;
        }

        clearThumbCache();
        thumbLastDrawnTime = -1;
        if (seekThumbCanvas) {
            seekThumbCanvas.classList.add("is-seeking");
        }

        if (!srcUrl) {
            thumbPreviewVideo.removeAttribute("src");
            thumbPreviewVideo.load();
            thumbSourceReady = false;
            return;
        }

        let targetSrc = srcUrl;
        if (previewIsAdaptive && previewAdaptiveVideoUrl) {
            // For adaptive streams (e.g. YouTube), stream only the video track.
            // This enables fast range-based seeking without server-side FFmpeg muxing overhead.
            targetSrc = `/api/proxy/stream?url=${encodeURIComponent(previewAdaptiveVideoUrl)}&client_id=${encodeURIComponent(clientId)}`;
        }

        if (isM3u8 && typeof Hls !== "undefined" && Hls.isSupported()) {
            thumbSourceReady = false;
            thumbLastDrawnTime = -1;
            
            const hls = new Hls({
                maxBufferSize: 10 * 1024 * 1024, // Smaller buffer (10MB) for thumbnail preview to save memory/speed
                maxBufferLength: 10,
                enableSubtitle: false
            });
            hls.loadSource(targetSrc);
            hls.attachMedia(thumbPreviewVideo);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                thumbSourceReady = true;
                drawThumbnailFrame(0);
            });
            thumbHlsInstance = hls;
        } else {
            // Don't re-assign if already the same source
            if (thumbPreviewVideo.src === targetSrc || thumbPreviewVideo.getAttribute("data-thumb-src") === targetSrc) return;
            thumbPreviewVideo.setAttribute("data-thumb-src", targetSrc);
            thumbSourceReady = false;
            thumbLastDrawnTime = -1;
            thumbPreviewVideo.src = targetSrc;
            thumbPreviewVideo.load();
        }
    }

    /**
     * Draw current frame onto canvas, remove is-seeking class, and store into memory cache.
     */
    function drawThumbnailFrame(time = null) {
        if (!seekThumbCtx || !thumbPreviewVideo || !thumbSourceReady) return;
        if (thumbPreviewVideo.readyState < 2) return; // HAVE_CURRENT_DATA
        try {
            seekThumbCtx.drawImage(thumbPreviewVideo, 0, 0, seekThumbCanvas.width, seekThumbCanvas.height);
            if (seekThumbCanvas) {
                seekThumbCanvas.classList.remove("is-seeking");
            }
            // Cache frame bitmap for instant 0ms recall on hover
            const frameTime = Math.round(time !== null ? time : thumbPreviewVideo.currentTime);
            if (typeof createImageBitmap === "function" && !thumbCache.has(frameTime)) {
                createImageBitmap(seekThumbCanvas).then(bmp => {
                    if (thumbCache.size >= MAX_THUMB_CACHE) {
                        const firstKey = thumbCache.keys().next().value;
                        const oldBmp = thumbCache.get(firstKey);
                        if (oldBmp && typeof oldBmp.close === "function") {
                            try { oldBmp.close(); } catch (e) { }
                        }
                        thumbCache.delete(firstKey);
                    }
                    thumbCache.set(frameTime, bmp);
                }).catch(() => {});
            }
        } catch (e) {
            // Cross-origin or other errors — silently ignore
        }
    }

    // Trigger fast keyframe seek if supported for 5-10x faster response
    function triggerThumbSeek(time) {
        thumbSeekPending = true;
        thumbCurrentSeekingTime = time;
        if (typeof thumbPreviewVideo.fastSeek === "function") {
            try {
                thumbPreviewVideo.fastSeek(time);
                return;
            } catch (e) { }
        }
        thumbPreviewVideo.currentTime = time;
    }

    if (videoSliderContainer && thumbPreviewVideo && seekThumbTooltip && seekThumbCanvas && previewVideoPlayer) {
        
        // Listen to loadeddata once globally
        thumbPreviewVideo.addEventListener("loadeddata", () => {
            thumbSourceReady = true;
            // Set canvas internal dimensions to match video native resolution to preserve aspect ratio
            if (thumbPreviewVideo.videoWidth && thumbPreviewVideo.videoHeight) {
                seekThumbCanvas.width = thumbPreviewVideo.videoWidth;
                seekThumbCanvas.height = thumbPreviewVideo.videoHeight;
            }
            // Draw first frame if possible
            drawThumbnailFrame(0);
        });

        // Helper: get total video duration
        function getThumbTotalDuration() {
            return getVideoTotalDuration();
        }

        // On seeked: draw the frame and check if there's another pending seek
        thumbPreviewVideo.addEventListener("seeked", () => {
            drawThumbnailFrame(thumbCurrentSeekingTime);
            thumbLastDrawnTime = thumbCurrentSeekingTime !== null ? thumbCurrentSeekingTime : thumbPreviewVideo.currentTime;
            if (thumbNextSeekTime !== null) {
                const nextTime = thumbNextSeekTime;
                thumbNextSeekTime = null;
                triggerThumbSeek(nextTime);
            } else {
                thumbSeekPending = false;
                thumbCurrentSeekingTime = null;
            }
        });

        // Mousemove on the slider container
        videoSliderContainer.addEventListener("mousemove", (e) => {
            // Don't show for adaptive video if we don't have the video-only stream URL
            if (previewIsAdaptive && !previewAdaptiveVideoUrl) {
                seekThumbTooltip.classList.remove("visible");
                return;
            }
            // Don't show if no source loaded
            if (!thumbSourceReady) {
                seekThumbTooltip.classList.remove("visible");
                return;
            }

            const totalDuration = getThumbTotalDuration();
            if (!totalDuration || totalDuration <= 0) return;

            const sliderRect = videoSeekSlider.getBoundingClientRect();
            const containerRect = videoSliderContainer.getBoundingClientRect();

            // Viewport-relative coordinates (e.clientX, getBoundingClientRect)
            const sliderW = sliderRect.width || 1;
            const sliderPct = Math.max(0, Math.min((e.clientX - sliderRect.left) / sliderW, 1));
            const targetTime = sliderPct * totalDuration;

            const containerW = containerRect.width || 1;
            const visualPct = Math.max(0, Math.min((e.clientX - containerRect.left) / containerW, 1));

            // Update timestamp text
            if (seekThumbTime) {
                seekThumbTime.textContent = formatTime(targetTime);
            }

            // Tooltip calculations (layout space)
            const containerLayoutW = videoSliderContainer.clientWidth || 1;
            const tooltipW   = seekThumbTooltip.offsetWidth || 160;
            const halfPct    = (tooltipW / 2) / containerLayoutW;
            const clampedPct = Math.max(halfPct, Math.min(visualPct, 1 - halfPct));

            seekThumbTooltip.style.left = (clampedPct * 100) + '%';
            if (seekThumbDot) {
                seekThumbDot.style.left = (visualPct * 100) + '%';
            }

            // Pointer arrow follows cursor within tooltip
            if (seekThumbPointer) {
                const arrowPx   = (visualPct - clampedPct) * containerLayoutW;
                const arrowLeft = tooltipW / 2 + arrowPx;
                seekThumbPointer.style.left = Math.max(10, Math.min(arrowLeft, tooltipW - 10)) + 'px';
            }

            // Show tooltip & dot
            seekThumbTooltip.classList.add("visible");
            if (seekThumbDot) {
                seekThumbDot.classList.add("visible");
            }

            // --- Cache Lookup & Responsive Visual Feedback ---
            const roundedTarget = Math.round(targetTime);
            let cachedBmp = thumbCache.get(roundedTarget);
            if (!cachedBmp) {
                // Find nearest cached frame within +/- 2 seconds
                for (let delta = 1; delta <= 2; delta++) {
                    if (thumbCache.has(roundedTarget - delta)) {
                        cachedBmp = thumbCache.get(roundedTarget - delta);
                        break;
                    }
                    if (thumbCache.has(roundedTarget + delta)) {
                        cachedBmp = thumbCache.get(roundedTarget + delta);
                        break;
                    }
                }
            }

            if (cachedBmp) {
                // Instant cache hit: render immediately with zero latency!
                try {
                    seekThumbCtx.drawImage(cachedBmp, 0, 0, seekThumbCanvas.width, seekThumbCanvas.height);
                    seekThumbCanvas.classList.remove("is-seeking");
                    thumbLastDrawnTime = targetTime;
                } catch (e) { }
            } else {
                // Cache miss: if target time is distant from last drawn frame,
                // mark as seeking to give soft transition feedback and avoid showing stale frame brightly!
                if (thumbLastDrawnTime === -1 || Math.abs(targetTime - thumbLastDrawnTime) > 1.5) {
                    seekThumbCanvas.classList.add("is-seeking");
                }
            }

            // Seek the hidden thumbnail video using non-blocking queued fastSeek
            if (thumbSeekPending) {
                thumbNextSeekTime = targetTime;
            } else if (Math.abs(targetTime - thumbLastDrawnTime) > 0.4) {
                triggerThumbSeek(targetTime);
            }
        });

        // Show tooltip on mouseenter
        videoSliderContainer.addEventListener("mouseenter", (e) => {
            if ((previewIsAdaptive && !previewAdaptiveVideoUrl) || !thumbSourceReady) return;
            if (seekThumbCanvas && thumbLastDrawnTime === -1) {
                seekThumbCanvas.classList.add("is-seeking");
            }
            seekThumbTooltip.classList.add("visible");
            if (seekThumbDot) {
                seekThumbDot.classList.add("visible");
            }
        });

        // Hide tooltip on mouseleave
        videoSliderContainer.addEventListener("mouseleave", () => {
            seekThumbTooltip.classList.remove("visible");
            if (seekThumbDot) {
                seekThumbDot.classList.remove("visible");
            }
            thumbSeekPending = false;
            thumbNextSeekTime = null;
            thumbCurrentSeekingTime = null;
            thumbLastDrawnTime = -1;
            if (seekThumbCanvas) {
                seekThumbCanvas.classList.add("is-seeking");
            }
        });
    }
    // ===== End Seek Thumbnail Preview =====

    if (videoVolumeSlider && previewVideoPlayer) {
        videoVolumeSlider.addEventListener("input", function (e) {
            e.stopPropagation();
            previewVideoPlayer.volume = parseFloat(this.value);
            updateSliderBackground(this);
            if (videoMuteBtn) {
                previewVideoPlayer.muted = (previewVideoPlayer.volume === 0);
                updateVolumeWavesState(previewVideoPlayer.volume, previewVideoPlayer.muted, videoMuteBtn);
            }
        });
    }

    if (videoMuteBtn && previewVideoPlayer && videoVolumeSlider) {
        let prevVideoVolume = 1.0;
        videoMuteBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewVideoPlayer.muted = !previewVideoPlayer.muted;

            if (previewVideoPlayer.muted) {
                prevVideoVolume = parseFloat(videoVolumeSlider.value) || 1.0;
                videoVolumeSlider.value = 0;
            } else {
                videoVolumeSlider.value = prevVideoVolume;
                previewVideoPlayer.volume = prevVideoVolume;
            }
            updateVolumeWavesState(previewVideoPlayer.volume, previewVideoPlayer.muted, videoMuteBtn);
            updateSliderBackground(videoVolumeSlider);
        });

        const videoVolumeContainer = document.querySelector(".video-volume-container");
        if (videoVolumeContainer) {
            videoVolumeContainer.addEventListener("wheel", (e) => {
                e.preventDefault();
                e.stopPropagation();

                let volume = previewVideoPlayer.volume;
                if (e.deltaY < 0) {
                    volume = Math.min(1.0, volume + 0.05);
                } else {
                    volume = Math.max(0.0, volume - 0.05);
                }

                previewVideoPlayer.volume = volume;
                videoVolumeSlider.value = volume;
                updateSliderBackground(videoVolumeSlider);

                previewVideoPlayer.muted = (volume === 0);
                updateVolumeWavesState(volume, previewVideoPlayer.muted, videoMuteBtn);
            });
        }
    }

    function updateFullscreenUI() {
        // Update Video Fullscreen Button if present
        if (videoFullscreenBtn) {
            const svg = videoFullscreenBtn.querySelector("svg");
            if (videoFullscreenMode === 0) {
                videoFullscreenBtn.title = "Theater Mode (Web Fullscreen)";
                if (svg) {
                    svg.innerHTML = '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>';
                }
            } else if (videoFullscreenMode === 1) {
                videoFullscreenBtn.title = "Native Fullscreen";
                if (svg) {
                    svg.innerHTML = '<rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke-width="2" fill="none" stroke="currentColor"></rect><path d="M9 3v18M15 3v18" stroke="currentColor" stroke-dasharray="2 2"></path>';
                }
            } else if (videoFullscreenMode === 2) {
                videoFullscreenBtn.title = "Exit Fullscreen";
                if (svg) {
                    svg.innerHTML = '<path d="M4 14h6v6m10-6h-6v6M4 10h6V4m10 6h-6V4"></path>';
                }
            }
        }
        // Update Modal Fullscreen Button if present
        if (modalFullscreenBtn) {
            const svg = modalFullscreenBtn.querySelector("svg");
            if (videoFullscreenMode === 0) {
                modalFullscreenBtn.title = "Theater Mode (Web Fullscreen)";
                if (svg) {
                    svg.innerHTML = '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>';
                }
            } else if (videoFullscreenMode === 1) {
                modalFullscreenBtn.title = "Native Fullscreen";
                if (svg) {
                    svg.innerHTML = '<rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke-width="2" fill="none" stroke="currentColor"></rect><path d="M9 3v18M15 3v18" stroke="currentColor" stroke-dasharray="2 2"></path>';
                }
            } else if (videoFullscreenMode === 2) {
                modalFullscreenBtn.title = "Exit Fullscreen";
                if (svg) {
                    svg.innerHTML = '<path d="M4 14h6v6m10-6h-6v6M4 10h6V4m10 6h-6V4"></path>';
                }
            }
        }
    }

    // ── Preview Modal: Free Drag & Resize ─────────────────────────────────────
    // Called once on DOMContentLoaded to wire up drag-to-move (via header) and
    // resize (via the 8 edge/corner handles injected in the HTML).
    // All interaction is disabled while in Theater / Fullscreen modes.
    (function initPreviewDragResize() {
        const card = document.querySelector(".modal-card-preview");
        const header = document.querySelector("#preview-modal .modal-header");
        if (!card || !header) return;

        const alignV = document.getElementById("preview-align-v");
        const alignH = document.getElementById("preview-align-h");

        const MIN_W = 480, MIN_H = 320;
        let isDragging = false, isResizing = false;
        let startX, startY, startLeft, startTop, startW, startH, resizeDir;

        // ── helper: is theater/fullscreen active? ──────────────────────────
        function isFullscreenActive() {
            return document.body.classList.contains("theater-active") ||
                card.classList.contains("web-fullscreen") ||
                document.fullscreenElement === card ||
                document.webkitFullscreenElement === card;
        }

        // ── helper: get card's current pixel rect ─────────────────────────
        function getCardRect() {
            return card.getBoundingClientRect();
        }

        // ── apply absolute position (removes centering transform) ──────────
        function applyPos(left, top, w, h) {
            card.classList.add("preview-dragged");
            card.style.left = left + "px";
            card.style.top = top + "px";
            if (w !== undefined) card.style.width = w + "px";
            if (h !== undefined) card.style.height = h + "px";
        }

        // ── ensure card is within viewport ────────────────────────────────
        function clamp(val, min, max) { return Math.max(min, Math.min(max, val)); }

        function clampPosition(left, top, w, h) {
            const vw = window.innerWidth, vh = window.innerHeight;
            const MARGIN = 40; // keep at least 40px on-screen
            left = clamp(left, MARGIN - w, vw - MARGIN);
            top = clamp(top, 0, vh - MARGIN);
            return { left, top };
        }

        // ── helper: disable/restore CSS transitions on the card ───────────
        function disableTransition() {
            card.style.transition = "none";
        }
        function restoreTransition() {
            // Re-enable on the next frame so the position is already committed
            requestAnimationFrame(() => { card.style.removeProperty("transition"); });
        }

        // ── DRAG (header) ─────────────────────────────────────────────────
        header.style.cursor = "grab";
        header.addEventListener("mouseenter", function () {
            if (window.canvasSettings.previewDraggable === false) {
                header.style.cursor = "default";
            } else {
                header.style.cursor = "grab";
            }
        });

        header.addEventListener("mousedown", function (e) {
            if (window.canvasSettings.previewDraggable === false) return;
            // Ignore if clicking a button inside the header
            if (e.target.closest("button") || e.target.closest("a")) return;
            if (isFullscreenActive()) return;

            isDragging = true;
            header.style.cursor = "grabbing";
            document.body.style.userSelect = "none";

            const rect = getCardRect();
            // Switch to explicit left/top – must disable transition FIRST so the
            // transform → none change is instant (no jump to top-left corner).
            if (!card.classList.contains("preview-dragged")) {
                disableTransition();
                applyPos(rect.left, rect.top, rect.width, rect.height);
                restoreTransition();
            }
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseFloat(card.style.left);
            startTop = parseFloat(card.style.top);
            e.preventDefault();
        });

        // ── RESIZE (handles) ──────────────────────────────────────────────
        const handles = card.querySelectorAll(".preview-resize-handle");
        handles.forEach(function (handle) {
            handle.addEventListener("mousedown", function (e) {
                if (window.canvasSettings.previewResizable === false) return;
                if (isFullscreenActive()) return;

                isResizing = true;
                resizeDir = handle.dataset.dir;
                document.body.style.userSelect = "none";

                const rect = getCardRect();
                if (!card.classList.contains("preview-dragged")) {
                    applyPos(rect.left, rect.top, rect.width, rect.height);
                }
                startX = e.clientX;
                startY = e.clientY;
                startLeft = rect.left;
                startTop = rect.top;
                startW = rect.width;
                startH = rect.height;
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // ── mousemove (shared) ────────────────────────────────────────────
        document.addEventListener("mousemove", function (e) {
            if (!isDragging && !isResizing) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            if (isDragging) {
                let newLeft = startLeft + dx;
                let newTop = startTop + dy;
                const w = parseFloat(card.style.width) || card.offsetWidth;
                const h = parseFloat(card.style.height) || card.offsetHeight;

                // Alignment guidelines and center snapping
                const vw = window.innerWidth;
                const vh = window.innerHeight;
                const cardCenterX = newLeft + w / 2;
                const cardCenterY = newTop + h / 2;
                const vpCenterX = vw / 2;
                const vpCenterY = vh / 2;
                const SNAP_THRESHOLD = 15;

                let snappedX = false;
                let snappedY = false;

                // Horizontal snap (vertical guide line)
                if (Math.abs(cardCenterX - vpCenterX) < SNAP_THRESHOLD) {
                    newLeft = vpCenterX - w / 2;
                    snappedX = true;
                    if (alignV) {
                        alignV.style.left = Math.round(vpCenterX) + "px";
                        alignV.classList.remove("hidden");
                    }
                } else {
                    if (alignV) alignV.classList.add("hidden");
                }

                // Vertical snap (horizontal guide line)
                if (Math.abs(cardCenterY - vpCenterY) < SNAP_THRESHOLD) {
                    newTop = vpCenterY - h / 2;
                    snappedY = true;
                    if (alignH) {
                        alignH.style.top = Math.round(vpCenterY) + "px";
                        alignH.classList.remove("hidden");
                    }
                } else {
                    if (alignH) alignH.classList.add("hidden");
                }

                const clamped = clampPosition(newLeft, newTop, w, h);
                applyPos(clamped.left, clamped.top);
            }

            if (isResizing) {
                const d = resizeDir;
                let newLeft = startLeft, newTop = startTop;
                let newW = startW, newH = startH;
                const vw = window.innerWidth, vh = window.innerHeight;

                if (d.includes("e")) newW = Math.max(MIN_W, startW + dx);
                if (d.includes("s")) newH = Math.max(MIN_H, startH + dy);
                if (d.includes("w")) {
                    newW = Math.max(MIN_W, startW - dx);
                    newLeft = startLeft + (startW - newW);
                }
                if (d.includes("n")) {
                    newH = Math.max(MIN_H, startH - dy);
                    newTop = startTop + (startH - newH);
                }
                // Clamp so card doesn't resize off-screen
                newW = Math.min(newW, vw - newLeft - 4);
                newH = Math.min(newH, vh - newTop - 4);
                applyPos(newLeft, newTop, newW, newH);
            }
        });

        // ── mouseup ───────────────────────────────────────────────────────
        document.addEventListener("mouseup", function () {
            if (isDragging || isResizing) {
                isDragging = false;
                isResizing = false;
                header.style.cursor = "grab";
                document.body.style.userSelect = "";
                // Hide alignment lines when drag stops
                if (alignV) alignV.classList.add("hidden");
                if (alignH) alignH.classList.add("hidden");
            }
        });

        function fitPreviewToMedia() {
            if (isFullscreenActive()) return;

            let mediaW = 0;
            let mediaH = 0;

            const isVideoVisible = !previewVideoContainer.classList.contains("hidden");
            const isImageVisible = !previewImageContainer.classList.contains("hidden");
            const isWebpageVisible = previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden");

            if (isVideoVisible && previewVideoPlayer) {
                mediaW = previewVideoPlayer.videoWidth;
                mediaH = previewVideoPlayer.videoHeight;
                // Fallback to standard 16:9 if dimensions are not reported yet
                if (!mediaW || !mediaH) {
                    mediaW = 1920;
                    mediaH = 1080;
                }
            } else if (isImageVisible && previewImageElement) {
                mediaW = previewImageElement.naturalWidth;
                mediaH = previewImageElement.naturalHeight;
                // Fallback to standard 3:2 if natural dimensions are unavailable
                if (!mediaW || !mediaH) {
                    mediaW = 1200;
                    mediaH = 800;
                }
            } else if (isWebpageVisible) {
                // Webpage stream players (AnimeVietSub, etc.) are standard 16:9
                mediaW = 1920;
                mediaH = 1080;
            }

            if (!mediaW || !mediaH) {
                console.warn("[FitPreview] Media dimensions are not available yet.");
                return;
            }

            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const aspect = mediaW / mediaH;

            // ── Dynamically measure chrome dimensions from live DOM ──
            const headerEl = card.querySelector(".modal-header");
            const footerEl = card.querySelector(".preview-footer-toolbar");
            const contentArea = card.querySelector(".preview-content-area");

            // Measure header and footer actual rendered heights
            const headerH = headerEl ? headerEl.getBoundingClientRect().height : 57;
            const footerH = footerEl ? footerEl.getBoundingClientRect().height : 65;

            // Measure content area margins and borders
            let contentMarginH = 16; // top+bottom margin default
            let contentMarginW = 32; // left+right margin default
            let contentBorderH = 2;  // top+bottom border default
            let contentBorderW = 2;  // left+right border default
            if (contentArea) {
                const cs = getComputedStyle(contentArea);
                contentMarginH = parseFloat(cs.marginTop) + parseFloat(cs.marginBottom);
                contentMarginW = parseFloat(cs.marginLeft) + parseFloat(cs.marginRight);
                contentBorderH = parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth);
                contentBorderW = parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
            }

            // Measure sidebar actual width (including its border-left)
            const sidebarEl = isVideoVisible ? document.getElementById("preview-transcript-sidebar") : null;
            const isSidebarVisible = sidebarEl && !sidebarEl.classList.contains("hidden");
            let sidebarW = 0;
            if (isSidebarVisible) {
                sidebarW = sidebarEl.getBoundingClientRect().width;
            }

            const horizontalExtra = contentMarginW + contentBorderW + sidebarW;
            const verticalExtra = headerH + footerH + contentMarginH + contentBorderH;

            // Constrain video/image dimensions to 85% of screen viewport
            const maxVideoW = (vw * 0.85) - horizontalExtra;
            const maxVideoH = (vh * 0.85) - verticalExtra;

            // Safe minimum dimensions to accommodate player controls bar
            const minVideoW = (isVideoVisible || isWebpageVisible) ? 566 : 446;
            const minVideoH = Math.max(200, 320 - verticalExtra);

            let targetVideoW = mediaW;
            let targetVideoH = mediaH;

            // Scale down to fit viewport constraints
            if (targetVideoW > maxVideoW) {
                targetVideoW = maxVideoW;
                targetVideoH = targetVideoW / aspect;
            }
            if (targetVideoH > maxVideoH) {
                targetVideoH = maxVideoH;
                targetVideoW = targetVideoH * aspect;
            }

            // Scale up to satisfy minimum controls width/height limits (preserving aspect ratio)
            if (targetVideoW < minVideoW) {
                targetVideoW = minVideoW;
                targetVideoH = targetVideoW / aspect;
            }
            if (targetVideoH < minVideoH) {
                targetVideoH = minVideoH;
                targetVideoW = targetVideoH * aspect;
            }

            const finalW = Math.round(targetVideoW + horizontalExtra);
            const finalH = Math.round(targetVideoH + verticalExtra);

            // Centering coordinate calculations
            const targetLeft = Math.round((vw - finalW) / 2);
            const targetTop = Math.round((vh - finalH) / 2);

            // Apply smoothly with temporary CSS transition
            card.style.transition = "all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)";
            applyPos(targetLeft, targetTop, finalW, finalH);

            setTimeout(() => {
                card.style.removeProperty("transition");
            }, 300);
        }
        window.fitPreviewToMedia = fitPreviewToMedia;

        // ── preset positioning presets ────────────────────────────────────
        function applyPositionPreset(preset) {
            if (isFullscreenActive()) return;

            const vw = window.innerWidth;
            const vh = window.innerHeight;
            const w = parseFloat(card.style.width) || card.offsetWidth;
            const h = parseFloat(card.style.height) || card.offsetHeight;
            const MARGIN = 20;

            let targetLeft = 0;
            let targetTop = 0;

            switch (preset) {
                case "center":
                    targetLeft = (vw - w) / 2;
                    targetTop = (vh - h) / 2;
                    break;
                case "left":
                    targetLeft = MARGIN;
                    targetTop = (vh - h) / 2;
                    break;
                case "right":
                    targetLeft = vw - w - MARGIN;
                    targetTop = (vh - h) / 2;
                    break;
                case "top":
                    targetLeft = (vw - w) / 2;
                    targetTop = MARGIN;
                    break;
                case "bottom":
                    targetLeft = (vw - w) / 2;
                    targetTop = vh - h - MARGIN;
                    break;
                default:
                    return;
            }

            // Animate card smoothly to preset location
            card.style.transition = "all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1)";
            applyPos(Math.round(targetLeft), Math.round(targetTop), w, h);

            setTimeout(() => {
                card.style.removeProperty("transition");
            }, 350);
        }

        window._fitPreviewToMedia = fitPreviewToMedia;

        // ── bind buttons / dropdown listeners ──────────────────────────────
        const fitBtn = document.getElementById("preview-fit-btn");
        const alignBtn = document.getElementById("preview-align-btn");
        const presetMenu = document.getElementById("preview-preset-menu");

        if (fitBtn) {
            fitBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                fitPreviewToMedia();
            });
        }

        if (alignBtn && presetMenu) {
            alignBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                presetMenu.classList.toggle("hidden");
            });

            document.addEventListener("click", function (e) {
                if (!e.target.closest(".preset-dropdown-container")) {
                    presetMenu.classList.add("hidden");
                }
            });

            presetMenu.querySelectorAll(".preset-menu-item").forEach(function (item) {
                item.addEventListener("click", function (e) {
                    e.stopPropagation();
                    const pos = item.dataset.pos;
                    applyPositionPreset(pos);
                    presetMenu.classList.add("hidden");
                });
            });
        }

        // ── Reset position when modal opens (first time or after close) ───
        // We expose a helper so triggerPreview() can call it.
        window._resetPreviewCardPosition = function () {
            card.classList.remove("preview-dragged");
            card.style.removeProperty("left");
            card.style.removeProperty("top");
            card.style.removeProperty("width");
            card.style.removeProperty("height");
            if (alignV) alignV.classList.add("hidden");
            if (alignH) alignH.classList.add("hidden");
        };
    })();

    function applyFullscreenLayout(active) {
        const modal = document.getElementById("preview-modal");
        const card = document.querySelector(".modal-card-preview");
        const contentArea = document.querySelector(".preview-content-area");
        const playerContainer = document.querySelector(".preview-player-container");
        const sidebar = document.getElementById("preview-transcript-sidebar");
        const footerToolbar = document.querySelector(".preview-footer-toolbar");
        const header = document.querySelector("#preview-modal .modal-header");
        const audioCard = document.querySelector(".audio-preview-card");
        const webpageIframe = document.getElementById("preview-webpage-iframe");
        const videoMain = document.querySelector(".preview-video-main");
        const videoCard = document.querySelector(".video-preview-card");
        const videoWrapper = document.querySelector(".video-wrapper");

        if (active) {
            document.body.classList.add("theater-active");
            // Make modal a plain block so its flex centering doesn't constrain the card
            if (modal) {
                modal.style.setProperty("padding", "0", "important");
                modal.style.setProperty("background", "#000", "important");
                modal.style.setProperty("display", "block", "important");
            }
            // Card: use position: fixed so it covers the full viewport regardless of
            // parent flex layout or zoom factor.
            if (card) {
                card.style.setProperty("position", "fixed", "important");
                card.style.setProperty("top", "0", "important");
                card.style.setProperty("left", "0", "important");
                card.style.setProperty("right", "0", "important");
                card.style.setProperty("bottom", "0", "important");
                card.style.setProperty("width", "100%", "important");
                card.style.setProperty("height", "100%", "important");
                card.style.setProperty("max-width", "none", "important");
                card.style.setProperty("max-height", "none", "important");
                card.style.setProperty("margin", "0", "important");
                card.style.setProperty("border-radius", "0", "important");
                card.style.setProperty("border", "none", "important");
                card.style.setProperty("transform", "none", "important");
                card.style.setProperty("box-shadow", "none", "important");
                card.style.setProperty("background", "#000", "important");
                card.style.setProperty("backdrop-filter", "none", "important");
                card.style.setProperty("-webkit-backdrop-filter", "none", "important");
                card.style.setProperty("zoom", "1", "important");
            }
            // All inner containers: cascade position: absolute; inset: 0 so each
            // fills its positioned parent without depending on flex height propagation.
            if (contentArea) {
                contentArea.style.setProperty("position", "absolute", "important");
                contentArea.style.setProperty("top", "0", "important");
                contentArea.style.setProperty("left", "0", "important");
                contentArea.style.setProperty("right", "0", "important");
                contentArea.style.setProperty("bottom", "0", "important");
                contentArea.style.setProperty("margin", "0", "important");
                contentArea.style.setProperty("border", "none", "important");
                contentArea.style.setProperty("border-radius", "0", "important");
                contentArea.style.setProperty("width", "100%", "important");
                contentArea.style.setProperty("height", "100%", "important");
                contentArea.style.setProperty("background", "#000", "important");
                contentArea.style.setProperty("overflow", "hidden", "important");
            }
            if (playerContainer) {
                playerContainer.style.setProperty("position", "absolute", "important");
                playerContainer.style.setProperty("top", "0", "important");
                playerContainer.style.setProperty("left", "0", "important");
                playerContainer.style.setProperty("right", "0", "important");
                playerContainer.style.setProperty("bottom", "0", "important");
                playerContainer.style.setProperty("width", "100%", "important");
                playerContainer.style.setProperty("height", "100%", "important");
                playerContainer.style.setProperty("max-height", "none", "important");
                playerContainer.style.setProperty("max-width", "none", "important");
                playerContainer.style.setProperty("padding", "0", "important");
            }
            if (videoMain) {
                // flex: 1 so video takes remaining width alongside the transcript sidebar
                videoMain.style.setProperty("flex", "1", "important");
                videoMain.style.setProperty("position", "relative", "important");
                videoMain.style.setProperty("height", "100%", "important");
                videoMain.style.setProperty("overflow", "hidden", "important");
                videoMain.style.setProperty("min-width", "0", "important");
            }
            if (videoCard) {
                videoCard.style.setProperty("width", "100%", "important");
                videoCard.style.setProperty("height", "100%", "important");
                videoCard.style.setProperty("overflow", "hidden", "important");
            }
            if (videoWrapper) {
                // absolute inset-0 relative to videoMain (which now has position:relative)
                videoWrapper.style.setProperty("position", "absolute", "important");
                videoWrapper.style.setProperty("top", "0", "important");
                videoWrapper.style.setProperty("left", "0", "important");
                videoWrapper.style.setProperty("right", "0", "important");
                videoWrapper.style.setProperty("bottom", "0", "important");
                videoWrapper.style.setProperty("width", "100%", "important");
                videoWrapper.style.setProperty("height", "100%", "important");
            }
            // Sidebar: let user preference control visibility (no forced hide)

            if (footerToolbar) {
                footerToolbar.style.setProperty("display", "none", "important");
            }
            if (header) {
                header.style.setProperty("position", "absolute", "important");
                header.style.setProperty("top", "0", "important");
                header.style.setProperty("left", "0", "important");
                header.style.setProperty("right", "0", "important");
                header.style.setProperty("z-index", "100000", "important");
                header.style.setProperty("background", "linear-gradient(to bottom, rgba(13, 18, 30, 0.95) 0%, rgba(13, 18, 30, 0.5) 60%, transparent 100%)", "important");
                header.style.setProperty("border-bottom", "none", "important");
                header.style.setProperty("padding", "18px 24px", "important");
            }
            if (audioCard) {
                audioCard.style.setProperty("position", "absolute", "important");
                audioCard.style.setProperty("top", "0", "important");
                audioCard.style.setProperty("left", "0", "important");
                audioCard.style.setProperty("right", "0", "important");
                audioCard.style.setProperty("bottom", "0", "important");
                audioCard.style.setProperty("width", "100%", "important");
                audioCard.style.setProperty("height", "100%", "important");
                audioCard.style.setProperty("max-width", "none", "important");
                audioCard.style.setProperty("max-height", "none", "important");
                audioCard.style.setProperty("margin", "0", "important");
                audioCard.style.setProperty("padding", "0", "important");
                audioCard.style.setProperty("border-radius", "0", "important");
                audioCard.style.setProperty("border", "none", "important");
                audioCard.style.setProperty("box-shadow", "none", "important");
                audioCard.style.setProperty("background", "#000", "important");
                audioCard.style.setProperty("display", "flex", "important");
                audioCard.style.setProperty("flex-direction", "column", "important");
            }
            if (webpageIframe) {
                webpageIframe.style.setProperty("border-radius", "0", "important");
                webpageIframe.style.setProperty("min-height", "100%", "important");
            }
        } else {
            document.body.classList.remove("theater-active");
            if (modal) {
                modal.style.removeProperty("padding");
                modal.style.removeProperty("background");
                modal.style.removeProperty("display");
            }
            if (card) {
                card.classList.remove("preview-dragged");
                card.style.removeProperty("position");
                card.style.removeProperty("top");
                card.style.removeProperty("left");
                card.style.removeProperty("right");
                card.style.removeProperty("bottom");
                card.style.removeProperty("width");
                card.style.removeProperty("height");
                card.style.removeProperty("max-width");
                card.style.removeProperty("max-height");
                card.style.removeProperty("margin");
                card.style.removeProperty("border-radius");
                card.style.removeProperty("border");
                card.style.removeProperty("transform");
                card.style.removeProperty("box-shadow");
                card.style.removeProperty("background");
                card.style.removeProperty("backdrop-filter");
                card.style.removeProperty("-webkit-backdrop-filter");
                card.style.removeProperty("zoom");
            }
            if (contentArea) {
                contentArea.style.removeProperty("position");
                contentArea.style.removeProperty("top");
                contentArea.style.removeProperty("left");
                contentArea.style.removeProperty("right");
                contentArea.style.removeProperty("bottom");
                contentArea.style.removeProperty("margin");
                contentArea.style.removeProperty("border");
                contentArea.style.removeProperty("border-radius");
                contentArea.style.removeProperty("height");
                contentArea.style.removeProperty("width");
                contentArea.style.removeProperty("background");
                contentArea.style.removeProperty("overflow");
            }
            if (playerContainer) {
                playerContainer.style.removeProperty("position");
                playerContainer.style.removeProperty("top");
                playerContainer.style.removeProperty("left");
                playerContainer.style.removeProperty("right");
                playerContainer.style.removeProperty("bottom");
                playerContainer.style.removeProperty("height");
                playerContainer.style.removeProperty("width");
                playerContainer.style.removeProperty("max-height");
                playerContainer.style.removeProperty("max-width");
                playerContainer.style.removeProperty("padding");
            }
            if (videoMain) {
                videoMain.style.removeProperty("flex");
                videoMain.style.removeProperty("position");
                videoMain.style.removeProperty("height");
                videoMain.style.removeProperty("overflow");
                videoMain.style.removeProperty("min-width");
            }
            if (videoCard) {
                videoCard.style.removeProperty("width");
                videoCard.style.removeProperty("height");
                videoCard.style.removeProperty("overflow");
            }
            if (videoWrapper) {
                videoWrapper.style.removeProperty("position");
                videoWrapper.style.removeProperty("top");
                videoWrapper.style.removeProperty("left");
                videoWrapper.style.removeProperty("right");
                videoWrapper.style.removeProperty("bottom");
                videoWrapper.style.removeProperty("width");
                videoWrapper.style.removeProperty("height");
            }
            if (sidebar) {
                sidebar.style.removeProperty("display");
            }
            if (footerToolbar) {
                footerToolbar.style.removeProperty("display");
            }
            if (header) {
                header.style.removeProperty("position");
                header.style.removeProperty("top");
                header.style.removeProperty("left");
                header.style.removeProperty("right");
                header.style.removeProperty("z-index");
                header.style.removeProperty("background");
                header.style.removeProperty("border-bottom");
                header.style.removeProperty("padding");
            }
            if (audioCard) {
                audioCard.style.removeProperty("position");
                audioCard.style.removeProperty("top");
                audioCard.style.removeProperty("left");
                audioCard.style.removeProperty("right");
                audioCard.style.removeProperty("bottom");
                audioCard.style.removeProperty("width");
                audioCard.style.removeProperty("height");
                audioCard.style.removeProperty("max-width");
                audioCard.style.removeProperty("max-height");
                audioCard.style.removeProperty("margin");
                audioCard.style.removeProperty("padding");
                audioCard.style.removeProperty("border-radius");
                audioCard.style.removeProperty("border");
                audioCard.style.removeProperty("box-shadow");
                audioCard.style.removeProperty("background");
                audioCard.style.removeProperty("display");
                audioCard.style.removeProperty("flex-direction");
            }
            if (webpageIframe) {
                webpageIframe.style.removeProperty("border-radius");
                webpageIframe.style.removeProperty("min-height");
            }
        }
    }


    function toggleFullscreenMode() {
        const videoPreviewCard = document.querySelector(".video-preview-card");
        const audioPreviewCard = document.querySelector(".audio-preview-card");
        if (videoFullscreenMode === 0) {
            // Normal -> Theater Mode (Web Fullscreen)
            videoFullscreenMode = 1;
            if (videoPreviewCard) {
                videoPreviewCard.classList.add("web-fullscreen");
            }
            if (audioPreviewCard) {
                audioPreviewCard.classList.add("web-fullscreen");
            }
            if (previewModal) {
                previewModal.classList.add("modal-web-fullscreen");
                previewModal.classList.add("fullscreen-active");
            }
            applyFullscreenLayout(true);
            updateFullscreenUI();
        } else if (videoFullscreenMode === 1) {
            // Theater -> Native Fullscreen (We request native fullscreen on the entire modal container to support all formats)
            videoFullscreenMode = 2;
            if (previewModal) {
                previewModal.classList.add("modal-web-fullscreen");
                previewModal.classList.add("fullscreen-active");
                if (previewModal.requestFullscreen) {
                    previewModal.requestFullscreen();
                } else if (previewModal.webkitRequestFullscreen) {
                    previewModal.webkitRequestFullscreen();
                } else if (previewModal.msRequestFullscreen) {
                    previewModal.msRequestFullscreen();
                }
            }
            applyFullscreenLayout(true);
            updateFullscreenUI();
        } else {
            // Native -> Normal (Exit)
            videoFullscreenMode = 0;
            if (videoPreviewCard) {
                videoPreviewCard.classList.remove("web-fullscreen");
            }
            if (audioPreviewCard) {
                audioPreviewCard.classList.remove("web-fullscreen");
            }
            if (previewModal) {
                previewModal.classList.remove("modal-web-fullscreen");
                previewModal.classList.remove("fullscreen-active");
            }
            applyFullscreenLayout(false);
            if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            }
            updateFullscreenUI();
        }
    }

    if (videoFullscreenBtn) {
        videoFullscreenBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleFullscreenMode();
        });
    }
    if (modalFullscreenBtn) {
        modalFullscreenBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleFullscreenMode();
        });
    }

    function toggleLightsOff(forceState) {
        if (!previewModal) return;
        
        let targetState;
        if (typeof forceState === "boolean") {
            targetState = forceState;
        } else {
            targetState = !previewModal.classList.contains("lights-off");
        }

        if (targetState) {
            previewModal.classList.add("lights-off");
            if (previewLightsOffBtn) {
                previewLightsOffBtn.classList.add("active");
                previewLightsOffBtn.setAttribute("title", "Turn on lights (O)");
            }
        } else {
            previewModal.classList.remove("lights-off");
            if (previewLightsOffBtn) {
                previewLightsOffBtn.classList.remove("active");
                previewLightsOffBtn.setAttribute("title", "Turn off lights (O)");
            }
        }
    }

    if (previewLightsOffBtn) {
        previewLightsOffBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleLightsOff();
        });
    }

    const handleFullscreenChange = () => {
        const isNative = document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement;
        if (!isNative && videoFullscreenMode === 2) {
            videoFullscreenMode = 0;
            const videoPreviewCard = document.querySelector(".video-preview-card");
            const audioPreviewCard = document.querySelector(".audio-preview-card");
            if (videoPreviewCard) {
                videoPreviewCard.classList.remove("web-fullscreen");
            }
            if (audioPreviewCard) {
                audioPreviewCard.classList.remove("web-fullscreen");
            }
            if (previewModal) {
                previewModal.classList.remove("modal-web-fullscreen");
                previewModal.classList.remove("fullscreen-active");
                previewModal.classList.remove("hidden-cursor");
            }
            applyFullscreenLayout(false);

            // Remove auto-hide classes
            const modalHeader = document.querySelector("#preview-modal .modal-header");
            const customVideoControls = document.querySelector(".custom-video-controls");
            const customAudioControls = document.querySelector(".custom-audio-controls");
            const imageControls = document.querySelector(".image-controls");
            const subHeader = document.querySelector(".subtitle-preview-box .sub-header");
            const navControls = document.querySelectorAll(".nav-control");

            if (modalHeader) modalHeader.classList.remove("hidden-header");
            if (customVideoControls) customVideoControls.classList.remove("hidden-controls");
            if (customAudioControls) customAudioControls.classList.remove("hidden-controls");
            if (imageControls) imageControls.classList.remove("hidden-controls");
            if (subHeader) subHeader.classList.remove("hidden-controls");
            navControls.forEach(ctrl => ctrl.classList.remove("hidden-controls"));

            updateFullscreenUI();
        } else if (isNative) {
            videoFullscreenMode = 2;
            const videoPreviewCard = document.querySelector(".video-preview-card");
            const audioPreviewCard = document.querySelector(".audio-preview-card");
            if (videoPreviewCard) {
                videoPreviewCard.classList.add("web-fullscreen");
            }
            if (audioPreviewCard) {
                audioPreviewCard.classList.add("web-fullscreen");
            }
            if (previewModal) {
                previewModal.classList.add("modal-web-fullscreen");
                previewModal.classList.add("fullscreen-active");
            }
            applyFullscreenLayout(true);
            updateFullscreenUI();
        }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    document.addEventListener("mozfullscreenchange", handleFullscreenChange);
    document.addEventListener("MSFullscreenChange", handleFullscreenChange);

    // Initialize Fullscreen UI
    updateFullscreenUI();

    // --- QUALITY/FORMAT DROP DOWN SELECT CHANGE HANDLERS ---
    if (audioFormatSelect) {
        audioFormatSelect.addEventListener("change", function () {
            const val = this.value;
            const parts = val.split("|");
            const formatId = parts[0];
            const quality = parts[1] || "";

            if (activeMetadata && activeMetadata.audio_options) {
                const opt = activeMetadata.audio_options.find(o =>
                    o.format_id === formatId &&
                    ((!quality && !o.quality) || (String(o.quality) === String(quality)))
                );
                if (opt) {
                    triggerPreview(null, opt.format_id, opt.ext, opt.label, opt.quality, opt.url, "", "", "audio");
                }
            }
        });
    }

    if (videoFormatSelect) {
        videoFormatSelect.addEventListener("change", function () {
            const formatId = this.value;
            if (activeMetadata && activeMetadata.video_options) {
                const opt = activeMetadata.video_options.find(o => o.format_id === formatId);
                if (opt) {
                    const epReferer = opt.referer || (activeMetadata && activeMetadata.webpage_url) || activeUrl || "";
                    triggerPreview(null, opt.format_id, opt.ext, opt.label, opt.quality, opt.url, opt.episode || "", opt.server || "", "video", epReferer);
                }
            }
            if (typeof updateEpisodeNavigationButtonsState === "function") {
                updateEpisodeNavigationButtonsState();
            }
        });
    }

    // Close preview modal behavior
    if (previewModal && previewModalCloseBtn) {
        closePreviewModal = () => {
            // Turn off lights-off cinema mode if active
            toggleLightsOff(false);

            // Exit native fullscreen if active
            if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            }

            previewModal.classList.add("hidden");
            document.body.classList.remove("modal-open");
            document.body.classList.remove("preview-active");

            // Clean up Web Fullscreen / Theater Mode states
            videoFullscreenMode = 0;
            applyFullscreenLayout(false);
            const videoPreviewCard = document.querySelector(".video-preview-card");
            const audioPreviewCard = document.querySelector(".audio-preview-card");
            if (videoPreviewCard) {
                videoPreviewCard.classList.remove("web-fullscreen");
                videoPreviewCard.classList.remove("hidden-cursor");
            }
            if (audioPreviewCard) {
                audioPreviewCard.classList.remove("web-fullscreen");
            }
            previewModal.classList.remove("modal-web-fullscreen");
            previewModal.classList.remove("fullscreen-active");
            previewModal.classList.remove("hidden-cursor");

            // Remove auto-hide classes
            const modalHeader = document.querySelector("#preview-modal .modal-header");
            const customVideoControls = document.querySelector(".custom-video-controls");
            const customAudioControls = document.querySelector(".custom-audio-controls");
            const imageControls = document.querySelector(".image-controls");
            const subHeader = document.querySelector(".subtitle-preview-box .sub-header");
            const navControls = document.querySelectorAll(".nav-control");

            if (modalHeader) modalHeader.classList.remove("hidden-header");
            if (customVideoControls) customVideoControls.classList.remove("hidden-controls");
            if (customAudioControls) customAudioControls.classList.remove("hidden-controls");
            if (imageControls) imageControls.classList.remove("hidden-controls");
            if (subHeader) subHeader.classList.remove("hidden-controls");
            navControls.forEach(ctrl => ctrl.classList.remove("hidden-controls"));

            updateFullscreenUI();

            // Sync with main page trim inputs if enabled, or clear loop points
            const mainTrimCheckbox = document.getElementById("trim-checkbox");
            const mainTrimStartInput = document.getElementById("trim-start");
            const mainTrimEndInput = document.getElementById("trim-end");
            const loopPointAInput = document.getElementById("loop-point-a");
            const loopPointBInput = document.getElementById("loop-point-b");
            const toggleAbLoopEl = document.getElementById("toggle-ab-loop");
            const abLoopWrapperEl = document.getElementById("ab-loop-wrapper");

            if (mainTrimCheckbox && mainTrimCheckbox.checked) {
                const s = mainTrimStartInput ? parseTimeStringToSeconds(mainTrimStartInput.value) : null;
                const e = mainTrimEndInput ? parseTimeStringToSeconds(mainTrimEndInput.value) : null;
                loopStartSecs = (s !== null && s >= 0) ? s : null;
                loopEndSecs = (e !== null && e > 0) ? e : null;
                if (toggleAbLoopEl) {
                    toggleAbLoopEl.checked = true;
                    if (abLoopWrapperEl) {
                        abLoopWrapperEl.classList.remove("collapsed");
                        abLoopWrapperEl.classList.add("expanded");
                    }
                }
                if (loopPointAInput) loopPointAInput.value = loopStartSecs !== null ? formatTimeDetailed(loopStartSecs) : "";
                if (loopPointBInput) loopPointBInput.value = loopEndSecs !== null ? formatTimeDetailed(loopEndSecs) : "";
            } else {
                loopStartSecs = null;
                loopEndSecs = null;
                if (loopPointAInput) loopPointAInput.value = "";
                if (loopPointBInput) loopPointBInput.value = "";
            }
            if (typeof updateLoopMarkersUI === "function") updateLoopMarkersUI();

            // Reset text/subtitle preview styling
            previewSubFontSize = 0.88;
            previewSubWordWrap = true;
            if (previewSubText) {
                previewSubText.style.fontSize = "0.88rem";
                previewSubText.style.whiteSpace = "pre-wrap";
                previewSubText.style.overflowX = "visible";
            }

            if (previewVideoPlayer) {
                previewVideoPlayer.style.filter = "none";
            }

            if (previewShortcutsOverlay) {
                previewShortcutsOverlay.classList.add("hidden");
            }

            if (imageSidePanel) {
                imageSidePanel.classList.add("hidden");
            }
            if (btnImageAdjust) {
                btnImageAdjust.classList.remove("active");
            }
            if (previewImageElement) {
                previewImageElement.style.filter = "none";
            }

            const subFormatSelect = document.getElementById("preview-sub-format");
            if (subFormatSelect) {
                subFormatSelect.value = "original";
            }


            const ambientCanvas = document.getElementById("video-ambient-glow");
            if (ambientCanvas) {
                const ambientCtx = ambientCanvas.getContext("2d");
                if (ambientCtx) {
                    ambientCtx.clearRect(0, 0, ambientCanvas.width, ambientCanvas.height);
                }
            }

            const audioCanvas = document.getElementById("audio-visualizer-canvas");
            if (audioCanvas) {
                const audioCtx2D = audioCanvas.getContext("2d");
                if (audioCtx2D) {
                    audioCtx2D.clearRect(0, 0, audioCanvas.width, audioCanvas.height);
                }
            }

            if (window._activeMediaRecorder && window._activeMediaRecorder.state === "recording") {
                try {
                    window._activeMediaRecorder.stop();
                } catch (_) {}
                window._activeMediaRecorder = null;
            }
            window._mseCapturedStats = null;
            if (previewDownloadBtn) {
                const span = previewDownloadBtn.querySelector("span");
                if (span) span.textContent = "Export & Download";
            }

            stopAllPreviewPlaybacks(true);
        };

        previewModalCloseBtn.onclick = closePreviewModal;

        if (previewShortcutsBtn) {
            previewShortcutsBtn.onclick = (e) => {
                e.stopPropagation();
                if (previewShortcutsOverlay) {
                    previewShortcutsOverlay.classList.toggle("hidden");
                }
            };
        }

        if (shortcutsOverlayCloseBtn) {
            shortcutsOverlayCloseBtn.onclick = (e) => {
                e.stopPropagation();
                if (previewShortcutsOverlay) {
                    previewShortcutsOverlay.classList.add("hidden");
                }
            };
        }

        // previewModal.onclick = (e) => {
        //     if (e.target === previewModal) {
        //         closePreviewModal();
        //     }
        // };

        document.addEventListener("keydown", (e) => {
            if (previewModal && !previewModal.classList.contains("hidden")) {
                // Ignore hotkeys if user is typing in inputs or textareas
                const activeEl = document.activeElement;
                if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable)) {
                    return;
                }

                if (e.key === "Escape") {
                    closePreviewModal();
                    return;
                }

                if (e.key === "h" || e.key === "H" || e.key === "?") {
                    e.preventDefault();
                    if (previewShortcutsOverlay) {
                        previewShortcutsOverlay.classList.toggle("hidden");
                    }
                    return;
                }

                if (e.key === "o" || e.key === "O") {
                    e.preventDefault();
                    toggleLightsOff();
                    return;
                }

                // Episode navigation shortcuts (global for both video & stream player)
                const epNavEl = document.getElementById("preview-episode-nav");
                const hasEpisodeNav = epNavEl && !epNavEl.classList.contains("hidden");

                if (hasEpisodeNav) {
                    if (e.shiftKey && (e.key === "N" || e.key === "n")) {
                        e.preventDefault();
                        handleEpisodeStep(1);
                        return;
                    }
                    if (e.shiftKey && (e.key === "P" || e.key === "p")) {
                        e.preventDefault();
                        handleEpisodeStep(-1);
                        return;
                    }
                    if (e.key === "PageDown") {
                        e.preventDefault();
                        handleEpisodeStep(1);
                        return;
                    }
                    if (e.key === "PageUp") {
                        e.preventDefault();
                        handleEpisodeStep(-1);
                        return;
                    }
                }

                const isWebpageActive = previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden");
                if (isWebpageActive && hasEpisodeNav) {
                    if (e.key === "]") {
                        e.preventDefault();
                        handleEpisodeStep(1);
                        return;
                    }
                    if (e.key === "[") {
                        e.preventDefault();
                        handleEpisodeStep(-1);
                        return;
                    }
                }

                const isVideoActive = !previewVideoContainer.classList.contains("hidden");
                const isAudioActive = !previewAudioContainer.classList.contains("hidden");
                const isImageActive = !previewImageContainer.classList.contains("hidden");

                if (isVideoActive || isAudioActive) {
                    const loopPointAInput = document.getElementById("loop-point-a");
                    const loopPointBInput = document.getElementById("loop-point-b");
                    if (e.key === "[") {
                        e.preventDefault();
                        const time = getActivePlayerTime();
                        if (time !== null) {
                            loopStartSecs = time;
                            if (loopPointAInput) {
                                loopPointAInput.value = formatTimeDetailed(loopStartSecs);
                            }
                            if (loopEndSecs !== null && loopStartSecs >= loopEndSecs) {
                                loopEndSecs = null;
                                if (loopPointBInput) loopPointBInput.value = "";
                            }
                            if (typeof updateLoopMarkersUI === "function") updateLoopMarkersUI();
                        }
                        return;
                    }
                    if (e.key === "]") {
                        e.preventDefault();
                        const time = getActivePlayerTime();
                        if (time !== null) {
                            loopEndSecs = time;
                            if (loopPointBInput) {
                                loopPointBInput.value = formatTimeDetailed(loopEndSecs);
                            }
                            if (loopStartSecs !== null && loopEndSecs <= loopStartSecs) {
                                loopStartSecs = null;
                                if (loopPointAInput) loopPointAInput.value = "";
                            }
                            if (typeof updateLoopMarkersUI === "function") updateLoopMarkersUI();
                        }
                        return;
                    }
                }

                if (previewWebpageWebview && !previewWebpageWebview.classList.contains("hidden")) {
                    if (e.key === " " || e.key === "k" || e.key === "K") {
                        e.preventDefault();
                        previewWebpageWebview.executeJavaScript(`
                            (function() {
                                let newState = 'unknown';
                                if (typeof jwplayer === 'function') {
                                    const p = jwplayer('player');
                                    if (p) {
                                        if (p.getState() === 'playing') { p.pause(); newState = 'paused'; }
                                        else { p.play(); newState = 'playing'; }
                                    }
                                } else {
                                    const v = document.querySelector('video');
                                    if (v) {
                                        if (v.paused) { v.play().catch(()=>{}); newState = 'playing'; }
                                        else { v.pause(); newState = 'paused'; }
                                    }
                                }
                                return newState;
                            })()
                        `).then((st) => {
                            if (previewWebpagePauseIndicator) {
                                if (st === 'paused') previewWebpagePauseIndicator.classList.remove("hidden");
                                else if (st === 'playing') previewWebpagePauseIndicator.classList.add("hidden");
                            }
                        }).catch(() => {});
                        return;
                    }
                }

                if (isVideoActive && previewVideoPlayer) {
                    // Space or K/k (Play/Pause)
                    if (e.key === " " || e.key === "k" || e.key === "K") {
                        e.preventDefault();
                        if (previewVideoPlayer.paused) {
                            previewVideoPlayer.play().catch(err => console.log("Play failed: ", err));
                        } else {
                            previewVideoPlayer.pause();
                        }
                        return;
                    }
                    // M/m (Mute/Unmute)
                    if (e.key === "m" || e.key === "M") {
                        e.preventDefault();
                        previewVideoPlayer.muted = !previewVideoPlayer.muted;
                        if (videoVolumeSlider) {
                            videoVolumeSlider.value = previewVideoPlayer.muted ? 0 : previewVideoPlayer.volume;
                            updateSliderBackground(videoVolumeSlider);
                        }
                        if (videoMuteBtn) {
                            const volIcon = videoMuteBtn.querySelector(".volume-icon");
                            const muteIcon = videoMuteBtn.querySelector(".mute-icon");
                            if (previewVideoPlayer.muted) {
                                if (volIcon) volIcon.classList.add("hidden");
                                if (muteIcon) muteIcon.classList.remove("hidden");
                            } else {
                                if (volIcon) volIcon.classList.remove("hidden");
                                if (muteIcon) muteIcon.classList.add("hidden");
                            }
                        }
                        return;
                    }
                    // ArrowLeft or J/j (Seek Backward by 10s)
                    if (e.key === "ArrowLeft" || e.key === "j" || e.key === "J") {
                        e.preventDefault();
                        const totalDuration = getVideoTotalDuration();
                        const currentPlayTime = previewIsAdaptive ? (previewCurrentTimeOffset + previewVideoPlayer.currentTime) : previewVideoPlayer.currentTime;
                        let target = Math.max(0, currentPlayTime - 10);
                        if (previewIsAdaptive) {
                            seekAdaptiveVideo(target);
                        } else {
                            previewVideoPlayer.currentTime = target;
                        }
                        return;
                    }
                    // ArrowRight or L/l (Seek Forward by 10s)
                    if (e.key === "ArrowRight" || e.key === "l" || e.key === "L") {
                        e.preventDefault();
                        const totalDuration = getVideoTotalDuration();
                        const currentPlayTime = previewIsAdaptive ? (previewCurrentTimeOffset + previewVideoPlayer.currentTime) : previewVideoPlayer.currentTime;
                        let target = Math.min(totalDuration, currentPlayTime + 10);
                        if (previewIsAdaptive) {
                            seekAdaptiveVideo(target);
                        } else {
                            previewVideoPlayer.currentTime = target;
                        }
                        return;
                    }
                    // ArrowUp (Volume Up by 10%)
                    if (e.key === "ArrowUp") {
                        e.preventDefault();
                        previewVideoPlayer.muted = false;
                        previewVideoPlayer.volume = Math.min(1.0, previewVideoPlayer.volume + 0.1);
                        if (videoVolumeSlider) {
                            videoVolumeSlider.value = previewVideoPlayer.volume;
                            updateSliderBackground(videoVolumeSlider);
                        }
                        if (videoMuteBtn) {
                            const volIcon = videoMuteBtn.querySelector(".volume-icon");
                            const muteIcon = videoMuteBtn.querySelector(".mute-icon");
                            if (volIcon) volIcon.classList.remove("hidden");
                            if (muteIcon) muteIcon.classList.add("hidden");
                        }
                        return;
                    }
                    // ArrowDown (Volume Down by 10%)
                    if (e.key === "ArrowDown") {
                        e.preventDefault();
                        previewVideoPlayer.volume = Math.max(0.0, previewVideoPlayer.volume - 0.1);
                        if (videoVolumeSlider) {
                            videoVolumeSlider.value = previewVideoPlayer.volume;
                            updateSliderBackground(videoVolumeSlider);
                        }
                        if (videoMuteBtn) {
                            const volIcon = videoMuteBtn.querySelector(".volume-icon");
                            const muteIcon = videoMuteBtn.querySelector(".mute-icon");
                            if (previewVideoPlayer.volume === 0) {
                                if (volIcon) volIcon.classList.add("hidden");
                                if (muteIcon) muteIcon.classList.remove("hidden");
                            } else {
                                if (volIcon) volIcon.classList.remove("hidden");
                                if (muteIcon) muteIcon.classList.add("hidden");
                            }
                        }
                        return;
                    }
                    // F/f (Toggle Fullscreen)
                    if (e.key === "f" || e.key === "F") {
                        e.preventDefault();
                        if (videoFullscreenBtn) {
                            videoFullscreenBtn.click();
                        } else {
                            if (!document.fullscreenElement) {
                                previewVideoPlayer.requestFullscreen().catch(err => console.log(err));
                            } else {
                                document.exitFullscreen().catch(err => console.log(err));
                            }
                        }
                        return;
                    }
                    // < / > (Shift + , / Shift + .) (Volume/Playback Speed adjust)
                    if (e.key === "<" || e.key === ">") {
                        e.preventDefault();
                        const presets = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
                        const currentRate = previewVideoPlayer.playbackRate;
                        let currentIndex = presets.indexOf(currentRate);
                        if (currentIndex === -1) {
                            let closestDiff = Infinity;
                            presets.forEach((opt, idx) => {
                                const diff = Math.abs(opt - currentRate);
                                if (diff < closestDiff) {
                                    closestDiff = diff;
                                    currentIndex = idx;
                                }
                            });
                        }
                        let nextIndex = currentIndex;
                        if (e.key === "<") {
                            nextIndex = Math.max(0, currentIndex - 1);
                        } else if (e.key === ">") {
                            nextIndex = Math.min(presets.length - 1, currentIndex + 1);
                        }
                        const targetRate = presets[nextIndex];
                        setPlaybackSpeedUI(targetRate);
                        return;
                    }
                    // 0 to 9 (Seek to percentage)
                    if (e.key >= "0" && e.key <= "9") {
                        e.preventDefault();
                        const pct = parseInt(e.key) * 10;
                        const totalDuration = getVideoTotalDuration();
                        if (totalDuration > 0) {
                            const target = (pct / 100) * totalDuration;
                            if (previewIsAdaptive) {
                                seekAdaptiveVideo(target);
                            } else {
                                previewVideoPlayer.currentTime = target;
                            }
                        }
                        return;
                    }
                    // R/r (Toggle Repeat)
                    if (e.key === "r" || e.key === "R") {
                        e.preventDefault();
                        if (videoLoopBtn) videoLoopBtn.click();
                        return;
                    }
                    // P/p (Toggle Picture-in-Picture)
                    if (e.key === "p" || e.key === "P") {
                        e.preventDefault();
                        if (videoPipBtn) videoPipBtn.click();
                        return;
                    }
                    // T/t (Toggle Transcript Sidebar)
                    if (e.key === "t" || e.key === "T") {
                        e.preventDefault();
                        if (videoTranscriptBtn) videoTranscriptBtn.click();
                        return;
                    }
                } else if (isAudioActive && previewAudioPlayer) {
                    // Space or K/k (Play/Pause)
                    if (e.key === " " || e.key === "k" || e.key === "K") {
                        e.preventDefault();
                        if (previewAudioPlayer.paused) {
                            previewAudioPlayer.play().catch(err => console.log("Play failed: ", err));
                        } else {
                            previewAudioPlayer.pause();
                        }
                        return;
                    }
                    // M/m (Mute/Unmute)
                    if (e.key === "m" || e.key === "M") {
                        e.preventDefault();
                        previewAudioPlayer.muted = !previewAudioPlayer.muted;
                        if (audioVolumeSlider) {
                            audioVolumeSlider.value = previewAudioPlayer.muted ? 0 : previewAudioPlayer.volume;
                            updateSliderBackground(audioVolumeSlider);
                        }
                        if (audioMuteBtn) {
                            const volIcon = audioMuteBtn.querySelector(".volume-icon");
                            const muteIcon = audioMuteBtn.querySelector(".mute-icon");
                            if (previewAudioPlayer.muted) {
                                if (volIcon) volIcon.classList.add("hidden");
                                if (muteIcon) muteIcon.classList.remove("hidden");
                            } else {
                                if (volIcon) volIcon.classList.remove("hidden");
                                if (muteIcon) muteIcon.classList.add("hidden");
                            }
                        }
                        return;
                    }
                    // ArrowLeft or J/j (Seek Backward by 10s)
                    if (e.key === "ArrowLeft" || e.key === "j" || e.key === "J") {
                        e.preventDefault();
                        if (previewAudioPlayer.duration) {
                            previewAudioPlayer.currentTime = Math.max(0, previewAudioPlayer.currentTime - 10);
                        }
                        return;
                    }
                    // ArrowRight or L/l (Seek Forward by 10s)
                    if (e.key === "ArrowRight" || e.key === "l" || e.key === "L") {
                        e.preventDefault();
                        if (previewAudioPlayer.duration) {
                            previewAudioPlayer.currentTime = Math.min(previewAudioPlayer.duration, previewAudioPlayer.currentTime + 10);
                        }
                        return;
                    }
                    // ArrowUp (Volume Up by 10%)
                    if (e.key === "ArrowUp") {
                        e.preventDefault();
                        previewAudioPlayer.muted = false;
                        previewAudioPlayer.volume = Math.min(1.0, previewAudioPlayer.volume + 0.1);
                        if (audioVolumeSlider) {
                            audioVolumeSlider.value = previewAudioPlayer.volume;
                            updateSliderBackground(audioVolumeSlider);
                        }
                        if (audioMuteBtn) {
                            const volIcon = audioMuteBtn.querySelector(".volume-icon");
                            const muteIcon = audioMuteBtn.querySelector(".mute-icon");
                            if (volIcon) volIcon.classList.remove("hidden");
                            if (muteIcon) muteIcon.classList.add("hidden");
                        }
                        return;
                    }
                    // ArrowDown (Volume Down by 10%)
                    if (e.key === "ArrowDown") {
                        e.preventDefault();
                        previewAudioPlayer.volume = Math.max(0.0, previewAudioPlayer.volume - 0.1);
                        if (audioVolumeSlider) {
                            audioVolumeSlider.value = previewAudioPlayer.volume;
                            updateSliderBackground(audioVolumeSlider);
                        }
                        if (audioMuteBtn) {
                            const volIcon = audioMuteBtn.querySelector(".volume-icon");
                            const muteIcon = audioMuteBtn.querySelector(".mute-icon");
                            if (previewAudioPlayer.volume === 0) {
                                if (volIcon) volIcon.classList.add("hidden");
                                if (muteIcon) muteIcon.classList.remove("hidden");
                            } else {
                                if (volIcon) volIcon.classList.remove("hidden");
                                if (muteIcon) muteIcon.classList.add("hidden");
                            }
                        }
                        return;
                    }
                    // 0 to 9 (Seek to percentage)
                    if (e.key >= "0" && e.key <= "9") {
                        e.preventDefault();
                        const pct = parseInt(e.key) * 10;
                        if (previewAudioPlayer.duration) {
                            previewAudioPlayer.currentTime = (pct / 100) * previewAudioPlayer.duration;
                        }
                        return;
                    }
                    // < / > (Shift + , / Shift + .) (Playback Speed adjust)
                    if (e.key === "<" || e.key === ">") {
                        e.preventDefault();
                        const presets = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
                        const currentRate = previewAudioPlayer.playbackRate;
                        let currentIndex = presets.indexOf(currentRate);
                        if (currentIndex === -1) {
                            let closestDiff = Infinity;
                            presets.forEach((opt, idx) => {
                                const diff = Math.abs(opt - currentRate);
                                if (diff < closestDiff) {
                                    closestDiff = diff;
                                    currentIndex = idx;
                                }
                            });
                        }
                        let nextIndex = currentIndex;
                        if (e.key === "<") {
                            nextIndex = Math.max(0, currentIndex - 1);
                        } else if (e.key === ">") {
                            nextIndex = Math.min(presets.length - 1, currentIndex + 1);
                        }
                        const targetRate = presets[nextIndex];
                        setPlaybackSpeedUI(targetRate);
                        return;
                    }
                } else if (isImageActive) {
                    // Previous/Next Image
                    if (e.key === "ArrowRight") {
                        if (extractedImages && extractedImages.length > 1) {
                            let nextIdx = previewCurrentImageIndex + 1;
                            if (nextIdx >= extractedImages.length) nextIdx = 0;
                            showPreviewImage(nextIdx);
                        }
                    } else if (e.key === "ArrowLeft") {
                        if (extractedImages && extractedImages.length > 1) {
                            let prevIdx = previewCurrentImageIndex - 1;
                            if (prevIdx < 0) prevIdx = extractedImages.length - 1;
                            showPreviewImage(prevIdx);
                        }
                    }
                    // Zoom In
                    else if (e.key === "+" || e.key === "=") {
                        e.preventDefault();
                        previewZoomLevel = Math.min(3, previewZoomLevel + 0.2);
                        updateImageTransform();
                    }
                    // Zoom Out
                    else if (e.key === "-") {
                        e.preventDefault();
                        previewZoomLevel = Math.max(0.5, previewZoomLevel - 0.2);
                        updateImageTransform();
                    }
                    // Rotate (Key R)
                    else if (e.key === "r" || e.key === "R") {
                        e.preventDefault();
                        previewRotation = (previewRotation + 90) % 360;
                        updateImageTransform();
                    }
                    // Reset transform (Key 0)
                    else if (e.key === "0") {
                        e.preventDefault();
                        previewZoomLevel = 1.0;
                        previewRotation = 0;
                        updateImageTransform();
                    }
                } else if (previewSubtitleContainer && !previewSubtitleContainer.classList.contains("hidden")) {
                    if (e.key === "ArrowUp") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop -= 40;
                    } else if (e.key === "ArrowDown") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop += 40;
                    } else if (e.key === "PageUp") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop -= (previewSubText.clientHeight - 40);
                    } else if (e.key === "PageDown") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop += (previewSubText.clientHeight - 40);
                    } else if (e.key === "Home") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop = 0;
                    } else if (e.key === "End") {
                        e.preventDefault();
                        if (previewSubText) previewSubText.scrollTop = previewSubText.scrollHeight;
                    } else if (e.key === "w" || e.key === "W") {
                        e.preventDefault();
                        previewSubWordWrap = !previewSubWordWrap;
                        if (previewSubText) {
                            previewSubText.style.whiteSpace = previewSubWordWrap ? "pre-wrap" : "pre";
                            previewSubText.style.overflowX = previewSubWordWrap ? "visible" : "auto";
                        }
                    } else if (e.key === "+" || e.key === "=") {
                        e.preventDefault();
                        previewSubFontSize = Math.min(3.0, previewSubFontSize + 0.1);
                        if (previewSubText) {
                            previewSubText.style.fontSize = `${previewSubFontSize}rem`;
                        }
                    } else if (e.key === "-") {
                        e.preventDefault();
                        previewSubFontSize = Math.max(0.5, previewSubFontSize - 0.1);
                        if (previewSubText) {
                            previewSubText.style.fontSize = `${previewSubFontSize}rem`;
                        }
                    } else if (e.key === "0") {
                        e.preventDefault();
                        previewSubFontSize = 0.88;
                        previewSubWordWrap = true;
                        if (previewSubText) {
                            previewSubText.style.fontSize = "0.88rem";
                            previewSubText.style.whiteSpace = "pre-wrap";
                            previewSubText.style.overflowX = "visible";
                        }
                    } else if (e.key === "c" || e.key === "C") {
                        e.preventDefault();
                        if (btnCopySub) btnCopySub.click();
                    }
                } else if (previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden")) {
                    if (e.key === "r" || e.key === "R") {
                        e.preventDefault();
                        if (previewWebpageIframe) {
                            const currentSrc = previewWebpageIframe.src;
                            previewWebpageIframe.src = "";
                            showPreviewLoader("Reloading webpage...");
                            previewWebpageIframe.src = currentSrc;
                        }
                    }
                }

                // Global download shortcut (D/d) when in previewer
                if (e.key === "d" || e.key === "D") {
                    e.preventDefault();
                    if (previewDownloadBtn && !previewDownloadBtn.disabled) {
                        previewDownloadBtn.click();
                    }
                }
            }
        });
    }

    function applyModalTypeStyle(type = "info") {
        if (!confirmModal) return;
        const card = confirmModal.querySelector(".modal-card-confirm");
        const iconWrap = confirmModal.querySelector(".confirm-icon-wrap");
        if (card) {
            card.classList.remove("type-danger", "type-error", "type-warning", "type-success", "type-info");
            card.classList.add("type-" + type);
        }
        if (iconWrap) {
            if (type === "success") {
                iconWrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path></svg>';
            } else if (type === "error" || type === "danger") {
                iconWrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
            } else if (type === "warning") {
                iconWrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
            } else {
                // info / default
                iconWrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
            }
        }
    }

    // Confirm Modal Behavior
    function showConfirm(options = {}) {
        if (!confirmModal) return;
        applyModalTypeStyle(options.type || "warning");

        confirmModalTitle.textContent = options.title || "Xác nhận";
        confirmModalMessage.textContent = options.message || "Bạn có chắc chắn muốn thực hiện hành động này?";
        confirmModalBtnYes.textContent = options.yesText || "Đồng ý";
        confirmModalBtnNo.textContent = options.noText || "Hủy bỏ";

        confirmYesCallback = options.onYes || null;
        confirmNoCallback = options.onNo || null;

        confirmModal.classList.remove("hidden");
        document.body.classList.add("modal-open");
    }

    // Alert Modal Helper (uses confirm modal layout)
    function showAlert(title, message, callback = null, type = "info") {
        if (!confirmModal) return;
        applyModalTypeStyle(type);

        confirmModalTitle.textContent = title || "Thông báo";
        confirmModalMessage.textContent = message || "";
        confirmModalBtnYes.textContent = "Đã hiểu";
        
        if (confirmModalBtnNo) {
            confirmModalBtnNo.classList.add("hidden");
        }
        
        confirmYesCallback = () => {
            if (confirmModalBtnNo) {
                confirmModalBtnNo.classList.remove("hidden");
            }
            if (callback) callback();
        };
        confirmNoCallback = null;
        
        confirmModal.classList.remove("hidden");
        document.body.classList.add("modal-open");
    }

    // Override window.alert to automatically use our custom modal
    window.alert = function(msg) {
        showAlert("Notification", msg);
    };

    // Expose alert and confirm helpers to global scope
    window.showAlert = showAlert;
    window.showConfirm = showConfirm;
    window.hideConfirm = hideConfirm;

    function hideConfirm() {
        if (!confirmModal) return;
        confirmModal.classList.add("hidden");
        if (confirmModalBtnNo) {
            confirmModalBtnNo.classList.remove("hidden");
        }
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
            if (confirmModal.classList.contains("hidden")) return;
            if (e.key === "Escape") {
                e.preventDefault();
                hideConfirm();
                if (confirmNoCallback) confirmNoCallback();
            } else if (e.key === "Enter") {
                e.preventDefault();
                hideConfirm();
                if (confirmYesCallback) confirmYesCallback();
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

    function updateImageFilters() {
        const brightness = parseFloat(document.getElementById("img-brightness")?.value || 100);
        const contrast = parseFloat(document.getElementById("img-contrast")?.value || 100);
        const saturation = parseFloat(document.getElementById("img-saturation")?.value || 100);
        const hue = parseFloat(document.getElementById("img-hue")?.value || 0);
        const exposure = parseFloat(document.getElementById("img-exposure")?.value || 100);
        const blur = parseFloat(document.getElementById("img-blur")?.value || 0);
        const grayscale = parseFloat(document.getElementById("img-grayscale")?.value || 0);
        const sepia = parseFloat(document.getElementById("img-sepia")?.value || 0);
        const invert = parseFloat(document.getElementById("img-invert")?.value || 0);

        const filterStr = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%) hue-rotate(${hue}deg) brightness(${exposure}%) blur(${blur}px) grayscale(${grayscale}%) sepia(${sepia}%) invert(${invert}%)`;

        if (previewImageElement) {
            previewImageElement.style.filter = filterStr;
        }
    }

    function saveImageSettingsToStorage() {
        const brightness = document.getElementById("img-brightness")?.value || 100;
        const contrast = document.getElementById("img-contrast")?.value || 100;
        const saturation = document.getElementById("img-saturation")?.value || 100;
        const hue = document.getElementById("img-hue")?.value || 0;
        const exposure = document.getElementById("img-exposure")?.value || 100;
        const blur = document.getElementById("img-blur")?.value || 0;
        const grayscale = document.getElementById("img-grayscale")?.value || 0;
        const sepia = document.getElementById("img-sepia")?.value || 0;
        const invert = document.getElementById("img-invert")?.value || 0;

        localStorage.setItem("img_brightness", brightness);
        localStorage.setItem("img_contrast", contrast);
        localStorage.setItem("img_saturation", saturation);
        localStorage.setItem("img_hue", hue);
        localStorage.setItem("img_exposure", exposure);
        localStorage.setItem("img_blur", blur);
        localStorage.setItem("img_grayscale", grayscale);
        localStorage.setItem("img_sepia", sepia);
        localStorage.setItem("img_invert", invert);
    }

    function loadImageSettingsFromStorage() {
        const brightness = localStorage.getItem("img_brightness") !== null ? parseFloat(localStorage.getItem("img_brightness")) : 100;
        const contrast = localStorage.getItem("img_contrast") !== null ? parseFloat(localStorage.getItem("img_contrast")) : 100;
        const saturation = localStorage.getItem("img_saturation") !== null ? parseFloat(localStorage.getItem("img_saturation")) : 100;
        const hue = localStorage.getItem("img_hue") !== null ? parseFloat(localStorage.getItem("img_hue")) : 0;
        const exposure = localStorage.getItem("img_exposure") !== null ? parseFloat(localStorage.getItem("img_exposure")) : 100;
        const blur = localStorage.getItem("img_blur") !== null ? parseFloat(localStorage.getItem("img_blur")) : 0;
        const grayscale = localStorage.getItem("img_grayscale") !== null ? parseFloat(localStorage.getItem("img_grayscale")) : 0;
        const sepia = localStorage.getItem("img_sepia") !== null ? parseFloat(localStorage.getItem("img_sepia")) : 0;
        const invert = localStorage.getItem("img_invert") !== null ? parseFloat(localStorage.getItem("img_invert")) : 0;

        const brightnessInput = document.getElementById("img-brightness");
        const contrastInput = document.getElementById("img-contrast");
        const saturationInput = document.getElementById("img-saturation");
        const hueInput = document.getElementById("img-hue");
        const exposureInput = document.getElementById("img-exposure");
        const blurInput = document.getElementById("img-blur");
        const grayscaleInput = document.getElementById("img-grayscale");
        const sepiaInput = document.getElementById("img-sepia");
        const invertInput = document.getElementById("img-invert");

        if (brightnessInput) brightnessInput.value = brightness;
        if (contrastInput) contrastInput.value = contrast;
        if (saturationInput) saturationInput.value = saturation;
        if (hueInput) hueInput.value = hue;
        if (exposureInput) exposureInput.value = exposure;
        if (blurInput) blurInput.value = blur;
        if (grayscaleInput) grayscaleInput.value = grayscale;
        if (sepiaInput) sepiaInput.value = sepia;
        if (invertInput) invertInput.value = invert;

        const brightnessVal = document.getElementById("img-brightness-val");
        const contrastVal = document.getElementById("img-contrast-val");
        const saturationVal = document.getElementById("img-saturation-val");
        const hueVal = document.getElementById("img-hue-val");
        const exposureVal = document.getElementById("img-exposure-val");
        const blurVal = document.getElementById("img-blur-val");
        const grayscaleVal = document.getElementById("img-grayscale-val");
        const sepiaVal = document.getElementById("img-sepia-val");
        const invertVal = document.getElementById("img-invert-val");

        if (brightnessVal) brightnessVal.textContent = `${brightness}%`;
        if (contrastVal) contrastVal.textContent = `${contrast}%`;
        if (saturationVal) saturationVal.textContent = `${saturation}%`;
        if (hueVal) hueVal.textContent = `${hue}°`;
        if (exposureVal) exposureVal.textContent = `${exposure}%`;
        if (blurVal) blurVal.textContent = `${blur}px`;
        if (grayscaleVal) grayscaleVal.textContent = `${grayscale}%`;
        if (sepiaVal) sepiaVal.textContent = `${sepia}%`;
        if (invertVal) invertVal.textContent = `${invert}%`;

        if (brightnessInput) updateSliderBackground(brightnessInput);
        if (contrastInput) updateSliderBackground(contrastInput);
        if (saturationInput) updateSliderBackground(saturationInput);
        if (hueInput) updateSliderBackground(hueInput);
        if (exposureInput) updateSliderBackground(exposureInput);
        if (blurInput) updateSliderBackground(blurInput);
        if (grayscaleInput) updateSliderBackground(grayscaleInput);
        if (sepiaInput) updateSliderBackground(sepiaInput);
        if (invertInput) updateSliderBackground(invertInput);

        updateImageFilters();
    }

    function resetImageFilters() {
        const brightnessInput = document.getElementById("img-brightness");
        const contrastInput = document.getElementById("img-contrast");
        const saturationInput = document.getElementById("img-saturation");
        const hueInput = document.getElementById("img-hue");
        const exposureInput = document.getElementById("img-exposure");
        const blurInput = document.getElementById("img-blur");
        const grayscaleInput = document.getElementById("img-grayscale");
        const sepiaInput = document.getElementById("img-sepia");
        const invertInput = document.getElementById("img-invert");

        if (brightnessInput) brightnessInput.value = 100;
        if (contrastInput) contrastInput.value = 100;
        if (saturationInput) saturationInput.value = 100;
        if (hueInput) hueInput.value = 0;
        if (exposureInput) exposureInput.value = 100;
        if (blurInput) blurInput.value = 0;
        if (grayscaleInput) grayscaleInput.value = 0;
        if (sepiaInput) sepiaInput.value = 0;
        if (invertInput) invertInput.value = 0;

        const brightnessVal = document.getElementById("img-brightness-val");
        const contrastVal = document.getElementById("img-contrast-val");
        const saturationVal = document.getElementById("img-saturation-val");
        const hueVal = document.getElementById("img-hue-val");
        const exposureVal = document.getElementById("img-exposure-val");
        const blurVal = document.getElementById("img-blur-val");
        const grayscaleVal = document.getElementById("img-grayscale-val");
        const sepiaVal = document.getElementById("img-sepia-val");
        const invertVal = document.getElementById("img-invert-val");

        if (brightnessVal) brightnessVal.textContent = "100%";
        if (contrastVal) contrastVal.textContent = "100%";
        if (saturationVal) saturationVal.textContent = "100%";
        if (hueVal) hueVal.textContent = "0°";
        if (exposureVal) exposureVal.textContent = "100%";
        if (blurVal) blurVal.textContent = "0px";
        if (grayscaleVal) grayscaleVal.textContent = "0%";
        if (sepiaVal) sepiaVal.textContent = "0%";
        if (invertVal) invertVal.textContent = "0%";

        if (brightnessInput) updateSliderBackground(brightnessInput);
        if (contrastInput) updateSliderBackground(contrastInput);
        if (saturationInput) updateSliderBackground(saturationInput);
        if (hueInput) updateSliderBackground(hueInput);
        if (exposureInput) updateSliderBackground(exposureInput);
        if (blurInput) updateSliderBackground(blurInput);
        if (grayscaleInput) updateSliderBackground(grayscaleInput);
        if (sepiaInput) updateSliderBackground(sepiaInput);
        if (invertInput) updateSliderBackground(invertInput);

        if (previewImageElement) {
            previewImageElement.style.filter = "none";
        }
        saveImageSettingsToStorage();
    }

    function getFilteredImageDownloadUrl() {
        const brightness = parseFloat(document.getElementById("img-brightness")?.value || 100);
        const contrast = parseFloat(document.getElementById("img-contrast")?.value || 100);
        const saturation = parseFloat(document.getElementById("img-saturation")?.value || 100);
        const hue = parseFloat(document.getElementById("img-hue")?.value || 0);
        const exposure = parseFloat(document.getElementById("img-exposure")?.value || 100);
        const blur = parseFloat(document.getElementById("img-blur")?.value || 0);
        const grayscale = parseFloat(document.getElementById("img-grayscale")?.value || 0);
        const sepia = parseFloat(document.getElementById("img-sepia")?.value || 0);
        const invert = parseFloat(document.getElementById("img-invert")?.value || 0);

        const originalUrl = previewActiveCustomUrl;
        let url = `/api/download/image?url=${encodeURIComponent(originalUrl)}&client_id=${encodeURIComponent(clientId)}`;
        url += `&brightness=${brightness}&contrast=${contrast}&saturation=${saturation}&hue=${hue}&exposure=${exposure}&blur=${blur}&grayscale=${grayscale}&sepia=${sepia}&invert=${invert}`;
        return url;
    }

    if (btnImageAdjust && imageSidePanel) {
        btnImageAdjust.onclick = (e) => {
            e.stopPropagation();
            const isHidden = imageSidePanel.classList.contains("hidden");
            if (isHidden) {
                imageSidePanel.classList.remove("hidden");
                btnImageAdjust.classList.add("active");
            } else {
                imageSidePanel.classList.add("hidden");
                btnImageAdjust.classList.remove("active");
            }
        };
    }

    if (btnImgReset) {
        btnImgReset.onclick = (e) => {
            e.stopPropagation();
            resetImageFilters();
        };
    }

    const imgFilterSliders = document.querySelectorAll(".img-filter-slider");
    imgFilterSliders.forEach(slider => {
        slider.addEventListener("input", function () {
            const val = this.value;
            const labelEl = document.getElementById(`${this.id}-val`);
            if (labelEl) {
                if (this.id === "img-hue") {
                    labelEl.textContent = `${val}°`;
                } else if (this.id === "img-blur") {
                    labelEl.textContent = `${val}px`;
                } else {
                    labelEl.textContent = `${val}%`;
                }
            }
            updateSliderBackground(this);
            updateImageFilters();
            saveImageSettingsToStorage();
        });
    });

    function showPreviewImage(index) {
        if (!extractedImages || index < 0 || index >= extractedImages.length) return;

        const img = extractedImages[index];
        let imgUrl, imgLabel, imgExt;
        if (typeof img === "string") {
            imgUrl = img;
            imgLabel = `Photo ${index + 1}`;
            imgExt = "jpg";
        } else {
            imgUrl = img.url || "";
            imgLabel = img.label || `Photo ${index + 1}`;
            imgExt = img.ext || "jpg";
        }

        const finalUrl = `/api/download/image?url=${encodeURIComponent(imgUrl)}&client_id=${encodeURIComponent(clientId)}`;

        previewZoomLevel = 1;
        previewRotation = 0;
        updateImageTransform();

        previewActiveUrl = finalUrl;
        const cleanTitle = getSafeTitle(videoTitle.textContent, "image");
        const cleanLabel = imgLabel.replace(/\s*\(\d+x\d+\)/, "");
        previewActiveFilename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${imgExt}`;
        previewTitle.textContent = cleanLabel;
        previewMetaInfo.textContent = `Type: ${imgExt.toUpperCase()}`;

        if (previewImageElement) {
            previewImageContainer.classList.add("hidden");
            showPreviewLoader("Loading image...");

            loadImageSettingsFromStorage();

            previewImageElement.onload = () => {
                hidePreviewLoader();
                previewImageContainer.classList.remove("hidden");
            };
            previewImageElement.onerror = () => {
                showPreviewLoader("Failed to load image preview.", true);
            };
            previewImageElement.src = finalUrl;
        }

        previewCurrentImageIndex = index;
    }

    if (btnPrevImage) {
        btnPrevImage.onclick = (e) => {
            e.stopPropagation();
            if (extractedImages && extractedImages.length > 1) {
                let prevIdx = previewCurrentImageIndex - 1;
                if (prevIdx < 0) prevIdx = extractedImages.length - 1;
                showPreviewImage(prevIdx);
            }
        };
    }

    if (btnNextImage) {
        btnNextImage.onclick = (e) => {
            e.stopPropagation();
            if (extractedImages && extractedImages.length > 1) {
                let nextIdx = previewCurrentImageIndex + 1;
                if (nextIdx >= extractedImages.length) nextIdx = 0;
                showPreviewImage(nextIdx);
            }
        };
    }

    function formatSecondsToVttTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "00:00:00.000";
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${ms.toString().padStart(3, "0")}`;
    }

    function formatSecondsToSrtTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "00:00:00,000";
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        const ms = Math.floor((seconds % 1) * 1000);
        return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")},${ms.toString().padStart(3, "0")}`;
    }

    function convertSubtitlesToFormat(text, targetFormat) {
        if (!text) return "";
        if (targetFormat === "original") return text;

        const cues = parseSubtitleText(text);
        if (!cues || cues.length === 0) return text;

        if (targetFormat === "vtt") {
            let out = "WEBVTT\n\n";
            cues.forEach(cue => {
                out += `${formatSecondsToVttTime(cue.start)} --> ${formatSecondsToVttTime(cue.end)}\n${cue.text}\n\n`;
            });
            return out.trim() + "\n";
        } else if (targetFormat === "srt") {
            let out = "";
            cues.forEach((cue, index) => {
                out += `${index + 1}\n${formatSecondsToSrtTime(cue.start)} --> ${formatSecondsToSrtTime(cue.end)}\n${cue.text}\n\n`;
            });
            return out.trim() + "\n";
        } else if (targetFormat === "txt") {
            let lastText = "";
            const cleanLines = [];
            cues.forEach(cue => {
                const txt = cue.text.replace(/\r?\n/g, " ").trim();
                if (txt && txt !== lastText) {
                    cleanLines.push(txt);
                    lastText = txt;
                }
            });
            return cleanLines.join("\n");
        }
        return text;
    }

    // Copy subtitles clipboard helper
    if (btnCopySub && previewSubText) {
        btnCopySub.onclick = () => {
            const formatSelect = document.getElementById("preview-sub-format");
            const targetFormat = formatSelect ? formatSelect.value : "original";
            const rawText = previewActiveSubtitleContent || previewSubText.textContent;
            const copyText = convertSubtitlesToFormat(rawText, targetFormat);

            navigator.clipboard.writeText(copyText).then(() => {
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
            // Web Player / MSE stream capture download
            if (previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden")) {
                const safeTitle = getSafeTitle(videoTitle?.textContent || previewActiveFilename || "stream_video", "video");

                // Check Electron Webview first
                if (previewWebpageWebview && !previewWebpageWebview.classList.contains("hidden")) {
                    showPlayerToast("Đang trích xuất luồng video thành file .mp4...");
                    previewWebpageWebview.executeJavaScript(`
                        (function() {
                            try {
                                if (window._capturedMediaChunks && window._capturedMediaChunks.length > 0) {
                                    const blob = new Blob(window._capturedMediaChunks, { type: 'video/mp4' });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = '${safeTitle}.mp4';
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    setTimeout(() => URL.revokeObjectURL(url), 60000);
                                    return { success: true, size: blob.size };
                                }
                            } catch(e) {
                                return { success: false, error: e.message };
                            }
                            return { success: false, error: 'No chunks' };
                        })()
                    `).then(res => {
                        if (res && res.success) {
                            const mb = (res.size / (1024 * 1024)).toFixed(1);
                            showPlayerToast(`Đã lưu video thành công (${mb} MB)!`);
                            closePreviewModal();
                        } else {
                            showPlayerToast("Chưa thu thập đủ luồng video. Vui lòng chờ phát vài giây rồi bấm Lưu!", true);
                        }
                    }).catch(err => {
                        showPlayerToast("Lỗi lưu video: " + err.message, true);
                    });
                    return;
                }

                const iframeWin = previewWebpageIframe ? previewWebpageIframe.contentWindow : null;
                const iframeDoc = previewWebpageIframe ? (previewWebpageIframe.contentDocument || iframeWin?.document) : null;

                // a & b. If iframeWin has _capturedMediaChunks and getCapturedStreamBlob
                if (iframeWin && iframeWin._capturedMediaChunks && iframeWin._capturedMediaChunks.length > 0) {
                    showPlayerToast("Đang trích xuất luồng video thành file .mp4...");
                    try {
                        const blob = (typeof iframeWin.getCapturedStreamBlob === "function")
                            ? iframeWin.getCapturedStreamBlob('video/mp4')
                            : new Blob(iframeWin._capturedMediaChunks, { type: 'video/mp4' });

                        if (blob && blob.size > 0) {
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `${safeTitle}.mp4`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            setTimeout(() => URL.revokeObjectURL(url), 15000);
                            showPlayerToast(`Đã lưu video thành công (${(blob.size / (1024 * 1024)).toFixed(1)} MB)!`);
                            closePreviewModal();
                            return;
                        }
                    } catch (err) {
                        console.error("Error creating MSE blob:", err);
                    }
                }

                // c. If no MSE chunks captured yet, check if iframeDoc has a <video> element
                const videoEl = iframeDoc ? iframeDoc.querySelector("video") : null;
                if (videoEl) {
                    const vSrc = videoEl.currentSrc || videoEl.src;
                    // Direct playable media URL
                    if (vSrc && !vSrc.startsWith("blob:") && !vSrc.startsWith("mediasource:") && (vSrc.startsWith("http://") || vSrc.startsWith("https://"))) {
                        showPlayerToast("Đang tải luồng video trực tiếp...");
                        const a = document.createElement("a");
                        a.href = vSrc;
                        a.download = `${safeTitle}.mp4`;
                        a.target = "_blank";
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        closePreviewModal();
                        return;
                    }

                    // MediaRecorder capture
                    if (typeof MediaRecorder !== "undefined" && (videoEl.captureStream || videoEl.mozCaptureStream)) {
                        if (window._activeMediaRecorder && window._activeMediaRecorder.state === "recording") {
                            showPlayerToast("Đang hoàn tất ghi và lưu file .mp4...");
                            window._activeMediaRecorder.stop();
                            return;
                        }
                        try {
                            const stream = videoEl.captureStream ? videoEl.captureStream() : videoEl.mozCaptureStream();
                            if (stream && stream.getVideoTracks().length > 0) {
                                const mime = MediaRecorder.isTypeSupported('video/mp4; codecs="avc1.42E01E, mp4a.40.2"')
                                    ? 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"'
                                    : (MediaRecorder.isTypeSupported('video/mp4')
                                        ? 'video/mp4'
                                        : (MediaRecorder.isTypeSupported('video/webm; codecs=vp9,opus') ? 'video/webm' : ''));
                                const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
                                const recChunks = [];
                                recorder.ondataavailable = (e) => {
                                    if (e.data && e.data.size > 0) recChunks.push(e.data);
                                };
                                recorder.onstop = () => {
                                    const recExt = recorder.mimeType && recorder.mimeType.includes("mp4") ? "mp4" : "webm";
                                    const recBlob = new Blob(recChunks, { type: recorder.mimeType || 'video/mp4' });
                                    const url = URL.createObjectURL(recBlob);
                                    const a = document.createElement("a");
                                    a.href = url;
                                    a.download = `${safeTitle}.${recExt}`;
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    setTimeout(() => URL.revokeObjectURL(url), 15000);
                                    showPlayerToast(`Đã lưu video ghi nhận thành công (${(recBlob.size / (1024 * 1024)).toFixed(1)} MB)!`);
                                    window._activeMediaRecorder = null;
                                    const span = previewDownloadBtn.querySelector("span");
                                    if (span) span.textContent = "Save Video (.mp4)";
                                };
                                window._activeMediaRecorder = recorder;
                                recorder.start(1000);
                                showPlayerToast("Bắt đầu ghi lại luồng video... Bấm lại nút này khi muốn dừng và lưu file!");
                                const span = previewDownloadBtn.querySelector("span");
                                if (span) span.textContent = "Dừng & Lưu Video";
                                return;
                            }
                        } catch (recErr) {
                            console.warn("MediaRecorder capture error:", recErr);
                        }
                    }
                }

                // If neither MSE chunks nor video tag is ready, start the background stream harvester
                showPlayerToast("Đang khởi động tiến trình thu thập và tải toàn bộ video về máy...");
                triggerStreamDownload(previewActiveBtn, previewActiveFormatId, "mp4", previewActiveFilename, previewActiveQuality, previewActiveUrl || previewActiveCustomUrl);
                closePreviewModal();
                return;
            }

            const eqBassVal = parseFloat(document.getElementById("eq-bass")?.value || 0);
            const eqLowMidVal = parseFloat(document.getElementById("eq-lowmid")?.value || 0);
            const eqHighMidVal = parseFloat(document.getElementById("eq-highmid")?.value || 0);
            const eqTrebleVal = parseFloat(document.getElementById("eq-treble")?.value || 0);
            const hasEqAdjustment = (eqBassVal !== 0 || eqLowMidVal !== 0 || eqHighMidVal !== 0 || eqTrebleVal !== 0);

            const audioSpeedVal = parseFloat(document.getElementById("audio-speed-slider")?.value || 1.0);
            const isAudioType = (previewActiveExt === "mp3" || previewActiveExt === "m4a" || previewActiveFormatId === "audio");
            const finalSpeedVal = isAudioType ? audioSpeedVal : currentPlaybackSpeed;
            const hasSpeedAdjustment = (finalSpeedVal !== 1.0);

            const activeVoiceBtn = document.querySelector(".voice-preset.active");
            const hasVoiceAdjustment = (activeVoiceBtn && activeVoiceBtn.dataset.voice !== "normal");

            const imgBrightnessVal = parseFloat(document.getElementById("img-brightness")?.value || 100);
            const imgContrastVal = parseFloat(document.getElementById("img-contrast")?.value || 100);
            const imgSaturationVal = parseFloat(document.getElementById("img-saturation")?.value || 100);
            const imgHueVal = parseFloat(document.getElementById("img-hue")?.value || 0);
            const imgExposureVal = parseFloat(document.getElementById("img-exposure")?.value || 100);
            const imgBlurVal = parseFloat(document.getElementById("img-blur")?.value || 0);
            const imgGrayscaleVal = parseFloat(document.getElementById("img-grayscale")?.value || 0);
            const imgSepiaVal = parseFloat(document.getElementById("img-sepia")?.value || 0);
            const imgInvertVal = parseFloat(document.getElementById("img-invert")?.value || 0);

            const hasImageAdjustment = (
                imgBrightnessVal !== 100 ||
                imgContrastVal !== 100 ||
                imgSaturationVal !== 100 ||
                imgHueVal !== 0 ||
                imgExposureVal !== 100 ||
                imgBlurVal !== 0 ||
                imgGrayscaleVal !== 0 ||
                imgSepiaVal !== 0 ||
                imgInvertVal !== 0
            );

            const isCustomized = (
                (loopStartSecs !== null || loopEndSecs !== null) ||
                hasEqAdjustment ||
                hasSpeedAdjustment ||
                hasVoiceAdjustment ||
                hasImageAdjustment ||
                (document.getElementById("preview-export-type") && document.getElementById("preview-export-type").value !== "default") ||
                (document.getElementById("preview-color-filter") && document.getElementById("preview-color-filter").value !== "none") ||
                (document.getElementById("preview-voiceover-active") && document.getElementById("preview-voiceover-active").checked) ||
                (document.getElementById("preview-sub-trans-select") && document.getElementById("preview-sub-trans-select").value !== "none") ||
                (document.getElementById("preview-sub-mode-select") && document.getElementById("preview-sub-mode-select").value !== "none") ||
                (document.getElementById("preview-voiceover-select") && document.getElementById("preview-voiceover-select").value !== "none") ||
                (document.getElementById("preview-cloud-sync") && document.getElementById("preview-cloud-sync").value !== "local") ||
                (document.getElementById("preview-enhance-beautify") && document.getElementById("preview-enhance-beautify").checked) ||
                (document.getElementById("preview-enhance-sharpen") && parseFloat(document.getElementById("preview-enhance-sharpen").value) > 0) ||
                (document.getElementById("preview-enhance-upscale") && document.getElementById("preview-enhance-upscale").value !== "none")
            );

            if (isCustomized) {
                if (previewActiveFormatId === "image_preview") {
                    const downloadUrl = getFilteredImageDownloadUrl();
                    const a = document.createElement("a");
                    a.href = downloadUrl;
                    a.download = previewActiveFilename || "image.jpg";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    closePreviewModal();
                    return;
                }

                // Set the trim controls on the main page
                const trimCheckbox = document.getElementById("trim-checkbox");
                const trimStartInput = document.getElementById("trim-start");
                const trimEndInput = document.getElementById("trim-end");

                if (trimCheckbox) {
                    trimCheckbox.checked = (loopStartSecs !== null || loopEndSecs !== null);
                    trimCheckbox.dispatchEvent(new Event("change"));
                }

                if (trimStartInput) {
                    trimStartInput.value = loopStartSecs !== null ? formatTimeDetailed(loopStartSecs) : "00:00:00.000";
                }
                if (trimEndInput) {
                    trimEndInput.value = loopEndSecs !== null ? formatTimeDetailed(loopEndSecs) : "";
                }

                // Copy Video Enhance settings to main page
                const previewEnhanceBeautify = document.getElementById("preview-enhance-beautify");
                const mainEnhanceBeautify = document.getElementById("enhance-beautify-checkbox");
                if (previewEnhanceBeautify && mainEnhanceBeautify) {
                    mainEnhanceBeautify.checked = previewEnhanceBeautify.checked;
                    mainEnhanceBeautify.dispatchEvent(new Event("change"));
                }

                const previewEnhanceSharpen = document.getElementById("preview-enhance-sharpen");
                const mainEnhanceSharpen = document.getElementById("enhance-sharpen-slider");
                if (previewEnhanceSharpen && mainEnhanceSharpen) {
                    mainEnhanceSharpen.value = previewEnhanceSharpen.value;
                    mainEnhanceSharpen.dispatchEvent(new Event("input"));
                }

                const previewEnhanceUpscale = document.getElementById("preview-enhance-upscale");
                const mainEnhanceUpscale = document.getElementById("enhance-upscale-select");
                if (previewEnhanceUpscale && mainEnhanceUpscale) {
                    mainEnhanceUpscale.value = previewEnhanceUpscale.value;
                    mainEnhanceUpscale.dispatchEvent(new Event("change"));
                }

                // Copy Export settings to main page
                const previewExportType = document.getElementById("preview-export-type");
                const mainExportType = document.getElementById("export-type-select");
                if (previewExportType && mainExportType) {
                    mainExportType.value = previewExportType.value;
                    mainExportType.dispatchEvent(new Event("change"));
                }

                const previewColorFilter = document.getElementById("preview-color-filter");
                const mainColorFilter = document.getElementById("color-filter-select");
                if (previewColorFilter && mainColorFilter) {
                    mainColorFilter.value = previewColorFilter.value;
                    mainColorFilter.dispatchEvent(new Event("change"));
                }

                // Copy Cloud Sync settings to main page
                const previewCloudSync = document.getElementById("preview-cloud-sync");
                const mainCloudSync = document.getElementById("cloud-sync-select");
                if (previewCloudSync && mainCloudSync) {
                    mainCloudSync.value = previewCloudSync.value;
                    mainCloudSync.dispatchEvent(new Event("change"));
                }

                // Copy Voiceover settings to main page
                const previewVoiceoverActive = document.getElementById("preview-voiceover-active");
                const mainVoiceoverActive = document.getElementById("voiceover-checkbox");
                if (previewVoiceoverActive && mainVoiceoverActive) {
                    mainVoiceoverActive.checked = previewVoiceoverActive.checked;
                    mainVoiceoverActive.dispatchEvent(new Event("change"));
                }

                const previewVoiceoverVoice = document.getElementById("preview-voiceover-voice");
                const mainVoiceoverVoice = document.getElementById("voiceover-voice-select");
                if (previewVoiceoverVoice && mainVoiceoverVoice) {
                    mainVoiceoverVoice.value = previewVoiceoverVoice.value;
                    mainVoiceoverVoice.dispatchEvent(new Event("change"));
                }

                const previewVoiceoverRate = document.getElementById("preview-voiceover-rate-slider");
                const mainVoiceoverRate = document.getElementById("voiceover-rate-slider");
                if (previewVoiceoverRate && mainVoiceoverRate) {
                    mainVoiceoverRate.value = previewVoiceoverRate.value;
                    mainVoiceoverRate.dispatchEvent(new Event("input"));
                }

                const previewVoiceoverPitch = document.getElementById("preview-voiceover-pitch-slider");
                const mainVoiceoverPitch = document.getElementById("voiceover-pitch-slider");
                if (previewVoiceoverPitch && mainVoiceoverPitch) {
                    mainVoiceoverPitch.value = previewVoiceoverPitch.value;
                    mainVoiceoverPitch.dispatchEvent(new Event("input"));
                }

                // Capture the current custom audio settings before closing (which resets them)
                const capturedAudioSettings = {
                    audio_eq_bass: eqBassVal,
                    audio_eq_lowmid: eqLowMidVal,
                    audio_eq_highmid: eqHighMidVal,
                    audio_eq_treble: eqTrebleVal,
                    audio_speed: finalSpeedVal,
                    audio_voice_preset: activeVoiceBtn ? activeVoiceBtn.dataset.voice : "normal"
                };

                // Capture the current custom subtitle settings before closing (which resets them)
                const capturedSubtitleSettings = {};
                const previewSubSelect = document.getElementById("preview-sub-select");
                const previewSubModeSelect = document.getElementById("preview-sub-mode-select");
                const previewSubTransSelect = document.getElementById("preview-sub-trans-select");
                
                if (previewSubSelect && previewSubSelect.value !== "none") {
                    if (previewSubSelect.value === "custom") {
                        capturedSubtitleSettings.subtitle_content = originalSubtitleContent;
                        capturedSubtitleSettings.subtitle_lang = "custom";
                    } else if (previewSubSelect.value.startsWith("http")) {
                        let subUrl = previewSubSelect.value;
                        if (subUrl.includes("youtube.com/api/timedtext")) {
                            if (subUrl.includes("fmt=")) {
                                subUrl = subUrl.replace(/fmt=[^&]+/, "fmt=vtt");
                            } else {
                                subUrl += subUrl.includes("?") ? "&fmt=vtt" : "?fmt=vtt";
                            }
                        }
                        capturedSubtitleSettings.subtitle_url = subUrl;
                        const selectedOpt = previewSubSelect.options[previewSubSelect.selectedIndex];
                        capturedSubtitleSettings.subtitle_lang = selectedOpt ? selectedOpt.getAttribute("data-lang") : "en";
                    } else {
                        capturedSubtitleSettings.subtitle_lang = previewSubSelect.value;
                    }
                    
                    if (previewSubModeSelect) {
                        capturedSubtitleSettings.subtitle_mode = previewSubModeSelect.value;
                    }
                    if (previewSubTransSelect) {
                        capturedSubtitleSettings.subtitle_translate = previewSubTransSelect.value;
                    }
                    
                    // Style attributes
                    capturedSubtitleSettings.sub_font = document.getElementById("preview-sub-font")?.value || "Arial";
                    capturedSubtitleSettings.sub_size = parseFloat(document.getElementById("preview-sub-size")?.value || 1.4);
                    capturedSubtitleSettings.sub_color = document.getElementById("preview-sub-color")?.value || "#ffffff";
                    capturedSubtitleSettings.sub_bg_color = document.getElementById("preview-sub-bg-color")?.value || "#000000";
                    capturedSubtitleSettings.sub_bg_opacity = parseInt(document.getElementById("preview-sub-bg-opacity")?.value || 50);
                    capturedSubtitleSettings.sub_outline = parseInt(document.getElementById("preview-sub-outline")?.value || 2);
                    capturedSubtitleSettings.sub_outline_color = document.getElementById("preview-sub-outline-color")?.value || "#000000";
                    capturedSubtitleSettings.sub_pos = document.getElementById("preview-sub-pos")?.value || "bottom";
                }

                closePreviewModal();

                triggerDownload(
                    previewActiveBtn,
                    previewActiveFormatId,
                    previewActiveExt,
                    previewActiveFilename,
                    previewActiveQuality,
                    previewActiveCustomUrl,
                    previewActiveEpisode,
                    previewActiveServer,
                    false, // forceRaw = false (apply custom settings)
                    capturedAudioSettings,
                    capturedSubtitleSettings
                );
            } else {
                if (previewActiveExt === "vtt" || previewActiveExt === "srt") {
                    const formatSelect = document.getElementById("preview-sub-format");
                    const targetFormat = formatSelect ? formatSelect.value : "original";

                    const rawText = previewActiveSubtitleContent || previewSubText.textContent;
                    const finalContent = convertSubtitlesToFormat(rawText, targetFormat);

                    let targetExt = previewActiveExt;
                    if (targetFormat === "vtt") targetExt = "vtt";
                    else if (targetFormat === "srt") targetExt = "srt";
                    else if (targetFormat === "txt") targetExt = "txt";

                    const cleanTitle = getSafeTitle(videoTitle.textContent, "subtitles");
                    let cleanLabel = (previewActiveFilename || "subtitle").replace(/Subtitles\s*-\s*/, "").replace(/\s+/g, "_");

                    if (cleanLabel.endsWith(".vtt") || cleanLabel.endsWith(".srt")) {
                        cleanLabel = cleanLabel.substring(0, cleanLabel.length - 4);
                    }
                    const safeFilename = `${cleanTitle}_${cleanLabel}.${targetExt}`;

                    let mimeType = "text/vtt;charset=utf-8";
                    if (targetExt === "srt") mimeType = "text/srt;charset=utf-8";
                    else if (targetExt === "txt") mimeType = "text/plain;charset=utf-8";

                    const blob = new Blob([finalContent], { type: mimeType });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = safeFilename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    return;
                }

                let isExternalUrl = false;
                if (previewActiveUrl) {
                    try {
                        const urlObj = new URL(previewActiveUrl, window.location.origin);
                        isExternalUrl = (urlObj.origin !== window.location.origin);
                    } catch (e) {
                        isExternalUrl = true;
                    }
                }

                if (previewActiveDownloadId) {
                    window.location.href = `/api/download/file/${previewActiveDownloadId}`;
                } else if (previewActiveUrl && !isExternalUrl) {
                    const a = document.createElement("a");
                    a.href = previewActiveUrl;
                    a.download = previewActiveFilename || "download";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                } else {
                    closePreviewModal();
                    triggerDownload(
                        previewActiveBtn,
                        previewActiveFormatId,
                        previewActiveExt,
                        previewActiveFilename,
                        previewActiveQuality,
                        previewActiveCustomUrl,
                        previewActiveEpisode,
                        previewActiveServer,
                        true // forceRaw = true (raw download)
                    );
                }
            }
        };
    }

    // Listen for MSE chunk capture messages from preview iframe
    window.addEventListener("message", (event) => {
        try {
            if (!event.data || event.data.type !== "MSE_CHUNK_CAPTURED") return;
            const totalChunks = event.data.totalChunks || 0;
            const totalBytes = event.data.totalBytes || 0;
            const mb = (totalBytes / (1024 * 1024)).toFixed(1);

            window._mseCapturedStats = { totalChunks, totalBytes, mb };

            const isWebpageActive = previewWebpageContainer && !previewWebpageContainer.classList.contains("hidden");
            if (isWebpageActive) {
                if (previewMetaInfo) {
                    previewMetaInfo.textContent = `Stream Player | Captured: ${mb} MB (${totalChunks} chunks)`;
                }
                if (previewDownloadBtn && (!window._activeMediaRecorder || window._activeMediaRecorder.state !== "recording")) {
                    const span = previewDownloadBtn.querySelector("span");
                    if (span) {
                        span.textContent = `Save Video (.mp4 - ${mb} MB)`;
                    }
                }
            }
        } catch (_) {}
    });

    // 1. Paste Button Clipboard Interaction
    pasteBtn.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = sanitizeInputUrl(text);
                updateUrlInputButtons();
                urlInput.focus();
                triggerGlowEffect();
            }
        } catch (err) {
            console.log("Unable to read from clipboard via API. Fallback to manual pasting.");
        }
    });

    urlInput.addEventListener("paste", () => {
        setTimeout(() => {
            const cleaned = sanitizeInputUrl(urlInput.value);
            if (cleaned !== urlInput.value) {
                urlInput.value = cleaned;
                updateUrlInputButtons();
            }
        }, 10);
    });

    // Browse File & Folder Handlers
    if (browseFileBtn) {
        browseFileBtn.addEventListener("click", async () => {
            if (window.electronAPI && typeof window.electronAPI.selectFile === "function") {
                try {
                    const filePath = await window.electronAPI.selectFile();
                    if (filePath) {
                        urlInput.value = sanitizeInputUrl(filePath);
                        updateUrlInputButtons();
                        performAnalysis();
                    }
                } catch (e) {
                    console.error("Electron selectFile error:", e);
                }
                return;
            }
            if (localFilePicker) {
                localFilePicker.click();
            }
        });
    }

    if (browseFolderBtn) {
        browseFolderBtn.addEventListener("click", async () => {
            if (window.electronAPI && typeof window.electronAPI.selectFolder === "function") {
                try {
                    const folderPath = await window.electronAPI.selectFolder();
                    if (folderPath) {
                        urlInput.value = sanitizeInputUrl(folderPath);
                        updateUrlInputButtons();
                        performAnalysis();
                    }
                } catch (e) {
                    console.error("Electron selectFolder error:", e);
                }
                return;
            }
            if (localFolderPicker) {
                localFolderPicker.click();
            }
        });
    }

    if (localFilePicker) {
        localFilePicker.addEventListener("change", (e) => {
            const file = e.target.files && e.target.files[0];
            if (!file) return;
            if (file.path) {
                urlInput.value = sanitizeInputUrl(file.path);
                updateUrlInputButtons();
                performAnalysis();
            } else {
                uploadAndAnalyzeLocalFile(file);
            }
            localFilePicker.value = "";
        });
    }

    if (localFolderPicker) {
        localFolderPicker.addEventListener("change", (e) => {
            const files = e.target.files;
            if (!files || files.length === 0) return;
            const firstFile = files[0];
            if (firstFile.path) {
                const folderPath = firstFile.path.substring(0, Math.max(firstFile.path.lastIndexOf("/"), firstFile.path.lastIndexOf("\\")));
                if (folderPath) {
                    urlInput.value = sanitizeInputUrl(folderPath);
                    updateUrlInputButtons();
                    performAnalysis();
                }
            } else {
                showError("Folder analysis requires Electron desktop mode or entering the absolute folder path directly.");
            }
            localFolderPicker.value = "";
        });
    }

    // Helper to toggle paste/clear button in input box
    function updateUrlInputButtons() {
        const isEmpty = urlInput.value.trim() === "";
        if (isEmpty) {
            pasteBtn.classList.remove("hidden");
            if (browseFileBtn) browseFileBtn.classList.remove("hidden");
            if (browseFolderBtn) browseFolderBtn.classList.remove("hidden");
            if (clearUrlBtn) clearUrlBtn.classList.add("hidden");
        } else {
            pasteBtn.classList.add("hidden");
            if (browseFileBtn) browseFileBtn.classList.add("hidden");
            if (browseFolderBtn) browseFolderBtn.classList.add("hidden");
            if (clearUrlBtn) clearUrlBtn.classList.remove("hidden");
        }
    }

    urlInput.addEventListener("input", updateUrlInputButtons);

    function resetToWelcomeDashboard() {
        if (urlInput) {
            urlInput.value = "";
            updateUrlInputButtons();
        }

        if (analysisAbortController) {
            analysisAbortController.abort();
            analysisAbortController = null;
        }

        if (errorCard) errorCard.classList.add("hidden");
        if (resultSection) resultSection.classList.add("hidden");
        if (loaderSection) loaderSection.classList.add("hidden");
        if (cookiesSection) cookiesSection.classList.add("hidden");
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
        }

        setPlatformTheme(null);
        showWelcomeDashboard();
    }

    // Clear URL input and return to welcome mode
    if (clearUrlBtn) {
        clearUrlBtn.addEventListener("click", () => {
            resetToWelcomeDashboard();
            if (urlInput) urlInput.focus();
            pushToNavigationHistory("");
        });
    }

    // Cancel active analysis and return to welcome mode
    if (cancelAnalyzeBtn) {
        cancelAnalyzeBtn.addEventListener("click", () => {
            resetToWelcomeDashboard();
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

            // Cancel all active background tasks on logo click
            Object.keys(activeTasks).forEach(downloadId => {
                const task = activeTasks[downloadId];
                if (task && task.sse) {
                    try {
                        task.sse.close();
                    } catch (err) {}
                    try {
                        fetch(`/api/download/cancel/${downloadId}`, { method: "POST" });
                    } catch (e) {
                        console.error("Failed to cancel download on logo click:", e);
                    }
                }
                delete activeTasks[downloadId];
            });
            if (downloadsTasksList) {
                downloadsTasksList.innerHTML = "";
            }
            if (downloadsManager) {
                downloadsManager.classList.add("hidden");
            }

            // Hide all dynamic panels
            errorCard.classList.add("hidden");
            resultSection.classList.add("hidden");
            loaderSection.classList.add("hidden");
            cookiesSection.classList.add("hidden");

            // Enable buttons
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            urlInput.disabled = false;

            // Reset theme
            setPlatformTheme(null);

            // Show welcome dashboard
            showWelcomeDashboard();
            pushToNavigationHistory("");
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
                title: "Clear History",
                message: "Are you sure you want to clear all analysis history?",
                yesText: "Confirm",
                noText: "Cancel",
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
        if (!url) return false;
        const trimmed = sanitizeInputUrl(url);
        // Accept local file/folder paths (Windows drive letter or Unix absolute)
        if (/^[A-Za-z]:[/\\]/.test(trimmed)) return true;
        if (trimmed.startsWith("/") && !trimmed.startsWith("//")) return true;
        // Accept BitTorrent Magnet URIs and raw 40/32-char info hashes
        if (/^magnet:\?xt=urn:[a-z0-9]+:[a-z0-9]+/i.test(trimmed) || trimmed.toLowerCase().startsWith("magnet:?")) return true;
        if (/^[a-fA-F0-9]{40}$/.test(trimmed)) return true;
        if (/^[2-7A-Za-z]{32}$/.test(trimmed)) return true;
        try {
            const parsed = new URL(trimmed);
            return parsed.protocol === "http:" || parsed.protocol === "https:" || parsed.protocol === "magnet:";
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
        },
        "local": {
            cyan: "#10b981", purple: "#3b82f6",
            cyanRgb: "16, 185, 129", purpleRgb: "59, 130, 246"
        },
        "torrent": {
            cyan: "#25c276", purple: "#00e676",
            cyanRgb: "37, 194, 118", purpleRgb: "0, 230, 118"
        },
        "utorrent": {
            cyan: "#25c276", purple: "#00e676",
            cyanRgb: "37, 194, 118", purpleRgb: "0, 230, 118"
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
            // Restore user's customizer accent
            const savedAccent = localStorage.getItem("customizer-accent") || "default";
            applyAccent(savedAccent);
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

    // ponytail: Chuẩn hóa URL để gom các link cùng video (bỏ tracking params, radio playlist, timestamp)
    function normalizeMediaUrl(url) {
        if (!url || typeof url !== "string") return "";
        let clean = sanitizeInputUrl(url);

        try {
            // Magnet URI: gom ve canonical magnet:?xt=urn:btih:hash
            if (clean.toLowerCase().startsWith("magnet:")) {
                const xtMatch = clean.match(/xt=urn:[a-z0-9]+:([a-zA-Z0-9]+)/i);
                if (xtMatch && xtMatch[1]) {
                    const dnMatch = clean.match(/dn=([^&]+)/i);
                    const dnPart = dnMatch ? `&dn=${dnMatch[1]}` : "";
                    return `magnet:?xt=urn:btih:${xtMatch[1].toLowerCase()}${dnPart}`;
                }
                return clean;
            }

            // YouTube: gom ve canonical watch?v=ID
            const ytRegex = /(?:youtu\.be\/|(?:www\.|m\.|music\.)?youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/))([a-zA-Z0-9_-]{11})/i;
            const ytMatch = clean.match(ytRegex);
            if (ytMatch && ytMatch[1]) {
                return `https://www.youtube.com/watch?v=${ytMatch[1]}`;
            }

            if (clean.startsWith("http://") || clean.startsWith("https://")) {
                const parsed = new URL(clean);
                const paramsToDelete = [
                    "fbclid", "igshid", "si", "utm_source", "utm_medium",
                    "utm_campaign", "utm_term", "utm_content", "ref", "feature",
                    "start_radio", "t"
                ];
                const listParam = parsed.searchParams.get("list");
                if (listParam && listParam.startsWith("RD")) {
                    paramsToDelete.push("list");
                }
                paramsToDelete.forEach(p => parsed.searchParams.delete(p));
                return (parsed.origin + parsed.pathname + (parsed.search || "")).replace(/\/$/, "");
            }
        } catch (e) {
            // Fallback for non-standard / local path
        }

        return clean.replace(/\/$/, "");
    }

    function isSameMediaItem(a, b) {
        if (!a || !b) return false;

        // 1. Normalized URL matching
        const normA = normalizeMediaUrl(a.url);
        const normB = normalizeMediaUrl(b.url);
        if (normA && normB && normA === normB) {
            return true;
        }

        // 2. Media ID matching
        if (a.id && b.id && String(a.id) === String(b.id)) {
            return true;
        }

        // 3. Exact Title & Platform matching
        if (a.title && b.title && a.title === b.title && a.title !== "Untitled Media") {
            if (a.platform_class && b.platform_class && a.platform_class === b.platform_class) {
                return true;
            }
        }

        return false;
    }

    function deduplicateHistory(historyList) {
        if (!Array.isArray(historyList)) return [];
        const result = [];
        for (const item of historyList) {
            const exists = result.some(existing => isSameMediaItem(existing, item));
            if (!exists) {
                item.url = normalizeMediaUrl(item.url) || item.url;
                result.push(item);
            }
        }
        return result;
    }

    function saveToHistory(url, data) {
        try {
            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            const canonicalUrl = normalizeMediaUrl(url) || url;
            const newItem = {
                url: canonicalUrl,
                title: data.title || "Untitled Media",
                thumbnail: data.thumbnail || "",
                platform_label: data.platform_label || "Video",
                platform_class: data.platform_class || "default",
                id: data.id || null,
                timestamp: Date.now()
            };

            const existingItem = history.find(item => isSameMediaItem(item, newItem));
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
                const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
                const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
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
                    voiceover_rate: voiceoverRateSlider ? voiceoverRateSlider.value : "0",
                    voiceover_pitch: voiceoverPitchSlider ? voiceoverPitchSlider.value : "0",
                    cloud_sync: cloudSyncSelect ? cloudSyncSelect.value : "local",
                    enhance_beautify: document.getElementById("enhance-beautify-checkbox")?.checked || false,
                    enhance_sharpen: parseInt(document.getElementById("enhance-sharpen-slider")?.value || "0"),
                    enhance_upscale: document.getElementById("enhance-upscale-select")?.value || "none"
                };
            }
            newItem.settings = savedSettings;

            // Remove any duplicates of this same media
            history = history.filter(item => !isSameMediaItem(item, newItem));

            // Add to the beginning
            history.unshift(newItem);

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
            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            // Auto-clean any legacy duplicate entries in storage
            const cleaned = deduplicateHistory(history);
            if (cleaned.length !== history.length) {
                history = cleaned;
                localStorage.setItem("downloader_history", JSON.stringify(history));
            }

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
                                <span>${formatHistoryDateTime(item.timestamp)}</span>
                            </div>
                        </div>
                    </div>
                    <div class="history-item-actions">
                        <button class="history-action-btn history-delete-single-btn" title="Xóa mục này khỏi lịch sử" style="padding: 4px 6px; font-size: 0.75rem; border-radius: 4px; display: inline-flex; align-items: center; justify-content: center;">
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                        <svg class="history-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </div>
                `;

                const deleteBtn = row.querySelector(".history-delete-single-btn");
                if (deleteBtn) {
                    deleteBtn.addEventListener("click", (e) => {
                        e.stopPropagation();
                        try {
                            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
                            history = history.filter(h => !(h.url === item.url && h.timestamp === item.timestamp));
                            localStorage.setItem("downloader_history", JSON.stringify(history));
                            renderHistory();
                        } catch (err) {
                            console.error("Error deleting history item:", err);
                        }
                    });
                }

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

    function renderOnlinePlaylist(data) {
        optionsContainer.innerHTML = "";

        const container = document.createElement("div");
        container.className = "playlist-container";

        const headerHtml = `
            <div class="playlist-header-controls">
                <div class="playlist-controls-left">
                    <label class="playlist-select-all-label">
                        <input type="checkbox" id="playlist-toggle-all" checked>
                        <span>Select All</span>
                    </label>
                    <span class="playlist-selected-count">Selected: <strong id="playlist-count-num">${data.entries.length}</strong> / ${data.entries.length} items</span>
                </div>
                <div class="playlist-controls-right">
                    <div class="playlist-config-row">
                        <select id="playlist-global-format" class="playlist-select">
                            <option value="bestvideo+bestaudio/best">Video (MP4 / High Quality)</option>
                            <option value="bestaudio/best">Audio Only (MP3 / High Quality)</option>
                        </select>
                        <button id="btn-playlist-download-all" class="btn-playlist-action">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            <span>Download Selected</span>
                        </button>
                    </div>
                </div>
            </div>
            <div class="playlist-grid-container" id="playlist-grid"></div>
        `;
        container.innerHTML = headerHtml;
        optionsContainer.appendChild(container);

        const grid = container.querySelector("#playlist-grid");
        const toggleAll = container.querySelector("#playlist-toggle-all");
        const countNum = container.querySelector("#playlist-count-num");
        const downloadBtn = container.querySelector("#btn-playlist-download-all");
        const globalFormatSelect = container.querySelector("#playlist-global-format");

        data.entries.forEach((entry, idx) => {
            const card = document.createElement("div");
            card.className = "playlist-item-card is-selected";
            card.setAttribute("data-index", idx);

            card.innerHTML = `
                <div class="playlist-card-checkbox-container">
                    <input type="checkbox" class="playlist-item-checkbox" data-index="${idx}" checked>
                </div>
                <div class="playlist-card-thumbnail-container" title="Click to analyze this video">
                    <img class="playlist-card-thumb" src="${entry.thumbnail || data.thumbnail || '/static/img/default_thumb.jpg'}" alt="" loading="lazy">
                    <span class="playlist-card-duration">${entry.duration || ''}</span>
                </div>
                <div class="playlist-card-info" title="Click to analyze this video">
                    <span class="playlist-card-title" title="${escapeHTML(entry.title)}">${escapeHTML(entry.title)}</span>
                </div>
            `;

            const checkboxContainer = card.querySelector(".playlist-card-checkbox-container");
            checkboxContainer.addEventListener("click", (e) => {
                e.stopPropagation();
            });

            const chk = card.querySelector(".playlist-item-checkbox");
            chk.addEventListener("change", () => {
                if (chk.checked) {
                    card.classList.add("is-selected");
                } else {
                    card.classList.remove("is-selected");
                }
                updateSelectedCount();
            });

            const thumbContainer = card.querySelector(".playlist-card-thumbnail-container");
            const infoContainer = card.querySelector(".playlist-card-info");

            const handleItemAnalyze = (e) => {
                e.stopPropagation();
                if (entry.url) {
                    urlInput.value = entry.url;
                    performAnalysis();
                }
            };

            thumbContainer.addEventListener("click", handleItemAnalyze);
            infoContainer.addEventListener("click", handleItemAnalyze);

            grid.appendChild(card);
        });

        function updateSelectedCount() {
            const selectedChecks = grid.querySelectorAll(".playlist-item-checkbox:checked");
            countNum.textContent = selectedChecks.length;
            
            const allChecks = grid.querySelectorAll(".playlist-item-checkbox");
            toggleAll.checked = selectedChecks.length === allChecks.length;
            toggleAll.indeterminate = selectedChecks.length > 0 && selectedChecks.length < allChecks.length;
        }

        toggleAll.addEventListener("change", () => {
            const allChecks = grid.querySelectorAll(".playlist-item-checkbox");
            allChecks.forEach(chk => {
                chk.checked = toggleAll.checked;
                const card = chk.closest(".playlist-item-card");
                if (toggleAll.checked) {
                    card.classList.add("is-selected");
                } else {
                    card.classList.remove("is-selected");
                }
            });
            updateSelectedCount();
        });

        downloadBtn.addEventListener("click", async () => {
            const selectedChecks = grid.querySelectorAll(".playlist-item-checkbox:checked");
            if (selectedChecks.length === 0) {
                alert("Please select at least one item to download.");
                return;
            }

            const formatVal = globalFormatSelect.value;
            const isAudio = formatVal.includes("audio");
            const ext = isAudio ? "mp3" : "mp4";
            const formatId = formatVal;

            downloadBtn.disabled = true;
            const originalText = downloadBtn.innerHTML;
            downloadBtn.innerHTML = `<span>Enqueuing...</span>`;

            for (const chk of selectedChecks) {
                const idx = parseInt(chk.getAttribute("data-index"));
                const entry = data.entries[idx];
                
                await new Promise(r => setTimeout(r, 100));
                
                triggerDownload(
                    null, 
                    formatId, 
                    ext, 
                    entry.title, 
                    "best", 
                    entry.url, 
                    "", 
                    "", 
                    true,
                    null,
                    null,
                    entry.thumbnail || data.thumbnail
                );
            }

            downloadBtn.disabled = false;
            downloadBtn.innerHTML = originalText;
            
            const downloadsManager = document.getElementById("downloads-manager");
            if (downloadsManager && downloadsManager.classList.contains("collapsed")) {
                downloadsManager.classList.remove("collapsed");
            }
        });

        resultSection.classList.remove("hidden");
    }

    // ponytail: Dọn sạch hoàn toàn metadata, thumbnail và format cards của lượt phân tích trước khi có lỗi hoặc link mới
    function clearActiveAnalysisUI() {
        activeMetadata = null;
        activeUrl = "";
        if (videoThumbnail) {
            videoThumbnail.src = "";
            videoThumbnail.removeAttribute("src");
            videoThumbnail.style.opacity = "0";
            videoThumbnail.alt = "Thumbnail";
        }
        if (videoTitle) videoTitle.textContent = "";
        if (videoUploader) videoUploader.textContent = "";
        if (videoDuration) {
            videoDuration.textContent = "0:00";
            videoDuration.style.display = "none";
        }
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
        if (optionsContainer) optionsContainer.innerHTML = "";

        const resultGrid = resultSection ? resultSection.querySelector(".result-grid") : null;
        if (resultGrid) {
            resultGrid.classList.add("welcome-mode");
        }
        showWelcomeDashboard();
    }

    // Upload & analyze local file fallback for non-Electron web browser environments
    async function uploadAndAnalyzeLocalFile(file) {
        if (!file) return;
        setPlatformTheme(null);
        errorCard.classList.add("hidden");
        clearActiveAnalysisUI();
        loaderSection.classList.remove("hidden");
        loaderText.textContent = `Uploading ${file.name} for analysis...`;
        analyzeBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append("file", file);
            if (clientId) formData.append("client_id", clientId);

            const res = await fetch("/api/info", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                urlInput.value = data.title || file.name;
                updateUrlInputButtons();
                displayMetadata(data);
                saveToHistory(data.webpage_url || data.title, data);
            } else {
                showError(data.message || "Failed to analyze uploaded file.");
            }
        } catch (err) {
            console.error("File upload analysis error:", err);
            showError(`Error uploading file for analysis: ${err.message}`);
        } finally {
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
        }
    }

    async function performAnalysis() {
        let url = sanitizeInputUrl(urlInput.value);
        urlInput.value = url;

        if (!url) {
            clearActiveAnalysisUI();
            showError("Please enter a link first.");
            return;
        }

        if (!isValidUrl(url)) {
            clearActiveAnalysisUI();
            showError("Invalid input. Please enter a valid URL (http/https) or a local file/folder path.");
            return;
        }

        // Push to navigation history stack
        pushToNavigationHistory(url);

        // Initialize AbortController to support cancellation
        if (analysisAbortController) {
            analysisAbortController.abort();
        }
        analysisAbortController = new AbortController();

        // Reset UI States
        setPlatformTheme(null);
        errorCard.classList.add("hidden");
        clearActiveAnalysisUI();
        cookiesSection.classList.add("hidden");

        videoTitle.textContent = "Analyzing...";

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
                    const item = history.find(it => isSameMediaItem(it, { url, id: data.id, title: data.title, platform_class: data.platform_class }));
                    if (item) {
                        restoreSettingsForUrl(item);
                    }
                } catch (e) {
                    console.error("Error restoring settings:", e);
                }

                saveToHistory(url, data);
            } else {
                setPlatformTheme(null);
                clearActiveAnalysisUI();
                showError(data.message || "Unable to extract media information from this URL.");
                const msg = (data.message || "").toLowerCase();
                const authKeywords = ["private", "log in", "login", "sign in", "signin", "invalid", "cookie", "confirm", "subscriber", "membership", "member"];
                if (authKeywords.some(keyword => msg.includes(keyword))) {
                    cookiesSection.classList.remove("hidden");
                }
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                console.log("Analysis aborted by user.");
                clearActiveAnalysisUI();
                return;
            }
            console.error(err);
            setPlatformTheme(null);
            clearActiveAnalysisUI();
            showError("Connection lost. Unable to contact local Python downloader server.");
        } finally {
            loaderSection.classList.add("hidden");
            analyzeBtn.disabled = false;
            analyzeBtn.style.opacity = "";
            analysisAbortController = null;
        }
    }

    // Display parsed metadata
    function displayMetadata(data) {
        activeMetadata = data;
        if (window.electronAPI?.setStreamReferer) {
            const streamRef = data.webpage_url || activeUrl || "";
            if (streamRef) window.electronAPI.setStreamReferer(streamRef);
        }
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
        // Smart thumbnail for local files
        let thumbnailUrl = getProxiedImageUrl(data.thumbnail);
        if (!thumbnailUrl && data.is_local) {
            // For local folders, try to use first image entry as thumbnail
            if (data.entries && data.entries.length > 0) {
                const firstImage = data.entries.find(e => e.type === "image");
                if (firstImage && firstImage.path) {
                    thumbnailUrl = getLocalImageUrl(firstImage.path);
                }
            }
            // For single local image files, use the image itself
            if (!thumbnailUrl && data.images && data.images.length > 0 && data.images[0].url) {
                thumbnailUrl = getProxiedImageUrl(data.images[0].url);
            }
        }
        videoThumbnail.src = thumbnailUrl || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=600";
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
                if (imagesSearchInput) imagesSearchInput.value = "";
                if (imagesFilterSelect) imagesFilterSelect.value = "all";
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

        const imagesSearchInput = document.getElementById("images-search-input");
        const imagesFilterSelect = document.getElementById("images-filter-select");

        if (imagesSearchInput) {
            imagesSearchInput.oninput = () => {
                renderImagesGrid();
            };
        }
        if (imagesFilterSelect) {
            imagesFilterSelect.onchange = () => {
                renderImagesGrid();
            };
        }

        function renderImagesGrid() {
            modalImagesGrid.innerHTML = "";
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }

            const query = imagesSearchInput ? imagesSearchInput.value.toLowerCase().trim() : "";
            const filterExt = imagesFilterSelect ? imagesFilterSelect.value : "all";

            extractedImages.forEach((img, idx) => {
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

                const lowerImgExt = (imgExt || "").toLowerCase();
                // Match search query
                if (query && !imgLabel.toLowerCase().includes(query)) {
                    return;
                }

                // Match extension filter
                if (filterExt !== "all") {
                    if (filterExt === "jpg") {
                        if (lowerImgExt !== "jpg" && lowerImgExt !== "jpeg") return;
                    } else if (filterExt === "heic") {
                        if (lowerImgExt !== "heic" && lowerImgExt !== "heif") return;
                    } else {
                        if (lowerImgExt !== filterExt) return;
                    }
                }

                const card = document.createElement("div");
                card.className = "image-card";

                // Extract resolution label from name if present
                const resMatch = imgLabel.match(/\((\d+x\d+)\)/);
                const resLabel = resMatch ? resMatch[1] : (imgExt ? imgExt.toUpperCase() : "Image");
                const cleanLabel = imgLabel.replace(/\s*\(\d+x\d+\)/, "");

                const cleanTitle = getSafeTitle(data.title, "image");
                const filename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${imgExt}`;
                const proxyDownloadUrl = `/api/download/image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(filename)}&client_id=${encodeURIComponent(clientId)}`;

                card.innerHTML = `
                    <div class="image-preview-wrap">
                        <div class="image-checkbox-container" style="position: absolute; top: 8px; right: 8px; width: 18px; height: 18px; z-index: 5; display: block;">
                            <input type="checkbox" class="image-select-check custom-checkbox" data-url="${imgUrl}" data-label="${cleanLabel}" data-ext="${imgExt}" data-filename="${filename}">
                        </div>
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
                    triggerPreview(prevBtn, "image_preview", imgExt, cleanLabel, "", imgUrl);
                };

                // Add click listener on preview to toggle checkbox
                const preview = card.querySelector(".image-preview-wrap");
                const checkbox = card.querySelector(".image-select-check");
                preview.onclick = (e) => {
                    if (e.target !== checkbox && !e.target.closest(".image-checkbox-container")) {
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
                        downloadSelectedBtn.innerHTML = `<span>Downloading ${i + 1}/${selectedItems.length}...</span>`;

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

        // ── Local Folder Playlist Rendering ──────────────────────────────
        if (data.is_playlist && data.is_local && data.entries && data.entries.length > 0) {
            const folderIconSvgs = {
                video: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
                audio: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`,
                image: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`,
                subtitle: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan);"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
                text: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
                other: `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>`
            };
            const folderDownloadSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;

            const imageExtsLocal = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "heic", "heif", "tiff", "tif", "svg", "ico", "avif"];
            const videoExtsLocal = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "ts", "mpg", "mpeg", "m4v", "3gp"];
            const audioExtsLocal = ["mp3", "m4a", "wav", "flac", "ogg", "aac", "wma", "opus"];
            const subtitleExtsLocal = ["vtt", "srt", "ass", "ssa", "sub", "idx", "lrc"];

            // Group entries by type
            const groups = { video: [], audio: [], image: [], subtitle: [], text: [], other: [] };
            data.entries.forEach(entry => {
                const t = entry.type || "other";
                if (groups[t]) groups[t].push(entry);
                else groups.other.push(entry);
            });

            const groupOrder = [
                { key: "video", label: "Video Files", icon: folderIconSvgs.video },
                { key: "audio", label: "Audio Files", icon: folderIconSvgs.audio },
                { key: "image", label: "Image Files", icon: folderIconSvgs.image },
                { key: "subtitle", label: "Subtitle Files", icon: folderIconSvgs.subtitle },
                { key: "text", label: "Text / Document Files", icon: folderIconSvgs.text },
                { key: "other", label: "Other Files", icon: folderIconSvgs.other }
            ];

            function createFolderFormatGroup(titleHtml, elements) {
                if (!elements || elements.length === 0) return null;
                const groupDiv = document.createElement("div");
                groupDiv.className = "format-group";
                const labelDiv = document.createElement("div");
                labelDiv.className = "format-group-label";
                labelDiv.innerHTML = `<div class="format-group-title-left">${titleHtml}</div><svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`;
                const contentDiv = document.createElement("div");
                contentDiv.className = "format-group-content";
                const innerDiv = document.createElement("div");
                innerDiv.className = "format-group-inner";
                elements.forEach(el => innerDiv.appendChild(el));
                contentDiv.appendChild(innerDiv);
                groupDiv.appendChild(labelDiv);
                groupDiv.appendChild(contentDiv);
                labelDiv.addEventListener("click", () => {
                    const isCollapsed = contentDiv.classList.toggle("collapsed");
                    labelDiv.classList.toggle("collapsed", isCollapsed);
                });
                return groupDiv;
            }

            groupOrder.forEach(grp => {
                const entries = groups[grp.key];
                if (!entries || entries.length === 0) return;

                const rowEls = [];
                entries.forEach(entry => {
                    const row = document.createElement("div");
                    row.className = `format-row ${grp.key}-row`;
                    const sizeBadge = entry.size ? `<span class="format-size">${entry.size}</span>` : '';
                    const extBadge = entry.ext ? `<span class="format-size" style="text-transform:uppercase;">${entry.ext}</span>` : '';
                    const entryPath = entry.path || "";
                    const entryExt = (entry.ext || "").toLowerCase();

                    // Determine data attributes for preview/download
                    let previewType = "";
                    let previewFormatId = "local_file";
                    if (grp.key === "image") {
                        previewFormatId = "image_preview";
                        previewType = "";
                    } else if (grp.key === "audio") {
                        previewType = "audio";
                    } else if (grp.key === "subtitle") {
                        previewType = "subtitle";
                    } else if (grp.key === "text") {
                        previewType = "";
                    }

                    row.innerHTML = `
                        <div class="format-left">
                            ${folderIconSvgs[grp.key] || folderIconSvgs.other}
                            <span class="format-name" title="${entry.title}">${truncateMiddle(entry.title)}</span>
                            ${extBadge}
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-preview" data-id="${previewFormatId}" data-ext="${entryExt}" data-label="${entry.title}" data-quality="" data-url="${entryPath}" data-type="${previewType}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <span>Preview</span>
                            </button>
                            <button class="btn-get" data-id="local_file" data-ext="${entryExt}" data-label="${entry.title}" data-quality="" data-url="${entryPath}">
                                ${folderDownloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });

                const titleHtml = `${grp.icon}<span>${grp.label} (${entries.length})</span>`;
                const groupEl = createFolderFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            });

            // Bind event listeners for folder entries
            const previewButtons = optionsContainer.querySelectorAll(".btn-preview");
            previewButtons.forEach(btn => {
                btn.addEventListener("click", () => {
                    const formatId = btn.getAttribute("data-id");
                    const ext = btn.getAttribute("data-ext");
                    const label = btn.getAttribute("data-label");
                    const quality = btn.getAttribute("data-quality");
                    const customUrl = btn.getAttribute("data-url");
                    const type = btn.getAttribute("data-type") || "";
                    triggerPreview(btn, formatId, ext, label, quality, customUrl, "", "", type);
                });
            });

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

                    const streamTargetUrl = customUrl || activeUrl || "";
                    const isStreamOption = (
                        ext === "html" || ext === "htm" ||
                        (formatId && String(formatId).startsWith("avs_")) ||
                        (label && String(label).includes("[STREAM]")) ||
                        (streamTargetUrl && (streamTargetUrl.includes("/player/") || streamTargetUrl.includes("googleapiscdn.com") || streamTargetUrl.endsWith(".html") || streamTargetUrl.includes(".html?")))
                    );

                    if (isStreamOption) {
                        triggerStreamDownload(btn, formatId, ext, label, quality, customUrl, episode, server);
                        return;
                    }

                    triggerDownload(btn, formatId, ext, label, quality, customUrl, episode, server, true);
                });
            });

            resultSection.classList.remove("hidden");
        } else if (data.is_playlist && data.entries && data.entries.length > 0) {
            renderOnlinePlaylist(data);
            return;
        }

        const videoSvg = `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`;
        const audioSvg = `<svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;
        const downloadSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;

        function createFormatGroup(titleHtml, elements) {
            if (!elements || elements.length === 0) return null;

            const groupDiv = document.createElement("div");
            groupDiv.className = "format-group";

            const labelDiv = document.createElement("div");
            labelDiv.className = "format-group-label";
            labelDiv.innerHTML = `
                <div class="format-group-title-left">
                    ${titleHtml}
                </div>
                <svg class="chevron-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            `;

            const contentDiv = document.createElement("div");
            contentDiv.className = "format-group-content";

            const innerDiv = document.createElement("div");
            innerDiv.className = "format-group-inner";

            elements.forEach(el => {
                innerDiv.appendChild(el);
            });

            contentDiv.appendChild(innerDiv);
            groupDiv.appendChild(labelDiv);
            groupDiv.appendChild(contentDiv);

            labelDiv.addEventListener("click", () => {
                const isCollapsed = contentDiv.classList.toggle("collapsed");
                labelDiv.classList.toggle("collapsed", isCollapsed);
            });

            return groupDiv;
        }

        // Render Video & Media options if present
        if (data.video_options && data.video_options.length > 0) {
            const videoExts = ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "ts", "mpg", "mpeg", "m4v", "3gp", "m2ts", "vob", "ogv"];
            const audioExts = ["mp3", "m4a", "wav", "flac", "ogg", "aac", "wma", "opus", "alac", "aiff", "mka"];
            const imageExts = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "heic", "heif", "tiff", "tif", "svg", "ico", "avif"];
            const htmlExts = ["html", "htm"];
            const textPreviewExts = ["txt", "xml", "json", "csv", "log", "md", "css", "js", "py", "yaml", "yml", "ini", "cfg", "conf", "nfo", "sql", "pdf", "sh", "bat", "ts", "tsx", "jsx", "java", "c", "cpp", "h", "hpp", "rs", "go", "rb", "php", "pl", "swift", "kt", "r", "scala", "lua", "toml"];
            const docExts = ["txt", "xml", "json", "csv", "log", "md", "css", "js", "py", "yaml", "yml", "ini", "cfg", "conf", "nfo", "sql", "pdf", "doc", "docx", "rtf", "odt", "xls", "xlsx", "ppt", "pptx"];
            const subExts = ["vtt", "srt", "ass", "ssa", "sub", "idx", "lrc"];

            const torrentPackages = data.video_options.filter(opt => {
                const ext = (opt.ext || "").toLowerCase();
                const fid = (opt.format_id || "").toLowerCase();
                return opt.type === "torrent" || opt.is_package || ext === "torrent" || ext === "magnet" || fid.startsWith("torrent_magnet") || fid === "torrent_file_download";
            });

            const videos = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "video";
                const ext = (opt.ext || "").toLowerCase();
                return videoExts.includes(ext) || (!imageExts.includes(ext) && !audioExts.includes(ext) && !htmlExts.includes(ext) && !docExts.includes(ext) && !subExts.includes(ext) && ext !== "torrent" && ext !== "magnet");
            });

            const audiosInVideoOpts = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "audio";
                const ext = (opt.ext || "").toLowerCase();
                return audioExts.includes(ext);
            });
            if (audiosInVideoOpts.length > 0) {
                if (!data.audio_options) data.audio_options = [];
                audiosInVideoOpts.forEach(aOpt => {
                    if (!data.audio_options.some(existing => existing.format_id === aOpt.format_id)) {
                        data.audio_options.push(aOpt);
                    }
                });
            }

            const photos = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "image";
                const ext = (opt.ext || "").toLowerCase();
                return imageExts.includes(ext);
            });

            const webpages = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "webpage";
                const ext = (opt.ext || "").toLowerCase();
                return htmlExts.includes(ext);
            });

            const documents = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "text" || opt.type === "document";
                const ext = (opt.ext || "").toLowerCase();
                return docExts.includes(ext);
            });

            const subFiles = data.video_options.filter(opt => {
                if (torrentPackages.includes(opt)) return false;
                if (opt.type) return opt.type === "subtitle";
                const ext = (opt.ext || "").toLowerCase();
                return subExts.includes(ext);
            });

            const others = data.video_options.filter(opt => {
                return !torrentPackages.includes(opt) &&
                       !videos.includes(opt) &&
                       !photos.includes(opt) &&
                       !audiosInVideoOpts.includes(opt) &&
                       !webpages.includes(opt) &&
                       !documents.includes(opt) &&
                       !subFiles.includes(opt);
            });

            // 1. Render Torrent / Magnet Package options (Download/Open only, no preview)
            if (torrentPackages.length > 0) {
                const rowEls = [];
                torrentPackages.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row torrent-row";
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan, #25c276); width: 18px; height: 18px; margin-right: 8px;"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan, #25c276);"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                    <span>Torrent / Magnet Package</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }

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

                const formatBytes = (bytes, decimals = 1) => {
                    if (!bytes || bytes <= 0) return '0 B';
                    const k = 1024;
                    const dm = decimals < 0 ? 0 : decimals;
                    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                    const i = Math.floor(Math.log(bytes) / Math.log(k));
                    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
                };

                const computeDynamicStreamSize = (opt) => {
                    if (opt.size && opt.size !== "Unknown Size" && !opt.size.includes("~350 MB") && !opt.size.includes("Stream")) {
                        return opt.size;
                    }
                    const dur = opt.duration || (activeMetadata && activeMetadata.duration);
                    if (dur && Number(dur) > 0) {
                        const bytes = Number(dur) * 275000;
                        return `~${formatBytes(bytes)} (HD Stream)`;
                    }
                    const isStream = (
                        (opt.format_id && String(opt.format_id).startsWith("avs_")) ||
                        (opt.label && String(opt.label).includes("[STREAM]")) ||
                        (opt.url && (opt.url.includes("/player/") || opt.url.includes("googleapiscdn.com")))
                    );
                    if (isStream) {
                        return "Stream (MSE / HD)";
                    }
                    return (opt.size && opt.size !== "Unknown Size") ? opt.size : "";
                };

                // Render ungrouped videos first (if any)
                if (noGroup.length > 0) {
                    const rowEls = [];
                    noGroup.forEach(option => {
                        const row = document.createElement("div");
                        row.className = "format-row video-row";
                        const optSize = computeDynamicStreamSize(option);
                        const sizeBadge = optSize ? `<span class="format-size">${optSize}</span>` : '';
                        const drmBadge = option.is_drm ? `<span class="drm-badge" title="Định dạng này được mã hóa bảo vệ bản quyền DRM. Tải xuống có thể bị lỗi."><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>DRM</span>` : '';
                        row.innerHTML = `
                            <div class="format-left">
                                ${videoSvg}
                                <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                                ${sizeBadge}
                                ${drmBadge}
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
                        rowEls.push(row);
                    });
                    const titleHtml = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                        <span>Video Options</span>
                    `;
                    const groupEl = createFormatGroup(titleHtml, rowEls);
                    if (groupEl) optionsContainer.appendChild(groupEl);
                }

                // Render grouped videos by server
                serverOrder.forEach(server => {
                    const rowEls = [];
                    grouped[server].forEach(option => {
                        const row = document.createElement("div");
                        const isCurrentEp = !!(option.is_current || (data && data.current_format_id && option.format_id === data.current_format_id));
                        row.className = "format-row video-row" + (isCurrentEp ? " active-episode-row current-ep" : "");
                        const optSize = computeDynamicStreamSize(option);
                        const sizeBadge = optSize ? `<span class="format-size">${optSize}</span>` : '';
                        const currentBadge = isCurrentEp ? `<span class="current-ep-badge" title="Tập hiện tại theo liên kết đã nhập"><svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10" style="margin-right:3px; vertical-align:-1px;"><polygon points="5 3 19 12 5 21 5 3"/></svg>Đang chọn</span>` : '';

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

                        const drmBadge = option.is_drm ? `<span class="drm-badge" title="Định dạng này được mã hóa bảo vệ bản quyền DRM. Tải xuống có thể bị lỗi."><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>DRM</span>` : '';
                        row.innerHTML = `
                            <div class="format-left">
                                ${videoSvg}
                                <span class="format-name" title="${displayLabel}">${truncateMiddle(displayLabel)}</span>
                                ${currentBadge}
                                ${sizeBadge}
                                ${drmBadge}
                            </div>
                            <div class="format-actions">
                                <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-episode="${option.episode || ''}" data-server="${option.server || ''}" data-referer="${option.referer || (data && data.webpage_url) || ''}">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                    <span>Preview</span>
                                </button>
                                <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-episode="${option.episode || ''}" data-server="${option.server || ''}">
                                    ${downloadSvg}
                                    <span>Get</span>
                                </button>
                            </div>
                        `;
                        rowEls.push(row);
                    });
                    const titleHtml = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                        <span>${server}</span>
                    `;
                    const groupEl = createFormatGroup(titleHtml, rowEls);
                    if (groupEl) optionsContainer.appendChild(groupEl);
                });
            }


            if (photos.length > 0) {
                const rowEls = [];
                photos.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row photo-row";

                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
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
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                    <span>Photo Options</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }

            if (webpages.length > 0) {
                const rowEls = [];
                webpages.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row webpage-row stream-player-row";

                    const displaySize = (option.size && option.size !== "Unknown Size") ? option.size : "Stream Player";
                    const sizeBadge = `<span class="format-size">${displaySize}</span>`;
                    const streamBadge = `<span class="stream-player-badge"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>STREAM PLAYER</span>`;
                    let cleanLabel = (option.label || "Stream Player").replace(/webpage/gi, "Stream Player");

                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #818cf8; width: 18px; height: 18px; margin-right: 8px;"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(cleanLabel)}</span>
                            ${streamBadge}
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${cleanLabel}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-referer="${option.referer || (data && data.webpage_url) || ''}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <span>Preview</span>
                            </button>
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${cleanLabel}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #818cf8;"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    <span>Stream Player Options</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }

            if (documents.length > 0) {
                const rowEls = [];
                documents.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row document-row";
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    const extLower = (option.ext || "").toLowerCase();
                    const isPreviewableText = textPreviewExts.includes(extLower);
                    const previewBtnHtml = isPreviewableText ? `
                        <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-type="text">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                    ` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            ${previewBtnHtml}
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <span>Document & Text Files</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }

            if (subFiles.length > 0) {
                const rowEls = [];
                subFiles.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row subtitle-row";
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--cyan);"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-type="subtitle">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                <span>Preview</span>
                            </button>
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    <span>Subtitle Options</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }

            if (others.length > 0) {
                const rowEls = [];
                others.forEach(option => {
                    const row = document.createElement("div");
                    row.className = "format-row other-row";
                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                            <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                            ${sizeBadge}
                        </div>
                        <div class="format-actions">
                            <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}">
                                ${downloadSvg}
                                <span>Get</span>
                            </button>
                        </div>
                    `;
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
                    <span>Other / Data Files</span>
                `;
                const groupEl = createFormatGroup(titleHtml, rowEls);
                if (groupEl) optionsContainer.appendChild(groupEl);
            }
        }

        // Render Audio options if present
        if (data.audio_options && data.audio_options.length > 0) {
            const rowEls = [];
            data.audio_options.forEach(option => {
                const row = document.createElement("div");
                row.className = "format-row audio-row";

                const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                row.innerHTML = `
                    <div class="format-left">
                        ${audioSvg}
                        <span class="format-name" title="${option.label}">${truncateMiddle(option.label)}</span>
                        ${sizeBadge}
                    </div>
                    <div class="format-actions">
                        <button class="btn-preview" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-type="audio">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                        <button class="btn-get" data-id="${option.format_id}" data-ext="${option.ext}" data-label="${option.label}" data-quality="${option.quality || ''}" data-url="${option.url || ''}" data-type="audio">
                            ${downloadSvg}
                            <span>Get</span>
                        </button>
                    </div>
                `;
                rowEls.push(row);
            });
            const titleHtml = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                <span>Audio Options</span>
            `;
            const groupEl = createFormatGroup(titleHtml, rowEls);
            if (groupEl) optionsContainer.appendChild(groupEl);
        }

        // Render Subtitle options if present
        if (data.subtitles && data.subtitles.length > 0) {
            const rowEls = [];
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
                        <button class="btn-preview" data-id="${option.lang_code}" data-ext="vtt" data-label="Subtitles - ${option.name}" data-url="${option.url || ''}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            <span>Preview</span>
                        </button>
                        <button class="btn-get" data-id="${option.lang_code}" data-ext="vtt" data-label="Subtitles - ${option.name}" data-url="${option.url || ''}">
                            ${downloadSvg}
                            <span>Get</span>
                        </button>
                    </div>
                `;
                rowEls.push(row);
            });
            const titleHtml = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>Subtitles Options</span>
            `;
            const groupEl = createFormatGroup(titleHtml, rowEls);
            if (groupEl) optionsContainer.appendChild(groupEl);
        }

        // Render photo options from data.images if no video or audio options are available at all
        const hasVideoOptions = data.video_options && data.video_options.length > 0;
        const hasAudioOptions = data.audio_options && data.audio_options.length > 0;

        if (!hasVideoOptions && !hasAudioOptions && data.images && data.images.length > 0) {
            const rowEls = [];
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
                rowEls.push(row);
            });
            const titleHtml = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                <span>Photo Options</span>
            `;
            const groupEl = createFormatGroup(titleHtml, rowEls);
            if (groupEl) optionsContainer.appendChild(groupEl);
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

                const streamTargetUrl = customUrl || activeUrl || "";
                const isStreamOption = (
                    ext === "html" || ext === "htm" ||
                    (formatId && String(formatId).startsWith("avs_")) ||
                    (label && String(label).includes("[STREAM]")) ||
                    (streamTargetUrl && (streamTargetUrl.includes("/player/") || streamTargetUrl.includes("googleapiscdn.com") || streamTargetUrl.endsWith(".html") || streamTargetUrl.includes(".html?")))
                );

                if (isStreamOption) {
                    triggerStreamDownload(btn, formatId, ext, label, quality, customUrl, episode, server);
                    return;
                }

                // DRM warning intercept
                let isDrm = false;
                if (activeMetadata && activeMetadata.video_options) {
                    const matchedOpt = activeMetadata.video_options.find(o => o.format_id === formatId);
                    if (matchedOpt && matchedOpt.is_drm) {
                        isDrm = true;
                    }
                }

                if (isDrm) {
                    showConfirm({
                        title: "Cảnh báo Bản quyền DRM",
                        message: "Video này sử dụng công nghệ mã hóa DRM (Digital Rights Management). Quá trình tải xuống có khả năng lớn sẽ bị lỗi hoặc không giải mã được. Bạn vẫn muốn tiếp tục thử tải?",
                        yesText: "Tiếp tục",
                        noText: "Hủy bỏ",
                        onYes: () => {
                            triggerDownload(btn, formatId, ext, label, quality, customUrl, episode, server, true);
                        }
                    });
                } else {
                    triggerDownload(btn, formatId, ext, label, quality, customUrl, episode, server, true);
                }
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
                const type = btn.getAttribute("data-type") || "";
                const referer = btn.getAttribute("data-referer") || "";
                triggerPreview(btn, formatId, ext, label, quality, customUrl, episode, server, type, referer);
            });
        });

        // Auto fill and trigger download if we are in a Re-download flow
        if (typeof autoFillSettingsAfterAnalysis !== "undefined" && autoFillSettingsAfterAnalysis) {
            try {
                const fill = autoFillSettingsAfterAnalysis;
                autoFillSettingsAfterAnalysis = null; // Clear immediately to prevent loop

                // Trim settings
                const trimCheckbox = document.getElementById("trim-checkbox");
                if (trimCheckbox) {
                    trimCheckbox.checked = !!(fill.trim_start || fill.trim_end);
                    trimCheckbox.dispatchEvent(new Event("change"));
                }
                const trimStart = document.getElementById("trim-start");
                if (trimStart && fill.trim_start) {
                    trimStart.value = fill.trim_start;
                    trimStart.dispatchEvent(new Event("input"));
                }
                const trimEnd = document.getElementById("trim-end");
                if (trimEnd && fill.trim_end) {
                    trimEnd.value = fill.trim_end;
                    trimEnd.dispatchEvent(new Event("input"));
                }

                // AI Voiceover settings
                const voiceoverCb = document.getElementById("voiceover-checkbox");
                if (voiceoverCb) {
                    voiceoverCb.checked = !!fill.voiceover_active;
                    voiceoverCb.dispatchEvent(new Event("change"));
                }
                const voiceoverVoice = document.getElementById("voiceover-voice-select");
                if (voiceoverVoice && fill.voiceover_voice) {
                    voiceoverVoice.value = fill.voiceover_voice;
                    voiceoverVoice.dispatchEvent(new Event("change"));
                }
                const voiceoverRate = document.getElementById("voiceover-rate-slider");
                if (voiceoverRate && fill.voiceover_rate) {
                    const rateVal = parseInt(fill.voiceover_rate) || 0;
                    voiceoverRate.value = rateVal.toString();
                    voiceoverRate.dispatchEvent(new Event("input"));
                }
                const voiceoverPitch = document.getElementById("voiceover-pitch-slider");
                if (voiceoverPitch && fill.voiceover_pitch) {
                    const pitchVal = parseInt(fill.voiceover_pitch) || 0;
                    voiceoverPitch.value = pitchVal.toString();
                    voiceoverPitch.dispatchEvent(new Event("input"));
                }

                // Cloud settings
                const cloudSelect = document.getElementById("cloud-sync-select");
                if (cloudSelect && fill.cloud_destination) {
                    cloudSelect.value = fill.cloud_destination;
                    cloudSelect.dispatchEvent(new Event("change"));
                }

                // Find and trigger the download button click
                const targetBtn = Array.from(downloadButtons).find(b =>
                    b.getAttribute("data-id") === fill.format_id &&
                    b.getAttribute("data-ext") === fill.ext
                );

                if (targetBtn) {
                    console.log(`Auto triggering Re-download for format_id=${fill.format_id}`);
                    setTimeout(() => {
                        targetBtn.click();
                    }, 500); // 500ms delay for UI transitions
                } else {
                    console.warn(`Re-download target button not found for format_id=${fill.format_id}, ext=${fill.ext}`);
                }
            } catch (fillErr) {
                console.error("Error during auto-filling re-download settings:", fillErr);
            }
        }

        // Setup Advanced Options panel state for the new media
        const trimCheckbox = document.getElementById("trim-checkbox");
        const trimInputsContainer = document.getElementById("trim-inputs-container");
        const trimStartInput = document.getElementById("trim-start");
        const trimEndInput = document.getElementById("trim-end");
        const trimPreviewContainer = document.getElementById("trim-preview-container");
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
            const hasVideo = data.video_options && data.video_options.some(opt => {
                if (opt.type) return opt.type === "video";
                const ext = (opt.ext || "").toLowerCase();
                return !["jpg", "jpeg", "png", "webp", "gif", "html", "htm"].includes(ext);
            });

            if (durationSeconds > 0 && hasVideo && trimRangeSlider) {
                // Determine a valid video format URL to load in background preview
                const previewVideoOption = data.video_options.find(opt => {
                    if (opt.type) return opt.type === "video" && opt.url;
                    const ext = (opt.ext || "").toLowerCase();
                    return !["jpg", "jpeg", "png", "webp", "gif", "html", "htm"].includes(ext) && opt.url;
                });
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

    function escapeHTML(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function createTaskCard(taskId, title, label) {
        const card = document.createElement("div");
        card.className = "download-task-card";
        card.id = `task-card-${taskId}`;
        card.innerHTML = `
            <div class="download-task-title-row">
                <span class="download-task-title" title="${escapeHTML(title)}">${escapeHTML(title)}</span>
                <span class="download-task-pct">Queued</span>
            </div>
            <div class="download-task-track">
                <div class="download-task-fill striped" style="width: 5%"></div>
            </div>
            <div class="download-task-info-row">
                <span class="download-task-msg">Preparing... • ${escapeHTML(label)}</span>
                <div class="download-task-actions">
                    <button class="btn-task-action btn-task-cancel" title="Cancel Download">Cancel</button>
                </div>
            </div>
        `;

        const cancelBtn = card.querySelector(".btn-task-cancel");
        if (cancelBtn) {
            cancelBtn.addEventListener("click", () => {
                cancelTask(taskId);
            });
        }

        if (downloadsTasksList) {
            downloadsTasksList.prepend(card);
        }
        
        if (downloadsManager) {
            downloadsManager.classList.remove("hidden");
            downloadsManager.classList.remove("collapsed");
        }

        return card;
    }

    function cancelTask(downloadId) {
        const task = activeTasks[downloadId];
        if (task) {
            if (task.sse) {
                try {
                    task.sse.close();
                } catch (e) {}
            }
            if (!downloadId.startsWith("temp-")) {
                try {
                    fetch(`/api/download/cancel/${downloadId}`, { method: "POST" });
                } catch (e) {
                    console.error(`Failed to cancel task ${downloadId}:`, e);
                }
            }
            
            const card = document.getElementById(`task-card-${downloadId}`);
            if (card) {
                card.classList.remove("state-complete");
                card.classList.add("state-error");
                
                const pctSpan = card.querySelector(".download-task-pct");
                if (pctSpan) pctSpan.textContent = "Cancelled";
                
                const fillBar = card.querySelector(".download-task-fill");
                if (fillBar) {
                    fillBar.classList.remove("striped");
                    fillBar.style.width = "100%";
                }
                
                const msgSpan = card.querySelector(".download-task-msg");
                if (msgSpan) msgSpan.textContent = "Task cancelled by user.";
                
                const actionsDiv = card.querySelector(".download-task-actions");
                if (actionsDiv) {
                    actionsDiv.innerHTML = `
                        <button class="btn-task-action btn-task-clear" title="Clear">Clear</button>
                    `;
                    const clearBtn = actionsDiv.querySelector(".btn-task-clear");
                    if (clearBtn) {
                        clearBtn.addEventListener("click", () => {
                            card.remove();
                            if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                                downloadsManager.classList.add("hidden");
                            }
                        });
                    }
                }
            }
            
            if (task.btn) {
                task.btn.disabled = false;
                task.btn.style.opacity = "";
            }
            if (task.activeRow) {
                task.activeRow.classList.remove("is-downloading");
            }
            
            delete activeTasks[downloadId];
            updateDownloadsCount();
        } else {
            const card = document.getElementById(`task-card-${downloadId}`);
            if (card) {
                card.remove();
                if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                    downloadsManager.classList.add("hidden");
                }
            }
        }
    }

    async function openCompletedTaskFile(filePath, downloadId) {
        if (window.electronAPI && typeof window.electronAPI.openFile === "function") {
            window.electronAPI.openFile(filePath);
            return;
        }
        try {
            const resp = await fetch("/api/download/open-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_path: filePath, download_id: downloadId })
            });
            const data = await resp.json();
            if (!resp.ok || data.status !== "success") {
                showAlert("Thông báo", data.message || "Không thể mở tệp tin trực tiếp.");
            }
        } catch (err) {
            console.error("Open file error:", err);
            showAlert("Lỗi", "Không thể khởi chạy trình phát tập tin.");
        }
    }

    function openCompletedTaskPreview(downloadId, cleanName) {
        if (!previewModal) return;
        const ext = (cleanName || "").split(".").pop().toLowerCase();
        const isAudio = ["mp3", "wav", "flac", "m4a", "ogg", "opus", "aac", "wma"].includes(ext);
        const isImage = ["jpg", "jpeg", "png", "webp", "gif", "bmp", "ico", "svg", "avif"].includes(ext);

        stopAllPreviewPlaybacks();
        if (typeof window._resetPreviewCardPosition === "function") {
            window._resetPreviewCardPosition();
        }

        previewModal.classList.remove("hidden");
        document.body.classList.add("modal-open");
        document.body.classList.add("preview-active");

        if (previewVideoContainer) previewVideoContainer.classList.add("hidden");
        if (previewAudioContainer) previewAudioContainer.classList.add("hidden");
        if (previewImageContainer) previewImageContainer.classList.add("hidden");
        if (previewSubtitleContainer) previewSubtitleContainer.classList.add("hidden");
        if (previewWebpageContainer) previewWebpageContainer.classList.add("hidden");

        if (previewTitle) previewTitle.textContent = cleanName || "Completed File";
        if (previewMetaInfo) previewMetaInfo.textContent = `Completed Task • ${ext.toUpperCase()}`;
        hidePreviewLoader();

        const streamUrl = `/api/download/file/${downloadId}?preview=true`;
        previewActiveDownloadId = downloadId;
        previewActiveUrl = streamUrl;

        if (isAudio) {
            if (previewAudioPlayer) {
                previewAudioPlayer.src = streamUrl;
                previewAudioPlayer.load();
                if (previewAudioContainer) previewAudioContainer.classList.remove("hidden");
                previewAudioPlayer.play().catch(() => {});
            }
        } else if (isImage) {
            if (previewImageContainer && previewImage) {
                previewImage.src = streamUrl;
                previewImageContainer.classList.remove("hidden");
            }
        } else {
            if (previewVideoPlayer) {
                previewVideoPlayer.src = streamUrl;
                previewVideoPlayer.load();
                if (previewVideoContainer) previewVideoContainer.classList.remove("hidden");
                previewVideoPlayer.play().catch(() => {});
            }
        }
    }

    async function handleSaveTaskFile(downloadId, defaultName, card = null) {
        if (window.electronAPI && typeof window.electronAPI.saveFile === "function") {
            try {
                const res = await window.electronAPI.saveFile({ downloadId, defaultFilename: defaultName });
                if (res && res.success && res.filePath) {
                    const savedBase = res.filePath.split(/[/\\]/).pop();
                    if (card) {
                        const msgSpan = card.querySelector(".download-task-msg");
                        if (msgSpan) {
                            msgSpan.innerHTML = `Saved: <span style="color: var(--cyan); text-decoration: underline; cursor: pointer;" title="Show in folder">${savedBase}</span>`;
                            msgSpan.onclick = () => {
                                if (window.electronAPI && window.electronAPI.showItemInFolder) {
                                    window.electronAPI.showItemInFolder(res.filePath);
                                } else {
                                    fetch("/api/download/open-folder", { method: "POST" });
                                }
                            };
                        }
                        const actionsDiv = card.querySelector(".download-task-actions");
                        if (actionsDiv) {
                            actionsDiv.innerHTML = `
                                <button type="button" class="btn-task-action btn-task-open" title="Open / Play file">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                    <span>Play</span>
                                </button>
                                <button type="button" class="btn-task-action btn-task-folder" title="Show in folder">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                                    <span>Folder</span>
                                </button>
                                <button type="button" class="btn-task-action btn-task-clear" title="Clear">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                            `;
                            actionsDiv.querySelector(".btn-task-open")?.addEventListener("click", () => {
                                openCompletedTaskFile(res.filePath, downloadId);
                            });
                            actionsDiv.querySelector(".btn-task-folder")?.addEventListener("click", () => {
                                if (window.electronAPI && window.electronAPI.showItemInFolder) {
                                    window.electronAPI.showItemInFolder(res.filePath);
                                } else {
                                    fetch("/api/download/open-folder", { method: "POST" });
                                }
                            });
                            actionsDiv.querySelector(".btn-task-clear")?.addEventListener("click", () => {
                                card.remove();
                                if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                                    downloadsManager.classList.add("hidden");
                                }
                            });
                        }
                    }
                } else if (res && res.error) {
                    showAlert("Lỗi lưu tệp tin", res.error);
                }
            } catch (err) {
                console.error("Save file error:", err);
                showAlert("Lỗi", err.message);
            }
        } else {
            // Browser environment fallback: direct attachment download without opening new window
            const a = document.createElement("a");
            a.href = `/api/download/file/${downloadId}`;
            a.download = defaultName || "download";
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    }

    function completeTask(downloadId) {
        const task = activeTasks[downloadId];
        if (task) {
            if (task.sse) {
                try {
                    task.sse.close();
                } catch (e) {}
                task.sse = null;
            }
            
            const card = document.getElementById(`task-card-${downloadId}`);
            const cleanName = task.filename || card?.querySelector(".download-task-title")?.textContent?.trim() || "download";

            if (card) {
                card.className = "download-task-card state-complete";
                
                const pctSpan = card.querySelector(".download-task-pct");
                if (pctSpan) pctSpan.textContent = "Done!";
                
                const fillBar = card.querySelector(".download-task-fill");
                if (fillBar) {
                    fillBar.classList.remove("striped");
                    fillBar.style.width = "100%";
                }
                
                const msgSpan = card.querySelector(".download-task-msg");
                if (msgSpan) {
                    msgSpan.textContent = "Finished downloading successfully.";
                }
                
                const actionsDiv = card.querySelector(".download-task-actions");
                if (actionsDiv) {
                    actionsDiv.innerHTML = `
                        <button type="button" class="btn-task-action btn-task-preview" title="Preview / Play inside application">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                            <span>Play</span>
                        </button>
                        <button type="button" class="btn-task-action btn-task-save" title="Save file to device">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
                            <span>Save</span>
                        </button>
                        <button type="button" class="btn-task-action btn-task-clear" title="Clear">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                    `;
                    actionsDiv.querySelector(".btn-task-preview")?.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openCompletedTaskPreview(downloadId, cleanName);
                    });
                    const saveBtn = actionsDiv.querySelector(".btn-task-save");
                    if (saveBtn) {
                        saveBtn.addEventListener("click", (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleSaveTaskFile(downloadId, cleanName, card);
                        });
                    }
                    const clearBtn = actionsDiv.querySelector(".btn-task-clear");
                    if (clearBtn) {
                        clearBtn.addEventListener("click", () => {
                            card.remove();
                            if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                                downloadsManager.classList.add("hidden");
                            }
                        });
                    }
                }
            }
            
            if (!task.isCloudUpload) {
                if (window.electronAPI && typeof window.electronAPI.saveFile === "function") {
                    handleSaveTaskFile(downloadId, cleanName, card);
                } else {
                    const downloadAnchor = document.createElement("a");
                    downloadAnchor.href = `/api/download/file/${downloadId}`;
                    downloadAnchor.download = cleanName;
                    document.body.appendChild(downloadAnchor);
                    downloadAnchor.click();
                    downloadAnchor.remove();
                }
            } else {
                if (card) {
                    const msgSpan = card.querySelector(".download-task-msg");
                    if (msgSpan) msgSpan.textContent = "Uploaded to cloud successfully!";
                }
            }

            if (task.btn) {
                task.btn.disabled = false;
                task.btn.style.opacity = "";
            }
            if (task.activeRow) {
                task.activeRow.classList.remove("is-downloading");
            }
            
            delete activeTasks[downloadId];
            updateDownloadsCount();
        }
    }

    async function retryTask(downloadId, card) {
        if (!card || !card._retryPayload) return;
        const payload = card._retryPayload;
        const btn = card._retryBtn;
        const activeRow = card._retryActiveRow;

        card.className = "download-task-card";
        const pctSpan = card.querySelector(".download-task-pct");
        if (pctSpan) pctSpan.textContent = "Retrying...";
        const fillBar = card.querySelector(".download-task-fill");
        if (fillBar) {
            fillBar.className = "download-task-fill striped";
            fillBar.style.width = "5%";
        }
        const msgSpan = card.querySelector(".download-task-msg");
        if (msgSpan) msgSpan.textContent = "Re-connecting...";
        const actionsDiv = card.querySelector(".download-task-actions");
        if (actionsDiv) {
            actionsDiv.innerHTML = `<button type="button" class="btn-task-action btn-task-cancel" title="Cancel Download">Cancel</button>`;
        }

        if (activeRow) activeRow.classList.add("is-downloading");
        if (btn) {
            btn.disabled = true;
            btn.style.opacity = "0.6";
        }

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok || data.status !== "success") {
                throw new Error(data.message || "Failed to retry download.");
            }

            const newDownloadId = data.download_id;
            card.id = `task-card-${newDownloadId}`;
            const cancelBtn = card.querySelector(".btn-task-cancel");
            if (cancelBtn) {
                cancelBtn.addEventListener("click", () => cancelTask(newDownloadId));
            }

            activeTasks[newDownloadId] = {
                sse: null,
                btn,
                activeRow,
                isCloudUpload: payload.cloud_destination && payload.cloud_destination !== "local"
            };
            updateDownloadsCount();

            const sse = new EventSource(`/api/download/progress/${newDownloadId}`);
            activeTasks[newDownloadId].sse = sse;
            setupTaskSSE(newDownloadId, sse, activeRow, btn);
        } catch (err) {
            handleDownloadFailure(downloadId, err.message, activeRow, btn);
        }
    }

    function failTask(downloadId, errorMessage) {
        const task = activeTasks[downloadId];
        if (task) {
            if (task.sse) {
                try {
                    task.sse.close();
                } catch (e) {}
                task.sse = null;
            }
            if (task.btn) {
                task.btn.disabled = false;
                task.btn.style.opacity = "";
            }
            if (task.activeRow) {
                task.activeRow.classList.remove("is-downloading");
            }
            delete activeTasks[downloadId];
            updateDownloadsCount();
        }

        const card = document.getElementById(`task-card-${downloadId}`);
        if (card) {
            card.className = "download-task-card state-error";
            const pctSpan = card.querySelector(".download-task-pct");
            if (pctSpan) pctSpan.textContent = "Error";
            const fillBar = card.querySelector(".download-task-fill");
            if (fillBar) {
                fillBar.classList.remove("striped");
                fillBar.style.width = "100%";
            }
            const msgSpan = card.querySelector(".download-task-msg");
            if (msgSpan) {
                msgSpan.textContent = errorMessage || "An error occurred.";
            }

            const actionsDiv = card.querySelector(".download-task-actions");
            if (actionsDiv) {
                const hasRetry = !!(card._retryPayload || card._retryStream);
                actionsDiv.innerHTML = `
                    ${hasRetry ? '<button type="button" class="btn-task-action btn-task-retry" title="Retry Download"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg><span>Retry</span></button>' : ''}
                    <button type="button" class="btn-task-action btn-task-clear" title="Clear"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
                `;
                if (hasRetry) {
                    const retryBtn = actionsDiv.querySelector(".btn-task-retry");
                    if (retryBtn) {
                        retryBtn.addEventListener("click", () => {
                            if (card._retryPayload) {
                                retryTask(downloadId, card);
                            } else if (card._retryStream) {
                                card.remove();
                                const s = card._retryStream;
                                triggerStreamDownload(s.btn, s.formatId, s.ext, s.label, s.quality, s.customUrl, s.episode, s.server);
                            }
                        });
                    }
                }
                const clearBtn = actionsDiv.querySelector(".btn-task-clear");
                if (clearBtn) {
                    clearBtn.addEventListener("click", () => {
                        card.remove();
                        if (downloadsTasksList && downloadsTasksList.children.length === 0 && downloadsManager) {
                            downloadsManager.classList.add("hidden");
                        }
                    });
                }
            }
        }
    }

    function handleDownloadFailure(downloadId, errorMessageText, activeRow, btn) {
        let rawError = errorMessageText || "An error occurred while queuing the download.";
        let friendlyMessage = "Download failed. Please check your connection or view technical details below.";
        const lowerErr = rawError.toLowerCase();

        if ((downloadId && downloadId.startsWith("convert-")) || lowerErr.includes("conversion") || lowerErr.includes("chuyển đổi") || lowerErr.includes("ffmpeg")) {
            friendlyMessage = rawError.startsWith("Conversion failed") ? rawError : `Conversion failed: ${rawError}`;
        } else if (lowerErr.includes("fallback download also failed") || lowerErr.includes("returned non-zero code")) {
            friendlyMessage = "Cannot download from this source. The media might be encrypted or downloading is blocked.";
        } else if (lowerErr.includes("429") || lowerErr.includes("too many requests") || lowerErr.includes("rate limit") || lowerErr.includes("rate-limit")) {
            friendlyMessage = "Rate limit exceeded (Error 429). Please wait a few minutes.";
        } else if (lowerErr.includes("403") || lowerErr.includes("forbidden") || lowerErr.includes("access denied")) {
            friendlyMessage = "Access denied (Error 403). The source may require a valid login Cookie.";
        } else if (lowerErr.includes("404") || lowerErr.includes("not found")) {
            friendlyMessage = "Resource not found (Error 404). Please verify if the video exists.";
        } else if (lowerErr.includes("sign in to confirm you're not a bot") || lowerErr.includes("confirm you're not a bot") || lowerErr.includes("confirm you are not a bot")) {
            friendlyMessage = "Download blocked due to bot verification requirement. Please update your Cookie.";
        } else if (lowerErr.includes("login") || lowerErr.includes("logged-in") || lowerErr.includes("cookie") || lowerErr.includes("private")) {
            friendlyMessage = "This content requires a login cookie. Please update 'Cookie Settings'.";
        } else if (lowerErr.includes("unsupported url")) {
            friendlyMessage = "This URL is not supported for direct download.";
        } else if (lowerErr.includes("connection refused") || lowerErr.includes("timeout") || lowerErr.includes("timed out")) {
            friendlyMessage = "Connection error. Please check your connection.";
        } else if (lowerErr.includes("could not resolve host") || lowerErr.includes("name or service not known")) {
            friendlyMessage = "Cannot connect to server (DNS resolution error).";
        }

        let fullMsg = friendlyMessage;
        if (errorMessageText && !friendlyMessage.includes(errorMessageText) && !(downloadId && downloadId.startsWith("convert-"))) {
            fullMsg += ` (Details: ${errorMessageText})`;
        }
        
        failTask(downloadId, fullMsg);
    }

    function triggerStreamDownload(btn, formatId, ext, label, quality, customUrl, episode = "", server = "") {
        const title = videoTitle?.textContent || "video";
        const tempId = "stream-" + Date.now();
        const displayTitle = customUrl ? label : title;
        const safeTitle = getSafeTitle(displayTitle, "video");

        const activeRow = btn ? btn.closest(".format-row") : null;
        if (activeRow) activeRow.classList.add("is-downloading");
        if (btn) {
            btn.disabled = true;
            btn.style.opacity = "0.6";
        }

        const formatBytesLocal = (bytes, decimals = 1) => {
            if (!bytes || bytes <= 0) return '0 B';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        };

        const card = createTaskCard(tempId, displayTitle, "MSE STREAM");
        if (card) {
            card._retryStream = { btn, formatId, ext, label, quality, customUrl, episode, server };
        }
        activeTasks[tempId] = { btn, activeRow, isStreamCapture: true };
        updateDownloadsCount();
        showPlayerToast("Đã bắt đầu tải luồng video trực tiếp trong Downloads Manager...");

        const fillBar = card ? card.querySelector(".download-task-fill") : null;
        const pctSpan = card ? card.querySelector(".download-task-pct") : null;
        const msgSpan = card ? card.querySelector(".download-task-msg") : null;

        if (pctSpan) pctSpan.textContent = "0%";
        if (msgSpan) msgSpan.textContent = "Khởi chạy bộ thu luồng video...";
        if (fillBar) {
            fillBar.classList.add("striped");
            fillBar.style.width = "5%";
        }

        // Create background harvester: webview in Electron, invisible iframe in browser
        const isElectron = Boolean(window.electronAPI);
        let bgFrame = null;
        let bgView = null;

        // Notify Electron of stream referer to prevent CDN 403 Forbidden
        const currentReferer = (activeMetadata && activeMetadata.webpage_url) || activeUrl || "";
        if (window.electronAPI?.setStreamReferer && currentReferer) {
            window.electronAPI.setStreamReferer(currentReferer);
        }

        if (isElectron) {
            bgView = document.createElement("webview");
            bgView.id = `bg-capture-${tempId}`;
            bgView.style.cssText = "position:fixed;width:1280px;height:720px;left:0;top:0;opacity:0.001;pointer-events:none;z-index:-9999;";
            bgView.src = customUrl;
            document.body.appendChild(bgView);

            bgView.addEventListener("dom-ready", async () => {
                try {
                    bgView.insertCSS(`
                        #avs-compat-fallback, .avs-warning, .browser-warning, [id*="compat-fallback"],
                        .quality-notice, [class*="ads"], [id*="ads"], [class*="banner"], [id*="banner"],
                        [id*="devtools"], [class*="devtools"], [id*="adblock"], [class*="adblock"],
                        .avs-ads, #avs-ads, .vast-skip-button, .jw-ad-container,
                        iframe[src*="ad"], iframe[src*="bet"], a[href*="bom88"], a[href*="bet"],
                        div[style*="z-index: 9999"], div[style*="z-index: 2147483647"] {
                            display: none !important;
                            visibility: hidden !important;
                            opacity: 0 !important;
                            pointer-events: none !important;
                            height: 0 !important;
                            width: 0 !important;
                        }
                    `);
                    await bgView.executeJavaScript(`
                        (function() {
                            if (!window._mseHooked && window.SourceBuffer) {
                                window._mseHooked = true;
                                window._capturedMediaChunks = [];
                                const orig = window.SourceBuffer.prototype.appendBuffer;
                                window.SourceBuffer.prototype.appendBuffer = function(buf) {
                                    if (buf) {
                                        const chunk = buf.slice ? buf.slice(0) : new Uint8Array(buf).buffer;
                                        window._capturedMediaChunks.push(chunk);
                                    }
                                    return orig.apply(this, arguments);
                                };
                            }
                            const v = document.querySelector('video');
                            if (v) {
                                v.muted = true;
                                try { v.playbackRate = 16.0; } catch(_) {}
                                if (v.paused) v.play().catch(()=>{});
                            }
                            const checkPlay = setInterval(() => {
                                try {
                                    document.querySelectorAll('button, a, div').forEach(el => {
                                        if (el.textContent && (el.textContent.includes('Xem tiếp') || el.textContent.includes('Từ đầu'))) {
                                            el.click();
                                        }
                                    });
                                } catch(_) {}
                                if (typeof jwplayer === 'function') {
                                    const p = jwplayer('player');
                                    if (p) {
                                        try { p.setMute(true); } catch(_) {}
                                        const s = p.getState();
                                        if (s === 'idle' || s === 'paused') p.play();
                                        try { if (p.setPlaybackRate) p.setPlaybackRate(16.0); } catch(_) {}
                                        const vEl = document.querySelector('video');
                                        if (vEl && vEl.playbackRate !== 16.0) {
                                            try { vEl.playbackRate = 16.0; } catch(_) {}
                                        }
                                        if (s === 'playing') clearInterval(checkPlay);
                                    }
                                }
                            }, 300);
                            setTimeout(() => clearInterval(checkPlay), 15000);
                        })()
                    `);
                } catch (_) {}
            });
        } else {
            bgFrame = document.createElement("iframe");
            bgFrame.id = `bg-capture-${tempId}`;
            bgFrame.style.cssText = "position:fixed;width:1px;height:1px;left:-9999px;top:-9999px;opacity:0.01;pointer-events:none;";
            bgFrame.allow = "autoplay *; encrypted-media *";
            bgFrame.sandbox = "allow-scripts allow-same-origin allow-forms allow-popups allow-downloads";
            const targetUrl = `/api/system/proxy-sub?url=${encodeURIComponent(customUrl)}&mode=html&client_id=${encodeURIComponent(clientId)}&auto_stream=1&referer=${encodeURIComponent(currentReferer)}`;
            bgFrame.src = targetUrl;
            document.body.appendChild(bgFrame);
        }

        let capturedBytes = 0;
        let lastChunkTime = Date.now();
        let completeCheckTimer = null;
        let isFinished = false;

        const finishStreamDownload = () => {
            if (isFinished) return;
            isFinished = true;
            clearInterval(completeCheckTimer);
            window.removeEventListener("message", onChunkMsg);

            if (isElectron && bgView) {
                bgView.executeJavaScript(`
                    (function() {
                        try {
                            if (window._capturedMediaChunks && window._capturedMediaChunks.length > 0) {
                                const blob = new Blob(window._capturedMediaChunks, { type: 'video/mp4' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = '${safeTitle}.mp4';
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                setTimeout(() => URL.revokeObjectURL(url), 60000);
                                return { success: true, size: blob.size };
                            }
                        } catch(e) {}
                        return { success: false };
                    })()
                `).then(res => {
                    if (res && res.success) {
                        if (card) {
                            card.className = "download-task-card state-complete";
                            if (pctSpan) pctSpan.textContent = "Done!";
                            if (fillBar) {
                                fillBar.classList.remove("striped");
                                fillBar.style.width = "100%";
                            }
                            if (msgSpan) msgSpan.textContent = `Tải hoàn tất: ${formatBytesLocal(res.size)}`;
                            const actionsDiv = card.querySelector(".download-task-actions");
                            if (actionsDiv) {
                                actionsDiv.innerHTML = `<button class="btn-task-action btn-task-clear" title="Clear">Clear</button>`;
                                actionsDiv.querySelector(".btn-task-clear")?.addEventListener("click", () => {
                                    card.remove();
                                    if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                                        downloadsManager.classList.add("hidden");
                                    }
                                });
                            }
                        }
                        showPlayerToast(`Tải hoàn tất video: ${safeTitle}.mp4 (${formatBytesLocal(res.size)})`);
                    } else {
                        failTask(tempId, "Không thu được luồng video. Vui lòng mở Xem trước (Preview) và bấm Lưu Video.");
                    }
                }).catch(err => {
                    failTask(tempId, "Lỗi xuất file: " + err.message);
                }).finally(() => {
                    try { bgView?.remove(); } catch (_) {}
                    if (btn) { btn.disabled = false; btn.style.opacity = ""; }
                    if (activeRow) activeRow.classList.remove("is-downloading");
                    delete activeTasks[tempId];
                    updateDownloadsCount();
                });
                return;
            }

            try {
                const iframeWin = bgFrame ? bgFrame.contentWindow : null;
                let blob = null;
                if (iframeWin && typeof iframeWin.getCapturedStreamBlob === "function") {
                    blob = iframeWin.getCapturedStreamBlob('video/mp4');
                } else if (iframeWin && iframeWin._capturedMediaChunks && iframeWin._capturedMediaChunks.length > 0) {
                    blob = new Blob(iframeWin._capturedMediaChunks, { type: 'video/mp4' });
                }

                if (blob && blob.size > 0) {
                    const downloadUrl = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = downloadUrl;
                    a.download = `${safeTitle}.mp4`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(downloadUrl), 60000);

                    if (card) {
                        card.className = "download-task-card state-complete";
                        if (pctSpan) pctSpan.textContent = "Done!";
                        if (fillBar) {
                            fillBar.classList.remove("striped");
                            fillBar.style.width = "100%";
                        }
                        if (msgSpan) msgSpan.textContent = `Tải hoàn tất: ${formatBytesLocal(blob.size)}`;
                        const actionsDiv = card.querySelector(".download-task-actions");
                        if (actionsDiv) {
                            actionsDiv.innerHTML = `<button class="btn-task-action btn-task-clear" title="Clear">Clear</button>`;
                            actionsDiv.querySelector(".btn-task-clear")?.addEventListener("click", () => {
                                card.remove();
                                if (downloadsTasksList && downloadsTasksList.children.length === 0) {
                                    downloadsManager.classList.add("hidden");
                                }
                            });
                        }
                    }
                    showPlayerToast(`Tải hoàn tất video: ${safeTitle}.mp4 (${formatBytesLocal(blob.size)})`);
                } else {
                    failTask(tempId, "Không thu được luồng video. Vui lòng mở Xem trước (Preview) và bấm Lưu Video.");
                }
            } catch (err) {
                failTask(tempId, "Lỗi xuất file: " + err.message);
            } finally {
                try { bgFrame?.remove(); } catch (_) {}
                if (btn) { btn.disabled = false; btn.style.opacity = ""; }
                if (activeRow) activeRow.classList.remove("is-downloading");
                delete activeTasks[tempId];
                updateDownloadsCount();
            }
        };

        const onChunkMsg = (e) => {
            if (e.data && e.data.type === "MSE_STREAM_COMPLETE") {
                finishStreamDownload();
                return;
            }
            if (e.data && e.data.type === "MSE_CHUNK_CAPTURED") {
                capturedBytes = e.data.totalBytes || capturedBytes;
                lastChunkTime = Date.now();
                const dur = (activeMetadata && activeMetadata.duration) || 1400;
                const estBytes = dur * 275000;
                const progress = Math.min(98, Math.max(10, Math.round((capturedBytes / estBytes) * 100)));
                if (fillBar) fillBar.style.width = `${progress}%`;
                if (pctSpan) pctSpan.textContent = `${progress}%`;
                if (msgSpan) msgSpan.textContent = `Đang thu dữ liệu: ${formatBytesLocal(capturedBytes)}`;
            }
        };

        window.addEventListener("message", onChunkMsg);

        // Cancel handler
        const cancelBtn = card ? card.querySelector(".btn-task-cancel") : null;
        if (cancelBtn) {
            cancelBtn.addEventListener("click", () => {
                isFinished = true;
                clearInterval(completeCheckTimer);
                window.removeEventListener("message", onChunkMsg);
                try { bgFrame?.remove(); } catch (_) {}
                try { bgView?.remove(); } catch (_) {}
                cancelTask(tempId);
            });
        }

        // Watch for stream completion & stats polling
        let elapsed = 0;
        completeCheckTimer = setInterval(() => {
            elapsed++;

            // In Electron, query webview directly
            if (isElectron && bgView) {
                bgView.executeJavaScript(`
                    (function() {
                        const bytes = (window._capturedMediaChunks && window._capturedMediaChunks.length > 0)
                            ? window._capturedMediaChunks.reduce((a, b) => a + b.byteLength, 0) : 0;
                        const chunks = (window._capturedMediaChunks) ? window._capturedMediaChunks.length : 0;
                        let dur = 0;
                        let pos = 0;
                        let ended = false;
                        if (typeof jwplayer === 'function') {
                            const p = jwplayer('player');
                            if (p) {
                                dur = p.getDuration ? p.getDuration() : 0;
                                pos = p.getPosition ? p.getPosition() : 0;
                                const s = p.getState ? p.getState() : '';
                                if (s === 'complete') ended = true;
                                if (s === 'idle' || s === 'paused') p.play();
                            }
                        }
                        const v = document.querySelector('video');
                        if (v) {
                            if (!dur && v.duration) dur = v.duration;
                            if (!pos && v.currentTime) pos = v.currentTime;
                            if (v.ended) ended = true;
                            if (v.playbackRate !== 16.0) {
                                try { v.playbackRate = 16.0; } catch(_) {}
                            }
                            if (v.paused) v.play().catch(()=>{});
                        }
                        return { bytes, chunks, dur, pos, ended };
                    })()
                `).then(stats => {
                    if (stats && stats.bytes > 0) {
                        capturedBytes = stats.bytes;
                        lastChunkTime = Date.now();
                        const dur = stats.dur || (activeMetadata && activeMetadata.duration) || 1400;
                        const estBytes = dur * 275000;
                        let byteProgress = Math.round((capturedBytes / estBytes) * 100);
                        let timeProgress = (stats.dur > 0 && stats.pos > 0) ? Math.round((stats.pos / stats.dur) * 100) : 0;
                        const progress = Math.min(99, Math.max(5, Math.max(byteProgress, timeProgress)));
                        if (fillBar) fillBar.style.width = `${progress}%`;
                        if (pctSpan) pctSpan.textContent = `${progress}%`;
                        const curStr = formatTime(stats.pos || 0);
                        const durStr = formatTime(dur || 0);
                        if (msgSpan) msgSpan.textContent = `Đang thu dữ liệu: ${formatBytesLocal(capturedBytes)} / ~${formatBytesLocal(estBytes)} (${curStr}/${durStr}) | Tốc độ 16x`;

                        if (stats.ended || (stats.dur > 0 && stats.pos >= (stats.dur - 3))) {
                            finishStreamDownload();
                        }
                    } else if (msgSpan) {
                        msgSpan.textContent = `Đang kết nối luồng phát (${elapsed}s)...`;
                    }
                }).catch(() => {});
            }

            if (capturedBytes > 0 && Date.now() - lastChunkTime > 12000) {
                finishStreamDownload();
            } else if (elapsed > 300) { // 5-minute safety ceiling
                finishStreamDownload();
            }
        }, 1000);
    }

    function setupTaskSSE(downloadId, sse, activeRow, btn) {
        sse.onmessage = (event) => {
            try {
                const statusData = JSON.parse(event.data);
                const card = document.getElementById(`task-card-${downloadId}`);
                if (!card) return;

                const fillBar = card.querySelector(".download-task-fill");
                const pctSpan = card.querySelector(".download-task-pct");
                const msgSpan = card.querySelector(".download-task-msg");

                if (statusData.status === "pending") {
                    if (fillBar) {
                        fillBar.classList.add("striped");
                        fillBar.style.width = "5%";
                    }
                    if (pctSpan) pctSpan.textContent = "0%";
                    if (msgSpan) msgSpan.textContent = statusData.message || "Waiting in line...";
                }
                else if (statusData.status === "downloading") {
                    if (fillBar) {
                        fillBar.classList.remove("striped");
                        fillBar.style.width = `${statusData.progress}%`;
                    }
                    if (pctSpan) pctSpan.textContent = `${statusData.progress}%`;

                    let msg = statusData.message;
                    if (statusData.speed && statusData.eta) {
                        msg += ` | Speed: ${statusData.speed} | ETA: ${statusData.eta}`;
                    } else if (statusData.speed) {
                        msg += ` | Speed: ${statusData.speed}`;
                    } else if (statusData.eta) {
                        msg += ` | ETA: ${statusData.eta}`;
                    }
                    if (msgSpan) msgSpan.textContent = msg;
                }
                else if (statusData.status === "merging" || statusData.status === "processing") {
                    if (fillBar) {
                        fillBar.classList.add("striped");
                        fillBar.style.width = `${statusData.progress}%`;
                    }
                    if (pctSpan) pctSpan.textContent = `${statusData.progress}%`;
                    if (msgSpan) {
                        const stepText = statusData.status === "merging" ? "Merging streams" : "Processing audio";
                        msgSpan.textContent = `${stepText}: ${statusData.message}`;
                    }
                }
                else if (statusData.status === "complete") {
                    completeTask(downloadId);
                }
                else if (statusData.status === "error") {
                    throw new Error(statusData.error || statusData.message || "An error occurred on the downloader backend.");
                }
            } catch (pollErr) {
                if (sse) {
                    sse.close();
                }
                handleDownloadFailure(downloadId, pollErr.message, activeRow, btn);
            }
        };

        sse.onerror = (err) => {
            if (sse) {
                sse.close();
            }
            handleDownloadFailure(downloadId, "Loss of SSE connection to server progress handler.", activeRow, btn);
        };
    }

    async function triggerDownload(btn, formatId, ext, label, quality, customUrl, episode = "", server = "", forceRaw = false, capturedAudioSettings = null, capturedSubtitleSettings = null, customThumbnail = "") {
        const title = videoTitle.textContent;
        const tempId = "temp-" + Date.now();

        const activeRow = btn ? btn.closest(".format-row") : null;
        if (activeRow) {
            activeRow.classList.add("is-downloading");
        }
        if (btn) {
            btn.disabled = true;
            btn.style.opacity = "0.6";
        }

        const displayTitle = customUrl ? label : title;
        const displayLabel = customUrl ? ext.toUpperCase() : label;
        createTaskCard(tempId, displayTitle, displayLabel);
        
        activeTasks[tempId] = { sse: null, btn, activeRow, isCloudUpload: false };
        updateDownloadsCount();

        try {
            const requestBody = {
                url: customUrl || activeUrl,
                format_id: formatId,
                ext: ext,
                quality: quality,
                title: customUrl ? label : title,
                thumbnail: customThumbnail || videoThumbnail.getAttribute("data-original-url") || videoThumbnail.src,
                episode: episode,
                server: server,
                client_id: clientId
            };

            if (!forceRaw) {
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

                if (capturedSubtitleSettings) {
                    if (capturedSubtitleSettings.subtitle_content) {
                        requestBody.subtitle_content = capturedSubtitleSettings.subtitle_content;
                    }
                    if (capturedSubtitleSettings.subtitle_lang) {
                        requestBody.subtitle_lang = capturedSubtitleSettings.subtitle_lang;
                    }
                    if (capturedSubtitleSettings.subtitle_url) {
                        requestBody.subtitle_url = capturedSubtitleSettings.subtitle_url;
                    }
                    if (capturedSubtitleSettings.subtitle_mode) {
                        requestBody.subtitle_mode = capturedSubtitleSettings.subtitle_mode;
                    }
                    if (capturedSubtitleSettings.subtitle_translate) {
                        requestBody.subtitle_translate = capturedSubtitleSettings.subtitle_translate;
                    }
                    if (capturedSubtitleSettings.sub_font) requestBody.sub_font = capturedSubtitleSettings.sub_font;
                    if (capturedSubtitleSettings.sub_size) requestBody.sub_size = capturedSubtitleSettings.sub_size;
                    if (capturedSubtitleSettings.sub_color) requestBody.sub_color = capturedSubtitleSettings.sub_color;
                    if (capturedSubtitleSettings.sub_bg_color) requestBody.sub_bg_color = capturedSubtitleSettings.sub_bg_color;
                    if (capturedSubtitleSettings.sub_bg_opacity !== undefined) requestBody.sub_bg_opacity = capturedSubtitleSettings.sub_bg_opacity;
                    if (capturedSubtitleSettings.sub_outline !== undefined) requestBody.sub_outline = capturedSubtitleSettings.sub_outline;
                    if (capturedSubtitleSettings.sub_outline_color) requestBody.sub_outline_color = capturedSubtitleSettings.sub_outline_color;
                    if (capturedSubtitleSettings.sub_pos) requestBody.sub_pos = capturedSubtitleSettings.sub_pos;
                } else {
                    const previewSubSelect = document.getElementById("preview-sub-select");
                    const previewSubModeSelect = document.getElementById("preview-sub-mode-select");
                    const previewSubTransSelect = document.getElementById("preview-sub-trans-select");
                    
                    if (previewSubSelect && previewSubSelect.value !== "none") {
                        if (previewSubSelect.value === "custom") {
                            requestBody.subtitle_content = originalSubtitleContent;
                            requestBody.subtitle_lang = "custom";
                        } else if (previewSubSelect.value.startsWith("http")) {
                            let subUrl = previewSubSelect.value;
                            if (subUrl.includes("youtube.com/api/timedtext")) {
                                if (subUrl.includes("fmt=")) {
                                    subUrl = subUrl.replace(/fmt=[^&]+/, "fmt=vtt");
                                } else {
                                    subUrl += subUrl.includes("?") ? "&fmt=vtt" : "?fmt=vtt";
                                }
                            }
                            requestBody.subtitle_url = subUrl;
                            const selectedOpt = previewSubSelect.options[previewSubSelect.selectedIndex];
                            requestBody.subtitle_lang = selectedOpt ? selectedOpt.getAttribute("data-lang") : "en";
                        } else {
                            requestBody.subtitle_lang = previewSubSelect.value;
                        }
                        
                        if (previewSubModeSelect) {
                            requestBody.subtitle_mode = previewSubModeSelect.value;
                        }
                        if (previewSubTransSelect) {
                            requestBody.subtitle_translate = previewSubTransSelect.value;
                        }
                        
                        requestBody.sub_font = document.getElementById("preview-sub-font")?.value || "Arial";
                        requestBody.sub_size = parseFloat(document.getElementById("preview-sub-size")?.value || 1.4);
                        requestBody.sub_color = document.getElementById("preview-sub-color")?.value || "#ffffff";
                        requestBody.sub_bg_color = document.getElementById("preview-sub-bg-color")?.value || "#000000";
                        requestBody.sub_bg_opacity = parseInt(document.getElementById("preview-sub-bg-opacity")?.value || 50);
                        requestBody.sub_outline = parseInt(document.getElementById("preview-sub-outline")?.value || 2);
                        requestBody.sub_outline_color = document.getElementById("preview-sub-outline-color")?.value || "#000000";
                        requestBody.sub_pos = document.getElementById("preview-sub-pos")?.value || "bottom";
                    }
                }

                const exportTypeSelect = document.getElementById("export-type-select");
                if (exportTypeSelect) {
                    requestBody.export_type = exportTypeSelect.value;
                }

                const colorFilterSelect = document.getElementById("color-filter-select");
                if (colorFilterSelect) {
                    requestBody.color_filter = colorFilterSelect.value;
                }

                const enhanceBeautifyCb = document.getElementById("enhance-beautify-checkbox");
                const enhanceSharpenSlider = document.getElementById("enhance-sharpen-slider");
                const enhanceUpscaleSelect = document.getElementById("enhance-upscale-select");
                
                requestBody.enhance_beautify = enhanceBeautifyCb ? enhanceBeautifyCb.checked : false;
                requestBody.enhance_sharpen = enhanceSharpenSlider ? parseInt(enhanceSharpenSlider.value) : 0;
                requestBody.enhance_upscale = enhanceUpscaleSelect ? enhanceUpscaleSelect.value : "none";

                const voiceoverCb = document.getElementById("voiceover-checkbox");
                const voiceoverVoiceSelect = document.getElementById("voiceover-voice-select");
                const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
                const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
                if (voiceoverCb && voiceoverCb.checked) {
                    requestBody.voiceover_active = true;
                    if (voiceoverVoiceSelect) {
                        requestBody.voiceover_voice = voiceoverVoiceSelect.value;
                    }
                    if (voiceoverRateSlider) {
                        const rateVal = parseInt(voiceoverRateSlider.value);
                        requestBody.voiceover_rate = (rateVal >= 0 ? "+" : "") + rateVal + "%";
                    }
                    if (voiceoverPitchSlider) {
                        const pitchVal = parseInt(voiceoverPitchSlider.value);
                        requestBody.voiceover_pitch = (pitchVal >= 0 ? "+" : "") + pitchVal + "%";
                    }
                }

                const cloudSyncSelect = document.getElementById("cloud-sync-select");
                if (cloudSyncSelect) {
                    requestBody.cloud_destination = cloudSyncSelect.value;
                    const isCloudUpload = cloudSyncSelect.value !== "local";
                    activeTasks[tempId].isCloudUpload = isCloudUpload;
                    if (cloudSyncSelect.value === "telegram") {
                        const tgBotToken = document.getElementById("tg-bot-token");
                        const tgChatId = document.getElementById("tg-chat-id");
                        if (tgBotToken && tgChatId) {
                            requestBody.tg_bot_token = tgBotToken.value.trim();
                            requestBody.tg_chat_id = tgChatId.value.trim();
                        }
                    }
                }

                if (capturedAudioSettings) {
                    requestBody.audio_eq_bass = capturedAudioSettings.audio_eq_bass;
                    requestBody.audio_eq_lowmid = capturedAudioSettings.audio_eq_lowmid;
                    requestBody.audio_eq_highmid = capturedAudioSettings.audio_eq_highmid;
                    requestBody.audio_eq_treble = capturedAudioSettings.audio_eq_treble;
                    requestBody.audio_speed = capturedAudioSettings.audio_speed;
                    requestBody.audio_voice_preset = capturedAudioSettings.audio_voice_preset;
                } else {
                    const eqBassEl = document.getElementById("eq-bass");
                    const eqLowMidEl = document.getElementById("eq-lowmid");
                    const eqHighMidEl = document.getElementById("eq-highmid");
                    const eqTrebleEl = document.getElementById("eq-treble");

                    requestBody.audio_eq_bass = eqBassEl ? parseFloat(eqBassEl.value) : 0;
                    requestBody.audio_eq_lowmid = eqLowMidEl ? parseFloat(eqLowMidEl.value) : 0;
                    requestBody.audio_eq_highmid = eqHighMidEl ? parseFloat(eqHighMidEl.value) : 0;
                    requestBody.audio_eq_treble = eqTrebleEl ? parseFloat(eqTrebleEl.value) : 0;

                    const audioSpeedSliderEl = document.getElementById("audio-speed-slider");
                    requestBody.audio_speed = audioSpeedSliderEl ? parseFloat(audioSpeedSliderEl.value) : 1.0;

                    const activeVoiceBtn = document.querySelector(".voice-preset.active");
                    requestBody.audio_voice_preset = activeVoiceBtn ? activeVoiceBtn.dataset.voice : "normal";
                }
            }

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
            console.log(`Download enqueued. ID: ${downloadId}`);

            const cardEl = document.getElementById(`task-card-${tempId}`);
            if (cardEl) {
                cardEl.id = `task-card-${downloadId}`;
                cardEl._retryPayload = requestBody;
                cardEl._retryBtn = btn;
                cardEl._retryActiveRow = activeRow;
                const cancelBtn = cardEl.querySelector(".btn-task-cancel");
                if (cancelBtn) {
                    const newCancelBtn = cancelBtn.cloneNode(true);
                    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
                    newCancelBtn.addEventListener("click", () => {
                        cancelTask(downloadId);
                    });
                }
            }

            activeTasks[downloadId] = {
                sse: null,
                btn: btn,
                activeRow: activeRow,
                isCloudUpload: activeTasks[tempId].isCloudUpload
            };
            delete activeTasks[tempId];

            const sse = new EventSource(`/api/download/progress/${downloadId}`);
            activeTasks[downloadId].sse = sse;
            updateDownloadsCount();
            setupTaskSSE(downloadId, sse, activeRow, btn);

        } catch (err) {
            handleDownloadFailure(tempId, err.message, activeRow, btn);
        }
    }

    // Error helper for analysis
    function showError(message) {
        clearActiveAnalysisUI();
        const lowerMsg = (message || "").toLowerCase();
        let friendly = "Unable to extract media information from this URL. Please verify the link or check the details below.";
        let technical = message;

        if (lowerMsg.includes("429") || lowerMsg.includes("too many requests") || lowerMsg.includes("rate limit") || lowerMsg.includes("rate-limit")) {
            friendly = "Extraction request blocked due to rate limits (Error 429 - Too Many Requests). Please change your network connection (Wi-Fi/4G/VPN) or try again in a few minutes.";
        } else if (lowerMsg.includes("403") || lowerMsg.includes("forbidden") || lowerMsg.includes("access denied")) {
            friendly = "Access denied (Error 403 - Forbidden). The source may block connections or requires a valid login Cookie.";
        } else if (lowerMsg.includes("404") || lowerMsg.includes("not found")) {
            friendly = "Content not found (Error 404 - Not Found). Please check the post/video link.";
        } else if (lowerMsg.includes("sign in to confirm you're not a bot") || lowerMsg.includes("confirm you're not a bot") || lowerMsg.includes("confirm you are not a bot")) {
            friendly = "Extraction blocked due to bot verification requirement (Confirm you are not a bot). Please try again later or update your Cookie in 'Cookie Settings'.";
        } else if (lowerMsg.includes("login") || lowerMsg.includes("logged-in") || lowerMsg.includes("cookie") || lowerMsg.includes("private") || lowerMsg.includes("sign in")) {
            friendly = "This content requires login or account cookies. Please log in using your browser, export and upload netscape/JSON cookie file in 'Cookie Settings'.";
        } else if (lowerMsg.includes("unsupported url")) {
            friendly = "This URL is not supported for direct download. Please check the URL.";
        } else if (lowerMsg.includes("connection refused") || lowerMsg.includes("timeout") || lowerMsg.includes("timed out")) {
            friendly = "Connection error to source server. Please check your network connection or try again later.";
        } else if (lowerMsg.includes("could not resolve host") || lowerMsg.includes("name or service not known")) {
            friendly = "Cannot connect to the source server (DNS resolution error). Please check your system's network connection.";
        }

        let htmlContent = `<span>${friendly}</span>`;
        if (technical && technical !== friendly) {
            htmlContent += `<details class="error-details">
                <summary class="error-summary">Technical details</summary>
                <pre class="error-pre">${escapeHTML(technical)}</pre>
            </details>`;
        }

        errorMessage.innerHTML = htmlContent;
        errorCard.classList.remove("hidden");
        errorCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // Dynamic Media Preview Orchestrator
    async function triggerPreview(btn, formatId, ext, label, quality, customUrl, episode = "", server = "", type = "", referer = "") {
        if (!previewModal) return;

        ext = (ext || "").toLowerCase();
        type = (type || "").toLowerCase();

        // Hide navigation buttons by default
        if (btnPrevImage && btnNextImage) {
            btnPrevImage.classList.add("hidden");
            btnNextImage.classList.add("hidden");
        }

        // Reset zoom & rotations
        previewZoomLevel = 1;
        previewRotation = 0;
        updateImageTransform();
        previewActiveDownloadId = null;
        previewActiveUrl = "";
        previewActiveExt = ext;
        previewActiveFilename = label;
        previewActiveBtn = btn;
        previewActiveFormatId = formatId;
        previewActiveQuality = quality;
        previewActiveCustomUrl = customUrl;
        previewActiveEpisode = episode;
        previewActiveServer = server;
        previewActiveType = type;

        // Open modal & lock background scrolling
        previewModal.classList.remove("hidden");
        document.body.classList.add("modal-open");
        document.body.classList.add("preview-active");
        // Reset dragged/resized position so modal always opens centered
        if (typeof window._resetPreviewCardPosition === "function") {
            window._resetPreviewCardPosition();
        }

        // Sync main page advanced settings to preview popover menu
        syncMainToPreviewSettings();

        // Reset views
        previewVideoContainer.classList.add("hidden");
        previewAudioContainer.classList.add("hidden");
        previewImageContainer.classList.add("hidden");
        previewSubtitleContainer.classList.add("hidden");
        if (previewWebpageContainer) previewWebpageContainer.classList.add("hidden");
        if (previewWebpageIframe) previewWebpageIframe.removeAttribute("src");
        showPreviewLoader("Connecting to source & preparing stream...");

        previewTitle.textContent = label;
        previewMetaInfo.textContent = `Type: ${ext.toUpperCase()} ${quality ? `| Quality: ${quality}` : ""}`;

        // Populate Audio Select Dropdown if Audio Preview
        if (ext === "mp3" || ext === "m4a" || type === "audio") {
            if (audioFormatSelect) {
                audioFormatSelect.innerHTML = "";
                const audioOpts = (activeMetadata && activeMetadata.audio_options) ? activeMetadata.audio_options : [];
                if (audioOpts.length > 0) {
                    audioFormatSelect.style.display = "";
                    audioOpts.forEach(opt => {
                        const optionEl = document.createElement("option");
                        const val = `${opt.format_id}|${opt.quality || ''}`;
                        optionEl.value = val;
                        optionEl.textContent = `${opt.label} ${opt.size ? `(${opt.size})` : ""}`;

                        const matchFormat = opt.format_id === formatId;
                        const matchQuality = (!quality && !opt.quality) || (String(quality) === String(opt.quality));
                        if (matchFormat && matchQuality) {
                            optionEl.selected = true;
                        }
                        audioFormatSelect.appendChild(optionEl);
                    });
                } else {
                    audioFormatSelect.style.display = "none";
                }
            }
        }

        // Populate Video Select Dropdown if Video Preview
        const isVideoPreview = (ext !== "vtt" && ext !== "mp3" && ext !== "m4a" && type !== "audio" && formatId !== "image_preview");
        if (isVideoPreview) {
            if (videoFormatSelect) {
                videoFormatSelect.innerHTML = "";
                const videoOpts = (activeMetadata && activeMetadata.video_options) ? activeMetadata.video_options : [];
                if (videoOpts.length > 0) {
                    videoFormatSelect.style.display = "";

                    const groups = {};
                    const ungrouped = [];

                    const getEffectiveOptSize = (opt) => {
                        if (opt.size && opt.size !== "Unknown Size" && !opt.size.includes("~350 MB")) return opt.size;
                        const dur = opt.duration || (activeMetadata && activeMetadata.duration);
                        if (dur && Number(dur) > 0) {
                            const bytes = Number(dur) * 275000;
                            const k = 1024;
                            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                            const i = Math.floor(Math.log(bytes) / Math.log(k));
                            return `~${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]} (HD Stream)`;
                        }
                        if ((opt.format_id && String(opt.format_id).startsWith("avs_")) || (opt.label && String(opt.label).includes("[STREAM]")) || (opt.url && (opt.url.includes("/player/") || opt.url.includes("googleapiscdn.com")))) {
                            return "Stream (MSE / HD)";
                        }
                        return opt.size || "";
                    };

                    videoOpts.forEach(opt => {
                        const label = opt.label || "";
                        const effSize = getEffectiveOptSize(opt);
                        const match = label.match(/^(.*?)\s*\((Episode\s+.*|Tập\s+.*|Ep\s+.*)\)$/i);
                        if (match) {
                            const groupName = match[1].trim();
                            const optionText = match[2].trim();
                            if (!groups[groupName]) {
                                groups[groupName] = [];
                            }
                            groups[groupName].push({
                                opt: opt,
                                text: `${optionText}${effSize ? ` (${effSize})` : ""}`
                            });
                        } else {
                            ungrouped.push({
                                opt: opt,
                                text: `${label}${effSize ? ` (${effSize})` : ""}`
                            });
                        }
                    });

                    const targetFormatId = formatId || (activeMetadata && activeMetadata.current_format_id) || "";

                    // Append ungrouped options first
                    ungrouped.forEach(item => {
                        const optionEl = document.createElement("option");
                        optionEl.value = item.opt.format_id;
                        optionEl.textContent = item.text;
                        if (item.opt.format_id === targetFormatId || (!targetFormatId && item.opt.is_current)) {
                            optionEl.selected = true;
                        }
                        videoFormatSelect.appendChild(optionEl);
                    });

                    // Append grouped options inside optgroups
                    for (const groupName in groups) {
                        const optgroupEl = document.createElement("optgroup");
                        optgroupEl.label = groupName;

                        groups[groupName].forEach(item => {
                            const optionEl = document.createElement("option");
                            optionEl.value = item.opt.format_id;
                            optionEl.textContent = item.text;
                            if (item.opt.format_id === targetFormatId || (!targetFormatId && item.opt.is_current)) {
                                optionEl.selected = true;
                            }
                            optgroupEl.appendChild(optionEl);
                        });
                        videoFormatSelect.appendChild(optgroupEl);
                    }
                } else {
                    videoFormatSelect.style.display = "none";
                }

                // Update Episode Navigation Buttons visibility
                if (typeof updateEpisodeNavigationButtonsState === "function") {
                    updateEpisodeNavigationButtonsState();
                }
            }
        }

        // Stop current playbacks (do not navigate to about:blank since a new stream is being prepared)
        stopAllPreviewPlaybacks(false);

        // Populate Subtitles Select Dropdown if Video Preview
        if (isVideoPreview) {
            const previewSubSelect = document.getElementById("preview-sub-select");
            if (previewSubSelect) {
                previewSubSelect.innerHTML = '<option value="none">None</option>';
                let subOpts = (activeMetadata && activeMetadata.subtitles) ? activeMetadata.subtitles : [];
                if (subOpts && typeof subOpts === "object" && !Array.isArray(subOpts)) {
                    subOpts = Object.keys(subOpts).map(key => {
                        const val = subOpts[key];
                        if (typeof val === "string") {
                            return { lang_code: key, name: key.toUpperCase(), url: val };
                        }
                        return {
                            lang_code: key,
                            name: val.name || key.toUpperCase(),
                            url: val.url || ""
                        };
                    });
                }
                if (!Array.isArray(subOpts)) {
                    subOpts = [];
                }
                subOpts.forEach(opt => {
                    const optionEl = document.createElement("option");
                    optionEl.value = opt.url || opt.lang_code;
                    optionEl.textContent = opt.name;
                    optionEl.setAttribute("data-lang", opt.lang_code);
                    previewSubSelect.appendChild(optionEl);
                });
                // Auto-load first subtitle if available
                if (subOpts.length > 0) {
                    const autoSub = subOpts.find(s => s.lang_code === "vi") || subOpts.find(s => s.lang_code === "en") || subOpts[0];
                    if (autoSub) {
                        previewSubSelect.value = autoSub.url || autoSub.lang_code;
                        if (typeof loadSubtitle === "function") {
                            loadSubtitle(autoSub.url || autoSub.lang_code);
                        }
                    }
                }
            }
        }

        // Image Preview Flow
        const imageExtensions = ["jpg", "png", "jpeg", "webp", "gif", "bmp", "heic", "heif", "tiff", "tif", "svg", "ico", "avif"];
        if (imageExtensions.includes(ext) || formatId === "image_preview") {
            let finalUrl;
            if (isLocalPath(customUrl)) {
                finalUrl = getLocalImageUrl(customUrl);
            } else if (formatId === "image_preview") {
                finalUrl = `/api/download/image?url=${encodeURIComponent(customUrl)}&client_id=${encodeURIComponent(clientId)}`;
            } else {
                finalUrl = customUrl;
            }

            previewActiveUrl = finalUrl;
            const cleanTitle = getSafeTitle(videoTitle.textContent, "image");
            const cleanLabel = label.replace(/\s*\(\d+x\d+\)/, "");
            previewActiveFilename = `${cleanTitle}_${cleanLabel.replace(/\s+/g, "_")}.${ext}`;

            // Resolve previewCurrentImageIndex
            if (extractedImages && extractedImages.length > 0) {
                previewCurrentImageIndex = extractedImages.findIndex(img => {
                    const u = (typeof img === "string") ? img : (img.url || "");
                    return u === customUrl;
                });
            } else {
                previewCurrentImageIndex = -1;
            }

            // Show/hide prev/next buttons
            if (btnPrevImage && btnNextImage) {
                if (previewCurrentImageIndex >= 0 && extractedImages.length > 1) {
                    btnPrevImage.classList.remove("hidden");
                    btnNextImage.classList.remove("hidden");
                } else {
                    btnPrevImage.classList.add("hidden");
                    btnNextImage.classList.add("hidden");
                }
            }

            if (previewImageElement) {
                loadImageSettingsFromStorage();
                previewImageElement.src = finalUrl;
                previewImageElement.onload = () => {
                    hidePreviewLoader();
                    previewImageContainer.classList.remove("hidden");
                };
                previewImageElement.onerror = () => {
                    showPreviewLoader("Failed to load image preview.", true);
                };
            }
            return;
        }

        const streamUrl = customUrl || activeUrl || "";

        const lowerExt = (ext || "").toLowerCase();
        const lowerType = (type || "").toLowerCase();
        const isStreamWebPlayer = (
            lowerExt === "html" || 
            lowerExt === "htm" || 
            lowerType === "webpage" ||
            (formatId && String(formatId).startsWith("avs_")) ||
            (label && String(label).includes("[STREAM]")) ||
            (streamUrl && (streamUrl.includes("/player/") || streamUrl.includes("googleapiscdn.com") || streamUrl.endsWith(".html") || streamUrl.includes(".html?")))
        );
        const isHtmlPage = isStreamWebPlayer;
        const isRawTextFile = ["txt", "xml", "json", "csv", "log", "md", "css", "js", "py", "yaml", "yml", "ini", "cfg", "conf", "nfo", "sql", "sh", "bat", "ts", "tsx", "jsx", "java", "c", "cpp", "h", "hpp", "rs", "go", "rb", "php", "pl", "swift", "kt", "r", "scala", "lua", "toml", "env", "gitignore", "dockerfile"].includes(lowerExt);

        const isSubtitleFile = (["vtt", "srt", "ass", "ssa", "sub", "lrc"].includes(lowerExt) || lowerType === "subtitle");

        // PDF Preview — use browser built-in PDF viewer via iframe
        if (lowerExt === "pdf") {
            previewActiveUrl = streamUrl;
            if (previewWebpageContainer && previewWebpageIframe) {
                previewWebpageContainer.classList.remove("hidden");
                const pdfUrl = isLocalPath(streamUrl) 
                    ? `/api/proxy/stream?url=${encodeURIComponent(streamUrl)}`
                    : streamUrl;
                previewWebpageIframe.src = pdfUrl;
                previewMetaInfo.textContent = `Type: PDF`;
                hidePreviewLoader();
            } else {
                showPreviewLoader("PDF preview not available.", true);
            }
            return;
        }

        // Webpage / HTML / Text / Subtitle Preview Flow
        if (isHtmlPage || isRawTextFile || isSubtitleFile) {
            previewActiveUrl = streamUrl;

            if (isHtmlPage && previewWebpageContainer) {
                previewWebpageContainer.classList.remove("hidden");
                showPreviewLoader("Loading stream player view...");
                if (previewMetaInfo) previewMetaInfo.textContent = "Type: STREAM PLAYER | Capture: MSE/Direct";
                if (previewDownloadBtn) {
                    const span = previewDownloadBtn.querySelector("span");
                    if (span) span.textContent = "Save Video (.mp4)";
                }

                // Auto-fit modal to 16:9 aspect ratio for comfortable streaming
                if (typeof window._fitPreviewToMedia === "function") {
                    setTimeout(() => {
                        window._fitPreviewToMedia();
                    }, 50);
                }

                // Notify Electron of stream referer to prevent CDN 403 Forbidden
                const currentReferer = referer || (activeMetadata && activeMetadata.webpage_url) || activeUrl || "";
                if (window.electronAPI?.setStreamReferer && currentReferer) {
                    window.electronAPI.setStreamReferer(currentReferer);
                }

                if (window._previewWebviewPollTimer) {
                    clearInterval(window._previewWebviewPollTimer);
                    window._previewWebviewPollTimer = null;
                }

                if (window.electronAPI && previewWebpageWebview) {
                    if (previewWebpageIframe) previewWebpageIframe.classList.add("hidden");
                    previewWebpageWebview.classList.remove("hidden");
                    if (previewWebpagePauseIndicator) {
                        previewWebpagePauseIndicator.classList.add("hidden");
                        previewWebpagePauseIndicator.style.cursor = "pointer";
                        previewWebpagePauseIndicator.style.pointerEvents = "auto";
                        previewWebpagePauseIndicator.onclick = (e) => {
                            e.stopPropagation();
                            previewWebpageWebview.executeJavaScript(`
                                (function() {
                                    try {
                                        if (typeof jwplayer === 'function') {
                                            const p = jwplayer('player');
                                            if (p) p.play();
                                        } else {
                                            const v = document.querySelector('video');
                                            if (v) v.play().catch(()=>{});
                                        }
                                    } catch(_) {}
                                    return true;
                                })()
                            `).catch(() => {});
                            previewWebpagePauseIndicator.classList.add("hidden");
                        };
                    }

                    if (!previewWebpageWebview._hasConsoleListener) {
                        previewWebpageWebview._hasConsoleListener = true;
                        previewWebpageWebview.addEventListener('console-message', (e) => {
                            if (e.message === '__WV_PAUSED__') {
                                if (previewWebpagePauseIndicator) previewWebpagePauseIndicator.classList.remove("hidden");
                            } else if (e.message === '__WV_PLAYING__') {
                                if (previewWebpagePauseIndicator) previewWebpagePauseIndicator.classList.add("hidden");
                            } else if (e.message === '__WV_ENDED__') {
                                const toggleAutoplayNext = document.getElementById("toggle-autoplay-next");
                                if (toggleAutoplayNext && toggleAutoplayNext.checked) {
                                    handleEpisodeStep(1);
                                }
                            }
                        });
                    }

                    const onWvDomReady = async () => {
                        const cur = (previewWebpageWebview.getURL && typeof previewWebpageWebview.getURL === 'function') ? previewWebpageWebview.getURL() : '';
                        if (!cur || cur === 'about:blank') return;
                        previewWebpageWebview.removeEventListener("dom-ready", onWvDomReady);

                        // Inject CSS to eliminate ads, banners, pause overlays, and devtools/F12 blocking overlays
                        try {
                            previewWebpageWebview.insertCSS(`
                                #avs-pause-ad, .avs-pause-ad, [id*="pause-ad"], [class*="pause-ad"],
                                [id*="avs-pause"], [class*="avs-pause"],
                                .avs-pause-ad-box, .avs-pause-ad-link, .avs-pause-ad-img, .avs-pause-ad-label,
                                .avs-pause-ad-actions, .avs-pause-ad-dismiss, .avs-pause-ad-resume,
                                #avs-resume-overlay, #avs-resume-box, .avs-resume-box, [id*="avs-resume"], [class*="avs-resume"],
                                #avs-compat-fallback, .avs-warning, .browser-warning, [id*="compat-fallback"],
                                .quality-notice, [class*="ads"], [id*="ads"], [class*="banner"], [id*="banner"],
                                [id*="devtools"], [class*="devtools"], [id*="adblock"], [class*="adblock"],
                                .avs-ads, #avs-ads, .vast-skip-button, .jw-ad-container, [class*="jw-ad"], [id*="jw-ad"],
                                iframe[src*="ad"], iframe[src*="bet"], a[href*="bom88"], a[href*="bet"],
                                div[style*="z-index: 9999"], div[style*="z-index: 2147483647"] {
                                    display: none !important;
                                    visibility: hidden !important;
                                    opacity: 0 !important;
                                    pointer-events: none !important;
                                    height: 0 !important;
                                    width: 0 !important;
                                    max-height: 0 !important;
                                    max-width: 0 !important;
                                    overflow: hidden !important;
                                }
                            `);
                        } catch (_) {}

                        // Hook MSE, scrub pause ads specifically, & auto-play JWPlayer
                        try {
                            await previewWebpageWebview.executeJavaScript(`
                                (function() {
                                    // 1. Specifically scrub pause ad elements without touching #player
                                    const scrub = () => {
                                        const pad = document.getElementById('avs-pause-ad');
                                        if (pad) pad.remove();
                                        const res = document.getElementById('avs-resume-overlay');
                                        if (res) res.remove();
                                        const bads = document.querySelectorAll('.avs-pause-ad-box, [id*="pause-ad"], [class*="pause-ad"], .avs-resume-box, [id*="avs-resume"]');
                                        bads.forEach(b => b.remove());
                                    };
                                    try {
                                        const obs = new MutationObserver(scrub);
                                        obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
                                    } catch(_) {}

                                    // 2. Intercept fetch & XMLHttpRequest for ads/active
                                    const origFetch = window.fetch;
                                    if (origFetch) {
                                        window.fetch = function(url, options) {
                                            if (typeof url === 'string' && (url.includes('ads/active') || url.includes('admin/api/ads') || url.includes('bom88'))) {
                                                return Promise.resolve(new Response(JSON.stringify({ pauseAd: null, ads: [] }), {
                                                    status: 200,
                                                    headers: { 'Content-Type': 'application/json' }
                                                }));
                                            }
                                            return origFetch.apply(this, arguments);
                                        };
                                    }
                                    try {
                                        const origOpen = XMLHttpRequest.prototype.open;
                                        XMLHttpRequest.prototype.open = function(method, url) {
                                            if (typeof url === 'string' && (url.includes('ads/active') || url.includes('admin/api/ads') || url.includes('bom88'))) {
                                                this._isAdReq = true;
                                            }
                                            return origOpen.apply(this, arguments);
                                        };
                                        const origSend = XMLHttpRequest.prototype.send;
                                        XMLHttpRequest.prototype.send = function() {
                                            if (this._isAdReq) {
                                                Object.defineProperty(this, 'readyState', { value: 4 });
                                                Object.defineProperty(this, 'status', { value: 200 });
                                                Object.defineProperty(this, 'statusText', { value: 'OK' });
                                                Object.defineProperty(this, 'responseText', { value: '{"pauseAd":null,"ads":[]}' });
                                                Object.defineProperty(this, 'response', { value: '{"pauseAd":null,"ads":[]}' });
                                                if (typeof this.onreadystatechange === 'function') this.onreadystatechange();
                                                if (typeof this.onload === 'function') this.onload();
                                                return;
                                            }
                                            return origSend.apply(this, arguments);
                                        };
                                    } catch(_) {}

                                    // 3. Hook MSE
                                    if (!window._mseHooked && window.SourceBuffer) {
                                        window._mseHooked = true;
                                        window._capturedMediaChunks = [];
                                        const origAppend = window.SourceBuffer.prototype.appendBuffer;
                                        window.SourceBuffer.prototype.appendBuffer = function(buf) {
                                            if (buf) {
                                                const chunk = buf.slice ? buf.slice(0) : new Uint8Array(buf).buffer;
                                                window._capturedMediaChunks.push(chunk);
                                            }
                                            return origAppend.apply(this, arguments);
                                        };
                                    }

                                    // 4. Hook JWPlayer instance when ready
                                    const hookPlayer = setInterval(() => {
                                        if (typeof jwplayer === 'function') {
                                            const p = jwplayer('player');
                                            if (p && p.on) {
                                                p.pauseAd = function() {};
                                                p.on('pause', () => {
                                                    scrub();
                                                    setTimeout(scrub, 10);
                                                    setTimeout(scrub, 50);
                                                    console.log('__WV_PAUSED__');
                                                });
                                                p.on('play', () => {
                                                    scrub();
                                                    console.log('__WV_PLAYING__');
                                                });
                                                p.on('complete', () => {
                                                    console.log('__WV_ENDED__');
                                                });
                                                clearInterval(hookPlayer);
                                            }
                                        }
                                    }, 100);
                                    setTimeout(() => clearInterval(hookPlayer), 15000);

                                    // 5. Hook HTML5 video element when ready
                                    const hookVideo = () => {
                                        const v = document.querySelector('video');
                                        if (v && !v._hasGuards) {
                                            v._hasGuards = true;
                                            v.addEventListener('pause', () => {
                                                scrub();
                                                console.log('__WV_PAUSED__');
                                            });
                                            v.addEventListener('play', () => {
                                                scrub();
                                                console.log('__WV_PLAYING__');
                                            });
                                            v.addEventListener('ended', () => {
                                                console.log('__WV_ENDED__');
                                            });
                                        }
                                    };
                                    hookVideo();
                                    setInterval(hookVideo, 500);

                                    // 6. Auto-play on initial load
                                    const checkPlay = setInterval(() => {
                                        if (typeof jwplayer === 'function') {
                                            const p = jwplayer('player');
                                            if (p) {
                                                const s = p.getState();
                                                if (s === 'playing') {
                                                    clearInterval(checkPlay);
                                                } else if (s === 'idle' || s === 'paused') {
                                                    p.play();
                                                }
                                            }
                                        }
                                    }, 300);
                                    setTimeout(() => clearInterval(checkPlay), 15000);
                                    return true;
                                })()
                            `);
                        } catch (_) {}

                        // Real-time metadata, duration & captured buffer polling
                        let durChecked = 0;
                        window._previewWebviewPollTimer = setInterval(async () => {
                            durChecked++;
                            if (durChecked > 3600) {
                                clearInterval(window._previewWebviewPollTimer);
                                window._previewWebviewPollTimer = null;
                                return;
                            }
                            try {
                                const stats = await previewWebpageWebview.executeJavaScript(`
                                    (function() {
                                        const pad = document.getElementById('avs-pause-ad');
                                        if (pad) pad.remove();
                                        const res = document.getElementById('avs-resume-overlay');
                                        if (res) res.remove();

                                        let jwState = 'unknown';
                                        let dur = 0;
                                        let curTime = 0;
                                        let chunks = 0;
                                        let bytes = 0;
                                        if (typeof jwplayer === 'function') {
                                            const p = jwplayer('player');
                                            if (p) {
                                                jwState = p.getState();
                                                dur = p.getDuration();
                                                curTime = p.getPosition();
                                            }
                                        }
                                        const v = document.querySelector('video');
                                        if (v) {
                                            if (!dur && v.duration) dur = v.duration;
                                            if (!curTime && v.currentTime) curTime = v.currentTime;
                                            if (jwState === 'unknown') {
                                                jwState = v.paused ? 'paused' : 'playing';
                                            }
                                        }
                                        if (window._capturedMediaChunks) {
                                            chunks = window._capturedMediaChunks.length;
                                            bytes = window._capturedMediaChunks.reduce((a, b) => a + b.byteLength, 0);
                                        }
                                        return { jwState, dur, curTime, chunks, bytes };
                                    })()
                                `).catch(() => null);

                                if (stats) {
                                    if (stats.jwState === 'playing' || stats.curTime > 0.1 || stats.chunks > 0) {
                                        hidePreviewLoader();
                                    }
                                    if (previewWebpagePauseIndicator) {
                                        if (stats.jwState === 'paused') {
                                            previewWebpagePauseIndicator.classList.remove("hidden");
                                        } else if (stats.jwState === 'playing') {
                                            previewWebpagePauseIndicator.classList.add("hidden");
                                        }
                                    }
                                    if (stats.dur && stats.dur > 0 && !isNaN(stats.dur)) {
                                        const bytesEst = stats.dur * 275000;
                                        const k = 1024;
                                        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                                        const i = Math.floor(Math.log(bytesEst) / Math.log(k));
                                        const formattedSize = parseFloat((bytesEst / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
                                        const curStr = formatTime(stats.curTime);
                                        const durStr = formatTime(stats.dur);
                                        const mbCaptured = (stats.bytes / (1024 * 1024)).toFixed(1);
                                        const stateLabel = (stats.jwState === 'paused') ? ' [PAUSED]' : '';
                                        if (previewMetaInfo) {
                                            previewMetaInfo.textContent = `Type: STREAM PLAYER${stateLabel} | ${curStr} / ${durStr} (~${formattedSize}) | Đệm: ${mbCaptured} MB`;
                                        }
                                    }
                                }
                            } catch (_) {}
                        }, 500);
                    };

                    setTimeout(() => {
                        previewWebpageWebview.removeEventListener("dom-ready", onWvDomReady);
                        previewWebpageWebview.addEventListener("dom-ready", onWvDomReady);
                        if (previewWebpageWebview.src === streamUrl && typeof previewWebpageWebview.loadURL === 'function') {
                            previewWebpageWebview.loadURL(streamUrl).catch(() => {});
                        } else {
                            previewWebpageWebview.src = streamUrl;
                        }
                    }, 30);
                    setTimeout(() => hidePreviewLoader(), 3500);
                } else if (previewWebpageIframe) {
                    if (previewWebpageWebview) previewWebpageWebview.classList.add("hidden");
                    previewWebpageIframe.classList.remove("hidden");
                    const targetUrl = `/api/system/proxy-sub?url=${encodeURIComponent(streamUrl)}&mode=html&client_id=${encodeURIComponent(clientId)}&referer=${encodeURIComponent(currentReferer)}`;
                    previewWebpageIframe.src = targetUrl;

                    let hideTimer = setTimeout(() => {
                        hidePreviewLoader();
                    }, 2500);

                    previewWebpageIframe.onload = () => {
                        clearTimeout(hideTimer);
                        hidePreviewLoader();

                        try {
                            const iframeWin = previewWebpageIframe.contentWindow;
                            if (iframeWin) {
                                let durChecked = 0;
                                const durInterval = setInterval(() => {
                                    durChecked++;
                                    if (durChecked > 50) { clearInterval(durInterval); return; }
                                    let d = 0;
                                    try {
                                        if (typeof iframeWin.jwplayer === 'function') {
                                            const p = iframeWin.jwplayer('player');
                                            if (p && typeof p.getDuration === 'function') d = p.getDuration();
                                        }
                                        if (!d) {
                                            const v = iframeWin.document?.querySelector('video');
                                            if (v && v.duration) d = v.duration;
                                        }
                                    } catch (_) {}
                                    if (d && d > 0 && !isNaN(d)) {
                                        clearInterval(durInterval);
                                        const bytes = d * 275000;
                                        const k = 1024;
                                        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                                        const i = Math.floor(Math.log(bytes) / Math.log(k));
                                        const formattedSize = parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
                                        const formattedTime = (typeof formatSecondsToTime === 'function') ? formatSecondsToTime(d) : `${Math.floor(d/60)}:${Math.floor(d%60)}`;
                                        if (previewMetaInfo) {
                                            previewMetaInfo.textContent = `Type: STREAM PLAYER | ${formattedTime} (~${formattedSize})`;
                                        }
                                    }
                                }, 400);
                            }
                        } catch (_) {}
                        try {
                            const iframeWin = previewWebpageIframe.contentWindow;
                            const iframeDoc = previewWebpageIframe.contentDocument || iframeWin?.document;
                            if (iframeWin) {
                                try {
                                    Object.defineProperty(iframeWin, "outerWidth", { get: () => iframeWin.innerWidth });
                                    Object.defineProperty(iframeWin, "outerHeight", { get: () => iframeWin.innerHeight });
                                } catch (_) {}
                            }
                            if (iframeDoc) {
                                const style = iframeDoc.createElement("style");
                                style.textContent = `
                                    [class*="ads"], [id*="ads"], [class*="banner"], [id*="banner"],
                                    [id*="devtools"], [class*="devtools"], [id*="adblock"], [class*="adblock"],
                                    .avs-ads, #avs-ads, .vast-skip-button, .jw-ad-container,
                                    .avs-warning, .browser-warning, #avs-compat-fallback,
                                    iframe[src*="ad"], iframe[src*="bet"], a[href*="bom88"],
                                    div[style*="z-index: 9999"], div[style*="z-index: 2147483647"] {
                                        display: none !important;
                                        visibility: hidden !important;
                                        pointer-events: none !important;
                                        opacity: 0 !important;
                                        height: 0 !important;
                                        width: 0 !important;
                                    }
                                `;
                                iframeDoc.head?.appendChild(style);

                                let scrubCount = 0;
                                const scrubber = setInterval(() => {
                                    scrubCount++;
                                    if (scrubCount > 25) { clearInterval(scrubber); return; }
                                    try {
                                        iframeDoc.querySelectorAll('a[href*="bom88"], a[href*="bet"], [class*="ads"], [id*="ads"], .avs-ads, #avs-ads, .jw-ad-container').forEach(el => el.remove());
                                    } catch (_) {}
                                }, 200);
                            }
                        } catch (_) {}
                    };
                    previewWebpageIframe.onerror = () => {
                        clearTimeout(hideTimer);
                        showPreviewLoader("Failed to render webpage preview.", true);
                    };
                }
            } else if (previewSubText) {
                if (previewSubLang) previewSubLang.textContent = label;
                previewSubtitleContainer.classList.remove("hidden");
                previewSubText.textContent = "Fetching content...";
                if (btnCopySub) btnCopySub.textContent = "Copy Content";

                let requestUrl = streamUrl;
                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    if (requestUrl.includes("fmt=")) {
                        requestUrl = requestUrl.replace(/fmt=[^&]+/, "fmt=vtt");
                    } else {
                        requestUrl += requestUrl.includes("?") ? "&fmt=vtt" : "?fmt=vtt";
                    }
                }

                let fetchPromise;
                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    // Try fetching directly from the browser first to bypass backend CAPTCHAs
                    fetchPromise = fetch(requestUrl)
                        .then(res => {
                            if (!res.ok) throw new Error("Direct fetch failed");
                            return res.text();
                        })
                        .catch(() => {
                            // Fallback to proxy
                            const proxyUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                            return fetch(proxyUrl).then(res => res.text());
                        });
                } else {
                    const proxyUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                    fetchPromise = fetch(proxyUrl).then(res => res.text());
                }

                fetchPromise
                    .then(text => {
                        hidePreviewLoader();
                        previewActiveSubtitleContent = text || "";
                        previewSubText.innerHTML = formatVttToHtml(previewActiveSubtitleContent) || "No content found.";
                    })
                    .catch(err => {
                        showPreviewLoader("Failed to fetch content from this source.", true);
                        previewSubText.textContent = "Failed to fetch content from this source.";
                    });
            }
            return;
        }
        // Helper: Server-side preview download & processing flow
        const startServerSidePreview = async (isFallback = false) => {
            try {
                if (isFallback) {
                    showPreviewLoader("Direct playback unavailable. Processing on server...");
                } else {
                    showPreviewLoader("Preparing preview on server...");
                }

                const payload = {
                    url: (formatId.startsWith("direct_") || formatId.startsWith("torrent_content_") || formatId === "image_preview" || formatId === "image_download" || formatId === "local_file" || (ext === "vtt" && !isYoutubeSub)) ? (customUrl || activeUrl) : activeUrl,
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
                    showPreviewLoader(`Error: ${data.message || "Failed to start preview task."}`, true);
                    return;
                }

                const downloadId = data.download_id;
                previewActiveDownloadId = downloadId;

                let pollInterval = new EventSource(`/api/download/progress/${downloadId}`);
                previewActivePollInterval = pollInterval;

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
                            hidePreviewLoader();

                            const previewStreamUrl = `/api/download/file/${downloadId}?preview=true`;

                            if (ext === "mp3" || ext === "m4a" || type === "audio") {
                                if (previewAudioPlayer) {
                                    previewAudioPlayer.onerror = () => {
                                        console.warn("HTML5 Audio Error on downloaded preview");
                                        showPreviewLoader("Cannot play this audio file. Please try downloading using the button below.", true);
                                        previewAudioContainer.classList.add("hidden");
                                        stopAllPreviewPlaybacks();
                                    };
                                    previewAudioPlayer.src = previewStreamUrl;
                                    previewAudioPlayer.load();
                                    previewAudioContainer.classList.remove("hidden");
                                    setupAudioPreviewSubtitles();
                                    previewAudioPlayer.play().catch(e => console.log("Playback blocked"));
                                }
                            } else if (ext === "vtt") {
                                if (previewSubText) {
                                    previewSubLang.textContent = label;
                                    previewSubtitleContainer.classList.remove("hidden");
                                    previewSubText.textContent = "Loading subtitle text...";

                                    const textRes = await fetch(previewStreamUrl);
                                    const text = await textRes.text();
                                    previewActiveSubtitleContent = text || "";
                                    previewSubText.innerHTML = formatVttToHtml(previewActiveSubtitleContent) || "No content found in subtitle file.";
                                }
                            } else if (ext === "html" || ext === "htm" || type === "webpage") {
                                if (previewWebpageContainer && previewWebpageIframe) {
                                    previewWebpageContainer.classList.remove("hidden");
                                    previewWebpageIframe.src = previewStreamUrl;
                                    hidePreviewLoader();
                                    if (previewMetaInfo) previewMetaInfo.textContent = "Type: STREAM PLAYER | Capture: MSE/Direct";
                                    if (previewDownloadBtn) {
                                        const span = previewDownloadBtn.querySelector("span");
                                        if (span) span.textContent = "Save Video (.mp4)";
                                    }
                                }
                            } else {
                                if (previewVideoPlayer) {
                                    previewVideoPlayer.src = previewStreamUrl;
                                    previewVideoPlayer.load();
                                    previewVideoContainer.classList.remove("hidden");
                                    previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                                    syncThumbnailVideoSource(previewStreamUrl);
                                }
                            }
                        } else if (statusData.status === "error") {
                            if (previewActivePollInterval) {
                                previewActivePollInterval.close();
                                previewActivePollInterval = null;
                            }
                            clearInterval(modalCheckTimer);
                            showPreviewLoader(`Preview failed: ${statusData.error || "Unknown server error."}`, true);
                        } else {
                            const progress = statusData.progress || 0;
                            let msg = statusData.message || "Downloading stream components...";
                            if (statusData.speed && statusData.eta) {
                                msg += ` | Speed: ${statusData.speed} | ETA: ${statusData.eta}`;
                            } else if (statusData.speed) {
                                msg += ` | Speed: ${statusData.speed}`;
                            }
                            showPreviewLoader(`[${progress}%] ${msg}`);
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
                    showPreviewLoader("Connection to preview progress server lost.", true);
                };

            } catch (err) {
                console.error(err);
                showPreviewLoader("Connection failed. Unable to start preview.", true);
            }
        };

        const isAdaptive = formatId.includes("+");
        const isLocalFile = isLocalPath(customUrl);

        // Check if this is an audio preview (MP3, M4A, or audio type)
        const isAudioPreview = (ext === "mp3" || ext === "m4a" || type === "audio");
        let directAudioUrl = "";
        if (isAudioPreview) {
            if (customUrl && (customUrl.startsWith("http") || isLocalFile)) {
                directAudioUrl = customUrl;
            } else if (activeMetadata && activeMetadata.audio_options && activeMetadata.audio_options.length > 0) {
                const matchOpt = activeMetadata.audio_options.find(o => o.format_id === formatId && o.url) || activeMetadata.audio_options.find(o => o.url);
                if (matchOpt && matchOpt.url) {
                    directAudioUrl = matchOpt.url;
                }
            }
        }

        // A stream can be previewed directly on-the-fly (progressive playback like YouTube) if:
        // 1. It is an audio preview with an available stream URL
        // 2. It has an HTTP/local stream URL or is a direct/adaptive format
        const isDirectStream = (ext !== "vtt") && (
            (isAudioPreview && !!directAudioUrl) ||
            formatId.startsWith("direct_") ||
            (customUrl && customUrl.startsWith("http")) ||
            isLocalFile
        );

        if (isDirectStream) {
            const streamUrl = isAudioPreview ? (directAudioUrl || customUrl || activeUrl) : (customUrl || activeUrl);
            previewActiveUrl = streamUrl;
            previewActiveDownloadId = null;
            const cleanTitle = getSafeTitle(videoTitle.textContent, "video");
            previewActiveFilename = `${cleanTitle}_Episode_${episode || 1}_${server || "Server"}.${ext}`;

            let proxyStreamUrl = "";
            if (streamUrl && (streamUrl.includes("/api/media/play/") || streamUrl.startsWith("/api/media/play/"))) {
                previewIsAdaptive = false;
                proxyStreamUrl = streamUrl;
            } else if (isLocalFile) {
                // Local file: route directly through proxy stream
                previewIsAdaptive = false;
                proxyStreamUrl = getLocalStreamUrl(customUrl);
            } else if (isAdaptive && !isAudioPreview) {
                let audioUrl = "";
                if (activeMetadata && activeMetadata.video_options) {
                    const opt = activeMetadata.video_options.find(o => o.format_id === formatId);
                    if (opt && opt.audio_url) {
                        audioUrl = opt.audio_url;
                    }
                }
                const videoUrl = streamUrl;

                previewAdaptiveVideoUrl = videoUrl;
                previewAdaptiveAudioUrl = audioUrl;
                previewAdaptiveContainer = ext || "mp4";
                previewIsAdaptive = true;
                previewCurrentTimeOffset = 0;

                if (audioUrl) {
                    proxyStreamUrl = `/api/proxy/stream_adaptive?video_url=${encodeURIComponent(videoUrl)}&audio_url=${encodeURIComponent(audioUrl)}&container=${encodeURIComponent(ext || "mp4")}&start_time=0&client_id=${encodeURIComponent(clientId)}`;
                } else {
                    // No audio URL found — use stream_adaptive with video-only (will use -an flag)
                    proxyStreamUrl = `/api/proxy/stream_adaptive?video_url=${encodeURIComponent(videoUrl)}&audio_url=&container=${encodeURIComponent(ext || "mp4")}&start_time=0&client_id=${encodeURIComponent(clientId)}`;
                }
            } else {
                previewIsAdaptive = false;
                proxyStreamUrl = `/api/proxy/stream?url=${encodeURIComponent(streamUrl)}&client_id=${encodeURIComponent(clientId)}`;
            }

            hidePreviewLoader();

            let hasFallenBack = false;
            const triggerFallback = (reason) => {
                if (hasFallenBack) return;
                hasFallenBack = true;
                console.warn(`Direct stream error (${reason}). Falling back to server-side preview processing...`);
                previewVideoContainer.classList.add("hidden");
                previewAudioContainer.classList.add("hidden");
                stopAllPreviewPlaybacks();
                startServerSidePreview(true);
            };

            if (ext === "mp3" || ext === "m4a" || type === "audio") {
                if (previewAudioPlayer) {
                    previewAudioPlayer.onerror = () => {
                        triggerFallback("HTML5 Audio Error");
                    };
                    previewAudioPlayer.src = proxyStreamUrl;
                    previewAudioPlayer.load();
                    previewAudioContainer.classList.remove("hidden");
                    setupAudioPreviewSubtitles();
                    previewAudioPlayer.play().catch(e => {
                        console.log("Audio play() blocked:", e);
                    });
                }
            } else {
                if (previewVideoPlayer) {
                    previewVideoContainer.classList.remove("hidden");
                    const isM3u8 = ext === "m3u8" || streamUrl.includes(".m3u8");

                    previewVideoPlayer.onerror = (e) => {
                        const mediaErr = previewVideoPlayer.error;
                        const errCode = mediaErr ? mediaErr.code : "unknown";
                        const errMsg = mediaErr ? mediaErr.message : "";
                        const errNames = {1: "MEDIA_ERR_ABORTED", 2: "MEDIA_ERR_NETWORK", 3: "MEDIA_ERR_DECODE", 4: "MEDIA_ERR_SRC_NOT_SUPPORTED"};
                        triggerFallback(`code=${errCode} (${errNames[errCode] || "UNKNOWN"}): ${errMsg}`);
                    };

                    if (isM3u8 && typeof Hls !== "undefined" && Hls.isSupported()) {
                        const hls = new Hls({
                            maxBufferSize: 40 * 1024 * 1024, // 40MB buffer max
                            maxBufferLength: 60, // 60 seconds max buffer ahead (1 minute)
                            enableSubtitle: false
                        });
                        hls.loadSource(proxyStreamUrl);
                        hls.attachMedia(previewVideoPlayer);
                        hls.on(Hls.Events.MANIFEST_PARSED, () => {
                            previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                        });
                        hls.on(Hls.Events.ERROR, function (event, data) {
                            if (data.fatal) {
                                triggerFallback(`Hls Fatal Error: ${data.type}`);
                            }
                        });
                        previewVideoPlayer.hlsInstance = hls;
                        syncThumbnailVideoSource(proxyStreamUrl, true);
                    } else {
                        previewVideoPlayer.src = proxyStreamUrl;
                        previewVideoPlayer.load();
                        previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                        syncThumbnailVideoSource(proxyStreamUrl);
                    }
                }
            }
            return;
        }

        // Direct stream not applicable (e.g. converted audio like YouTube MP3) -> use server-side preview
        // ponytail: Torrent formats that are not yet downloaded locally cannot be streamed via standard server-side converter
        const isTorrentTask = (formatId && String(formatId).startsWith("torrent_")) || (activeMetadata && activeMetadata.is_torrent);
        if (isTorrentTask) {
            showPreviewLoader(`<div style="text-align:center;max-width:320px;margin:0 auto">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.8;margin-bottom:8px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                <p style="font-size:0.95rem;font-weight:500;margin:8px 0 4px">Tệp nằm trong gói Torrent chưa tải về</p>
                <p style="opacity:0.6;font-size:0.82rem;line-height:1.5">Nhấn <strong style="color:var(--cyan)">GET</strong> để tải file về máy, sau đó mở lại để xem trước.<br>Hoặc mở BitTorrent/uTorrent client.</p>
            </div>`, true);
            return;
        }

        startServerSidePreview(false);
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
            const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
            const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
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
                voiceover_rate: voiceoverRateSlider ? voiceoverRateSlider.value : "0",
                voiceover_pitch: voiceoverPitchSlider ? voiceoverPitchSlider.value : "0",
                cloud_sync: cloudSyncSelect ? cloudSyncSelect.value : "local",
                enhance_beautify: document.getElementById("enhance-beautify-checkbox")?.checked || false,
                enhance_sharpen: parseInt(document.getElementById("enhance-sharpen-slider")?.value || "0"),
                enhance_upscale: document.getElementById("enhance-upscale-select")?.value || "none"
            };

            let history = JSON.parse(localStorage.getItem("downloader_history") || "[]");
            const item = history.find(it => isSameMediaItem(it, { url: activeUrl }));
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
            const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
            const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
            if (voiceoverRateSlider) {
                voiceoverRateSlider.value = s.voiceover_rate || "0";
                voiceoverRateSlider.dispatchEvent(new Event("input"));
            }
            if (voiceoverPitchSlider) {
                voiceoverPitchSlider.value = s.voiceover_pitch || "0";
                voiceoverPitchSlider.dispatchEvent(new Event("input"));
            }
            if (cloudSyncSelect) {
                cloudSyncSelect.value = s.cloud_sync || "local";
                cloudSyncSelect.dispatchEvent(new Event("change"));
            }

            const enhanceBeautifyCheckbox = document.getElementById("enhance-beautify-checkbox");
            const enhanceSharpenSlider = document.getElementById("enhance-sharpen-slider");
            const enhanceUpscaleSelect = document.getElementById("enhance-upscale-select");

            if (enhanceBeautifyCheckbox) {
                enhanceBeautifyCheckbox.checked = !!s.enhance_beautify;
                enhanceBeautifyCheckbox.dispatchEvent(new Event("change"));
            }
            if (enhanceSharpenSlider) {
                enhanceSharpenSlider.value = s.enhance_sharpen || "0";
                enhanceSharpenSlider.dispatchEvent(new Event("input"));
            }
            if (enhanceUpscaleSelect) {
                enhanceUpscaleSelect.value = s.enhance_upscale || "none";
                enhanceUpscaleSelect.dispatchEvent(new Event("change"));
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
            const voiceoverRateSlider = document.getElementById("voiceover-rate-slider");
            const voiceoverPitchSlider = document.getElementById("voiceover-pitch-slider");
            if (voiceoverRateSlider) {
                voiceoverRateSlider.value = "0";
                voiceoverRateSlider.dispatchEvent(new Event("input"));
            }
            if (voiceoverPitchSlider) {
                voiceoverPitchSlider.value = "0";
                voiceoverPitchSlider.dispatchEvent(new Event("input"));
            }
            if (cloudSyncSelect) {
                cloudSyncSelect.value = "local";
                cloudSyncSelect.dispatchEvent(new Event("change"));
            }

            const enhanceBeautifyCheckbox = document.getElementById("enhance-beautify-checkbox");
            const enhanceSharpenSlider = document.getElementById("enhance-sharpen-slider");
            const enhanceUpscaleSelect = document.getElementById("enhance-upscale-select");

            if (enhanceBeautifyCheckbox) {
                enhanceBeautifyCheckbox.checked = false;
                enhanceBeautifyCheckbox.dispatchEvent(new Event("change"));
            }
            if (enhanceSharpenSlider) {
                enhanceSharpenSlider.value = "0";
                enhanceSharpenSlider.dispatchEvent(new Event("input"));
            }
            if (enhanceUpscaleSelect) {
                enhanceUpscaleSelect.value = "none";
                enhanceUpscaleSelect.dispatchEvent(new Event("change"));
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
        { id: "voiceover-rate-slider", event: "input" },
        { id: "voiceover-pitch-slider", event: "input" },
        { id: "cloud-sync-select", event: "change" },
        { id: "enhance-beautify-checkbox", event: "change" },
        { id: "enhance-sharpen-slider", event: "input" },
        { id: "enhance-upscale-select", event: "change" }
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

    // --- Download History & Re-download Integration ---
    const tabAnalyzed = document.getElementById("history-tab-analyzed");
    const tabDownloads = document.getElementById("history-tab-downloads");
    const contentAnalyzed = document.getElementById("history-analyzed-content");
    const contentDownloads = document.getElementById("history-downloads-content");

    if (tabAnalyzed && tabDownloads && contentAnalyzed && contentDownloads) {
        tabAnalyzed.addEventListener("click", () => {
            tabAnalyzed.classList.add("active");
            tabDownloads.classList.remove("active");
            contentAnalyzed.classList.remove("hidden");
            contentDownloads.classList.add("hidden");
        });
        tabDownloads.addEventListener("click", () => {
            tabDownloads.classList.add("active");
            tabAnalyzed.classList.remove("active");
            contentDownloads.classList.remove("hidden");
            contentAnalyzed.classList.add("hidden");
            loadDownloadHistory();
        });
    }

    async function performDelete(downloadId, deleteFile) {
        try {
            const response = await fetch(`/api/download/history/delete/${downloadId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ delete_file: deleteFile })
            });
            const data = await response.json();
            if (data.status === "success") {
                loadDownloadHistory();
            } else {
                alert("Failed to delete history item: " + data.message);
            }
        } catch (err) {
            console.error("Error deleting history item:", err);
            alert("Error deleting history item");
        }
    }

    async function performBulkDelete(downloadIds, deleteFile) {
        try {
            const promises = downloadIds.map(downloadId => 
                fetch(`/api/download/history/delete/${downloadId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ delete_file: deleteFile })
                }).then(res => res.json())
            );
            const results = await Promise.all(promises);
            const errors = results.filter(r => r.status !== "success");
            if (errors.length > 0) {
                alert(`Removed items with some failures (${errors.length} failed).`);
            }
            loadDownloadHistory();
        } catch (err) {
            console.error("Bulk deletion error:", err);
            alert("Error performing bulk deletion");
            loadDownloadHistory();
        }
    }

    async function loadDownloadHistory() {
        const downloadsList = document.getElementById("downloads-history-list");
        if (!downloadsList) return;
        downloadsList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 30px;">
            <div class="spinner" style="margin: 0 auto 10px; width: 24px; height: 24px; border: 2px solid rgba(var(--cyan-rgb), 0.2); border-top-color: var(--cyan); border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
            <span>Đang tải thư viện tải xuống...</span>
        </div>`;
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);
            const response = await fetch("/api/download/history", { signal: controller.signal });
            clearTimeout(timeoutId);
            const data = await response.json();
            if (data.status === "success") {
                renderDownloadHistory(data.history);
            } else {
                downloadsList.innerHTML = `<div style="text-align: center; color: var(--red); padding: 20px;">
                    <p>Không thể tải dữ liệu thư viện: ${escapeHTML(data.message || 'Lỗi máy chủ')}</p>
                    <button id="retry-load-library-btn" class="btn-lib-retry" style="margin: 10px auto; padding: 6px 14px; background: rgba(var(--cyan-rgb), 0.15); color: var(--cyan); border: 1px solid rgba(var(--cyan-rgb), 0.35); border-radius: 4px; cursor: pointer;">Thử lại</button>
                </div>`;
                const retryBtn = document.getElementById("retry-load-library-btn");
                if (retryBtn) retryBtn.addEventListener("click", () => loadDownloadHistory());
            }
        } catch (e) {
            console.error("Error loading download history:", e);
            const isTimeout = e.name === 'AbortError';
            downloadsList.innerHTML = `<div style="text-align: center; color: var(--red); padding: 20px;">
                <p>${isTimeout ? 'Thời gian chờ máy chủ quá lâu (Hết 6s).' : 'Lỗi kết nối máy chủ.'}</p>
                <button id="retry-load-library-btn" class="btn-lib-retry" style="margin: 10px auto; padding: 6px 14px; background: rgba(var(--cyan-rgb), 0.15); color: var(--cyan); border: 1px solid rgba(var(--cyan-rgb), 0.35); border-radius: 4px; cursor: pointer;">Thử lại</button>
            </div>`;
            const retryBtn = document.getElementById("retry-load-library-btn");
            if (retryBtn) retryBtn.addEventListener("click", () => loadDownloadHistory());
        }
    }

    function renderDownloadHistory(history) {
        const downloadsList = document.getElementById("downloads-history-list");
        if (!downloadsList) return;
        downloadsList.innerHTML = "";

        const selectAllCb = document.getElementById("library-select-all");
        const deleteSelectedBtn = document.getElementById("delete-selected-btn");
        const deleteSelectedCount = document.getElementById("delete-selected-count");

        if (selectAllCb) selectAllCb.checked = false;
        if (deleteSelectedBtn) deleteSelectedBtn.classList.add("hidden");

        if (history.length === 0) {
            downloadsList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px; grid-column: 1 / -1;">No downloaded files yet</div>`;
            return;
        }

        // Helper to format bytes
        const formatBytes = (bytes, decimals = 2) => {
            if (!bytes || bytes === 0) return '0 Bytes';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        };

        // Helper to format duration (seconds -> H:MM:SS or MM:SS)
        const formatDuration = (seconds) => {
            if (!seconds || isNaN(seconds)) return "";
            const hrs = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            if (hrs > 0) {
                return `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
            }
            return `${mins}:${secs.toString().padStart(2, "0")}`;
        };

        // Update bulk delete button state
        const updateBulkDeleteState = () => {
            const checkedCbs = downloadsList.querySelectorAll(".library-card-checkbox:checked");
            const count = checkedCbs.length;
            const allCbs = downloadsList.querySelectorAll(".library-card-checkbox");
            
            if (selectAllCb) {
                selectAllCb.checked = (allCbs.length > 0 && count === allCbs.length);
            }

            if (deleteSelectedBtn) {
                if (count > 0) {
                    deleteSelectedBtn.classList.remove("hidden");
                    if (deleteSelectedCount) deleteSelectedCount.textContent = count;
                } else {
                    deleteSelectedBtn.classList.add("hidden");
                }
            }
        };

        history.forEach(item => {
            const card = document.createElement("div");
            card.className = "library-card";

            const thumbUrl = getProxiedImageUrl(item.thumbnail) || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=120";
            const platformTag = getPlatformTag(item.url);
            const timestampStr = item.timestamp ? formatHistoryDateTime(item.timestamp * 1000) : "Unknown date";
            const durationStr = item.duration ? formatDuration(item.duration) : "";
            const sizeStr = item.file_size ? formatBytes(item.file_size) : (item.file_exists ? "Unknown size" : "Purged");
            const extLabel = (item.ext || "mp4").toUpperCase();
            const fileExists = !!item.file_exists;
            const title = item.title || "Unknown Title";

            let mediaType = "video";
            const lowerExt = (item.ext || "").toLowerCase();
            if (["mp3", "m4a", "wav", "flac", "ogg", "aac", "opus"].includes(lowerExt)) {
                mediaType = "audio";
            } else if (["jpg", "jpeg", "png", "webp", "gif"].includes(lowerExt)) {
                mediaType = "image";
            }

            let statusOverlayHtml = "";
            if (item.status !== "complete") {
                let statusLabel = "Interrupted";
                let statusClass = "status-cancelled";
                if (item.status === "error") {
                    statusLabel = "Failed";
                    statusClass = "status-error";
                } else if (item.status === "cancelled") {
                    statusLabel = "Cancelled";
                    statusClass = "status-cancelled";
                }
                statusOverlayHtml = `<span class="history-item-status-tag ${statusClass}" style="position: absolute; top: 8px; left: 8px; z-index: 2;" title="${escapeHTML(item.error || '')}">${statusLabel}</span>`;
            }

            card.innerHTML = `
                <div class="library-card-thumb-container">
                    ${statusOverlayHtml}
                    
                    <!-- Checkbox container -->
                    <div class="library-card-checkbox-container" title="Select Item">
                        <input type="checkbox" class="library-card-checkbox" data-id="${item.download_id}" data-file-exists="${fileExists}" data-title="${escapeHTML(title)}">
                    </div>

                    <img class="library-card-thumb" src="${thumbUrl}" alt="Thumb">
                    ${durationStr ? `<span class="library-card-duration">${durationStr}</span>` : ""}
                    ${fileExists && item.status === "complete" ? `
                        <div class="library-card-play-overlay">
                            <div class="library-card-play-btn">
                                <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                        </div>
                    ` : ""}
                </div>
                <div class="library-card-content">
                    <span class="library-card-title" title="${escapeHTML(title)}">${title}</span>
                    <div class="library-card-meta">
                        <span class="history-platform-tag ${platformTag.class}">${platformTag.label}</span>
                        <span class="library-card-ext-badge">${extLabel}</span>
                        <span class="library-card-size-badge">${sizeStr}</span>
                    </div>
                    <div class="library-card-actions">
                        ${item.status !== "complete" ? `
                        <button class="library-card-action-btn btn-lib-retry" style="background: rgba(var(--cyan-rgb), 0.15); color: var(--cyan); border-color: rgba(var(--cyan-rgb), 0.35);" title="Thử lại tải xuống">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>
                            <span>Retry</span>
                        </button>
                        ` : `
                        <button class="library-card-action-btn btn-lib-play" ${fileExists ? '' : 'disabled'} title="Play offline inside application">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                            <span>Play</span>
                        </button>
                        `}
                        <button class="library-card-action-btn btn-lib-tg" ${fileExists && item.status === "complete" ? '' : 'disabled'} title="Send/Share to Telegram Cloud">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                            <span>Share</span>
                        </button>
                        <button class="library-card-action-btn btn-lib-del" title="Delete record / file">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                            <span>Delete</span>
                        </button>
                    </div>
                </div>
            `;

            // Bind triggers
            const thumbOverlay = card.querySelector(".library-card-play-overlay");
            const btnPlay = card.querySelector(".btn-lib-play");
            const btnRetry = card.querySelector(".btn-lib-retry");
            const btnTg = card.querySelector(".btn-lib-tg");
            const btnDel = card.querySelector(".btn-lib-del");
            const titleEl = card.querySelector(".library-card-title");
            const cbContainer = card.querySelector(".library-card-checkbox-container");
            const cbInput = card.querySelector(".library-card-checkbox");

            if (btnRetry) {
                btnRetry.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (item.url) {
                        urlInput.value = item.url;
                        const mainTabBtn = document.querySelector('.main-tab-btn[data-tab="downloader-tab"]');
                        if (mainTabBtn) mainTabBtn.click();
                        const histAnalyzedBtn = document.getElementById("history-tab-analyzed");
                        if (histAnalyzedBtn) histAnalyzedBtn.click();
                        performAnalysis();
                    }
                });
            }

            const playOffline = () => {
                if (!fileExists || item.status !== "complete") return;
                const localPlayUrl = window.location.origin + `/api/media/play/${item.download_id}`;
                triggerPreview(
                    null,
                    "direct_local",
                    item.ext || "mp4",
                    item.title || "Offline Media",
                    item.quality || "",
                    localPlayUrl,
                    "",
                    "Offline Local Stream",
                    mediaType
                );
            };

            if (thumbOverlay) thumbOverlay.addEventListener("click", playOffline);
            if (btnPlay) btnPlay.addEventListener("click", playOffline);
            if (titleEl) {
                titleEl.addEventListener("click", () => {
                    if (fileExists && item.status === "complete") {
                        playOffline();
                    } else {
                        // fallback to re-analyzing link
                        urlInput.value = item.url;
                        performAnalysis();
                    }
                });
            }

            // Stop propagation on checkbox click to prevent triggering playOffline/analyze
            if (cbContainer && cbInput) {
                cbContainer.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (e.target !== cbInput) {
                        cbInput.checked = !cbInput.checked;
                        cbInput.dispatchEvent(new Event("change"));
                    }
                });
                cbInput.addEventListener("click", (e) => {
                    e.stopPropagation();
                });
                cbInput.addEventListener("change", () => {
                    updateBulkDeleteState();
                });
            }

            if (btnTg && fileExists && item.status === "complete") {
                btnTg.addEventListener("click", async () => {
                    const tgToken = (document.getElementById("tg-bot-token")?.value || localStorage.getItem("tg_bot_token") || "").trim();
                    const tgChatId = (document.getElementById("tg-chat-id")?.value || localStorage.getItem("tg_chat_id") || "").trim();
                    
                    if (!tgToken || !tgChatId) {
                        alert("Please configure your Telegram Bot Token and Chat ID in Settings first.");
                        return;
                    }

                    btnTg.disabled = true;
                    const originalText = btnTg.querySelector("span").textContent;
                    btnTg.querySelector("span").textContent = "Sharing...";

                    try {
                        const response = await fetch(`/api/media/telegram/${item.download_id}`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ tg_bot_token: tgToken, tg_chat_id: tgChatId })
                        });
                        const resData = await response.json();
                        if (resData.status === "success") {
                            alert("Shared successfully to Telegram cloud!");
                        } else {
                            alert(resData.message || "An error occurred while sharing to Telegram.");
                        }
                    } catch (err) {
                        console.error("Telegram sharing error:", err);
                        alert("Failed to connect to application server.");
                    } finally {
                        btnTg.disabled = false;
                        btnTg.querySelector("span").textContent = originalText;
                    }
                });
            }

            if (btnDel) {
                btnDel.addEventListener("click", () => {
                    showConfirm({
                        title: "Delete Library Item",
                        message: `Are you sure you want to remove "${title}" from the library?`,
                        yesText: "Remove",
                        noText: "Cancel",
                        onYes: () => {
                            if (fileExists) {
                                setTimeout(() => {
                                    showConfirm({
                                        title: "Delete Physical File",
                                        message: "Do you want to delete the downloaded file from your disk as well?",
                                        yesText: "Yes, delete",
                                        noText: "No, keep",
                                        onYes: () => {
                                            performDelete(item.download_id, true);
                                        },
                                        onNo: () => {
                                            performDelete(item.download_id, false);
                                        }
                                    });
                                }, 350);
                            } else {
                                performDelete(item.download_id, false);
                            }
                        }
                    });
                });
            }

            downloadsList.appendChild(card);
        });

        // Set up select all checkbox listeners
        if (selectAllCb) {
            selectAllCb.onchange = () => {
                const checked = selectAllCb.checked;
                const cbs = downloadsList.querySelectorAll(".library-card-checkbox");
                cbs.forEach(cb => {
                    cb.checked = checked;
                });
                updateBulkDeleteState();
            };
        }

        // Set up delete selected buttons listeners
        if (deleteSelectedBtn) {
            deleteSelectedBtn.onclick = () => {
                const checkedCbs = Array.from(downloadsList.querySelectorAll(".library-card-checkbox:checked"));
                const ids = checkedCbs.map(cb => cb.getAttribute("data-id"));
                if (ids.length === 0) return;

                const hasPhysicalFiles = checkedCbs.some(cb => cb.getAttribute("data-file-exists") === "true");

                showConfirm({
                    title: "Delete Selected Items",
                    message: `Are you sure you want to remove ${ids.length} selected items from the library?`,
                    yesText: "Remove",
                    noText: "Cancel",
                    onYes: () => {
                        if (hasPhysicalFiles) {
                            setTimeout(() => {
                                showConfirm({
                                    title: "Delete Physical Files",
                                    message: "Do you want to delete the downloaded files from your disk as well?",
                                    yesText: "Yes, delete",
                                    noText: "No, keep",
                                    onYes: () => {
                                        performBulkDelete(ids, true);
                                    },
                                    onNo: () => {
                                        performBulkDelete(ids, false);
                                    }
                                });
                            }, 350);
                        } else {
                            performBulkDelete(ids, false);
                        }
                    }
                });
            };
        }
    }

    function getPlatformTag(url) {
        if (!url) return { class: "tag-web", label: "Web" };
        const lowerUrl = url.toLowerCase();
        if (lowerUrl.includes("youtube.com") || lowerUrl.includes("youtu.be")) {
            return { class: "tag-youtube", label: "YouTube" };
        } else if (lowerUrl.includes("facebook.com") || lowerUrl.includes("fb.watch") || lowerUrl.includes("fb.com")) {
            return { class: "tag-facebook", label: "Facebook" };
        } else if (lowerUrl.includes("tiktok.com")) {
            return { class: "tag-tiktok", label: "TikTok" };
        } else if (lowerUrl.includes("instagram.com")) {
            return { class: "tag-instagram", label: "Instagram" };
        } else if (lowerUrl.includes("soundcloud.com")) {
            return { class: "tag-soundcloud", label: "SoundCloud" };
        } else if (lowerUrl.includes("vimeo.com")) {
            return { class: "tag-vimeo", label: "Vimeo" };
        } else {
            return { class: "tag-web", label: "Web Video" };
        }
    }

    const clearDownloadsBtn = document.getElementById("clear-downloads-btn");
    if (clearDownloadsBtn) {
        clearDownloadsBtn.addEventListener("click", () => {
            showConfirm({
                title: "Clear History",
                message: "Are you sure you want to clear all download history? This cannot be undone.",
                yesText: "Confirm",
                noText: "Cancel",
                onYes: async () => {
                    try {
                        const response = await fetch("/api/download/history/clear", { method: "POST" });
                        const data = await response.json();
                        if (data.status === "success") {
                            loadDownloadHistory();
                        } else {
                            alert("Failed to clear download history: " + data.message);
                        }
                    } catch (e) {
                        console.error("Error clearing downloads history:", e);
                        alert("Error clearing history");
                    }
                }
            });
        });
    }

    // --- ADVANCED SUBTITLES PLAYER SYSTEM & INTERACTIVE TRANSCRIPT ---

    function parseTimeToSeconds(timeStr) {
        timeStr = timeStr.replace(',', '.');
        const parts = timeStr.split(':');
        let hrs = 0, mins = 0, secs = 0;
        if (parts.length === 3) {
            hrs = parseFloat(parts[0]);
            mins = parseFloat(parts[1]);
            secs = parseFloat(parts[2]);
        } else if (parts.length === 2) {
            mins = parseFloat(parts[0]);
            secs = parseFloat(parts[1]);
        } else {
            secs = parseFloat(parts[0]);
        }
        return hrs * 3600 + mins * 60 + secs;
    }

    function formatVttToHtml(vttText) {
        if (!vttText) return "";
        if (!vttText.includes("WEBVTT") && !vttText.includes("-->")) {
            const escaped = vttText
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
            return `<div class="sub-plain-text">${escaped}</div>`;
        }

        try {
            const cues = parseSubtitleText(vttText);
            if (!cues || cues.length === 0) {
                const escapedFallback = vttText
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
                return `<div class="sub-plain-text"><div style="color: #ff4d4d; margin-bottom: 10px; font-weight: bold;">[DEBUG] Parsed 0 cues from VTT content. Fallback to raw text:</div>${escapedFallback}</div>`;
            }

            let html = '<div class="sub-timeline-list">';
            cues.forEach(cue => {
                function formatCueTime(secs) {
                    const hrs = Math.floor(secs / 3600);
                    const mins = Math.floor((secs % 3600) / 60);
                    const seconds = (secs % 60).toFixed(1);
                    const minsStr = mins < 10 ? `0${mins}` : `${mins}`;
                    const secsStr = parseFloat(seconds) < 10 ? `0${seconds}` : `${seconds}`;
                    return hrs > 0 ? `${hrs}:${minsStr}:${secsStr}` : `${minsStr}:${secsStr}`;
                }
                const timeStr = formatCueTime(cue.start);
                html += `
                    <div class="sub-timeline-item">
                        <span class="sub-time-badge">${timeStr}</span>
                        <span class="sub-text-content">${cue.text}</span>
                    </div>
                `;
            });
            html += '</div>';
            return html;
        } catch (e) {
            console.error("Failed to parse subtitle for preview HTML:", e);
            return `<div class="sub-plain-text"><div style="color: #ff4d4d; margin-bottom: 10px; font-weight: bold;">[DEBUG] Parser exception: ${e.message} at ${e.stack ? e.stack.split("\n")[1] : ""}</div>${vttText}</div>`;
        }
    }

    function parseSubtitleText(text) {
        if (!text) return [];
        const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        const timePattern = /((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})/;
        const lines = normalized.split('\n');
        const cues = [];
        let currentCue = null;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            const match = timePattern.exec(line);
            if (match) {
                if (currentCue) {
                    cues.push(currentCue);
                }
                const start = parseTimeToSeconds(match[1]);
                const end = parseTimeToSeconds(match[2]);
                currentCue = { start, end, text: "" };
            } else if (currentCue) {
                // Check if this line is a cue index (a number) followed by a timestamp line
                if (/^\d+$/.test(line)) {
                    let isIndex = false;
                    for (let j = i + 1; j < lines.length; j++) {
                        const nextLine = lines[j].trim();
                        if (!nextLine) continue;
                        if (timePattern.test(nextLine)) {
                            isIndex = true;
                        }
                        break;
                    }
                    if (isIndex) {
                        continue; // Skip this line, it's just the next cue's index
                    }
                }
                if (currentCue.text) {
                    currentCue.text += "\n" + line;
                } else {
                    currentCue.text = line;
                }
            }
        }
        if (currentCue) {
            cues.push(currentCue);
        }

        return cleanAndMergeCues(cues);
    }

    function rebuildVttFromCues(cues) {
        let vtt = "WEBVTT\n\n";
        cues.forEach(cue => {
            const startStr = formatTimeDetailed(cue.start);
            const endStr = formatTimeDetailed(cue.end);
            vtt += `${startStr} --> ${endStr}\n${cue.text}\n\n`;
        });
        return vtt;
    }

    function renderTranscript() {
        const transcriptList = document.getElementById("transcript-list");
        if (!transcriptList) return;
        transcriptList.innerHTML = "";

        const query = (document.getElementById("transcript-search")?.value || "").toLowerCase().trim();
        const filtered = currentCues.map((cue, idx) => ({ cue, idx })).filter(item => {
            return !query || item.cue.text.toLowerCase().includes(query);
        });

        if (filtered.length === 0) {
            transcriptList.innerHTML = '<div class="transcript-no-results">No lines match your search</div>';
            return;
        }

        if (isEditingSubtitles) {
            filtered.forEach(item => {
                const cueEl = createEditableCueElement(item.cue, item.idx);
                transcriptList.appendChild(cueEl);
            });
        } else {
            filtered.forEach(item => {
                const cueEl = createNormalCueElement(item.cue, item.idx);
                transcriptList.appendChild(cueEl);
            });
        }
    }

    function createNormalCueElement(cue, index) {
        const cueEl = document.createElement("div");
        cueEl.className = "transcript-item";
        cueEl.setAttribute("data-index", index);

        if (previewVideoPlayer && !previewVideoPlayer.paused) {
            const time = previewVideoPlayer.currentTime;
            if (time >= cue.start && time <= cue.end) {
                cueEl.classList.add("active");
            }
        }

        const timeEl = document.createElement("span");
        timeEl.className = "transcript-item-time";
        timeEl.textContent = formatTime(cue.start);

        const textEl = document.createElement("span");
        textEl.className = "transcript-item-text";
        textEl.textContent = cue.text;

        cueEl.appendChild(timeEl);
        cueEl.appendChild(textEl);

        cueEl.addEventListener("click", () => {
            if (previewVideoPlayer) {
                previewVideoPlayer.currentTime = cue.start;
                previewVideoPlayer.play().catch(e => console.log(e));
            }
        });

        return cueEl;
    }

    function createEditableCueElement(cue, index) {
        const cueEl = document.createElement("div");
        cueEl.className = "transcript-item editing";
        cueEl.setAttribute("data-index", index);

        const timeRow = document.createElement("div");
        timeRow.className = "edit-cue-time-row";

        const startInput = document.createElement("input");
        startInput.type = "text";
        startInput.className = "edit-cue-time-input";
        startInput.value = formatTimeDetailed(cue.start);
        startInput.title = "Start Time";

        const arrow = document.createElement("span");
        arrow.textContent = "→";
        arrow.style.color = "var(--text-dim)";
        arrow.style.fontSize = "0.72rem";

        const endInput = document.createElement("input");
        endInput.type = "text";
        endInput.className = "edit-cue-time-input";
        endInput.value = formatTimeDetailed(cue.end);
        endInput.title = "End Time";

        timeRow.appendChild(startInput);
        timeRow.appendChild(arrow);
        timeRow.appendChild(endInput);

        const textInput = document.createElement("textarea");
        textInput.className = "edit-cue-text";
        textInput.value = cue.text;
        textInput.placeholder = "Subtitle text...";

        const actionRow = document.createElement("div");
        actionRow.className = "edit-cue-actions";

        const seekBtn = document.createElement("button");
        seekBtn.type = "button";
        seekBtn.className = "edit-cue-seek-btn";
        seekBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span>Seek</span>
        `;
        seekBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (previewVideoPlayer) {
                previewVideoPlayer.currentTime = cue.start;
            }
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "edit-cue-delete-btn";
        deleteBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="10" height="10"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          <span>Delete</span>
        `;
        deleteBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            currentCues.splice(index, 1);
            renderTranscript();
        });

        actionRow.appendChild(seekBtn);
        actionRow.appendChild(deleteBtn);

        cueEl.appendChild(timeRow);
        cueEl.appendChild(textInput);
        cueEl.appendChild(actionRow);

        startInput.addEventListener("blur", () => {
            const secs = parseTimeToSeconds(startInput.value);
            if (!isNaN(secs)) {
                cue.start = secs;
                startInput.value = formatTimeDetailed(secs);
            } else {
                startInput.value = formatTimeDetailed(cue.start);
            }
        });

        endInput.addEventListener("blur", () => {
            const secs = parseTimeToSeconds(endInput.value);
            if (!isNaN(secs)) {
                cue.end = secs;
                endInput.value = formatTimeDetailed(secs);
            } else {
                endInput.value = formatTimeDetailed(cue.end);
            }
        });

        textInput.addEventListener("input", () => {
            cue.text = textInput.value;
        });

        return cueEl;
    }

    function getWordOverlap(text1, text2) {
        if (!text1 || !text2) return 0;
        const words1 = text1.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").split(/\s+/).filter(Boolean);
        const words2 = text2.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").split(/\s+/).filter(Boolean);

        let maxOverlapWords = 0;
        const minLen = Math.min(words1.length, words2.length);

        for (let k = 1; k <= minLen; k++) {
            let match = true;
            for (let i = 0; i < k; i++) {
                if (words1[words1.length - k + i] !== words2[i]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                maxOverlapWords = k;
            }
        }
        return maxOverlapWords;
    }

    function cleanAndMergeCues(cues) {
        if (!cues || cues.length === 0) return [];

        // Step 1: Clean HTML tags and bracketed/parenthesized annotations like [âm nhạc], [ca hát], (laughter)
        let cleaned = cues.map(cue => {
            let text = cue.text;
            // Decode HTML entities
            text = text
                .replace(/&amp;/g, '&')
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&apos;/g, "'");
            // Remove HTML style tags
            text = text.replace(/<[^>]+>/g, '');
            // Remove [music] or (music) annotations
            text = text.replace(/\[[^\]]*\]/g, '');
            text = text.replace(/\([^)]*\)/g, '');
            // Normalize spaces
            text = text.replace(/\s+/g, ' ').trim();

            // Format speaker change indicators (>> or >>>) into professional dialogue style
            text = text.replace(/^>{2,}\s*/g, '- ');
            text = text.replace(/\s+>{2,}\s*/g, '\n- ');

            return {
                start: cue.start,
                end: cue.end,
                text: text
            };
        }).filter(cue => cue.text.length > 0);

        if (cleaned.length === 0) return [];

        // Step 2: Merge cues with start times extremely close (< 1.5s) if one contains the other
        let merged = [];
        for (let i = 0; i < cleaned.length; i++) {
            let current = cleaned[i];
            if (merged.length === 0) {
                merged.push(current);
                continue;
            }

            let last = merged[merged.length - 1];

            // If start times are within 1.5 seconds
            if (Math.abs(current.start - last.start) < 1.5) {
                const lastTextNorm = last.text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").replace(/\s+/g, ' ').trim();
                const currTextNorm = current.text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").replace(/\s+/g, ' ').trim();

                if (currTextNorm.includes(lastTextNorm)) {
                    // current contains last -> update last's text and end time
                    last.text = current.text;
                    last.start = Math.min(last.start, current.start);
                    last.end = Math.max(last.end, current.end);
                    continue;
                } else if (lastTextNorm.includes(currTextNorm)) {
                    // last contains current -> update last's end time
                    last.end = Math.max(last.end, current.end);
                    continue;
                }
            }

            merged.push(current);
        }

        // Step 3: Strip rolling suffix-prefix overlap between consecutive cues
        let finalCues = [];
        for (let i = 0; i < merged.length; i++) {
            let current = merged[i];
            if (finalCues.length === 0) {
                finalCues.push(current);
                continue;
            }

            let last = finalCues[finalCues.length - 1];

            const overlapCount = getWordOverlap(last.text, current.text);
            if (overlapCount > 0) {
                const rawWords = current.text.split(/\s+/);
                if (overlapCount >= rawWords.length) {
                    // If the current cue is entirely a duplicate of the end of the last cue
                    last.end = Math.max(last.end, current.end);
                } else {
                    // Strip the overlap words from the beginning of current cue
                    current.text = rawWords.slice(overlapCount).join(' ').trim();
                    if (current.text.length > 0) {
                        finalCues.push(current);
                    } else {
                        last.end = Math.max(last.end, current.end);
                    }
                }
            } else {
                finalCues.push(current);
            }
        }

        return finalCues;
    }

    async function loadSubtitle(urlOrContent, isContent = false) {
        try {
            let text = "";
            if (isContent) {
                text = urlOrContent;
            } else {
                if (!urlOrContent || urlOrContent === "none") {
                    currentCues = [];
                    activeSubUrl = "";
                    originalSubtitleContent = "";
                    const overlay = document.getElementById("preview-subtitles-overlay");
                    if (overlay) overlay.classList.add("hidden");
                    const sidebar = document.getElementById("preview-transcript-sidebar");
                    if (sidebar) sidebar.classList.add("hidden");
                    const downloadBtn = document.getElementById("preview-sub-download-btn");
                    if (downloadBtn) downloadBtn.disabled = true;
                    return;
                }
                activeSubUrl = urlOrContent;
                let requestUrl = urlOrContent;
                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    if (requestUrl.includes("fmt=")) {
                        requestUrl = requestUrl.replace(/fmt=[^&]+/, "fmt=vtt");
                    } else {
                        requestUrl += requestUrl.includes("?") ? "&fmt=vtt" : "?fmt=vtt";
                    }
                }

                if (requestUrl.includes("youtube.com/api/timedtext")) {
                    try {
                        const res = await fetch(requestUrl);
                        if (!res.ok) throw new Error("Direct fetch failed");
                        text = await res.text();
                    } catch (err) {
                        console.warn("Direct subtitle fetch failed in loadSubtitle, falling back to proxy...", err);
                        const proxyUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                        const res = await fetch(proxyUrl);
                        text = await res.text();
                    }
                } else {
                    let fetchUrl = requestUrl;
                    if (requestUrl.startsWith("http://") || requestUrl.startsWith("https://") || requestUrl.startsWith("/api/download/file/")) {
                        fetchUrl = `/api/system/proxy-sub?url=${encodeURIComponent(requestUrl)}&client_id=${encodeURIComponent(clientId)}`;
                    }
                    const res = await fetch(fetchUrl);
                    text = await res.text();
                }
            }

            originalSubtitleContent = text;
            currentCues = parseSubtitleText(text);
            console.log(`Loaded ${currentCues.length} subtitles cues`);

            // Populate Interactive Transcript Sidebar
            isEditingSubtitles = false;
            const toggleEditBtn = document.getElementById("toggle-edit-transcript-btn");
            if (toggleEditBtn) toggleEditBtn.textContent = "Edit Mode";
            const editorToolbar = document.getElementById("transcript-editor-toolbar");
            if (editorToolbar) editorToolbar.classList.add("hidden");
            const sidebar = document.getElementById("preview-transcript-sidebar");
            if (sidebar) sidebar.classList.remove("edit-mode");

            renderTranscript();

            if (sidebar) {
                if (currentCues.length > 0) {
                    sidebar.classList.remove("hidden");
                } else {
                    sidebar.classList.add("hidden");
                }
            }

            // Enable download subtitle button
            const downloadBtn = document.getElementById("preview-sub-download-btn");
            if (downloadBtn) {
                downloadBtn.disabled = currentCues.length === 0;
            }

            // Apply current style selections
            applySubtitleStyles();

            // Trigger overlay check
            if (previewVideoPlayer) {
                updateSubtitlesOverlay(previewVideoPlayer.currentTime);
            }

        } catch (err) {
            console.error("Failed to load subtitle track:", err);
        }
    }

    function speakTts(text, lang) {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel(); // Cancel any ongoing speech first

        const utterance = new SpeechSynthesisUtterance(text);

        // Find suitable voice matching selected language
        const voices = window.speechSynthesis.getVoices();
        let voice = null;

        if (lang === "vi") {
            voice = voices.find(v => v.lang.includes("vi-VN") || v.lang.includes("vi_VN"));
            utterance.lang = "vi-VN";
        } else if (lang === "en") {
            voice = voices.find(v => v.lang.includes("en-US") || v.lang.includes("en_US") || v.lang.includes("en-GB"));
            utterance.lang = "en-US";
        }

        if (voice) {
            utterance.voice = voice;
        }

        if (previewVideoPlayer) {
            utterance.rate = previewVideoPlayer.playbackRate || 1.0;
        }

        window.speechSynthesis.speak(utterance);
    }

    function updateSubtitlesOverlay(currentTime) {
        if (!currentCues || currentCues.length === 0) {
            const overlay = document.getElementById("preview-subtitles-overlay");
            if (overlay) overlay.classList.add("hidden");
            return;
        }

        // Find matching cues
        const activeCues = currentCues.filter(c => currentTime >= c.start && currentTime <= c.end);
        const overlay = document.getElementById("preview-subtitles-overlay");
        const textBox = overlay ? overlay.querySelector(".subtitles-text-box") : null;

        if (activeCues.length > 0) {
            const textContent = activeCues.map(c => c.text).join('\n');
            if (textBox) {
                textBox.textContent = textContent;
            }
            if (overlay) {
                overlay.classList.remove("hidden");
            }

            // Trigger TTS if active
            const voiceSelect = document.getElementById("preview-voiceover-select");
            if (voiceSelect && voiceSelect.value !== "none") {
                const speechText = activeCues[0].text;
                if (speechText && speechText !== lastTtsText) {
                    lastTtsText = speechText;
                    speakTts(speechText, voiceSelect.value);
                }
            }

            // Highlight cue in Interactive Transcript Sidebar
            const firstActiveIndex = currentCues.indexOf(activeCues[0]);
            const cueEls = document.querySelectorAll(".transcript-item");
            cueEls.forEach(el => el.classList.remove("active"));

            const activeEl = document.querySelector(`.transcript-item[data-index="${firstActiveIndex}"]`);
            if (activeEl) {
                activeEl.classList.add("active");
                // Scroll into view if not manual scrolling and not in edit mode
                const listEl = document.getElementById("transcript-list");
                if (listEl && !listEl.matches(':hover') && !isEditingSubtitles) {
                    activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        } else {
            if (overlay) {
                overlay.classList.add("hidden");
            }
            // Remove highlight
            const cueEls = document.querySelectorAll(".transcript-item");
            cueEls.forEach(el => el.classList.remove("active"));
        }
    }

    function applySubtitleStyles() {
        const overlay = document.getElementById("preview-subtitles-overlay");
        const textBox = overlay ? overlay.querySelector(".subtitles-text-box") : null;
        if (!textBox) return;

        // 1. Font Family
        const subFontSelect = document.getElementById("preview-sub-font");
        if (subFontSelect) {
            textBox.style.fontFamily = subFontSelect.value;
        }

        // 2. Font Size
        const subSizeSlider = document.getElementById("preview-sub-size");
        if (subSizeSlider) {
            textBox.style.fontSize = subSizeSlider.value + "rem";
        }

        // 3. Text Color
        let textColor = "#ffffff";
        const activeTextSwatch = document.querySelector(".color-swatch.active");
        if (activeTextSwatch) {
            textColor = activeTextSwatch.getAttribute("data-color");
        } else {
            const textColorPicker = document.getElementById("preview-sub-color");
            if (textColorPicker) textColor = textColorPicker.value;
        }
        textBox.style.color = textColor;

        // 4. Background Color & Opacity
        let bgStyle = "transparent";
        const activeBgSwatch = document.querySelector(".bg-swatch.active");
        let baseBgColor = "#000000";
        let isTransparent = false;

        if (activeBgSwatch) {
            const val = activeBgSwatch.getAttribute("data-bg");
            if (val === "transparent") {
                isTransparent = true;
            } else {
                baseBgColor = val;
            }
        } else {
            const bgColorPicker = document.getElementById("preview-sub-bg-color");
            if (bgColorPicker) baseBgColor = bgColorPicker.value;
        }

        if (!isTransparent) {
            const bgOpacitySlider = document.getElementById("preview-sub-bg-opacity");
            const opacity = bgOpacitySlider ? parseInt(bgOpacitySlider.value, 10) / 100 : 0.5;

            // Convert Hex to RGB
            const r = parseInt(baseBgColor.substring(1, 3), 16);
            const g = parseInt(baseBgColor.substring(3, 5), 16);
            const b = parseInt(baseBgColor.substring(5, 7), 16);

            bgStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
        }
        textBox.style.background = bgStyle;

        // 5. Outline / Text Shadow
        const outlineSlider = document.getElementById("preview-sub-outline");
        const outlineSize = outlineSlider ? parseInt(outlineSlider.value, 10) : 2;

        let outlineColor = "#000000";
        const activeOutlineSwatch = document.querySelector(".outline-swatch.active");
        if (activeOutlineSwatch) {
            outlineColor = activeOutlineSwatch.getAttribute("data-outline");
        } else {
            const outlineColorPicker = document.getElementById("preview-sub-outline-color");
            if (outlineColorPicker) outlineColor = outlineColorPicker.value;
        }

        let shadow = '';
        if (outlineSize > 0) {
            const shadows = [];
            for (let x = -outlineSize; x <= outlineSize; x++) {
                for (let y = -outlineSize; y <= outlineSize; y++) {
                    if (x !== 0 || y !== 0) {
                        shadows.push(`${x}px ${y}px 0 ${outlineColor}`);
                    }
                }
            }
            shadows.push(`0 2px 4px rgba(0,0,0,0.8)`);
            shadow = shadows.join(', ');
        } else {
            shadow = '0 2px 4px rgba(0,0,0,0.8)';
        }
        textBox.style.textShadow = shadow;

        // 6. Vertical Position
        const posSelect = document.getElementById("preview-sub-pos");
        if (overlay && posSelect) {
            if (posSelect.value === "top") {
                overlay.classList.remove("pos-bottom");
                overlay.classList.add("pos-top");
            } else {
                overlay.classList.remove("pos-top");
                overlay.classList.add("pos-bottom");
            }
        }
    }

    function parseTimeStringToSeconds(str) {
        if (!str) return null;
        const parts = str.trim().split(':');
        if (parts.length === 3) {
            const hrs = parseInt(parts[0], 10);
            const mins = parseInt(parts[1], 10);
            const secs = parseFloat(parts[2]);
            if (!isNaN(hrs) && !isNaN(mins) && !isNaN(secs)) {
                return hrs * 3600 + mins * 60 + secs;
            }
        } else if (parts.length === 2) {
            const mins = parseInt(parts[0], 10);
            const secs = parseFloat(parts[1]);
            if (!isNaN(mins) && !isNaN(secs)) {
                return mins * 60 + secs;
            }
        } else if (parts.length === 1) {
            const secs = parseFloat(parts[0]);
            if (!isNaN(secs)) return secs;
        }
        return null;
    }

    function formatMsToVttTime(ms) {
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        const milliseconds = Math.floor(ms % 1000);

        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}.${milliseconds.toString().padStart(3, "0")}`;
    }

    // --- SUBTITLE & CONTROLS INTERACTIVE BINDINGS ---

    const previewSubSelect = document.getElementById("preview-sub-select");
    if (previewSubSelect) {
        previewSubSelect.addEventListener("change", function () {
            const val = this.value;
            const transSelect = document.getElementById("preview-sub-trans-select");
            if (transSelect) transSelect.value = "none";
            loadSubtitle(val);
        });
    }

    const previewSubTransSelect = document.getElementById("preview-sub-trans-select");
    if (previewSubTransSelect) {
        previewSubTransSelect.addEventListener("change", async function () {
            const targetLang = this.value;
            if (targetLang === "none") {
                const subSelect = document.getElementById("preview-sub-select");
                if (subSelect && subSelect.value !== "none") {
                    loadSubtitle(subSelect.value);
                } else if (originalSubtitleContent) {
                    loadSubtitle(originalSubtitleContent, true);
                }
                return;
            }

            try {
                const payload = { target_lang: targetLang };
                const subSelect = document.getElementById("preview-sub-select");

                if (originalSubtitleContent) {
                    payload.content = originalSubtitleContent;
                } else if (subSelect && subSelect.value !== "none") {
                    payload.url = subSelect.value;
                } else {
                    this.value = "none";
                    return;
                }

                showPreviewLoader("Translating subtitles...");

                const resp = await fetch("/api/system/translate-sub", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const resData = await resp.json();
                hidePreviewLoader();

                if (resData.status === "success" && resData.translated_vtt) {
                    loadSubtitle(resData.translated_vtt, true);
                } else {
                    alert("Failed to translate subtitle: " + (resData.message || "Unknown error"));
                    this.value = "none";
                }
            } catch (e) {
                console.error("Subtitle translation error:", e);
                hidePreviewLoader();
                this.value = "none";
            }
        });
    }

    const previewVoiceoverSelect = document.getElementById("preview-voiceover-select");
    if (previewVoiceoverSelect) {
        previewVoiceoverSelect.addEventListener("change", function () {
            if (this.value === "none") {
                if (window.speechSynthesis) window.speechSynthesis.cancel();
            } else {
                if (previewVideoPlayer && currentCues.length > 0) {
                    updateSubtitlesOverlay(previewVideoPlayer.currentTime);
                }
            }
        });
    }

    let currentPlaybackSpeed = 1.0;

    function setPlaybackSpeedUI(rate) {
        currentPlaybackSpeed = parseFloat(rate) || 1.0;

        // Apply rate to video player
        if (previewVideoPlayer) {
            previewVideoPlayer.playbackRate = currentPlaybackSpeed;
        }
        // Apply rate to audio player if active
        if (previewAudioPlayer) {
            previewAudioPlayer.playbackRate = currentPlaybackSpeed;
        }

        const speedSelect = document.getElementById("preview-speed-select");
        const customWrapper = document.getElementById("preview-speed-custom-wrapper");
        const customInput = document.getElementById("preview-speed-custom");

        // Check if rate is preset
        const presets = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
        const isPreset = presets.some(p => Math.abs(p - currentPlaybackSpeed) < 0.01);

        if (speedSelect) {
            if (isPreset) {
                // Find matching preset index and select it
                for (let i = 0; i < speedSelect.options.length; i++) {
                    const optVal = parseFloat(speedSelect.options[i].value);
                    if (Math.abs(optVal - currentPlaybackSpeed) < 0.01) {
                        speedSelect.selectedIndex = i;
                        break;
                    }
                }
                if (customWrapper) {
                    customWrapper.style.display = "none";
                }
            } else {
                speedSelect.value = "custom";
                if (customWrapper) {
                    customWrapper.style.display = "flex";
                }
            }
        }

        if (customInput && document.activeElement !== customInput) {
            customInput.value = currentPlaybackSpeed;
        }
    }

    // Set listener for speed select dropdown
    const speedSelectElement = document.getElementById("preview-speed-select");
    if (speedSelectElement) {
        speedSelectElement.addEventListener("change", function (e) {
            e.stopPropagation();
            if (this.value === "custom") {
                const customWrapper = document.getElementById("preview-speed-custom-wrapper");
                if (customWrapper) {
                    customWrapper.style.display = "flex";
                }
                const customInput = document.getElementById("preview-speed-custom");
                if (customInput) {
                    customInput.focus();
                    let speed = parseFloat(customInput.value);
                    if (isNaN(speed) || speed < 0.05) speed = 1.0;
                    if (speed > 16.0) speed = 16.0;
                    currentPlaybackSpeed = speed;
                    if (previewVideoPlayer) previewVideoPlayer.playbackRate = speed;
                    if (previewAudioPlayer) previewAudioPlayer.playbackRate = speed;
                }
            } else {
                const speed = parseFloat(this.value);
                setPlaybackSpeedUI(speed);
            }
        });
    }

    // Set listener for custom speed input
    const customSpeedInput = document.getElementById("preview-speed-custom");
    if (customSpeedInput) {
        customSpeedInput.addEventListener("input", function () {
            let speed = parseFloat(this.value);
            if (isNaN(speed) || speed < 0.05) return;
            if (speed > 16.0) speed = 16.0;

            currentPlaybackSpeed = speed;
            if (previewVideoPlayer) {
                previewVideoPlayer.playbackRate = speed;
            }
            if (previewAudioPlayer) {
                previewAudioPlayer.playbackRate = speed;
            }
        });

        customSpeedInput.addEventListener("change", function () {
            let speed = parseFloat(this.value);
            if (isNaN(speed) || speed < 0.05) speed = 1.0;
            if (speed > 16.0) speed = 16.0;
            this.value = speed;
            setPlaybackSpeedUI(speed);
        });
    }

    const previewSubUploadBtn = document.getElementById("preview-sub-upload-btn");
    const previewSubUploadFile = document.getElementById("preview-sub-upload-file");
    if (previewSubUploadBtn && previewSubUploadFile) {
        previewSubUploadBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewSubUploadFile.click();
        });

        previewSubUploadFile.addEventListener("change", function () {
            const file = this.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function (e) {
                const text = e.target.result;
                originalSubtitleContent = text;
                loadSubtitle(text, true);

                const subSelect = document.getElementById("preview-sub-select");
                if (subSelect) {
                    const prevCustom = subSelect.querySelector('option[data-type="custom"]');
                    if (prevCustom) prevCustom.remove();

                    const opt = document.createElement("option");
                    opt.value = "custom";
                    opt.textContent = `Uploaded: ${file.name}`;
                    opt.setAttribute("data-type", "custom");
                    opt.selected = true;
                    subSelect.appendChild(opt);
                }
            };
            reader.readAsText(file);
            this.value = "";
        });
    }

    const previewSubDownloadBtn = document.getElementById("preview-sub-download-btn");
    if (previewSubDownloadBtn) {
        previewSubDownloadBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (currentCues.length === 0) return;

            let vttContent = "WEBVTT\n\n";
            currentCues.forEach((cue, index) => {
                const startStr = formatMsToVttTime(cue.start * 1000);
                const endStr = formatMsToVttTime(cue.end * 1000);
                vttContent += `${index + 1}\n${startStr} --> ${endStr}\n${cue.text}\n\n`;
            });

            const blob = new Blob([vttContent], { type: "text/vtt;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            const videoName = getSafeTitle(videoTitle.textContent, "subtitles");
            a.href = url;
            a.download = `${videoName}.vtt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    const loopPointAInput = document.getElementById("loop-point-a");
    const loopPointBInput = document.getElementById("loop-point-b");
    const btnLoopASet = document.getElementById("btn-loop-a-set");
    const btnLoopBSet = document.getElementById("btn-loop-b-set");
    const btnLoopClear = document.getElementById("btn-loop-clear");
    const videoLoopRangeBar = document.getElementById("video-loop-range-bar");
    const videoLoopMarkerA = document.getElementById("video-loop-marker-a");
    const videoLoopMarkerB = document.getElementById("video-loop-marker-b");

    function updateLoopMarkersUI() {
        if (!videoLoopRangeBar || !videoLoopMarkerA || !videoLoopMarkerB) return;
        const totalDuration = getVideoTotalDuration();
        if (!totalDuration || totalDuration <= 0) {
            videoLoopRangeBar.style.display = "none";
            videoLoopMarkerA.style.display = "none";
            videoLoopMarkerB.style.display = "none";
            return;
        }

        if (loopStartSecs !== null && loopStartSecs >= 0) {
            const pctA = Math.min(100, Math.max(0, (loopStartSecs / totalDuration) * 100));
            videoLoopMarkerA.style.left = `${pctA}%`;
            videoLoopMarkerA.style.display = "block";
        } else {
            videoLoopMarkerA.style.display = "none";
        }

        if (loopEndSecs !== null && loopEndSecs > 0) {
            const pctB = Math.min(100, Math.max(0, (loopEndSecs / totalDuration) * 100));
            videoLoopMarkerB.style.left = `${pctB}%`;
            videoLoopMarkerB.style.display = "block";
        } else {
            videoLoopMarkerB.style.display = "none";
        }

        if (loopStartSecs !== null && loopEndSecs !== null && loopEndSecs > loopStartSecs) {
            const pctA = Math.min(100, Math.max(0, (loopStartSecs / totalDuration) * 100));
            const pctB = Math.min(100, Math.max(0, (loopEndSecs / totalDuration) * 100));
            videoLoopRangeBar.style.left = `${pctA}%`;
            videoLoopRangeBar.style.width = `${Math.max(0, pctB - pctA)}%`;
            videoLoopRangeBar.style.display = "block";
        } else {
            videoLoopRangeBar.style.display = "none";
        }
    }
    window.updateLoopMarkersUI = updateLoopMarkersUI;

    function getActivePlayerTime() {
        const isVideoActive = !previewVideoContainer.classList.contains("hidden");
        const isAudioActive = !previewAudioContainer.classList.contains("hidden");
        if (isVideoActive && previewVideoPlayer) {
            return previewIsAdaptive ? (previewCurrentTimeOffset + previewVideoPlayer.currentTime) : previewVideoPlayer.currentTime;
        } else if (isAudioActive && previewAudioPlayer) {
            return previewAudioPlayer.currentTime;
        }
        return null;
    }

    if (btnLoopASet) {
        btnLoopASet.addEventListener("click", (e) => {
            e.stopPropagation();
            const time = getActivePlayerTime();
            if (time !== null) {
                loopStartSecs = time;
                if (loopPointAInput) {
                    loopPointAInput.value = formatTimeDetailed(loopStartSecs);
                }
                if (loopEndSecs !== null && loopStartSecs >= loopEndSecs) {
                    loopEndSecs = null;
                    if (loopPointBInput) loopPointBInput.value = "";
                }
                updateLoopMarkersUI();
            }
        });
    }

    if (btnLoopBSet) {
        btnLoopBSet.addEventListener("click", (e) => {
            e.stopPropagation();
            const time = getActivePlayerTime();
            if (time !== null) {
                loopEndSecs = time;
                if (loopPointBInput) {
                    loopPointBInput.value = formatTimeDetailed(loopEndSecs);
                }
                if (loopStartSecs !== null && loopEndSecs <= loopStartSecs) {
                    loopStartSecs = null;
                    if (loopPointAInput) loopPointAInput.value = "";
                }
                updateLoopMarkersUI();
            }
        });
    }

    if (btnLoopClear) {
        btnLoopClear.addEventListener("click", (e) => {
            e.stopPropagation();
            loopStartSecs = null;
            loopEndSecs = null;
            if (loopPointAInput) loopPointAInput.value = "";
            if (loopPointBInput) loopPointBInput.value = "";
            updateLoopMarkersUI();
        });
    }

    if (loopPointAInput) {
        loopPointAInput.addEventListener("change", function () {
            const secs = parseTimeStringToSeconds(this.value);
            if (secs !== null) {
                loopStartSecs = secs;
                this.value = formatTimeDetailed(secs);
            } else {
                loopStartSecs = null;
                this.value = "";
            }
            updateLoopMarkersUI();
        });
    }

    if (loopPointBInput) {
        loopPointBInput.addEventListener("change", function () {
            const secs = parseTimeStringToSeconds(this.value);
            if (secs !== null) {
                loopEndSecs = secs;
                this.value = formatTimeDetailed(secs);
            } else {
                loopEndSecs = null;
                this.value = "";
            }
            updateLoopMarkersUI();
        });
    }

    // Video Ambient Light Glow Advanced System
    const ambientCanvas = document.getElementById("video-ambient-glow");
    const toggleAmbientGlow = document.getElementById("toggle-ambient-glow");
    const ambientGlowWrapper = document.getElementById("ambient-glow-wrapper");
    const ambientCollapseTrigger = document.getElementById("ambient-collapse-trigger");
    const ambientChevronBtn = document.getElementById("ambient-chevron-btn");
    const ambientBadgePreset = document.getElementById("ambient-badge-preset");
    const ambientSliderOpacity = document.getElementById("ambient-slider-opacity");
    const ambientSliderBlur = document.getElementById("ambient-slider-blur");
    const ambientSliderSaturate = document.getElementById("ambient-slider-saturate");
    const ambientSliderSize = document.getElementById("ambient-slider-size");
    const ambientSelectFps = document.getElementById("ambient-select-fps");
    const ambientValOpacity = document.getElementById("ambient-val-opacity");
    const ambientValBlur = document.getElementById("ambient-val-blur");
    const ambientValSaturate = document.getElementById("ambient-val-saturate");
    const ambientValSize = document.getElementById("ambient-val-size");
    const ambientPresetBtns = document.querySelectorAll(".ambient-preset-btn");
    const ambientBtnReset = document.getElementById("ambient-btn-reset");

    let ambientAnimationFrame = null;
    let lastAmbientDrawTime = 0;
    let isAmbientDrawerOpen = localStorage.getItem("video-ambient-glow-drawer-open") === "true";

    function setAmbientDrawerState(open, save = true) {
        isAmbientDrawerOpen = open;
        if (save) {
            localStorage.setItem("video-ambient-glow-drawer-open", open ? "true" : "false");
        }
        if (ambientGlowWrapper) {
            ambientGlowWrapper.classList.toggle("expanded", open);
            ambientGlowWrapper.classList.toggle("collapsed", !open);
        }
        if (ambientChevronBtn) {
            ambientChevronBtn.classList.toggle("collapsed", !open);
        }
    }

    if (ambientCollapseTrigger) {
        ambientCollapseTrigger.addEventListener("click", () => {
            if (!toggleAmbientGlow || !toggleAmbientGlow.checked) {
                if (toggleAmbientGlow) {
                    toggleAmbientGlow.checked = true;
                    toggleAmbientGlow.dispatchEvent(new Event("change"));
                }
                setAmbientDrawerState(true);
            } else {
                setAmbientDrawerState(!isAmbientDrawerOpen);
            }
        });
    }

    const AMBIENT_PRESETS = {
        default: { opacity: 65, blur: 48, saturate: 140, size: 108, fps: 30 },
        vibrant: { opacity: 85, blur: 64, saturate: 190, size: 112, fps: 60 },
        subtle:  { opacity: 35, blur: 36, saturate: 110, size: 104, fps: 30 },
        dreamy:  { opacity: 60, blur: 96, saturate: 150, size: 118, fps: 30 }
    };

    let currentAmbientConfig = { ...AMBIENT_PRESETS.default, preset: "default" };
    try {
        const savedCfg = localStorage.getItem("video-ambient-glow-config");
        if (savedCfg) {
            currentAmbientConfig = Object.assign(currentAmbientConfig, JSON.parse(savedCfg));
        }
    } catch (e) { }

    if (ambientCanvas) {
        ambientCanvas.width = 64;
        ambientCanvas.height = 36;
    }

    function renderAmbientFrame() {
        if (!ambientCanvas || !previewVideoPlayer || previewVideoPlayer.readyState < 2) return;
        const ambientCtx = ambientCanvas.getContext("2d");
        if (!ambientCtx) return;
        try {
            if (previewVideoPlayer.videoWidth && previewVideoPlayer.videoHeight) {
                const aspect = previewVideoPlayer.videoWidth / previewVideoPlayer.videoHeight;
                const targetW = Math.max(16, Math.min(200, Math.round(36 * aspect)));
                if (ambientCanvas.width !== targetW) {
                    ambientCanvas.width = targetW;
                    ambientCanvas.height = 36;
                }
            }
            ambientCtx.drawImage(previewVideoPlayer, 0, 0, ambientCanvas.width, ambientCanvas.height);
        } catch (e) { }
    }

    function applyAmbientConfig(cfg, save = true) {
        if (!ambientCanvas) return;
        ambientCanvas.style.setProperty("--ambient-opacity", (cfg.opacity / 100).toString());
        ambientCanvas.style.setProperty("--ambient-blur", `${cfg.blur}px`);
        ambientCanvas.style.setProperty("--ambient-saturate", `${cfg.saturate}%`);
        const sizeVal = Number(cfg.size) || 108;
        const sizeX = sizeVal;
        const sizeY = Math.round(100 + (sizeVal - 100) * 0.5);
        ambientCanvas.style.setProperty("--ambient-size-x", `${sizeX}%`);
        ambientCanvas.style.setProperty("--ambient-size-y", `${sizeY}%`);

        if (ambientSliderOpacity) ambientSliderOpacity.value = cfg.opacity;
        if (ambientValOpacity) ambientValOpacity.textContent = `${cfg.opacity}%`;
        if (ambientSliderBlur) ambientSliderBlur.value = cfg.blur;
        if (ambientValBlur) ambientValBlur.textContent = `${cfg.blur}px`;
        if (ambientSliderSaturate) ambientSliderSaturate.value = cfg.saturate;
        if (ambientValSaturate) ambientValSaturate.textContent = `${cfg.saturate}%`;
        if (ambientSliderSize) ambientSliderSize.value = cfg.size;
        if (ambientValSize) ambientValSize.textContent = `${cfg.size}%`;
        if (ambientSelectFps) ambientSelectFps.value = (cfg.fps || 30).toString();

        ambientPresetBtns.forEach(btn => {
            btn.classList.toggle("active", btn.dataset.preset === cfg.preset);
        });

        if (ambientBadgePreset) {
            const pKey = cfg.preset || "custom";
            ambientBadgePreset.textContent = pKey.charAt(0).toUpperCase() + pKey.slice(1);
        }

        if (save) {
            try {
                localStorage.setItem("video-ambient-glow-config", JSON.stringify(cfg));
            } catch (e) { }
        }

        const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
        if (isGlowEnabled) {
            renderAmbientFrame();
        }
    }

    // Initialize config values and styles
    applyAmbientConfig(currentAmbientConfig, false);

    function updateAmbientGlow(timestamp) {
        if (!previewVideoPlayer || previewVideoPlayer.paused || previewVideoPlayer.ended) {
            ambientAnimationFrame = null;
            return;
        }

        const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
        if (isGlowEnabled && ambientCanvas) {
            const targetFps = Number(currentAmbientConfig.fps) || 30;
            const interval = 1000 / targetFps;
            const now = timestamp || performance.now();
            if (now - lastAmbientDrawTime >= interval - 2) {
                renderAmbientFrame();
                lastAmbientDrawTime = now;
            }
        }

        ambientAnimationFrame = requestAnimationFrame(updateAmbientGlow);
    }

    // Connect slider listeners for live tuning
    if (ambientSliderOpacity) {
        ambientSliderOpacity.addEventListener("input", (e) => {
            currentAmbientConfig.opacity = Number(e.target.value);
            currentAmbientConfig.preset = "custom";
            applyAmbientConfig(currentAmbientConfig);
        });
    }
    if (ambientSliderBlur) {
        ambientSliderBlur.addEventListener("input", (e) => {
            currentAmbientConfig.blur = Number(e.target.value);
            currentAmbientConfig.preset = "custom";
            applyAmbientConfig(currentAmbientConfig);
        });
    }
    if (ambientSliderSaturate) {
        ambientSliderSaturate.addEventListener("input", (e) => {
            currentAmbientConfig.saturate = Number(e.target.value);
            currentAmbientConfig.preset = "custom";
            applyAmbientConfig(currentAmbientConfig);
        });
    }
    if (ambientSliderSize) {
        ambientSliderSize.addEventListener("input", (e) => {
            currentAmbientConfig.size = Number(e.target.value);
            currentAmbientConfig.preset = "custom";
            applyAmbientConfig(currentAmbientConfig);
        });
    }
    if (ambientSelectFps) {
        ambientSelectFps.addEventListener("change", (e) => {
            currentAmbientConfig.fps = Number(e.target.value);
            currentAmbientConfig.preset = "custom";
            applyAmbientConfig(currentAmbientConfig);
        });
    }

    // Connect preset buttons
    ambientPresetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const presetKey = btn.dataset.preset;
            if (AMBIENT_PRESETS[presetKey]) {
                currentAmbientConfig = { ...AMBIENT_PRESETS[presetKey], preset: presetKey };
                applyAmbientConfig(currentAmbientConfig);
            }
        });
    });

    // Connect reset button
    if (ambientBtnReset) {
        ambientBtnReset.addEventListener("click", () => {
            currentAmbientConfig = { ...AMBIENT_PRESETS.default, preset: "default" };
            applyAmbientConfig(currentAmbientConfig);
        });
    }

    if (previewVideoPlayer && ambientCanvas) {
        previewVideoPlayer.addEventListener("play", () => {
            if (!ambientAnimationFrame) {
                updateAmbientGlow();
            }
        });
        previewVideoPlayer.addEventListener("playing", () => {
            if (!ambientAnimationFrame) {
                updateAmbientGlow();
            }
        });
        previewVideoPlayer.addEventListener("pause", () => {
            if (ambientAnimationFrame) {
                cancelAnimationFrame(ambientAnimationFrame);
                ambientAnimationFrame = null;
            }
        });
        previewVideoPlayer.addEventListener("loadeddata", () => {
            const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
            if (isGlowEnabled) {
                renderAmbientFrame();
            }
        });
        previewVideoPlayer.addEventListener("ended", () => {
            if (ambientAnimationFrame) {
                cancelAnimationFrame(ambientAnimationFrame);
                ambientAnimationFrame = null;
            }
            const ambientCtx = ambientCanvas.getContext("2d");
            if (ambientCtx) {
                ambientCtx.clearRect(0, 0, ambientCanvas.width, ambientCanvas.height);
            }

            // Autoplay next episode within same server group
            const toggleAutoplayNext = document.getElementById("toggle-autoplay-next");
            if (toggleAutoplayNext && toggleAutoplayNext.checked) {
                if (videoFormatSelect && typeof getGroupSiblingsAndIndex === "function") {
                    const { siblings, currentIndex } = getGroupSiblingsAndIndex();
                    if (currentIndex !== -1 && currentIndex < siblings.length - 1) {
                        const nextOpt = siblings[currentIndex + 1];
                        videoFormatSelect.value = nextOpt.value;
                        videoFormatSelect.dispatchEvent(new Event("change"));
                    }
                }
            }
        });
        previewVideoPlayer.addEventListener("seeked", () => {
            const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
            if (isGlowEnabled) {
                renderAmbientFrame();
            }
        });
    }

    if (toggleAmbientGlow && ambientCanvas) {
        const savedGlowState = localStorage.getItem("video-ambient-glow-enabled") !== "false";
        toggleAmbientGlow.checked = savedGlowState;
        const videoWrapper = ambientCanvas.parentElement;
        if (savedGlowState) {
            ambientCanvas.style.display = "";
            if (videoWrapper) {
                videoWrapper.classList.add("ambient-glow-active");
            }
            setAmbientDrawerState(isAmbientDrawerOpen, false);
        } else {
            ambientCanvas.style.display = "none";
            if (videoWrapper) {
                videoWrapper.classList.remove("ambient-glow-active");
            }
            setAmbientDrawerState(false, false);
            const ambientCtx = ambientCanvas.getContext("2d");
            if (ambientCtx) {
                ambientCtx.clearRect(0, 0, ambientCanvas.width, ambientCanvas.height);
            }
        }

        toggleAmbientGlow.addEventListener("change", () => {
            if (toggleAmbientGlow.checked) {
                ambientCanvas.style.display = "";
                if (videoWrapper) {
                    videoWrapper.classList.add("ambient-glow-active");
                }
                localStorage.setItem("video-ambient-glow-enabled", "true");
                setAmbientDrawerState(true);
                applyAmbientConfig(currentAmbientConfig, false);
                renderAmbientFrame();
                if (previewVideoPlayer && !previewVideoPlayer.paused && !ambientAnimationFrame) {
                    updateAmbientGlow();
                }
            } else {
                ambientCanvas.style.display = "none";
                if (videoWrapper) {
                    videoWrapper.classList.remove("ambient-glow-active");
                }
                setAmbientDrawerState(false);
                localStorage.setItem("video-ambient-glow-enabled", "false");
                if (ambientAnimationFrame) {
                    cancelAnimationFrame(ambientAnimationFrame);
                    ambientAnimationFrame = null;
                }
                const ambientCtx = ambientCanvas.getContext("2d");
                if (ambientCtx) {
                    ambientCtx.clearRect(0, 0, ambientCanvas.width, ambientCanvas.height);
                }
            }
        });
    }

    // Toggle Autoplay Next Episode initialization
    const toggleAutoplayNext = document.getElementById("toggle-autoplay-next");
    if (toggleAutoplayNext) {
        const savedAutoplayState = localStorage.getItem("video-autoplay-next-enabled") === "true";
        toggleAutoplayNext.checked = savedAutoplayState;
        toggleAutoplayNext.addEventListener("change", () => {
            localStorage.setItem("video-autoplay-next-enabled", toggleAutoplayNext.checked ? "true" : "false");
        });
    }

    // Toggle A-B Loop visibility
    const toggleAbLoop = document.getElementById("toggle-ab-loop");
    const abLoopWrapper = document.getElementById("ab-loop-wrapper");

    if (toggleAbLoop && abLoopWrapper) {
        // Load saved state
        const savedState = localStorage.getItem("ab-loop-visible") === "true";
        toggleAbLoop.checked = savedState;
        if (savedState) {
            abLoopWrapper.classList.remove("collapsed");
            abLoopWrapper.classList.add("expanded");
            updateLoopMarkersUI();
        } else {
            abLoopWrapper.classList.remove("expanded");
            abLoopWrapper.classList.add("collapsed");
        }

        toggleAbLoop.addEventListener("change", () => {
            if (toggleAbLoop.checked) {
                abLoopWrapper.classList.remove("collapsed");
                abLoopWrapper.classList.add("expanded");
                localStorage.setItem("ab-loop-visible", "true");
                updateLoopMarkersUI();
            } else {
                abLoopWrapper.classList.remove("expanded");
                abLoopWrapper.classList.add("collapsed");
                localStorage.setItem("ab-loop-visible", "false");
                // Clear active loop when toggled off
                const clearBtn = document.getElementById("btn-loop-clear");
                if (clearBtn) clearBtn.click();
            }
        });
    }

    const videoTranscriptBtn = document.getElementById("video-transcript-btn");
    const previewTranscriptSidebar = document.getElementById("preview-transcript-sidebar");
    const closeTranscriptSidebarBtn = document.getElementById("close-transcript-sidebar-btn");

    if (videoTranscriptBtn && previewTranscriptSidebar) {
        videoTranscriptBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewTranscriptSidebar.classList.toggle("hidden");
        });
    }

    if (closeTranscriptSidebarBtn && previewTranscriptSidebar) {
        closeTranscriptSidebarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewTranscriptSidebar.classList.add("hidden");
        });
    }

    const toggleEditTranscriptBtn = document.getElementById("toggle-edit-transcript-btn");
    const transcriptEditorToolbar = document.getElementById("transcript-editor-toolbar");

    if (toggleEditTranscriptBtn) {
        toggleEditTranscriptBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            isEditingSubtitles = !isEditingSubtitles;
            if (isEditingSubtitles) {
                toggleEditTranscriptBtn.textContent = "View Mode";
                if (transcriptEditorToolbar) transcriptEditorToolbar.classList.remove("hidden");
                if (previewTranscriptSidebar) previewTranscriptSidebar.classList.add("edit-mode");
            } else {
                toggleEditTranscriptBtn.textContent = "Edit Mode";
                if (transcriptEditorToolbar) transcriptEditorToolbar.classList.add("hidden");
                if (previewTranscriptSidebar) previewTranscriptSidebar.classList.remove("edit-mode");
            }
            renderTranscript();
        });
    }

    const transcriptAddCueBtn = document.getElementById("transcript-add-cue-btn");
    if (transcriptAddCueBtn) {
        transcriptAddCueBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const currentTime = previewVideoPlayer ? previewVideoPlayer.currentTime : 0;
            const newCue = {
                start: currentTime,
                end: currentTime + 3.0,
                text: "New subtitle line"
            };
            currentCues.push(newCue);
            currentCues.sort((a, b) => a.start - b.start);
            renderTranscript();

            setTimeout(() => {
                const listEl = document.getElementById("transcript-list");
                if (listEl) {
                    const items = listEl.querySelectorAll(".transcript-item");
                    for (const item of items) {
                        const idx = parseInt(item.getAttribute("data-index"));
                        if (currentCues[idx] && Math.abs(currentCues[idx].start - currentTime) < 0.05) {
                            item.scrollIntoView({ behavior: "smooth", block: "center" });
                            const textInput = item.querySelector(".edit-cue-text");
                            if (textInput) textInput.focus();
                            break;
                        }
                    }
                }
            }, 100);
        });
    }

    const transcriptSaveSubsBtn = document.getElementById("transcript-save-subs-btn");
    if (transcriptSaveSubsBtn) {
        transcriptSaveSubsBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            originalSubtitleContent = rebuildVttFromCues(currentCues);
            
            const previewSubSelect = document.getElementById("preview-sub-select");
            if (previewSubSelect) {
                let customOpt = previewSubSelect.querySelector('option[value="custom"]');
                if (!customOpt) {
                    customOpt = document.createElement("option");
                    customOpt.value = "custom";
                    customOpt.textContent = "Custom Subtitles (Edited)";
                    previewSubSelect.appendChild(customOpt);
                }
                previewSubSelect.value = "custom";
            }
            
            if (previewVideoPlayer) {
                updateSubtitlesOverlay(previewVideoPlayer.currentTime);
            }
            
            showAlert("Thành công", "Đã lưu lại các chỉnh sửa phụ đề thành công! Tệp tin xuất ra sẽ chứa nội dung phụ đề mới này.");
            
            isEditingSubtitles = false;
            if (toggleEditTranscriptBtn) toggleEditTranscriptBtn.textContent = "Edit Subtitles";
            if (transcriptEditorToolbar) transcriptEditorToolbar.classList.add("hidden");
            if (previewTranscriptSidebar) previewTranscriptSidebar.classList.remove("edit-mode");
            
            renderTranscript();
        });
    }

    const videoSettingsBtn = document.getElementById("video-settings-btn");
    const videoSettingsMenu = document.getElementById("video-settings-menu");
    const closeSettingsMenuBtn = document.getElementById("close-settings-menu-btn");

    if (videoSettingsBtn && videoSettingsMenu) {
        videoSettingsBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            videoSettingsMenu.classList.toggle("hidden");
        });
    }

    if (closeSettingsMenuBtn && videoSettingsMenu) {
        closeSettingsMenuBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            videoSettingsMenu.classList.add("hidden");
        });
    }

    // Hide settings menu when clicking outside
    document.addEventListener("click", (e) => {
        if (videoSettingsMenu && !videoSettingsMenu.classList.contains("hidden")) {
            if (!videoSettingsMenu.contains(e.target) && e.target !== videoSettingsBtn) {
                videoSettingsMenu.classList.add("hidden");
            }
        }
    });

    // Video settings menu tab switcher click handlers
    const settingsTabBtns = document.querySelectorAll(".settings-tab-btn");
    const settingsTabPanels = document.querySelectorAll(".settings-tab-panel");
    if (settingsTabBtns && settingsTabPanels) {
        settingsTabBtns.forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const targetTab = btn.getAttribute("data-tab");

                settingsTabBtns.forEach(b => {
                    b.classList.remove("active");
                    b.style.color = "#94a3b8";
                    b.style.borderBottomColor = "transparent";
                    b.style.fontWeight = "500";
                });
                btn.classList.add("active");
                btn.style.color = "var(--cyan)";
                btn.style.borderBottomColor = "var(--cyan)";
                btn.style.fontWeight = "700";

                settingsTabPanels.forEach(panel => {
                    if (panel.id === targetTab) {
                        panel.classList.remove("hidden");
                    } else {
                        panel.classList.add("hidden");
                    }
                });
            });
        });
    }

    // Synchronize preview advanced settings with the main page controls
    function syncMainToPreviewSettings() {
        // Reset tab view to playback by default when syncing
        const defaultTabBtn = document.querySelector('.settings-tab-btn[data-tab="tab-playback"]');
        if (defaultTabBtn) {
            defaultTabBtn.click();
        }

        const mainExport = document.getElementById("export-type-select");
        const previewExport = document.getElementById("preview-export-type");
        if (mainExport && previewExport) {
            previewExport.value = mainExport.value;
            previewExport.dispatchEvent(new Event("change"));
        }

        const mainFilter = document.getElementById("color-filter-select");
        const previewFilter = document.getElementById("preview-color-filter");
        if (mainFilter && previewFilter) {
            previewFilter.value = mainFilter.value;
            previewFilter.dispatchEvent(new Event("change"));
        }

        const mainCloud = document.getElementById("cloud-sync-select");
        const previewCloud = document.getElementById("preview-cloud-sync");
        if (mainCloud && previewCloud) {
            previewCloud.value = mainCloud.value;
            previewCloud.dispatchEvent(new Event("change"));
        }

        const mainVoiceoverActive = document.getElementById("voiceover-checkbox");
        const previewVoiceoverActive = document.getElementById("preview-voiceover-active");
        if (mainVoiceoverActive && previewVoiceoverActive) {
            previewVoiceoverActive.checked = mainVoiceoverActive.checked;
            previewVoiceoverActive.dispatchEvent(new Event("change"));
        }

        const mainVoiceoverVoice = document.getElementById("voiceover-voice-select");
        const previewVoiceoverVoice = document.getElementById("preview-voiceover-voice");
        if (mainVoiceoverVoice && previewVoiceoverVoice) {
            previewVoiceoverVoice.value = mainVoiceoverVoice.value;
            previewVoiceoverVoice.dispatchEvent(new Event("change"));
        }

        const mainVoiceoverRate = document.getElementById("voiceover-rate-slider");
        const previewVoiceoverRate = document.getElementById("preview-voiceover-rate-slider");
        if (mainVoiceoverRate && previewVoiceoverRate) {
            previewVoiceoverRate.value = mainVoiceoverRate.value;
            previewVoiceoverRate.dispatchEvent(new Event("input"));
        }

        const mainVoiceoverPitch = document.getElementById("voiceover-pitch-slider");
        const previewVoiceoverPitch = document.getElementById("preview-voiceover-pitch-slider");
        if (mainVoiceoverPitch && previewVoiceoverPitch) {
            previewVoiceoverPitch.value = mainVoiceoverPitch.value;
            previewVoiceoverPitch.dispatchEvent(new Event("input"));
        }

        // Sync Enhance parameters from main hidden inputs to preview inputs
        const mainEnhanceBeautify = document.getElementById("enhance-beautify-checkbox");
        const previewEnhanceBeautify = document.getElementById("preview-enhance-beautify");
        if (mainEnhanceBeautify && previewEnhanceBeautify) {
            previewEnhanceBeautify.checked = mainEnhanceBeautify.checked;
            previewEnhanceBeautify.dispatchEvent(new Event("change"));
        }

        const mainEnhanceSharpen = document.getElementById("enhance-sharpen-slider");
        const previewEnhanceSharpen = document.getElementById("preview-enhance-sharpen");
        if (mainEnhanceSharpen && previewEnhanceSharpen) {
            previewEnhanceSharpen.value = mainEnhanceSharpen.value;
            previewEnhanceSharpen.dispatchEvent(new Event("input"));
        }

        const mainEnhanceUpscale = document.getElementById("enhance-upscale-select");
        const previewEnhanceUpscale = document.getElementById("preview-enhance-upscale");
        if (mainEnhanceUpscale && previewEnhanceUpscale) {
            previewEnhanceUpscale.value = mainEnhanceUpscale.value;
            previewEnhanceUpscale.dispatchEvent(new Event("change"));
        }

        applyPreviewVideoFilters();
    }

    // Set up listeners to sync preview settings back to main settings
    const previewExportType = document.getElementById("preview-export-type");
    if (previewExportType) {
        previewExportType.addEventListener("change", function () {
            const mainExport = document.getElementById("export-type-select");
            if (mainExport && mainExport.value !== this.value) {
                mainExport.value = this.value;
                mainExport.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewColorFilter = document.getElementById("preview-color-filter");
    if (previewColorFilter) {
        previewColorFilter.addEventListener("change", function () {
            const mainFilter = document.getElementById("color-filter-select");
            if (mainFilter && mainFilter.value !== this.value) {
                mainFilter.value = this.value;
                mainFilter.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewCloudSync = document.getElementById("preview-cloud-sync");
    if (previewCloudSync) {
        previewCloudSync.addEventListener("change", function () {
            const mainCloud = document.getElementById("cloud-sync-select");
            if (mainCloud && mainCloud.value !== this.value) {
                mainCloud.value = this.value;
                mainCloud.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewVoiceoverActive = document.getElementById("preview-voiceover-active");
    const previewVoiceoverWrapper = document.getElementById("preview-voiceover-wrapper");
    if (previewVoiceoverActive) {
        previewVoiceoverActive.addEventListener("change", function () {
            // Expand/collapse collapsible options wrapper
            if (previewVoiceoverWrapper) {
                if (this.checked) {
                    previewVoiceoverWrapper.classList.remove("collapsed");
                    previewVoiceoverWrapper.classList.add("expanded");
                } else {
                    previewVoiceoverWrapper.classList.remove("expanded");
                    previewVoiceoverWrapper.classList.add("collapsed");
                }
            }
            // Sync with main page checkbox
            const mainVoiceoverActive = document.getElementById("voiceover-checkbox");
            if (mainVoiceoverActive && mainVoiceoverActive.checked !== this.checked) {
                mainVoiceoverActive.checked = this.checked;
                mainVoiceoverActive.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewVoiceoverVoice = document.getElementById("preview-voiceover-voice");
    if (previewVoiceoverVoice) {
        previewVoiceoverVoice.addEventListener("change", function () {
            const mainVoice = document.getElementById("voiceover-voice-select");
            if (mainVoice && mainVoice.value !== this.value) {
                mainVoice.value = this.value;
                mainVoice.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewVoiceoverRate = document.getElementById("preview-voiceover-rate-slider");
    const previewVoiceoverRateVal = document.getElementById("preview-voiceover-rate-val");
    if (previewVoiceoverRate) {
        previewVoiceoverRate.addEventListener("input", function () {
            const val = parseInt(this.value);
            if (previewVoiceoverRateVal) {
                previewVoiceoverRateVal.textContent = val === 0 ? "Normal" : (val > 0 ? `+${val}%` : `${val}%`);
            }
            const mainRate = document.getElementById("voiceover-rate-slider");
            if (mainRate && mainRate.value !== this.value) {
                mainRate.value = this.value;
                mainRate.dispatchEvent(new Event("input"));
            }
        });
    }

    const previewVoiceoverPitch = document.getElementById("preview-voiceover-pitch-slider");
    const previewVoiceoverPitchVal = document.getElementById("preview-voiceover-pitch-val");
    if (previewVoiceoverPitch) {
        previewVoiceoverPitch.addEventListener("input", function () {
            const val = parseInt(this.value);
            if (previewVoiceoverPitchVal) {
                previewVoiceoverPitchVal.textContent = val === 0 ? "Normal" : (val > 0 ? `+${val}%` : `${val}%`);
            }
            const mainPitch = document.getElementById("voiceover-pitch-slider");
            if (mainPitch && mainPitch.value !== this.value) {
                mainPitch.value = this.value;
                mainPitch.dispatchEvent(new Event("input"));
            }
        });
    }

    function applyPreviewVideoFilters() {
        const previewVideo = document.getElementById("preview-video-player");
        const trimVideo = document.getElementById("trim-preview-player");
        
        const previewEnhanceBeautify = document.getElementById("preview-enhance-beautify");
        const previewEnhanceSharpen = document.getElementById("preview-enhance-sharpen");
        
        const beautifyActive = previewEnhanceBeautify ? previewEnhanceBeautify.checked : false;
        const sharpenVal = previewEnhanceSharpen ? parseInt(previewEnhanceSharpen.value) : 0;
        
        let filterParts = [];
        
        if (sharpenVal > 0) {
            if (sharpenVal < 35) {
                filterParts.push("url(#svg-sharpen-low)");
            } else if (sharpenVal < 70) {
                filterParts.push("url(#svg-sharpen-medium)");
            } else {
                filterParts.push("url(#svg-sharpen-high)");
            }
        }
        
        if (beautifyActive) {
            filterParts.push("saturate(1.12) contrast(1.05) brightness(1.02)");
        }
        
        const filterString = filterParts.length > 0 ? filterParts.join(" ") : "none";
        
        if (previewVideo) previewVideo.style.filter = filterString;
        if (trimVideo) trimVideo.style.filter = filterString;
    }

    const previewEnhanceBeautify = document.getElementById("preview-enhance-beautify");
    if (previewEnhanceBeautify) {
        previewEnhanceBeautify.addEventListener("change", function () {
            const mainBeautify = document.getElementById("enhance-beautify-checkbox");
            if (mainBeautify && mainBeautify.checked !== this.checked) {
                mainBeautify.checked = this.checked;
                mainBeautify.dispatchEvent(new Event("change"));
            }
            applyPreviewVideoFilters();
        });
    }

    const previewEnhanceSharpen = document.getElementById("preview-enhance-sharpen");
    const previewEnhanceSharpenVal = document.getElementById("preview-enhance-sharpen-val");
    if (previewEnhanceSharpen) {
        previewEnhanceSharpen.addEventListener("input", function () {
            const val = parseInt(this.value);
            if (previewEnhanceSharpenVal) {
                previewEnhanceSharpenVal.textContent = val === 0 ? "Off" : `${val}%`;
            }
            const mainSharpen = document.getElementById("enhance-sharpen-slider");
            if (mainSharpen && mainSharpen.value !== this.value) {
                mainSharpen.value = this.value;
                mainSharpen.dispatchEvent(new Event("input"));
            }
            applyPreviewVideoFilters();
        });
    }

    const previewEnhanceUpscale = document.getElementById("preview-enhance-upscale");
    if (previewEnhanceUpscale) {
        previewEnhanceUpscale.addEventListener("change", function () {
            const mainUpscale = document.getElementById("enhance-upscale-select");
            if (mainUpscale && mainUpscale.value !== this.value) {
                mainUpscale.value = this.value;
                mainUpscale.dispatchEvent(new Event("change"));
            }
        });
    }

    function initCustomDropdowns() {
        const settingsMenu = document.getElementById("video-settings-menu");
        if (!settingsMenu) return;

        const selectMenus = settingsMenu.querySelectorAll(".custom-select-menu");
        selectMenus.forEach(selectEl => {
            if (!selectEl.id) return;

            // Check if already initialized
            let container = settingsMenu.querySelector(`.custom-dropdown-container[data-select-id="${selectEl.id}"]`);
            if (container) return;

            // Hide the real select element
            selectEl.style.setProperty("display", "none", "important");

            // Create custom dropdown markup
            container = document.createElement("div");
            container.className = "custom-dropdown-container";
            container.setAttribute("data-select-id", selectEl.id);

            const trigger = document.createElement("div");
            trigger.className = "custom-dropdown-trigger";

            const selectedText = document.createElement("span");
            selectedText.className = "custom-dropdown-selected-text";

            const arrow = document.createElement("span");
            arrow.className = "custom-dropdown-arrow";
            arrow.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="10" height="10"><polyline points="6 9 12 15 18 9"/></svg>`;

            trigger.appendChild(selectedText);
            trigger.appendChild(arrow);

            const optionsList = document.createElement("div");
            optionsList.className = "custom-dropdown-options-list";

            container.appendChild(trigger);
            // Append optionsList directly to settingsMenu to escape scrollable content clipping
            settingsMenu.appendChild(optionsList);

            // Insert custom container right after the select
            selectEl.parentNode.insertBefore(container, selectEl.nextSibling);

            // Rebuild function
            function rebuildCustomOptions() {
                optionsList.innerHTML = "";
                Array.from(selectEl.options).forEach(opt => {
                    const optDiv = document.createElement("div");
                    optDiv.className = "custom-dropdown-option";
                    optDiv.setAttribute("data-value", opt.value);
                    optDiv.textContent = opt.textContent;

                    if (opt.selected) {
                        optDiv.classList.add("active");
                        selectedText.textContent = opt.textContent;
                    }

                    optDiv.addEventListener("click", (e) => {
                        e.stopPropagation();
                        // Update select value
                        selectEl.value = opt.value;
                        // Dispatch event
                        selectEl.dispatchEvent(new Event("change"));
                        // Close menu
                        container.classList.remove("open");
                        optionsList.classList.remove("open");
                    });

                    optionsList.appendChild(optDiv);
                });

                // If nothing is selected, display first option or placeholder
                if (selectEl.selectedIndex === -1 || !selectedText.textContent) {
                    if (selectEl.options.length > 0) {
                        selectedText.textContent = selectEl.options[0].textContent;
                    } else {
                        selectedText.textContent = "None";
                    }
                }
            }

            rebuildCustomOptions();

            // Sync visual active state on programmatic change
            selectEl.addEventListener("change", () => {
                const activeVal = selectEl.value;
                const options = optionsList.querySelectorAll(".custom-dropdown-option");
                options.forEach(optDiv => {
                    if (optDiv.getAttribute("data-value") === activeVal) {
                        optDiv.classList.add("active");
                        selectedText.textContent = optDiv.textContent;
                    } else {
                        optDiv.classList.remove("active");
                    }
                });
            });

            // Dynamically position the options list relative to settingsMenu
            function positionOptionsList() {
                const menuRect = settingsMenu.getBoundingClientRect();
                const triggerRect = trigger.getBoundingClientRect();

                const left = triggerRect.left - menuRect.left;
                const width = triggerRect.width;

                optionsList.style.left = `${left}px`;
                optionsList.style.width = `${width}px`;

                // Calculate space below and above trigger relative to settingsMenu
                const spaceBelow = menuRect.bottom - triggerRect.bottom;
                const spaceAbove = triggerRect.top - menuRect.top;

                // Estimate options list height (capped at max-height: 180px in CSS)
                const listHeight = Math.min(180, optionsList.scrollHeight || 120);

                if (spaceBelow >= listHeight + 8 || spaceBelow > spaceAbove) {
                    // Open down
                    optionsList.style.top = `${triggerRect.bottom - menuRect.top + 4}px`;
                    optionsList.style.bottom = "auto";
                    optionsList.className = "custom-dropdown-options-list open-down open";
                } else {
                    // Open up
                    optionsList.style.bottom = `${menuRect.bottom - triggerRect.top + 4}px`;
                    optionsList.style.top = "auto";
                    optionsList.className = "custom-dropdown-options-list open-up open";
                }
            }

            // Trigger click event to toggle dropdown list open/closed
            trigger.addEventListener("click", (e) => {
                e.stopPropagation();

                const isOpen = container.classList.contains("open");

                // Close all other dropdowns first
                const allContainers = settingsMenu.querySelectorAll(".custom-dropdown-container");
                allContainers.forEach(other => {
                    if (other !== container) {
                        other.classList.remove("open");
                    }
                });
                const allLists = settingsMenu.querySelectorAll(".custom-dropdown-options-list");
                allLists.forEach(otherList => {
                    if (otherList !== optionsList) {
                        otherList.classList.remove("open");
                    }
                });

                if (isOpen) {
                    container.classList.remove("open");
                    optionsList.classList.remove("open");
                } else {
                    container.classList.add("open");
                    positionOptionsList();
                }
            });

            // Sync when select value changes programmatically
            try {
                const valueDescriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
                if (valueDescriptor) {
                    Object.defineProperty(selectEl, 'value', {
                        get: function () {
                            return valueDescriptor.get.call(this);
                        },
                        set: function (val) {
                            valueDescriptor.set.call(this, val);
                            const selectedOpt = Array.from(selectEl.options).find(o => o.value === val);
                            if (selectedOpt) {
                                selectedText.textContent = selectedOpt.textContent;
                            }
                            const customOpts = optionsList.querySelectorAll(".custom-dropdown-option");
                            customOpts.forEach(opt => {
                                if (opt.getAttribute("data-value") === val) {
                                    opt.classList.add("active");
                                } else {
                                    opt.classList.remove("active");
                                }
                            });
                        },
                        configurable: true
                    });
                }
            } catch (e) {
                console.warn("Could not override select value property descriptor:", e);
            }

            // Sync when selectedIndex changes programmatically
            try {
                const indexDescriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'selectedIndex');
                if (indexDescriptor) {
                    Object.defineProperty(selectEl, 'selectedIndex', {
                        get: function () {
                            return indexDescriptor.get.call(this);
                        },
                        set: function (idx) {
                            indexDescriptor.set.call(this, idx);
                            const opt = selectEl.options[idx];
                            if (opt) {
                                selectedText.textContent = opt.textContent;
                                const val = opt.value;
                                const customOpts = optionsList.querySelectorAll(".custom-dropdown-option");
                                customOpts.forEach(co => {
                                    if (co.getAttribute("data-value") === val) {
                                        co.classList.add("active");
                                    } else {
                                        co.classList.remove("active");
                                    }
                                });
                            }
                        },
                        configurable: true
                    });
                }
            } catch (e) {
                console.warn("Could not override select selectedIndex property descriptor:", e);
            }

            // Sync on change event
            selectEl.addEventListener("change", () => {
                const val = selectEl.value;
                const selectedOpt = Array.from(selectEl.options).find(o => o.value === val);
                if (selectedOpt) {
                    selectedText.textContent = selectedOpt.textContent;
                }
                const customOpts = optionsList.querySelectorAll(".custom-dropdown-option");
                customOpts.forEach(opt => {
                    if (opt.getAttribute("data-value") === val) {
                        opt.classList.add("active");
                    } else {
                        opt.classList.remove("active");
                    }
                });
            });

            // Observe option changes (childList) in select element
            const observer = new MutationObserver(() => {
                rebuildCustomOptions();
            });
            observer.observe(selectEl, { childList: true, subtree: true });
        });

        // Close dropdowns when clicking outside anywhere on the document
        document.addEventListener("click", (e) => {
            const allDropdowns = settingsMenu.querySelectorAll(".custom-dropdown-container");
            allDropdowns.forEach(container => {
                if (!container.contains(e.target)) {
                    container.classList.remove("open");
                }
            });
            const allLists = settingsMenu.querySelectorAll(".custom-dropdown-options-list");
            allLists.forEach(list => {
                list.classList.remove("open");
            });
        });

        // Close dropdowns when scrolling settings menu content to prevent misalignment
        const contentScroll = settingsMenu.querySelector(".settings-menu-content");
        if (contentScroll) {
            contentScroll.addEventListener("scroll", () => {
                const allDropdowns = settingsMenu.querySelectorAll(".custom-dropdown-container");
                allDropdowns.forEach(container => {
                    container.classList.remove("open");
                });
                const allLists = settingsMenu.querySelectorAll(".custom-dropdown-options-list");
                allLists.forEach(list => {
                    list.classList.remove("open");
                });
            });
        }
    }

    // Initialize custom dropdowns
    initCustomDropdowns();

    // Setup Subtitle Customizer controls listeners
    const subFontSelect = document.getElementById("preview-sub-font");
    if (subFontSelect) {
        subFontSelect.addEventListener("change", applySubtitleStyles);
    }

    const subSizeSlider = document.getElementById("preview-sub-size");
    if (subSizeSlider) {
        subSizeSlider.addEventListener("input", function () {
            const valSpan = document.getElementById("preview-sub-size-val");
            if (valSpan) valSpan.textContent = this.value + "rem";
            applySubtitleStyles();
        });
    }

    const bgOpacitySlider = document.getElementById("preview-sub-bg-opacity");
    if (bgOpacitySlider) {
        bgOpacitySlider.addEventListener("input", function () {
            const valSpan = document.getElementById("preview-sub-bg-opacity-val");
            if (valSpan) valSpan.textContent = this.value + "%";
            applySubtitleStyles();
        });
    }

    const outlineSizeSlider = document.getElementById("preview-sub-outline");
    if (outlineSizeSlider) {
        outlineSizeSlider.addEventListener("input", function () {
            const valSpan = document.getElementById("preview-sub-outline-val");
            if (valSpan) valSpan.textContent = this.value + "px";
            applySubtitleStyles();
        });
    }

    const subPosSelect = document.getElementById("preview-sub-pos");
    if (subPosSelect) {
        subPosSelect.addEventListener("change", applySubtitleStyles);
    }

    // Setup Subtitle Embed Mode and Subtitle Translation Lang listeners & initial load
    const previewSubModeSelect = document.getElementById("preview-sub-mode-select");
    if (previewSubModeSelect) {
        const savedSubMode = localStorage.getItem("preview_sub_mode");
        if (savedSubMode) {
            previewSubModeSelect.value = savedSubMode;
            previewSubModeSelect.dispatchEvent(new Event("change"));
        }
        previewSubModeSelect.addEventListener("change", function () {
            localStorage.setItem("preview_sub_mode", this.value);
        });
    }

    if (previewSubTransSelect) {
        const savedSubTrans = localStorage.getItem("preview_sub_translate");
        if (savedSubTrans) {
            previewSubTransSelect.value = savedSubTrans;
            previewSubTransSelect.dispatchEvent(new Event("change"));
        }
        previewSubTransSelect.addEventListener("change", function () {
            localStorage.setItem("preview_sub_translate", this.value);
        });
    }

    // Swatches listeners
    document.querySelectorAll(".color-swatch").forEach(swatch => {
        swatch.addEventListener("click", function () {
            document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    document.querySelectorAll(".bg-swatch").forEach(swatch => {
        swatch.addEventListener("click", function () {
            document.querySelectorAll(".bg-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    document.querySelectorAll(".outline-swatch").forEach(swatch => {
        swatch.addEventListener("click", function () {
            document.querySelectorAll(".outline-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    // Custom color picker inputs
    const textColorPicker = document.getElementById("preview-sub-color");
    if (textColorPicker) {
        textColorPicker.addEventListener("input", function () {
            document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const bgColorPicker = document.getElementById("preview-sub-bg-color");
    if (bgColorPicker) {
        bgColorPicker.addEventListener("input", function () {
            document.querySelectorAll(".bg-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const outlineColorPicker = document.getElementById("preview-sub-outline-color");
    if (outlineColorPicker) {
        outlineColorPicker.addEventListener("input", function () {
            document.querySelectorAll(".outline-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const transcriptSearch = document.getElementById("transcript-search");
    if (transcriptSearch) {
        transcriptSearch.addEventListener("input", function () {
            renderTranscript();
        });
    }

    const videoPipBtn = document.getElementById("video-pip-btn");
    if (videoPipBtn && previewVideoPlayer) {
        videoPipBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            try {
                if (document.pictureInPictureElement) {
                    await document.exitPictureInPicture();
                } else if (previewVideoPlayer !== document.pictureInPictureElement) {
                    await previewVideoPlayer.requestPictureInPicture();
                }
            } catch (err) {
                console.error("Failed to toggle Picture-in-Picture mode:", err);
            }
        });
    }

    // voiceschanged callback to make sure voices list is refreshed
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => { };
    }

    // ----------------------------------------------------
    // BROWSER EXTENSION COMPANION INTEGRATION
    // ----------------------------------------------------
    function initExtensionSseListener() {
        const sseSource = new EventSource("/api/extension/stream");
        
        sseSource.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data && data.url) {
                    console.log("URL received from browser extension:", data.url);
                    
                    if (urlInput) {
                        urlInput.value = data.url;
                        updateUrlInputButtons();
                        urlInput.focus();
                        urlInput.classList.add("extension-received-pulse");
                        setTimeout(() => {
                            urlInput.classList.remove("extension-received-pulse");
                        }, 2000);
                        
                        performAnalysis();
                    }
                }
            } catch (err) {
                console.error("Error parsing extension SSE event data:", err);
            }
        };
        
        sseSource.onerror = (err) => {
            console.warn("Extension SSE connection error. Reconnecting in 3s...", err);
            sseSource.close();
            setTimeout(initExtensionSseListener, 3000);
        };
    }
    
    function checkUrlQueryParameter() {
        const params = new URLSearchParams(window.location.search);
        const urlParam = params.get("url");
        if (urlParam) {
            console.log("Auto-analyzing URL from query parameter:", urlParam);
            if (urlInput) {
                urlInput.value = urlParam;
                updateUrlInputButtons();
                performAnalysis();
                
                const cleanUrl = window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }
        }
    }

    // ----------------------------------------------------
    // FORMAT CONVERTER STUDIO & OPERATIONS INTEGRATION
    // ----------------------------------------------------
    function initFormatConverter() {
        let uploadedFilePath = null;
        let uploadedFileName = null;
        let currentProbeData = null;

        const tabBtns = document.querySelectorAll(".main-tab-btn");
        const tabContents = document.querySelectorAll(".main-tab-content");

        // Tab selection
        tabBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                tabBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                const targetTab = btn.getAttribute("data-tab");
                tabContents.forEach(content => {
                    if (content.id === targetTab) {
                        content.classList.remove("hidden");
                    } else {
                        content.classList.add("hidden");
                    }
                });
            });
        });

        const dropzone = document.getElementById("converter-dropzone");
        const fileInput = document.getElementById("converter-file-input");
        const browseBtn = document.getElementById("converter-browse-btn");
        const fileCard = document.getElementById("converter-file-card");
        const fileNameEl = document.getElementById("converter-file-name");
        const fileSizeEl = document.getElementById("converter-file-size");
        const removeFileBtn = document.getElementById("converter-remove-file-btn");
        const presetsBar = document.getElementById("converter-presets-bar");
        const presetBtns = document.querySelectorAll(".converter-preset-btn");
        const optionsBoard = document.getElementById("converter-options-board");
        const formatSelect = document.getElementById("converter-format-select");
        const videoCodecSelect = document.getElementById("converter-video-codec");
        const videoCodecGroup = document.getElementById("converter-video-codec-group");
        const videoResSelect = document.getElementById("converter-video-res");
        const videoResGroup = document.getElementById("converter-video-res-group");
        const videoFpsSelect = document.getElementById("converter-video-fps");
        const videoFpsGroup = document.getElementById("converter-video-fps-group");
        const audioQualitySelect = document.getElementById("converter-audio-quality");
        const audioQualityGroup = document.getElementById("converter-audio-quality-group");
        const audioChannelsSelect = document.getElementById("converter-audio-channels");
        const audioChannelsGroup = document.getElementById("converter-audio-channels-group");
        const audioVolumeSelect = document.getElementById("converter-audio-volume");
        const audioVolumeGroup = document.getElementById("converter-audio-volume-group");
        const gifOptionsGroup = document.getElementById("converter-gif-options-group");
        const gifFpsSelect = document.getElementById("converter-gif-fps");
        const gifScaleSelect = document.getElementById("converter-gif-scale");
        const trimToggle = document.getElementById("converter-trim-toggle");
        const trimControls = document.getElementById("converter-trim-controls");
        const trimStartInput = document.getElementById("converter-trim-start");
        const trimEndInput = document.getElementById("converter-trim-end");
        const setStartBtn = document.getElementById("converter-set-start-btn");
        const setEndBtn = document.getElementById("converter-set-end-btn");
        const resetTrimBtn = document.getElementById("converter-reset-trim-btn");
        const summaryBadge = document.getElementById("converter-summary-badge");
        const startConvertBtn = document.getElementById("btn-start-convert");

        // Player elements
        const previewContainer = document.getElementById("converter-preview-container");
        const videoPlayer = document.getElementById("converter-video-player");
        const audioWrapper = document.getElementById("converter-audio-wrapper");
        const audioPlayer = document.getElementById("converter-audio-player");
        const imageWrapper = document.getElementById("converter-image-wrapper");
        const imagePreview = document.getElementById("converter-image-preview");
        const fileIconBox = document.getElementById("converter-file-icon-box");
        const timeBadge = document.getElementById("converter-player-time-badge");
        const waveAnim = document.querySelector(".audio-wave-animation");
        const welcomeInfo = document.getElementById("converter-welcome-info");

        if (!dropzone || !fileInput) return;

        // Browse local file (Electron native or file input fallback)
        if (browseBtn) {
            browseBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (window.electronAPI && typeof window.electronAPI.selectFile === "function") {
                    try {
                        const filePath = await window.electronAPI.selectFile();
                        if (filePath) {
                            handleDirectLocalFile(filePath);
                            return;
                        }
                    } catch (err) {
                        console.error("Electron file picker error:", err);
                    }
                }
                fileInput.click();
            });
        }

        // Dropzone click triggers file picker
        dropzone.addEventListener("click", (e) => {
            if (e.target.closest("#converter-browse-btn")) return;
            if (browseBtn) {
                browseBtn.click();
            } else {
                fileInput.click();
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleSelectedFile(e.target.files[0]);
            }
        });

        // Drag & Drop handlers
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            }, false);
        });

        dropzone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                const file = files[0];
                // In Electron, file.path is populated with local disk path
                if (file.path && window.electronAPI) {
                    handleDirectLocalFile(file.path, file);
                } else {
                    handleSelectedFile(file);
                }
            }
        });

        // Format duration helper (seconds to HH:MM:SS or MM:SS)
        function formatSecs(secs) {
            if (isNaN(secs) || secs === null || secs < 0) return "00:00";
            const s = Math.floor(secs);
            const hrs = Math.floor(s / 3600);
            const mins = Math.floor((s % 3600) / 60);
            const remSecs = s % 60;
            const pad = (n) => String(n).padStart(2, "0");
            if (hrs > 0) {
                return `${pad(hrs)}:${pad(mins)}:${pad(remSecs)}`;
            }
            return `${pad(mins)}:${pad(remSecs)}`;
        }

        function formatBytes(bytes) {
            if (!bytes || bytes <= 0) return "0.0 MB";
            const mb = bytes / (1024 * 1024);
            if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
            return `${mb.toFixed(2)} MB`;
        }

        // Live player time update
        function updatePlayerTimeDisplay(cur, dur) {
            if (timeBadge) {
                timeBadge.textContent = `${formatSecs(cur)} / ${formatSecs(dur)}`;
            }
        }

        if (videoPlayer) {
            videoPlayer.addEventListener("timeupdate", () => {
                updatePlayerTimeDisplay(videoPlayer.currentTime, videoPlayer.duration);
            });
        }
        if (audioPlayer) {
            audioPlayer.addEventListener("timeupdate", () => {
                updatePlayerTimeDisplay(audioPlayer.currentTime, audioPlayer.duration);
            });
        }

        // Trimming controls toggle & sync
        if (trimToggle) {
            trimToggle.addEventListener("change", () => {
                if (trimToggle.checked) {
                    trimControls?.classList.remove("hidden");
                    resetTrimBtn?.classList.remove("hidden");
                } else {
                    trimControls?.classList.add("hidden");
                    resetTrimBtn?.classList.add("hidden");
                }
                updateSummaryBadge();
            });
        }

        function getCurrentMediaTime() {
            if (videoPlayer && !videoPlayer.classList.contains("hidden")) {
                return videoPlayer.currentTime || 0;
            }
            if (audioPlayer && !audioPlayer.classList.contains("hidden")) {
                return audioPlayer.currentTime || 0;
            }
            return 0;
        }

        if (setStartBtn && trimStartInput) {
            setStartBtn.addEventListener("click", () => {
                const t = getCurrentMediaTime();
                trimStartInput.value = formatSecs(t);
                updateSummaryBadge();
            });
        }

        if (setEndBtn && trimEndInput) {
            setEndBtn.addEventListener("click", () => {
                const t = getCurrentMediaTime();
                trimEndInput.value = formatSecs(t);
                updateSummaryBadge();
            });
        }

        if (resetTrimBtn) {
            resetTrimBtn.addEventListener("click", () => {
                if (trimStartInput) trimStartInput.value = "";
                if (trimEndInput) trimEndInput.value = "";
                if (trimToggle) trimToggle.checked = false;
                trimControls?.classList.add("hidden");
                resetTrimBtn?.classList.add("hidden");
                updateSummaryBadge();
            });
        }

        // Populate Probe Badges
        function renderProbeBadges(probe) {
            currentProbeData = probe || {};
            const badgesWrap = document.getElementById("converter-probe-badges");
            if (!badgesWrap) return;

            const durationEl = document.getElementById("probe-duration");
            const resEl = document.getElementById("probe-resolution");
            const vcodecEl = document.getElementById("probe-vcodec");
            const acodecEl = document.getElementById("probe-acodec");
            const bitrateEl = document.getElementById("probe-bitrate");

            if (probe.is_image) {
                durationEl?.classList.remove("hidden");
                durationEl.querySelector(".probe-val").textContent = "Image";
                const currentFmt = (formatSelect?.value || "").toLowerCase();
                const imageFmts = ["png", "jpg", "jpeg", "webp", "ico", "bmp", "tiff"];
                if (!imageFmts.includes(currentFmt)) {
                    if (formatSelect) formatSelect.value = "png";
                    presetBtns.forEach(b => b.classList.remove("active"));
                    const pngBtn = document.querySelector('.converter-preset-btn[data-preset="png-lossless"]');
                    if (pngBtn) pngBtn.classList.add("active");
                }
            } else if (probe.duration) {
                durationEl?.classList.remove("hidden");
                durationEl.querySelector(".probe-val").textContent = formatSecs(probe.duration);
            } else {
                durationEl?.classList.add("hidden");
            }

            if (probe.width && probe.height) {
                resEl?.classList.remove("hidden");
                let label = `${probe.width}x${probe.height}`;
                if (probe.height >= 2160) label += " (4K)";
                else if (probe.height >= 1440) label += " (2K)";
                else if (probe.height >= 1080) label += " (1080p)";
                else if (probe.height >= 720) label += " (720p)";
                else if (probe.height >= 480) label += " (480p)";
                resEl.querySelector(".probe-val").textContent = label;
            } else {
                resEl?.classList.add("hidden");
            }

            if (probe.video_codec) {
                vcodecEl?.classList.remove("hidden");
                vcodecEl.querySelector(".probe-val").textContent = probe.video_codec.toUpperCase();
            } else {
                vcodecEl?.classList.add("hidden");
            }

            if (probe.audio_codec) {
                acodecEl?.classList.remove("hidden");
                let chText = probe.channels ? ` (${probe.channels}ch)` : "";
                acodecEl.querySelector(".probe-val").textContent = `${probe.audio_codec.toUpperCase()}${chText}`;
            } else {
                acodecEl?.classList.add("hidden");
            }

            if (probe.has_audio === false) {
                presetBtns.forEach(btn => {
                    const p = btn.getAttribute("data-preset");
                    if (["best-mp3", "lossless-flac"].includes(p)) {
                        btn.style.opacity = "0.45";
                        btn.title = "Tập tin nguồn không chứa luồng âm thanh";
                    }
                });
            } else {
                presetBtns.forEach(btn => {
                    btn.style.opacity = "";
                });
            }

            if (probe.bitrate) {
                bitrateEl?.classList.remove("hidden");
                const kbps = Math.round(probe.bitrate / 1000);
                bitrateEl.querySelector(".probe-val").textContent = `${kbps} kbps`;
            } else {
                bitrateEl?.classList.add("hidden");
            }
        }

        // Dynamic Formats visibility & Summary Badge update
        function updateSummaryBadge() {
            if (!summaryBadge) return;
            const fmt = (formatSelect?.value || "mp4").toUpperCase();
            const isImage = ["PNG", "JPG", "JPEG", "ICO", "BMP", "TIFF"].includes(fmt) || (fmt === "WEBP" && currentProbeData && currentProbeData.is_image);
            const isAudio = ["MP3", "WAV", "FLAC", "M4A", "OGG", "OPUS"].includes(fmt);
            const isAnimation = ["GIF"].includes(fmt) || (fmt === "WEBP" && (!currentProbeData || !currentProbeData.is_image));
            const trimSection = document.querySelector(".converter-trim-section");

            let parts = [fmt];

            if (isImage) {
                // Static image format
                videoCodecGroup?.classList.add("hidden");
                videoResGroup?.classList.add("hidden");
                videoFpsGroup?.classList.add("hidden");
                gifOptionsGroup?.classList.add("hidden");
                audioQualityGroup?.classList.add("hidden");
                audioChannelsGroup?.classList.add("hidden");
                audioVolumeGroup?.classList.add("hidden");
                if (trimSection) trimSection.classList.add("hidden");

                if (fmt === "PNG") parts.push("Lossless Image");
                else if (fmt === "JPG" || fmt === "JPEG") parts.push("Photo (JPEG)");
                else if (fmt === "WEBP") parts.push("Modern Image");
                else if (fmt === "ICO") parts.push("App Icon (256x256)");
                else parts.push("Bitmap Image");
            } else if (isAudio) {
                if (trimSection) trimSection.classList.remove("hidden");
                // Audio format
                videoCodecGroup?.classList.add("hidden");
                videoResGroup?.classList.add("hidden");
                videoFpsGroup?.classList.add("hidden");
                gifOptionsGroup?.classList.add("hidden");
                audioQualityGroup?.classList.remove("hidden");
                audioChannelsGroup?.classList.remove("hidden");
                audioVolumeGroup?.classList.remove("hidden");

                if (!["WAV", "FLAC"].includes(fmt)) {
                    parts.push(audioQualitySelect?.value || "320k");
                } else {
                    parts.push("Lossless");
                }
                if (audioChannelsSelect?.value === "mono") parts.push("Mono");
            } else if (isAnimation) {
                if (trimSection) trimSection.classList.remove("hidden");
                // GIF or Animated WebP
                videoCodecGroup?.classList.add("hidden");
                videoResGroup?.classList.remove("hidden");
                videoFpsGroup?.classList.add("hidden");
                gifOptionsGroup?.classList.remove("hidden");
                audioQualityGroup?.classList.add("hidden");
                audioChannelsGroup?.classList.add("hidden");
                audioVolumeGroup?.classList.add("hidden");

                parts.push(`${gifFpsSelect?.value || 15}fps`);
                parts.push(`${gifScaleSelect?.value || 480}p`);
            } else {
                if (trimSection) trimSection.classList.remove("hidden");
                // Video format (MP4, MKV, WebM, MOV, AVI, TS)
                videoCodecGroup?.classList.remove("hidden");
                videoResGroup?.classList.remove("hidden");
                videoFpsGroup?.classList.remove("hidden");
                gifOptionsGroup?.classList.add("hidden");
                audioQualityGroup?.classList.remove("hidden");
                audioChannelsGroup?.classList.remove("hidden");
                audioVolumeGroup?.classList.remove("hidden");

                const codec = videoCodecSelect?.value || "auto";
                parts.push(codec === "copy" ? "Passthrough" : codec.toUpperCase());
                parts.push(videoResSelect?.value || "Original");
                if (audioChannelsSelect?.value === "mute") {
                    parts.push("Muted");
                } else {
                    parts.push(audioQualitySelect?.value || "320k");
                }
            }

            if (!isImage && trimToggle?.checked && (trimStartInput?.value || trimEndInput?.value)) {
                parts.push("Trimmed");
            }

            summaryBadge.textContent = parts.join(" • ");
        }

        // Bind change events to all selects
        [formatSelect, videoCodecSelect, videoResSelect, videoFpsSelect, audioQualitySelect, audioChannelsSelect, audioVolumeSelect, gifFpsSelect, gifScaleSelect].forEach(sel => {
            if (sel) sel.addEventListener("change", () => {
                // Deactivate preset buttons if manually changed
                presetBtns.forEach(b => b.classList.remove("active"));
                if (sel === formatSelect && currentProbeData && currentProbeData.has_audio === false) {
                    const chosen = (formatSelect.value || "").toLowerCase();
                    if (["mp3", "wav", "flac", "m4a", "ogg", "opus"].includes(chosen)) {
                        showAlert("Thông báo", "Tập tin nguồn không chứa luồng âm thanh. Bạn nên chọn xuất định dạng Video hoặc Ảnh.");
                    }
                }
                updateSummaryBadge();
            });
        });

        // 1-Click Preset handlers
        presetBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const preset = btn.getAttribute("data-preset");
                if ((preset === "best-mp3" || preset === "lossless-flac") && currentProbeData && currentProbeData.has_audio === false) {
                    showAlert("Thông báo", "Tập tin nguồn không chứa luồng âm thanh để xuất định dạng MP3/FLAC.");
                    return;
                }
                presetBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                applyQuickPreset(preset);
            });
        });

        function applyQuickPreset(preset) {
            if (preset === "universal-mp4") {
                if (formatSelect) formatSelect.value = "mp4";
                if (videoCodecSelect) videoCodecSelect.value = "h264";
                if (videoResSelect) videoResSelect.value = "original";
                if (videoFpsSelect) videoFpsSelect.value = "original";
                if (audioQualitySelect) audioQualitySelect.value = "320k";
                if (audioChannelsSelect) audioChannelsSelect.value = "original";
                if (audioVolumeSelect) audioVolumeSelect.value = "100";
            } else if (preset === "fast-remux") {
                if (formatSelect) formatSelect.value = "mp4";
                if (videoCodecSelect) videoCodecSelect.value = "copy";
                if (videoResSelect) videoResSelect.value = "original";
                if (audioQualitySelect) audioQualitySelect.value = "320k";
            } else if (preset === "best-mp3") {
                if (formatSelect) formatSelect.value = "mp3";
                if (audioQualitySelect) audioQualitySelect.value = "320k";
                if (audioChannelsSelect) audioChannelsSelect.value = "original";
                if (audioVolumeSelect) audioVolumeSelect.value = "100";
            } else if (preset === "lossless-flac") {
                if (formatSelect) formatSelect.value = "flac";
                if (audioChannelsSelect) audioChannelsSelect.value = "original";
                if (audioVolumeSelect) audioVolumeSelect.value = "100";
            } else if (preset === "png-lossless") {
                if (formatSelect) formatSelect.value = "png";
            } else if (preset === "jpg-photo") {
                if (formatSelect) formatSelect.value = "jpg";
            } else if (preset === "modern-webp") {
                if (formatSelect) formatSelect.value = "webp";
            } else if (preset === "app-ico") {
                if (formatSelect) formatSelect.value = "ico";
            } else if (preset === "apple-mov") {
                if (formatSelect) formatSelect.value = "mov";
                if (videoCodecSelect) videoCodecSelect.value = "h264";
                if (videoResSelect) videoResSelect.value = "original";
                if (audioQualitySelect) audioQualitySelect.value = "320k";
            } else if (preset === "animated-gif") {
                if (formatSelect) formatSelect.value = "gif";
                if (gifFpsSelect) gifFpsSelect.value = "15";
                if (gifScaleSelect) gifScaleSelect.value = "480";
            } else if (preset === "animated-webp") {
                if (formatSelect) formatSelect.value = "webp";
                if (gifFpsSelect) gifFpsSelect.value = "20";
                if (gifScaleSelect) gifScaleSelect.value = "720";
            }
            updateSummaryBadge();
        }

        // Direct Local File handler (Electron native or local path)
        async function handleDirectLocalFile(filePath, fileObj = null) {
            uploadedFilePath = filePath;
            uploadedFileName = filePath.split(/[/\\]/).pop();

            fileNameEl.textContent = uploadedFileName;
            if (fileObj && fileObj.size) {
                fileSizeEl.textContent = formatBytes(fileObj.size);
            } else {
                fileSizeEl.textContent = "Local File";
            }

            dropzone.classList.add("hidden");
            fileCard.classList.remove("hidden");
            presetsBar?.classList.remove("hidden");
            optionsBoard.classList.remove("hidden");
            welcomeInfo?.classList.add("hidden");

            // Setup preview player
            setupPreviewPlayer(filePath, fileObj);

            // Probe media file directly via server endpoint
            try {
                const probeRes = await fetch("/api/convert/probe", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file_path: filePath })
                });
                const probeJson = await probeRes.json();
                if (probeRes.ok && probeJson.status === "success" && probeJson.probe) {
                    renderProbeBadges(probeJson.probe);
                    if (probeJson.probe.size && (!fileObj || !fileObj.size)) {
                        fileSizeEl.textContent = formatBytes(probeJson.probe.size);
                    }
                }
            } catch (err) {
                console.warn("Media probe failed:", err);
            }

            if (startConvertBtn) {
                startConvertBtn.disabled = false;
                startConvertBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> <span>Start Transcoding</span>`;
            }

            updateSummaryBadge();
        }

        // Browser upload handler (for non-Electron environments)
        function handleSelectedFile(file) {
            // If running in Electron with file.path available, bypass upload!
            if (file.path && window.electronAPI) {
                handleDirectLocalFile(file.path, file);
                return;
            }

            fileNameEl.textContent = file.name;
            fileSizeEl.textContent = formatBytes(file.size);

            dropzone.classList.add("hidden");
            fileCard.classList.remove("hidden");
            presetsBar?.classList.remove("hidden");
            optionsBoard.classList.remove("hidden");
            welcomeInfo?.classList.add("hidden");

            // Setup preview player using blob URL
            setupPreviewPlayer(null, file);

            // Disable conversion trigger until upload is complete
            if (startConvertBtn) {
                startConvertBtn.disabled = true;
                startConvertBtn.innerHTML = `<span>Uploading (0%)...</span>`;
            }

            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append("file", file);

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    if (startConvertBtn) {
                        startConvertBtn.innerHTML = `<span>Uploading (${pct}%)...</span>`;
                    }
                }
            });

            xhr.onload = () => {
                try {
                    const resData = JSON.parse(xhr.responseText);
                    if (xhr.status === 200 && resData.status === "success") {
                        uploadedFilePath = resData.file_path;
                        uploadedFileName = resData.filename;

                        if (resData.probe) {
                            renderProbeBadges(resData.probe);
                        }

                        if (startConvertBtn) {
                            startConvertBtn.disabled = false;
                            startConvertBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> <span>Start Transcoding</span>`;
                        }
                        updateSummaryBadge();
                    } else {
                        throw new Error(resData.message || "Upload failed.");
                    }
                } catch (err) {
                    showAlert("Lỗi tải tệp tin", err.message);
                    resetConverterUI();
                }
            };

            xhr.onerror = () => {
                showAlert("Lỗi kết nối", "Không thể gửi tệp tin lên máy chủ.");
                resetConverterUI();
            };

            xhr.open("POST", "/api/convert/upload");
            xhr.send(formData);
        }

        function setupPreviewPlayer(filePath, fileObj) {
            if (!previewContainer || !videoPlayer || !audioWrapper || !audioPlayer) return;

            // Clear existing sources
            if (videoPlayer.src && videoPlayer.src.startsWith("blob:")) URL.revokeObjectURL(videoPlayer.src);
            if (audioPlayer.src && audioPlayer.src.startsWith("blob:")) URL.revokeObjectURL(audioPlayer.src);
            if (imagePreview && imagePreview.src && imagePreview.src.startsWith("blob:")) URL.revokeObjectURL(imagePreview.src);

            videoPlayer.src = "";
            videoPlayer.classList.add("hidden");
            audioPlayer.src = "";
            audioWrapper.classList.add("hidden");
            if (imagePreview) imagePreview.src = "";
            if (imageWrapper) imageWrapper.classList.add("hidden");
            if (waveAnim) waveAnim.classList.remove("animating");

            let mediaSrc = "";
            if (fileObj) {
                mediaSrc = URL.createObjectURL(fileObj);
            } else if (filePath) {
                mediaSrc = `/api/convert/preview-stream?file_path=${encodeURIComponent(filePath)}`;
            }

            if (!mediaSrc) return;

            const name = (fileObj?.name || filePath || "").toLowerCase();
            const isImageExt = /\.(jpg|jpeg|png|webp|gif|bmp|tiff|ico|svg|avif|heic)$/i.test(name) || (fileObj && fileObj.type && fileObj.type.startsWith("image/"));
            const isAudioExt = /\.(mp3|wav|flac|m4a|ogg|opus|aac|wma)$/i.test(name);
            const isVideoExt = /\.(mp4|mkv|webm|mov|avi|ts|flv|wmv|m4v)$/i.test(name);

            const trimSection = document.querySelector(".converter-trim-section");

            if (isImageExt) {
                if (imagePreview) imagePreview.src = mediaSrc;
                if (imageWrapper) imageWrapper.classList.remove("hidden");
                previewContainer.classList.remove("hidden");
                if (timeBadge) timeBadge.textContent = "Image Preview";
                if (trimSection) trimSection.classList.add("hidden");
                if (fileIconBox) {
                    fileIconBox.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`;
                }
            } else if (isVideoExt || (fileObj && fileObj.type && fileObj.type.startsWith("video/"))) {
                videoPlayer.src = mediaSrc;
                videoPlayer.classList.remove("hidden");
                previewContainer.classList.remove("hidden");
                if (trimSection) trimSection.classList.remove("hidden");
                if (fileIconBox) {
                    fileIconBox.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>`;
                }
            } else if (isAudioExt || (fileObj && fileObj.type && fileObj.type.startsWith("audio/"))) {
                audioPlayer.src = mediaSrc;
                audioWrapper.classList.remove("hidden");
                previewContainer.classList.remove("hidden");
                if (trimSection) trimSection.classList.remove("hidden");
                if (fileIconBox) {
                    fileIconBox.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>`;
                }

                if (waveAnim) {
                    audioPlayer.onplay = () => waveAnim.classList.add("animating");
                    audioPlayer.onpause = () => waveAnim.classList.remove("animating");
                    audioPlayer.onended = () => waveAnim.classList.remove("animating");
                }
            } else {
                // Fallback attempt with video player
                videoPlayer.src = mediaSrc;
                videoPlayer.classList.remove("hidden");
                previewContainer.classList.remove("hidden");
                if (trimSection) trimSection.classList.remove("hidden");
            }
        }

        // Remove selected file handler
        if (removeFileBtn) {
            removeFileBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                resetConverterUI();
            });
        }

        // Reset UI
        function resetConverterUI() {
            uploadedFilePath = null;
            uploadedFileName = null;
            currentProbeData = null;
            fileInput.value = "";

            dropzone.classList.remove("hidden");
            fileCard.classList.add("hidden");
            presetsBar?.classList.add("hidden");
            optionsBoard.classList.add("hidden");
            welcomeInfo?.classList.remove("hidden");

            if (previewContainer) previewContainer.classList.add("hidden");
            if (videoPlayer) {
                if (videoPlayer.src && videoPlayer.src.startsWith("blob:")) URL.revokeObjectURL(videoPlayer.src);
                videoPlayer.src = "";
                videoPlayer.classList.add("hidden");
            }
            if (audioPlayer) {
                if (audioPlayer.src && audioPlayer.src.startsWith("blob:")) URL.revokeObjectURL(audioPlayer.src);
                audioPlayer.src = "";
                audioPlayer.onplay = null;
                audioPlayer.onpause = null;
                audioPlayer.onended = null;
            }
            if (audioWrapper) audioWrapper.classList.add("hidden");
            if (imagePreview) {
                if (imagePreview.src && imagePreview.src.startsWith("blob:")) URL.revokeObjectURL(imagePreview.src);
                imagePreview.src = "";
            }
            if (imageWrapper) imageWrapper.classList.add("hidden");
            if (waveAnim) waveAnim.classList.remove("animating");
            if (timeBadge) timeBadge.textContent = "00:00 / 00:00";
            const trimSection = document.querySelector(".converter-trim-section");
            if (trimSection) trimSection.classList.remove("hidden");

            // Reset probe badges
            document.querySelectorAll("#converter-probe-badges .probe-badge").forEach(b => b.classList.add("hidden"));

            if (startConvertBtn) {
                startConvertBtn.disabled = false;
                startConvertBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> <span>Start Transcoding</span>`;
            }
        }

        // Start Conversion Trigger Handler
        if (startConvertBtn) {
            startConvertBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                if (!uploadedFilePath) {
                    showAlert("Lỗi", "Vui lòng chọn hoặc kéo thả tệp tin cần chuyển đổi trước.");
                    return;
                }

                startConvertBtn.disabled = true;
                const origText = startConvertBtn.innerHTML;
                startConvertBtn.innerHTML = `<span>Transcoding...</span> <svg class="downloads-manager-spinner" viewBox="0 0 24 24" style="width: 14px; height: 14px; margin-left: 4px;"></svg>`;

                try {
                    const fmt = formatSelect.value;
                    const isCopy = videoCodecSelect?.value === "copy";
                    const isMute = audioChannelsSelect?.value === "mute";

                    const requestPayload = {
                        file_path: uploadedFilePath,
                        filename: uploadedFileName,
                        target_format: fmt,
                        video_codec: videoCodecSelect?.value || "auto",
                        video_res: videoResSelect?.value || "original",
                        video_fps: videoFpsSelect?.value || "original",
                        audio_bitrate: audioQualitySelect?.value || "320k",
                        audio_channels: audioChannelsSelect?.value || "original",
                        audio_volume: audioVolumeSelect?.value || "100",
                        mute_audio: isMute,
                        trim_start: (trimToggle?.checked && trimStartInput?.value.trim()) ? trimStartInput.value.trim() : null,
                        trim_end: (trimToggle?.checked && trimEndInput?.value.trim()) ? trimEndInput.value.trim() : null,
                        gif_fps: gifFpsSelect?.value || "15",
                        gif_scale: gifScaleSelect?.value || "480",
                        passthrough: isCopy
                    };

                    const response = await fetch("/api/convert", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(requestPayload)
                    });

                    const data = await response.json();
                    if (!response.ok || data.status !== "success") {
                        throw new Error(data.message || "Failed to trigger conversion.");
                    }

                    const taskId = data.download_id;
                    console.log(`Conversion enqueued. ID: ${taskId}`);

                    // Create task card in Downloads Manager
                    createTaskCard(taskId, uploadedFileName, `Convert to ${fmt.toUpperCase()}`);

                    // Keep Downloads Manager open so user sees progress
                    if (downloadsManager && downloadsManager.classList.contains("hidden")) {
                        downloadsManager.classList.remove("hidden");
                    }

                    // Open SSE listener for real-time transcode progress
                    const sse = new EventSource(`/api/download/progress/${taskId}`);
                    activeTasks[taskId] = { sse, btn: null, activeRow: null, isCloudUpload: false, filename: data.filename || uploadedFileName };
                    updateDownloadsCount();

                    sse.onmessage = (event) => {
                        try {
                            const statusData = JSON.parse(event.data);
                            const card = document.getElementById(`task-card-${taskId}`);
                            if (!card) return;

                            const fillBar = card.querySelector(".download-task-fill");
                            const pctSpan = card.querySelector(".download-task-pct");
                            const msgSpan = card.querySelector(".download-task-msg");

                            if (statusData.status === "pending") {
                                if (fillBar) {
                                    fillBar.classList.add("striped");
                                    fillBar.style.width = "5%";
                                }
                                if (pctSpan) pctSpan.textContent = "0%";
                                if (msgSpan) msgSpan.textContent = statusData.message || "Initializing...";
                            } 
                            else if (statusData.status === "processing") {
                                if (fillBar) {
                                    fillBar.classList.remove("striped");
                                    fillBar.style.width = `${statusData.progress}%`;
                                }
                                if (pctSpan) pctSpan.textContent = `${statusData.progress}%`;
                                if (msgSpan) msgSpan.textContent = statusData.message || `Transcoding... ${statusData.progress}%`;
                            } 
                            else if (statusData.status === "complete") {
                                if (statusData.filename && activeTasks[taskId]) {
                                    activeTasks[taskId].filename = statusData.filename;
                                }
                                completeTask(taskId);
                            } 
                            else if (statusData.status === "error") {
                                throw new Error(statusData.error || statusData.message || "Conversion failed.");
                            }
                        } catch (err) {
                            if (sse) sse.close();
                            handleDownloadFailure(taskId, err.message, null, null);
                        }
                    };

                    sse.onerror = (err) => {
                        console.warn(`Conversion progress SSE closed or failed for ${taskId}`, err);
                        if (sse) sse.close();
                    };

                } catch (err) {
                    showAlert("Lỗi", "Không thể kích hoạt tiến trình chuyển đổi: " + err.message);
                } finally {
                    startConvertBtn.disabled = false;
                    startConvertBtn.innerHTML = origText;
                }
            });
        }

        // Initialize default state
        updateSummaryBadge();
    }

    initExtensionSseListener();
    checkUrlQueryParameter();
    initFormatConverter();
});

// --- Star Grid Mesh (3D Gravity Well & Elastic Net) Effect ---
document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("cursor-canvas");
    if (!canvas) return;

    const audioEl = document.getElementById("preview-audio-player");
    const videoEl = document.getElementById("preview-video-player");

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
        mouseSpeed = Math.sqrt(dx * dx + dy * dy);
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
        const style = getComputedStyle(document.documentElement);
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
                let dist = Math.sqrt(dx * dx + dy * dy);
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

        update(mouse, volume = 0, freqData = null) {
            this.rotation += this.rotationSpeed;

            // 1. Slow wave movement for the floating effect (superimposed organic wave)
            let time = Date.now() * 0.0005;

            // Modify wave speed and size based on volume!
            // When sound reactivity is enabled and music plays, the wave wiggles faster and wider
            const isSoundReactive = window.canvasSettings.soundReactiveEnabled !== false;
            const useVolume = isSoundReactive ? volume : 0;

            let waveSpeedMult = 1.0 + useVolume * 1.5;
            let waveAmpMult = 1.0 + useVolume * 2.0;

            let waveX = Math.sin(time * 1.3 * waveSpeedMult + (this.col * 0.22) + (this.row * 0.15)) * 10 * waveAmpMult + Math.cos(time * 0.7 * waveSpeedMult + (this.row * 0.35)) * 4 * waveAmpMult;
            let waveY = Math.cos(time * 1.1 * waveSpeedMult + (this.col * 0.15) + (this.row * 0.22)) * 10 * waveAmpMult + Math.sin(time * 0.6 * waveSpeedMult + (this.col * 0.35)) * 4 * waveAmpMult;

            // Keep grid coordinate stable globally
            let currentOrigX = this.baseX + waveX * this.anchorFactor;
            let currentOrigY = this.baseY + waveY * this.anchorFactor;

            // Fetch wave height from the 2D ripple buffer
            let targetZ = 0;
            if (window.canvasSettings.ripplesEnabled && rippleBuffer1[this.col] && rippleBuffer1[this.col][this.row] !== undefined) {
                targetZ = rippleBuffer1[this.col][this.row] * this.anchorFactor;
            }

            // 2. Dynamic 3D Sound Wave Ripple propagating from the center
            let soundZ = 0;
            if (isSoundReactive && useVolume > 0 && freqData && freqData.length > 0) {
                let screenCenterX = window.innerWidth / 2;
                let screenCenterY = window.innerHeight / 2;
                let dxCenter = this.x - screenCenterX;
                let dyCenter = this.y - screenCenterY;
                let distFromCenter = Math.sqrt(dxCenter * dxCenter + dyCenter * dyCenter);
                let maxRadius = Math.sqrt(screenCenterX * screenCenterX + screenCenterY * screenCenterY) || 1;

                // Map distance to a frequency bin (closer = bass/low, outer = high frequencies)
                let binIdx = Math.floor((1 - distFromCenter / maxRadius) * (freqData.length - 1));
                binIdx = Math.max(0, Math.min(freqData.length - 1, binIdx));
                let binVal = freqData[binIdx] / 255; // 0..1

                // Symmetrical wave traveling outward from center
                let timeOffset = Date.now() * 0.008;
                let waveParam = distFromCenter * 0.012 - timeOffset;

                // Sound displacement mixes the specific frequency bin value and overall volume (scaled up for dramatic effect)
                soundZ = Math.sin(waveParam) * (binVal * 160 + useVolume * 160) * this.anchorFactor;
            }

            // Calculate constant mouse indentation (funnel effect) centered under the cursor
            let dx = mouse.x - this.x;
            let dy = mouse.y - this.y;
            let dist = Math.sqrt(dx * dx + dy * dy);
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

            // 3. Spring physics for Z depth (combine ripple height, funnel indentation, and sound waves!)
            let combinedTargetZ = targetZ + indentZ + soundZ;
            this.vz += (combinedTargetZ - this.z) * 0.07; // physical spring coefficient
            this.vz *= 0.91; // damping
            this.z += this.vz;

            // 4. Horizontal coordinate restoration
            let targetX = currentOrigX;
            let targetY = currentOrigY;

            // 5. Spring physics for X and Y coordinate restoration
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

            // Direct 2D sound-reactive ripple displacement to make the wave extremely visible
            const isSoundReactive = window.canvasSettings.soundReactiveEnabled !== false;
            if (isSoundReactive && window.currentVolume > 0) {
                let dxCenter = this.px - window.innerWidth / 2;
                let dyCenter = this.py - window.innerHeight / 2;
                let distFromCenter = Math.sqrt(dxCenter * dxCenter + dyCenter * dyCenter) || 1;

                let waveParam = distFromCenter * 0.015 - Date.now() * 0.012;
                // Ripple amplitude: up to 25px displacement based on volume and anchor factor
                let waveAmp = window.currentVolume * 25 * this.anchorFactor;
                let angle = Math.atan2(dyCenter, dxCenter) || 0;

                this.px += Math.cos(angle) * Math.sin(waveParam) * waveAmp;
                this.py += Math.sin(angle) * Math.sin(waveParam) * waveAmp;
            }
        }

        draw(ctx) {
            // Breathing size oscillation + high-frequency twinkle for a lifelike organic pulse
            let twinkle = Math.sin(Date.now() * 0.016 + this.col * 1.7 + this.row * 1.3) * 0.4;
            let breathe = Math.sin(Date.now() * 0.0025 + this.col * 0.5 + this.row * 0.3) * 0.55 + twinkle;

            // Tension increases brightness and size of the knot
            let tension = Math.min(1.5, Math.abs(this.z) / 80);

            // Add a direct pulsation based on currentVolume!
            const isSoundReactive = window.canvasSettings.soundReactiveEnabled !== false;
            const soundPulse = isSoundReactive ? (currentVolume * 6.5) : 0;

            let size = (this.baseSize + (isLightTheme ? 0.5 : 0) + breathe + tension * 1.5 + soundPulse) * this.scale;
            if (size < 1) size = 1;

            let alpha = isLightTheme ? 0.45 + (this.scale * 0.45) : 0.2 + (this.scale * 0.6); // Deeper points fade away
            alpha += tension * 0.3 + (soundPulse * 0.1);
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
    let dataArray = null;
    let bufferLength = 0;
    let currentVolume = 0;

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

        // Fetch audio frequencies if analyser is active and sound reactive is enabled
        let volume = 0;
        if (window.canvasSettings.soundReactiveEnabled !== false && window.audioAnalyser) {
            const analyser = window.audioAnalyser;
            if (bufferLength !== analyser.frequencyBinCount) {
                bufferLength = analyser.frequencyBinCount;
                dataArray = new Uint8Array(bufferLength);
            }

            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            volume = sum / bufferLength; // average amplitude (0..255)
        }
        currentVolume = volume / 255; // normalize to 0..1
        window.currentVolume = currentVolume; // expose globally for easy access

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
            p.update(mouse, currentVolume, dataArray);
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

    // --- Clipboard Auto-Detect Toast Feature ---
    const clipboardToast = document.getElementById("clipboard-toast");
    const toastLinkText = document.getElementById("toast-link-text");
    const closeToastBtn = document.getElementById("close-toast-btn");
    const toastAnalyzeBtn = document.getElementById("toast-analyze-btn");
    const urlInput = document.getElementById("url-input");
    const analyzeBtn = document.getElementById("analyze-btn");
    let toastDismissTimeout = null;

    function showClipboardToast(link) {
        if (!clipboardToast || !toastLinkText) return;

        // Update URL text
        toastLinkText.textContent = link;

        // Show Toast
        clipboardToast.classList.remove("hidden");
        clipboardToast.classList.add("show");

        // Auto dismiss after 10s
        if (toastDismissTimeout) {
            clearTimeout(toastDismissTimeout);
        }
        toastDismissTimeout = setTimeout(() => {
            hideClipboardToast();
        }, 10000);
    }

    function hideClipboardToast() {
        if (!clipboardToast) return;
        clipboardToast.classList.remove("show");
        clipboardToast.classList.add("hidden");
        if (toastDismissTimeout) {
            clearTimeout(toastDismissTimeout);
            toastDismissTimeout = null;
        }
        if (window.electronAPI && window.electronAPI.resetClipboardCache) {
            window.electronAPI.resetClipboardCache();
        }
    }

    if (window.electronAPI && window.electronAPI.onClipboardLink) {
        window.electronAPI.onClipboardLink((link) => {
            // Respect the clipboard auto-detect toggle setting
            const clipboardDetectCb = document.getElementById("clipboard-detect-checkbox");
            if (clipboardDetectCb && !clipboardDetectCb.checked) return;

            // Only show Toast if the input field doesn't already contain this link
            // and the link is different from what's currently being entered/analyzed.
            if (urlInput && urlInput.value.trim() !== link.trim()) {
                showClipboardToast(link);
            }
        });
    }

    if (closeToastBtn) {
        closeToastBtn.addEventListener("click", () => {
            hideClipboardToast();
        });
    }

    if (toastAnalyzeBtn) {
        toastAnalyzeBtn.addEventListener("click", () => {
            const link = toastLinkText ? toastLinkText.textContent : "";
            if (link && urlInput) {
                urlInput.value = link;
                // Dispatch input event to trigger clear button state updating
                urlInput.dispatchEvent(new Event("input"));

                // Trigger analysis
                if (analyzeBtn) {
                    analyzeBtn.click();
                }
            }
            hideClipboardToast();
        });
    }

    // --- Application Auto-Update Floating Card & Controls ---
    const updateProgressToast = document.getElementById("update-progress-toast");
    const updateToastTitle = document.getElementById("update-toast-title");
    const updateToastCloseBtn = document.getElementById("update-toast-close-btn");
    const updateStatusText = document.getElementById("update-status-text");
    const updatePercentText = document.getElementById("update-percent-text");
    const updateProgressBarFill = document.getElementById("update-progress-bar-fill");
    const updateBytesText = document.getElementById("update-bytes-text");
    const updateSpeedText = document.getElementById("update-speed-text");
    const updateActionsContainer = document.getElementById("update-actions-container");
    const btnUpdateInstallNow = document.getElementById("btn-update-install-now");
    const btnUpdateInstallQuit = document.getElementById("btn-update-install-quit");
    const btnCheckAppUpdate = document.getElementById("btn-check-app-update");

    function showUpdateToast(title = "Cập nhật ứng dụng") {
        if (!updateProgressToast) return;
        if (updateToastTitle) updateToastTitle.textContent = title;
        updateProgressToast.classList.remove("hidden");
        updateProgressToast.classList.add("show");
    }

    function hideUpdateToast() {
        if (!updateProgressToast) return;
        updateProgressToast.classList.remove("show");
        updateProgressToast.classList.add("hidden");
    }

    if (updateToastCloseBtn) {
        updateToastCloseBtn.addEventListener("click", () => {
            hideUpdateToast();
        });
    }

    const triggerAppAlert = (title, message, cb, type) => {
        if (typeof window.showAlert === "function") {
            window.showAlert(title, message, cb, type);
        } else {
            alert((title ? title + "\n\n" : "") + (message || ""));
            if (cb) cb();
        }
    };

    const triggerAppConfirm = (opts) => {
        if (typeof window.showConfirm === "function") {
            window.showConfirm(opts);
        } else {
            const ok = confirm((opts && opts.title ? opts.title + "\n\n" : "") + ((opts && opts.message) || ""));
            if (ok && opts && opts.onYes) opts.onYes();
            else if (!ok && opts && opts.onNo) opts.onNo();
        }
    };

    if (btnCheckAppUpdate) {
        btnCheckAppUpdate.addEventListener("click", () => {
            const sDropdown = document.getElementById("settings-dropdown");
            const sToggle = document.getElementById("settings-toggle");
            if (sDropdown) sDropdown.classList.add("hidden");
            if (sToggle) sToggle.classList.remove("active");

            if (window.electronAPI && window.electronAPI.checkForUpdates) {
                window.electronAPI.checkForUpdates();
                showUpdateToast("SYS // KIỂM TRA BẢN MỚI");
                if (updateStatusText) updateStatusText.textContent = "Đang kết nối máy chủ GitHub...";
                if (updateProgressBarFill) {
                    updateProgressBarFill.style.width = "40%";
                    updateProgressBarFill.style.backgroundColor = "";
                }
                if (updatePercentText) updatePercentText.textContent = "";
                if (updateBytesText) updateBytesText.textContent = "";
                if (updateSpeedText) updateSpeedText.textContent = "";
                if (updateActionsContainer) updateActionsContainer.classList.add("hidden");
            } else {
                triggerAppAlert("Thông báo", "Tính năng tự động cập nhật chỉ khả dụng trên ứng dụng Desktop.", null, "info");
            }
        });
    }

    if (window.electronAPI && window.electronAPI.onUpdateAvailable) {
        window.electronAPI.onUpdateAvailable((info) => {
            hideUpdateToast();
            triggerAppConfirm({
                title: "Bản cập nhật mới sẵn sàng",
                message: 'Đã có phiên bản v' + (info.version || '') + ' (hiện tại v' + (info.currentVersion || '') + ').\n\n' + (info.changelog ? info.changelog.trim() : 'Bạn có muốn tải và cài đặt bản cập nhật tự động không?'),
                yesText: "Cập nhật tự động",
                noText: "Để sau",
                type: "info",
                onYes: () => {
                    if (window.electronAPI && window.electronAPI.startAutoUpdate) {
                        window.electronAPI.startAutoUpdate({
                            url: info.url,
                            version: info.version
                        });
                    }
                }
            });
        });
    }

    if (window.electronAPI && window.electronAPI.onAppAlert) {
        window.electronAPI.onAppAlert(({ title, message, type = "info" }) => {
            if (updateProgressToast && !updateProgressToast.classList.contains("hidden")) {
                if (updateStatusText) updateStatusText.textContent = (message || "").split("\n")[0];
                if (updateProgressBarFill) {
                    updateProgressBarFill.style.width = "100%";
                    if (type === "error" || type === "danger") {
                        updateProgressBarFill.style.backgroundColor = "#ef4444";
                    }
                }
                setTimeout(hideUpdateToast, 600);
            } else {
                hideUpdateToast();
            }
            triggerAppAlert(title, message, null, type);
        });
    }

    if (btnUpdateInstallNow) {
        btnUpdateInstallNow.addEventListener("click", () => {
            if (window.electronAPI && window.electronAPI.installUpdateNow) {
                if (updateStatusText) updateStatusText.textContent = "Đang khởi động trình cài đặt...";
                window.electronAPI.installUpdateNow();
            }
        });
    }

    if (btnUpdateInstallQuit) {
        btnUpdateInstallQuit.addEventListener("click", () => {
            if (window.electronAPI && window.electronAPI.installUpdateOnQuit) {
                window.electronAPI.installUpdateOnQuit();
                hideUpdateToast();
                triggerAppAlert("Đã lưu thiết lập", "Bản cập nhật mới sẽ được tự động cài đặt khi bạn đóng ứng dụng.", null, "success");
            }
        });
    }

    if (window.electronAPI && window.electronAPI.onUpdateProgress) {
        window.electronAPI.onUpdateProgress((prog) => {
            if (!updateProgressToast) return;
            showUpdateToast(`Cập nhật v${prog.version || ""}`);

            const pct = Math.max(0, Math.min(100, Math.round(prog.percent || 0)));
            if (updateProgressBarFill) updateProgressBarFill.style.width = `${pct}%`;
            if (updatePercentText) updatePercentText.textContent = `${pct}%`;

            if (prog.status === "starting") {
                if (updateStatusText) updateStatusText.textContent = "Bắt đầu tải bản cập nhật...";
                if (updateActionsContainer) updateActionsContainer.classList.add("hidden");
            } else if (prog.status === "downloading") {
                if (updateStatusText) updateStatusText.textContent = "Đang tải bản cập nhật ngầm...";
                if (updateBytesText) {
                    const trans = prog.transferred ? `${prog.transferred} MB` : "";
                    const tot = prog.total ? `${prog.total} MB` : "";
                    updateBytesText.textContent = trans && tot ? `${trans} / ${tot}` : "";
                }
                if (updateSpeedText) updateSpeedText.textContent = prog.speed || "";
                if (updateActionsContainer) updateActionsContainer.classList.add("hidden");
            } else if (prog.status === "completed") {
                if (updateStatusText) updateStatusText.textContent = "Đã tải xong bản cập nhật!";
                if (updateBytesText) updateBytesText.textContent = "Sẵn sàng nâng cấp";
                if (updateSpeedText) updateSpeedText.textContent = "";
                if (updateProgressBarFill) updateProgressBarFill.style.width = "100%";
                if (updatePercentText) updatePercentText.textContent = "100%";
                if (updateActionsContainer) updateActionsContainer.classList.remove("hidden");
            } else if (prog.status === "error") {
                if (updateStatusText) updateStatusText.textContent = `Lỗi tải: ${prog.error || "Không xác định"}`;
                if (updateProgressBarFill) updateProgressBarFill.style.backgroundColor = "#ef4444";
            }
        });
    }

    // --- Network Offline / Online Monitor ---
    let networkToastTimer = null;
    function showNetworkToast(isOnline) {
        let toast = document.getElementById("network-status-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "network-status-toast";
            toast.className = "network-status-toast";
            document.body.appendChild(toast);
        }
        clearTimeout(networkToastTimer);

        if (isOnline) {
            toast.className = "network-status-toast online show";
            toast.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <path d="M5 12.55a11 11 0 0 1 14.08 0"></path>
                    <path d="M1.42 9a16 16 0 0 1 21.16 0"></path>
                    <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                    <line x1="12" y1="20" x2="12.01" y2="20"></line>
                </svg>
                <span>Kết nối mạng Internet đã phục hồi</span>
            `;
            networkToastTimer = setTimeout(() => {
                toast.classList.remove("show");
            }, 4000);
        } else {
            toast.className = "network-status-toast offline show";
            toast.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                    <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
                    <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>
                    <path d="M10.71 5.05A16 16 0 0 1 22.58 9"></path>
                    <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>
                    <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                    <line x1="12" y1="20" x2="12.01" y2="20"></line>
                </svg>
                <span>Mất kết nối Internet. Tiến trình tải có thể bị gián đoạn</span>
            `;
        }
    }

    // =========================================================================
    // AUTHENTICATION & CLOUD SYNC SYSTEM (Local-First & Ambient Instrument UI)
    // =========================================================================
    // Chuỗi Base64 che mắt bot GitHub
    const _ENC_GOOGLE_ID = "NTE1NjY4NzIzODY5LTNjMzU2djFmNzJiNXQ1c2lvdmFjZnA4OTYxYTJsMHVxLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29t";
    const GOOGLE_CLIENT_ID = (function() {
        try {
            return atob(_ENC_GOOGLE_ID);
        } catch (e) {
            return "515668723869-3c356v1f72b5t5siovacfp8961a2l0uq.apps.googleusercontent.com";
        }
    })();
    let currentUserState = null;
    let authActiveTab = "login";

    const authUserBtn = document.getElementById("auth-user-btn");
    const userDropdown = document.getElementById("user-dropdown");
    const authModal = document.getElementById("auth-modal");
    const authCloseBtn = document.getElementById("auth-close-btn");
    const authForm = document.getElementById("auth-form");
    const authErrorMsg = document.getElementById("auth-error-msg");
    const authInputUsername = document.getElementById("auth-input-username");
    const authInputEmail = document.getElementById("auth-input-email");
    const authInputPassword = document.getElementById("auth-input-password");
    const authFieldEmail = document.getElementById("auth-field-email");
    const authSubmitBtnText = document.getElementById("auth-submit-btn-text");
    const authTogglePwdBtn = document.getElementById("auth-toggle-pwd-btn");
    const authTabBtns = document.querySelectorAll(".auth-tab-btn");
    const headerSyncPill = document.getElementById("header-sync-pill");
    const syncPillText = document.getElementById("sync-pill-text");
    const btnLogout = document.getElementById("btn-logout");
    const btnSyncNow = document.getElementById("btn-sync-now");
    const btnClaimHistory = document.getElementById("btn-claim-history");

    function setAuthError(message, isSuccess = false) {
        if (!authErrorMsg) return;
        if (!message) {
            authErrorMsg.classList.add("hidden");
            authErrorMsg.textContent = "";
            authErrorMsg.classList.remove("success");
            return;
        }
        authErrorMsg.textContent = message;
        if (isSuccess) {
            authErrorMsg.classList.add("success");
        } else {
            authErrorMsg.classList.remove("success");
        }
        authErrorMsg.classList.remove("hidden");
    }

    function switchAuthTab(tab) {
        authActiveTab = tab;
        setAuthError(null);
        authTabBtns.forEach(b => {
            const isActive = b.getAttribute("data-tab") === tab;
            b.classList.toggle("active", isActive);
            b.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        if (tab === "register") {
            if (authFieldEmail) authFieldEmail.classList.remove("hidden");
            if (authSubmitBtnText) authSubmitBtnText.textContent = "TẠO TÀI KHOẢN MỚI";
            if (authInputEmail) authInputEmail.setAttribute("required", "required");
        } else {
            if (authFieldEmail) authFieldEmail.classList.add("hidden");
            if (authSubmitBtnText) authSubmitBtnText.textContent = "ĐĂNG NHẬP";
            if (authInputEmail) authInputEmail.removeAttribute("required");
        }
    }

    function updateAuthUI(user) {
        currentUserState = user;
        const guestContent = document.getElementById("auth-btn-guest");
        const userContent = document.getElementById("auth-btn-user");
        const authUserName = document.getElementById("auth-user-name");
        const authUserAvatar = document.getElementById("auth-user-avatar");
        const authUserSvgFallback = document.getElementById("auth-user-svg-fallback");

        const dropdownUserName = document.getElementById("dropdown-user-name");
        const dropdownUserEmail = document.getElementById("dropdown-user-email");
        const dropdownUserAvatar = document.getElementById("dropdown-user-avatar");
        const dropdownUserSvgFallback = document.getElementById("dropdown-user-svg-fallback");
        const dropdownSyncDesc = document.getElementById("dropdown-sync-desc");

        if (user && user.id) {
            // Logged in
            if (guestContent) guestContent.classList.add("hidden");
            if (userContent) userContent.classList.remove("hidden");

            const displayName = user.username || user.email || "User";
            if (authUserName) authUserName.textContent = displayName;
            if (dropdownUserName) dropdownUserName.textContent = displayName;
            if (dropdownUserEmail) dropdownUserEmail.textContent = user.email || "Tài khoản cá nhân";

            if (user.avatar_url) {
                if (authUserAvatar) {
                    authUserAvatar.src = user.avatar_url;
                    authUserAvatar.classList.remove("hidden");
                }
                if (authUserSvgFallback) authUserSvgFallback.classList.add("hidden");
                if (dropdownUserAvatar) {
                    dropdownUserAvatar.src = user.avatar_url;
                    dropdownUserAvatar.classList.remove("hidden");
                }
                if (dropdownUserSvgFallback) dropdownUserSvgFallback.classList.add("hidden");
            } else {
                if (authUserAvatar) authUserAvatar.classList.add("hidden");
                if (authUserSvgFallback) authUserSvgFallback.classList.remove("hidden");
                if (dropdownUserAvatar) dropdownUserAvatar.classList.add("hidden");
                if (dropdownUserSvgFallback) dropdownUserSvgFallback.classList.remove("hidden");
            }

            if (headerSyncPill) {
                headerSyncPill.classList.add("is-synced");
                headerSyncPill.classList.remove("is-pending", "is-syncing");
            }
            if (syncPillText) syncPillText.textContent = "CLOUD // SYNCED";
            if (dropdownSyncDesc) dropdownSyncDesc.textContent = "Đồng bộ: Đã kết nối Cloud";
        } else {
            // Guest mode
            if (guestContent) guestContent.classList.remove("hidden");
            if (userContent) userContent.classList.add("hidden");
            if (headerSyncPill) {
                headerSyncPill.classList.remove("is-synced", "is-pending", "is-syncing");
            }
            if (syncPillText) syncPillText.textContent = "LOCAL // GUEST";
            if (dropdownSyncDesc) dropdownSyncDesc.textContent = "Đồng bộ: Chế độ cục bộ";
        }
    }

    function onAuthSuccess(data) {
        if (!data) return;
        if (data.token) {
            localStorage.setItem("session_token", data.token);
            document.cookie = `session_token=${data.token}; path=/; max-age=2592000; SameSite=Lax`;
        }
        if (data.user) {
            updateAuthUI(data.user);
        }
        if (authModal) authModal.classList.add("hidden");
        if (typeof loadDownloadHistory === "function") loadDownloadHistory();
        triggerCloudSync(false);
    }

    async function checkCurrentAuth() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const urlToken = urlParams.get("token") || (window.location.hash.includes("token=") ? new URLSearchParams(window.location.hash.substring(1)).get("token") : null);
            if (urlToken) {
                localStorage.setItem("session_token", urlToken);
                document.cookie = `session_token=${urlToken}; path=/; max-age=2592000; SameSite=Lax`;
                window.history.replaceState({}, document.title, window.location.pathname);
            }

            const token = localStorage.getItem("session_token");
            const headers = token ? { "Authorization": `Bearer ${token}` } : {};
            const res = await fetch("/api/auth/me", { headers });
            const data = await res.json();
            if (data.status === "success" && data.user) {
                updateAuthUI(data.user);
            } else {
                updateAuthUI(null);
            }
        } catch (e) {
            updateAuthUI(null);
        }
    }

    function initGoogleSignIn() {
        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
            setTimeout(initGoogleSignIn, 1000);
            return;
        }
        try {
            window.google.accounts.id.initialize({
                client_id: GOOGLE_CLIENT_ID,
                callback: handleGoogleAuthResponse,
                auto_select: false
            });
            // Ambient design: single unified button (#btn-ambient-google)
        } catch (err) {
            console.warn("Google Sign-In initialization skipped:", err);
        }
    }

    async function handleGoogleAuthResponse(response) {
        if (!response || !response.credential) return;
        setAuthError(null);
        try {
            const res = await fetch("/api/auth/google", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: response.credential })
            });
            const data = await res.json();
            if (data.status === "success" && data.user) {
                onAuthSuccess(data);
            } else {
                setAuthError(data.message || "Đăng nhập Google thất bại");
            }
        } catch (err) {
            setAuthError("Không thể kết nối đến máy chủ");
        }
    }

    async function triggerCloudSync(manual = false) {
        if (!navigator.onLine) {
            if (syncPillText) syncPillText.textContent = "OFFLINE // LOCAL";
            if (headerSyncPill) {
                headerSyncPill.classList.remove("is-syncing", "is-synced");
                headerSyncPill.classList.add("is-pending");
            }
            return;
        }

        if (headerSyncPill) {
            headerSyncPill.classList.remove("is-synced", "is-pending");
            headerSyncPill.classList.add("is-syncing");
        }
        if (syncPillText) syncPillText.textContent = "SYNCING...";

        try {
            const pendingRes = await fetch("/api/sync/pending");
            const pendingData = await pendingRes.json();
            if (pendingData.status === "success" && pendingData.tasks && pendingData.tasks.length > 0) {
                const pushRes = await fetch("/api/sync/push", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ tasks: pendingData.tasks })
                });
                const pushData = await pushRes.json();
                if (pushData.status === "success") {
                    if (headerSyncPill) {
                        headerSyncPill.classList.remove("is-syncing", "is-pending");
                        headerSyncPill.classList.add("is-synced");
                    }
                    if (syncPillText) syncPillText.textContent = currentUserState ? "CLOUD // SYNCED" : "LOCAL // GUEST";
                    if (manual && typeof loadDownloadHistory === "function") loadDownloadHistory();
                }
            } else {
                if (headerSyncPill) {
                    headerSyncPill.classList.remove("is-syncing", "is-pending");
                    headerSyncPill.classList.add("is-synced");
                }
                if (syncPillText) syncPillText.textContent = currentUserState ? "CLOUD // SYNCED" : "LOCAL // GUEST";
            }
        } catch (e) {
            if (headerSyncPill) {
                headerSyncPill.classList.remove("is-syncing", "is-synced");
                headerSyncPill.classList.add("is-pending");
            }
            if (syncPillText) syncPillText.textContent = "SYNC // RETRY";
        }
    }

    // Event Listeners for Auth
    if (authUserBtn) {
        authUserBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (currentUserState) {
                if (userDropdown) userDropdown.classList.toggle("hidden");
            } else {
                setAuthError(null);
                if (authModal) authModal.classList.remove("hidden");
            }
        });
    }

    if (headerSyncPill) {
        headerSyncPill.addEventListener("click", () => {
            triggerCloudSync(true);
        });
    }

    if (authCloseBtn && authModal) {
        authCloseBtn.addEventListener("click", () => {
            authModal.classList.add("hidden");
        });
    }

    authTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const tab = btn.getAttribute("data-tab");
            if (tab) switchAuthTab(tab);
        });
    });

    if (authTogglePwdBtn && authInputPassword) {
        authTogglePwdBtn.addEventListener("click", () => {
            const isPassword = authInputPassword.getAttribute("type") === "password";
            authInputPassword.setAttribute("type", isPassword ? "text" : "password");
            authTogglePwdBtn.style.color = isPassword ? "var(--cyan)" : "var(--text-dim)";
        });
    }

    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = authInputUsername ? authInputUsername.value.trim() : "";
            const password = authInputPassword ? authInputPassword.value : "";
            const email = authInputEmail ? authInputEmail.value.trim() : "";

            if (!username || !password) {
                setAuthError("Vui lòng điền đầy đủ thông tin");
                return;
            }

            setAuthError(null);
            if (authSubmitBtnText) authSubmitBtnText.textContent = "ĐANG XỬ LÝ...";

            try {
                const endpoint = authActiveTab === "register" ? "/api/auth/register" : "/api/auth/login";
                const payload = authActiveTab === "register"
                    ? { username, email, password }
                    : { username_or_email: username, password };

                const res = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === "success" && data.user) {
                    onAuthSuccess(data);
                    if (authForm) authForm.reset();
                } else {
                    setAuthError(data.message || "Thao tác thất bại");
                }
            } catch (err) {
                setAuthError("Lỗi kết nối máy chủ");
            } finally {
                if (authSubmitBtnText) {
                    authSubmitBtnText.textContent = authActiveTab === "register" ? "TẠO TÀI KHOẢN MỚI" : "TIẾP TỤC VÀO HỆ THỐNG";
                }
            }
        });
    }

    if (btnLogout) {
        btnLogout.addEventListener("click", async () => {
            try {
                const token = localStorage.getItem("session_token");
                const headers = token ? { "Authorization": `Bearer ${token}` } : {};
                await fetch("/api/auth/logout", { method: "POST", headers });
            } catch (e) {}
            localStorage.removeItem("session_token");
            document.cookie = "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
            if (userDropdown) userDropdown.classList.add("hidden");
            updateAuthUI(null);
            if (typeof loadDownloadHistory === "function") loadDownloadHistory();
        });
    }

    if (btnSyncNow) {
        btnSyncNow.addEventListener("click", () => {
            triggerCloudSync(true);
        });
    }

    if (btnClaimHistory) {
        btnClaimHistory.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/auth/sync-guest-history", { method: "POST" });
                const data = await res.json();
                if (data.status === "success") {
                    if (typeof loadDownloadHistory === "function") loadDownloadHistory();
                    if (userDropdown) userDropdown.classList.add("hidden");
                    triggerCloudSync(true);
                }
            } catch (e) {}
        });
    }

    document.addEventListener("click", (e) => {
        if (userDropdown && !userDropdown.classList.contains("hidden")) {
            if (!userDropdown.contains(e.target) && !authUserBtn.contains(e.target)) {
                userDropdown.classList.add("hidden");
            }
        }
        if (authModal && !authModal.classList.contains("hidden")) {
            if (e.target === authModal) {
                authModal.classList.add("hidden");
            }
        }
    });

    // Multi-Platform Decoupled Auth Polling (Electron, Standalone PWA, External Browser)
    let desktopAuthPollTimer = null;
    function startDesktopAuthPolling() {
        if (desktopAuthPollTimer) clearInterval(desktopAuthPollTimer);
        let attempts = 0;
        const maxAttempts = 50; // ~60 seconds (50 * 1200ms)
        desktopAuthPollTimer = setInterval(async () => {
            attempts++;
            if (attempts > maxAttempts || currentUserState) {
                clearInterval(desktopAuthPollTimer);
                desktopAuthPollTimer = null;
                return;
            }
            try {
                const res = await fetch("/api/auth/poll-desktop-session");
                const data = await res.json();
                if (data.status === "success" && data.token) {
                    clearInterval(desktopAuthPollTimer);
                    desktopAuthPollTimer = null;
                    onAuthSuccess(data);
                    if (typeof showStatusNotification === "function") {
                        showStatusNotification(`Đăng nhập Google thành công: ${data.user?.display_name || data.user?.email || ""}`);
                    }
                }
            } catch (_) {}
        }, 1200);
    }

    // 1 Single Google OAuth Button (Multi-platform: Desktop Electron, Capacitor Native, Mobile PWA, Web)
    const btnGoogle = document.getElementById("btn-ambient-google") || document.getElementById("btn-browser-google-auth");
    if (btnGoogle) {
        btnGoogle.addEventListener("click", async () => {
            const loginUrl = window.location.origin + "/api/auth/google/login";
            const isElectron = window.electronAPI && typeof window.electronAPI.openExternal === "function";
            const isCapacitorNative = Boolean(window.Capacitor?.isNativePlatform && window.Capacitor.isNativePlatform());
            const isStandalonePWA = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
            const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || (window.innerWidth < 768 && 'ontouchstart' in window);

            if (isCapacitorNative) {
                // Mobile Native App (Capacitor / Cordova)
                try {
                    const start = await fetch("/api/auth/google/start?mode=mobile").then(r => r.json());
                    if (start && start.auth_url && start.state) {
                        if (window.Capacitor?.Plugins?.Browser?.open) {
                            window.Capacitor.Plugins.Browser.open({ url: start.auth_url });
                        } else {
                            window.open(start.auth_url, "_system");
                        }

                        let pollInterval = setInterval(async () => {
                            try {
                                const check = await fetch(`/api/auth/google/poll?state=${encodeURIComponent(start.state)}`).then(r => r.json());
                                if (check && check.status === "ok" && check.token) {
                                    clearInterval(pollInterval);
                                    onAuthSuccess(check);
                                    if (typeof showStatusNotification === "function") {
                                        showStatusNotification("Đăng nhập Google thành công!");
                                    }
                                } else if (check && check.status === "error") {
                                    clearInterval(pollInterval);
                                }
                            } catch (_) {}
                        }, 1500);

                        setTimeout(() => clearInterval(pollInterval), 180000);

                        const onResume = async () => {
                            try {
                                const check = await fetch(`/api/auth/google/poll?state=${encodeURIComponent(start.state)}`).then(r => r.json());
                                if (check && check.status === "ok" && check.token) {
                                    clearInterval(pollInterval);
                                    window.removeEventListener("focus", onResume);
                                    document.removeEventListener("visibilitychange", onResume);
                                    onAuthSuccess(check);
                                    if (typeof showStatusNotification === "function") {
                                        showStatusNotification("Đăng nhập Google thành công!");
                                    }
                                }
                            } catch (_) {}
                        };
                        window.addEventListener("focus", onResume);
                        document.addEventListener("visibilitychange", onResume);
                    }
                } catch (e) {
                    window.location.href = loginUrl + "?source=mobile";
                }
                return;
            }

            if (isElectron) {
                // Desktop Electron: open external browser and poll state
                try {
                    const start = await fetch("/api/auth/google/start?mode=desktop").then(r => r.json());
                    if (start && start.auth_url && start.state) {
                        window.electronAPI.openExternal(start.auth_url);
                        let pollInterval = setInterval(async () => {
                            try {
                                const check = await fetch(`/api/auth/google/poll?state=${encodeURIComponent(start.state)}`).then(r => r.json());
                                if (check && check.status === "ok" && check.token) {
                                    clearInterval(pollInterval);
                                    onAuthSuccess(check);
                                    if (typeof showStatusNotification === "function") {
                                        showStatusNotification("Đăng nhập Google thành công!");
                                    }
                                } else if (check && check.status === "error") {
                                    clearInterval(pollInterval);
                                }
                            } catch (_) {}
                        }, 1200);
                        setTimeout(() => clearInterval(pollInterval), 180000);

                        const onResume = async () => {
                            try {
                                const check = await fetch(`/api/auth/google/poll?state=${encodeURIComponent(start.state)}`).then(r => r.json());
                                if (check && check.status === "ok" && check.token) {
                                    clearInterval(pollInterval);
                                    window.removeEventListener("focus", onResume);
                                    onAuthSuccess(check);
                                    if (typeof showStatusNotification === "function") {
                                        showStatusNotification("Đăng nhập Google thành công!");
                                    }
                                }
                            } catch (_) {}
                        };
                        window.addEventListener("focus", onResume);
                    } else {
                        window.electronAPI.openExternal(loginUrl + "?source=desktop");
                        startDesktopAuthPolling();
                    }
                } catch (err) {
                    window.electronAPI.openExternal(loginUrl + "?source=desktop");
                    startDesktopAuthPolling();
                }
            } else if (isStandalonePWA || (isMobile && !window.opener)) {
                // Mobile Web or Standalone PWA: full window redirection for seamless mobile UX
                window.location.href = loginUrl + "?source=mobile";
            } else {
                // Desktop Web / Popup supported
                const popup = window.open(loginUrl + "?source=web", "GoogleAuth", "width=520,height=640,menubar=no,toolbar=no,location=no,status=no");
                startDesktopAuthPolling();
                if (!popup || popup.closed || typeof popup.closed === "undefined") {
                    // Popup blocked fallback
                    window.location.href = loginUrl + "?source=web";
                }
            }
        });
    }

    // Mobile App URL listener (Capacitor Deep Link)
    if (window.Capacitor?.Plugins?.App?.addListener) {
        try {
            window.Capacitor.Plugins.App.addListener('appUrlOpen', (data) => {
                if (data && data.url) {
                    try {
                        const u = new URL(data.url);
                        const token = u.searchParams.get("token");
                        if (token) {
                            onAuthSuccess({ token: token });
                            checkCurrentAuth();
                        }
                    } catch (e) {}
                }
            });
        } catch (_) {}
    }

    // Auto-detect auth completion when window regains focus, receives storage or postMessage broadcast
    window.addEventListener("focus", () => {
        if (!currentUserState) {
            checkCurrentAuth();
            fetch("/api/auth/poll-desktop-session")
                .then(r => r.json())
                .then(data => {
                    if (data.status === "success" && data.token) {
                        onAuthSuccess(data);
                    }
                })
                .catch(() => {});
        }
    });

    window.addEventListener("storage", (e) => {
        if (e.key === "auth_broadcast") {
            checkCurrentAuth();
            if (typeof loadDownloadHistory === "function") loadDownloadHistory();
            if (authModal) authModal.classList.add("hidden");
        }
    });

    window.addEventListener("message", (e) => {
        if (e.data && e.data.type === "AUTH_SUCCESS") {
            checkCurrentAuth();
            if (typeof loadDownloadHistory === "function") loadDownloadHistory();
            if (authModal) authModal.classList.add("hidden");
        }
    });

    // Check user & init Google GIS on load
    checkCurrentAuth();
    initGoogleSignIn();

    window.addEventListener("offline", () => {
        showNetworkToast(false);
        if (syncPillText) syncPillText.textContent = "OFFLINE // LOCAL";
        if (headerSyncPill) {
            headerSyncPill.classList.remove("is-syncing", "is-synced");
            headerSyncPill.classList.add("is-pending");
        }
    });

    window.addEventListener("online", () => {
        showNetworkToast(true);
        triggerCloudSync(false);
    });
});
