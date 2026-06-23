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
        clearTempCacheBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm("Are you sure you want to delete all downloaded temporary files and cache? This won't affect active downloads.")) {
                return;
            }
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
        });
    }

    const resetUiBtn = document.getElementById("btn-reset-ui-settings");
    if (resetUiBtn) {
        resetUiBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const legacyResetBtn = document.getElementById("customizer-reset-btn");
            if (legacyResetBtn) {
                legacyResetBtn.click();
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
    const customizerBlur = document.getElementById("customizer-blur");
    const customizerBlurVal = document.getElementById("customizer-blur-val");

    const customizerGridEnable = document.getElementById("customizer-grid-enable");
    const customizerRipplesEnable = document.getElementById("customizer-ripples-enable");
    const customizerSparklesEnable = document.getElementById("customizer-sparkles-enable");

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
    if (customizerSparklesEnable) {
        customizerSparklesEnable.addEventListener("change", (e) => updateCanvasOption("sparklesEnabled", e.target.checked));
    }

    if (customizerResetBtn) {
        customizerResetBtn.addEventListener("click", () => {
            applyAccent("default");
            applyRadius("rounded");
            applyBlur(24);
            applyFontSize("medium");
            applyFontFamily("outfit");
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
            if (customizerSparklesEnable) {
                customizerSparklesEnable.checked = true;
                updateCanvasOption("sparklesEnabled", true);
            }
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

    const savedSparkles = localStorage.getItem("customizer-sparklesEnabled") !== null ? localStorage.getItem("customizer-sparklesEnabled") === "true" : true;
    if (customizerSparklesEnable) {
        customizerSparklesEnable.checked = savedSparkles;
        window.canvasSettings.sparklesEnabled = savedSparkles;
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

    const downloadProgress = document.getElementById("download-progress");
    const progressPercent = document.getElementById("progress-percent");
    const progressBarFill = document.getElementById("progress-fill");
    const downloadStatusTitle = document.getElementById("download-status-title");
    const downloadStatusMessage = document.getElementById("download-status-message");
    const downloadFormatLabel = document.getElementById("download-format-label");

    // Preview Modal DOM Elements
    const previewModal = document.getElementById("preview-modal");
    const previewModalCloseBtn = document.getElementById("preview-modal-close-btn");
    const modalFullscreenBtn = document.getElementById("modal-fullscreen-btn");
    const previewShortcutsBtn = document.getElementById("preview-shortcuts-btn");
    const previewShortcutsOverlay = document.getElementById("preview-shortcuts-overlay");
    const shortcutsOverlayCloseBtn = document.getElementById("shortcuts-overlay-close-btn");
    let closePreviewModal = () => {};

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
            previewLoaderText.textContent = text;
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

    function getProxiedImageUrl(url) {
        if (!url) return "";
        if (url.startsWith("/")) return url;
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
    let pollingInterval = null;
    let activeDownloadId = null;
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

    function seekAdaptiveVideo(targetTime) {
        if (!previewIsAdaptive) return;
        
        showPreviewLoader("Seeking stream...");
        previewCurrentTimeOffset = targetTime;
        
        // Stop current playback
        previewVideoPlayer.pause();
        
        // Re-construct the proxy stream URL with start_time = targetTime
        const proxyStreamUrl = `/api/proxy/stream_adaptive?video_url=${encodeURIComponent(previewAdaptiveVideoUrl)}&audio_url=${encodeURIComponent(previewAdaptiveAudioUrl)}&container=${encodeURIComponent(previewAdaptiveContainer)}&start_time=${targetTime}`;
        
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
    // Helper to stop all preview playbacks and destroy Hls instances
    function stopAllPreviewPlaybacks() {
        if (previewActivePollInterval) {
            previewActivePollInterval.close();
            previewActivePollInterval = null;
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
            } catch (e) {}
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
            } catch (e) {}
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

    // Dynamic track fill for ranges
    function updateSliderBackground(slider) {
        if (!slider) return;
        const val = parseFloat(slider.value) || 0;
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 100;
        const pct = ((val - min) / (max - min)) * 100;
        slider.style.background = `linear-gradient(to right, var(--cyan) 0%, var(--cyan) ${pct}%, var(--slider-track) ${pct}%, var(--slider-track) 100%)`;
    }

    // --- AUDIO VISUALIZER LOGIC (WEB AUDIO API) ---
    let audioCtx = null;
    let analyser = null;
    let sourceNode = null;
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
            analyser.fftSize = 64; // Gives 32 frequency bins, perfect for our 20 bars

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

        const bars = document.querySelectorAll(".waveform-animation .bar");
        if (bars.length === 0) return;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        // Target the outer visible box for border/glow effects (card is now transparent)
        const contentArea = document.querySelector(".preview-content-area");

        const draw = () => {
            if (!previewAudioPlayer || previewAudioPlayer.paused) {
                // Smoothly decay bars and backdrop back to rest height/state
                let stillDecaying = false;
                bars.forEach(bar => {
                    const currentHeight = parseFloat(bar.style.height) || 10;
                    if (currentHeight > 10) {
                        bar.style.height = `${Math.max(10, currentHeight * 0.85 - 0.5)}px`;
                        stillDecaying = true;
                    } else {
                        bar.style.height = "10px";
                    }
                });

                const backdrop = document.querySelector(".visualizer-glow-backdrop");
                if (backdrop) {
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

                const vinylLabel = document.querySelector(".vinyl-label");
                if (vinylLabel) {
                    const currentTransform = vinylLabel.style.transform || "";
                    const scaleMatch = currentTransform.match(/scale\(([^)]+)\)/);
                    let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
                    if (currentScale > 1.0) {
                        currentScale = Math.max(1.0, currentScale * 0.9);
                        vinylLabel.style.transform = `scale(${currentScale})`;
                        stillDecaying = true;
                    }
                }

                // Reset the content-area glow back to CSS-driven state
                if (contentArea) {
                    contentArea.style.boxShadow = "";
                    contentArea.style.borderColor = "";
                }

                const vinylRecord = document.querySelector(".vinyl-record");
                if (vinylRecord) {
                    vinylRecord.style.boxShadow = "";
                }

                if (stillDecaying) {
                    visualizerAnimationId = requestAnimationFrame(draw);
                } else {
                    visualizerAnimationId = null;
                }
                return;
            }

            visualizerAnimationId = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            let sum = 0;
            const barCount = bars.length;
            for (let i = 0; i < barCount; i++) {
                // Focus on lower-mid frequencies (mostly 0% to 75% of the spectrum)
                const percentIdx = i / barCount;
                const dataIdx = Math.floor(percentIdx * bufferLength * 0.75);
                const value = dataArray[dataIdx] || 0;
                sum += value;

                // Map value (0-255) to height (10px - 55px)
                const height = 10 + (value / 255) * 45;
                bars[i].style.height = `${height}px`;
            }

            // Pulse the background glow backdrop and vinyl record center label in sync with average audio energy
            const average = sum / barCount;
            const backdrop = document.querySelector(".visualizer-glow-backdrop");
            if (backdrop) {
                const scale = 1.0 + (average / 255) * 0.35;
                const opacity = 0.15 + (average / 255) * 0.65;
                backdrop.style.transform = `translate(-50%, -50%) scale(${scale})`;
                backdrop.style.opacity = opacity;
            }
            
            const vinylLabel = document.querySelector(".vinyl-label");
            if (vinylLabel) {
                const labelScale = 1.0 + (average / 255) * 0.18;
                vinylLabel.style.transform = `scale(${labelScale})`;
            }

            // Dynamically pulse the outer box border & glow in sync with audio energy
            if (contentArea) {
                const innerBlur = 10 + (average / 255) * 25; // 10px → 35px
                const outerBlur = 40 + (average / 255) * 60; // 40px → 100px
                const innerOpacity = 0.15 + (average / 255) * 0.5;  // 0.15 → 0.65
                const outerOpacity = 0.08 + (average / 255) * 0.3;  // 0.08 → 0.38
                const borderOpacity = 0.1 + (average / 255) * 0.5;  // 0.1 → 0.6

                contentArea.style.boxShadow = `0 0 ${innerBlur}px rgba(var(--cyan-rgb), ${innerOpacity}), 0 0 ${outerBlur}px rgba(var(--cyan-rgb), ${outerOpacity})`;
                contentArea.style.borderColor = `rgba(var(--cyan-rgb), ${borderOpacity})`;
            }

            const vinylRecord = document.querySelector(".vinyl-record");
            if (vinylRecord) {
                const innerBlur = 8 + (average / 255) * 20; // 8px to 28px blur
                const outerBlur = 30 + (average / 255) * 50; // 30px to 80px blur
                
                const innerOpacity = 0.3 + (average / 255) * 0.5; // 0.3 to 0.8 opacity
                const outerOpacity = 0.15 + (average / 255) * 0.45; // 0.15 to 0.6 opacity
                
                vinylRecord.style.boxShadow = `
                    0 10px 30px rgba(0, 0, 0, 0.7), 
                    0 0 ${innerBlur}px rgba(var(--cyan-rgb), ${innerOpacity}), 
                    0 0 ${outerBlur}px rgba(var(--cyan-rgb), ${outerOpacity}), 
                    inset 0 0 1px rgba(255, 255, 255, 0.15)
                `;
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
        audioSeekSlider.addEventListener("input", function() {
            isDraggingAudioSlider = true;
            updateSliderBackground(this);
        });
        audioSeekSlider.addEventListener("change", function() {
            if (previewAudioPlayer.duration) {
                previewAudioPlayer.currentTime = (parseFloat(this.value) / 100) * previewAudioPlayer.duration;
            }
            setTimeout(() => {
                isDraggingAudioSlider = false;
            }, 300);
        });
    }

    if (audioVolumeSlider && previewAudioPlayer) {
        audioVolumeSlider.addEventListener("input", function() {
            previewAudioPlayer.volume = parseFloat(this.value);
            updateSliderBackground(this);
            // Sync mute icon if needed
            if (audioMuteBtn) {
                const volIcon = audioMuteBtn.querySelector(".volume-icon");
                const muteIcon = audioMuteBtn.querySelector(".mute-icon");
                if (previewAudioPlayer.volume === 0) {
                    if (volIcon) volIcon.classList.add("hidden");
                    if (muteIcon) muteIcon.classList.remove("hidden");
                } else {
                    if (volIcon) volIcon.classList.remove("hidden");
                    if (muteIcon) muteIcon.classList.add("hidden");
                    previewAudioPlayer.muted = false;
                }
            }
        });
    }

    if (audioMuteBtn && previewAudioPlayer && audioVolumeSlider) {
        let prevVolume = 1.0;
        audioMuteBtn.addEventListener("click", () => {
            previewAudioPlayer.muted = !previewAudioPlayer.muted;
            const volIcon = audioMuteBtn.querySelector(".volume-icon");
            const muteIcon = audioMuteBtn.querySelector(".mute-icon");

            if (previewAudioPlayer.muted) {
                if (volIcon) volIcon.classList.add("hidden");
                if (muteIcon) muteIcon.classList.remove("hidden");
                prevVolume = parseFloat(audioVolumeSlider.value) || 1.0;
                audioVolumeSlider.value = 0;
            } else {
                if (volIcon) volIcon.classList.remove("hidden");
                if (muteIcon) muteIcon.classList.add("hidden");
                audioVolumeSlider.value = prevVolume;
                previewAudioPlayer.volume = prevVolume;
            }
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
        audioSubSelect.addEventListener("change", function() {
            loadAudioSubtitle(this.value);
        });
    }

    if (audioSubUploadBtn && audioSubFile) {
        audioSubUploadBtn.addEventListener("click", () => {
            audioSubFile.click();
        });
        audioSubFile.addEventListener("change", function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(evt) {
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
        audioSpeedSlider.addEventListener("input", function() {
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
        slider.addEventListener("input", function() {
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
        
        // Auto-hide controls, header, and cursor if fullscreen is active (Stage 1 or 2)
        if (videoFullscreenMode > 0) {
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
            if (videoFullscreenMode > 0) {
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
            const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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
            const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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
        });

        previewVideoPlayer.addEventListener("durationchange", () => {
            const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
            if (videoTimeTotal && totalDuration > 0) {
                videoTimeTotal.textContent = formatTime(totalDuration);
            }
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

    // Clicking on video itself toggles play/pause
    if (previewVideoPlayer) {
        previewVideoPlayer.addEventListener("click", () => {
            if (previewVideoPlayer.paused) {
                previewVideoPlayer.play().catch(e => console.log("Play failed: ", e));
            } else {
                previewVideoPlayer.pause();
            }
        });
    }

    if (videoSeekSlider && previewVideoPlayer) {
        const setVideoDragging = () => { isDraggingVideoSlider = true; };
        videoSeekSlider.addEventListener("mousedown", setVideoDragging);
        videoSeekSlider.addEventListener("touchstart", setVideoDragging);
        videoSeekSlider.addEventListener("input", function(e) {
            e.stopPropagation();
            isDraggingVideoSlider = true;
            updateSliderBackground(this);
        });
        videoSeekSlider.addEventListener("change", function(e) {
            e.stopPropagation();
            const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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

    if (videoVolumeSlider && previewVideoPlayer) {
        videoVolumeSlider.addEventListener("input", function(e) {
            e.stopPropagation();
            previewVideoPlayer.volume = parseFloat(this.value);
            updateSliderBackground(this);
            // Sync mute icon if needed
            if (videoMuteBtn) {
                const volIcon = videoMuteBtn.querySelector(".volume-icon");
                const muteIcon = videoMuteBtn.querySelector(".mute-icon");
                if (previewVideoPlayer.volume === 0) {
                    if (volIcon) volIcon.classList.add("hidden");
                    if (muteIcon) muteIcon.classList.remove("hidden");
                } else {
                    if (volIcon) volIcon.classList.remove("hidden");
                    if (muteIcon) muteIcon.classList.add("hidden");
                    previewVideoPlayer.muted = false;
                }
            }
        });
    }

    if (videoMuteBtn && previewVideoPlayer && videoVolumeSlider) {
        let prevVideoVolume = 1.0;
        videoMuteBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            previewVideoPlayer.muted = !previewVideoPlayer.muted;
            const volIcon = videoMuteBtn.querySelector(".volume-icon");
            const muteIcon = videoMuteBtn.querySelector(".mute-icon");

            if (previewVideoPlayer.muted) {
                if (volIcon) volIcon.classList.add("hidden");
                if (muteIcon) muteIcon.classList.remove("hidden");
                prevVideoVolume = parseFloat(videoVolumeSlider.value) || 1.0;
                videoVolumeSlider.value = 0;
            } else {
                if (volIcon) volIcon.classList.remove("hidden");
                if (muteIcon) muteIcon.classList.add("hidden");
                videoVolumeSlider.value = prevVideoVolume;
                previewVideoPlayer.volume = prevVideoVolume;
            }
            updateSliderBackground(videoVolumeSlider);
        });
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
        audioFormatSelect.addEventListener("change", function() {
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
        videoFormatSelect.addEventListener("change", function() {
            const formatId = this.value;
            if (activeMetadata && activeMetadata.video_options) {
                const opt = activeMetadata.video_options.find(o => o.format_id === formatId);
                if (opt) {
                    triggerPreview(null, opt.format_id, opt.ext, opt.label, opt.quality, opt.url, "", "", "video");
                }
            }
        });
    }

    // Close preview modal behavior
    if (previewModal && previewModalCloseBtn) {
        closePreviewModal = () => {
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
            
            // Clear loop points and inputs
            loopStartSecs = null;
            loopEndSecs = null;
            const loopPointAInput = document.getElementById("loop-point-a");
            const loopPointBInput = document.getElementById("loop-point-b");
            if (loopPointAInput) loopPointAInput.value = "";
            if (loopPointBInput) loopPointBInput.value = "";
            
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

            stopAllPreviewPlaybacks();
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

        previewModal.onclick = (e) => {
            if (e.target === previewModal) {
                closePreviewModal();
            }
        };

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
                        }
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
                        const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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
                        const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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
                        const totalDuration = previewIsAdaptive ? (parseFloat(activeMetadata ? activeMetadata.duration_raw : 0) || 0) : (previewVideoPlayer.duration || 0);
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

    // Confirm Modal Behavior
    function showConfirm(options = {}) {
        if (!confirmModal) return;
        confirmModalTitle.textContent = options.title || "Confirm";
        confirmModalMessage.textContent = options.message || "Are you sure?";
        confirmModalBtnYes.textContent = options.yesText || "Yes";
        confirmModalBtnNo.textContent = options.noText || "No";

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
        slider.addEventListener("input", function() {
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
                (document.getElementById("preview-voiceover-select") && document.getElementById("preview-voiceover-select").value !== "none") ||
                (document.getElementById("preview-cloud-sync") && document.getElementById("preview-cloud-sync").value !== "local")
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
                
                // Capture the current custom audio settings before closing (which resets them)
                const capturedAudioSettings = {
                    audio_eq_bass: eqBassVal,
                    audio_eq_lowmid: eqLowMidVal,
                    audio_eq_highmid: eqHighMidVal,
                    audio_eq_treble: eqTrebleVal,
                    audio_speed: finalSpeedVal,
                    audio_voice_preset: activeVoiceBtn ? activeVoiceBtn.dataset.voice : "normal"
                };

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
                    capturedAudioSettings
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

                if (previewActiveDownloadId) {
                    window.location.href = `/api/download/file/${previewActiveDownloadId}`;
                } else if (previewActiveUrl) {
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
                                <span>${formatHistoryDateTime(item.timestamp)}</span>
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
        videoTitle.textContent = "Analyzing...";
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
        activeMetadata = data;
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
                    triggerPreview(prevBtn, "image_preview", "jpg", cleanLabel, "", img.url);
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

        // Render Video options if present
        if (data.video_options && data.video_options.length > 0) {
            const imageExts = ["jpg", "jpeg", "png", "webp", "gif", "bmp"];
            const htmlExts = ["html", "htm"];
            
            const videos = data.video_options.filter(opt => {
                if (opt.type) return opt.type === "video";
                const ext = (opt.ext || "").toLowerCase();
                return !imageExts.includes(ext) && !htmlExts.includes(ext);
            });
            
            const photos = data.video_options.filter(opt => {
                if (opt.type) return opt.type === "image";
                const ext = (opt.ext || "").toLowerCase();
                return imageExts.includes(ext);
            });
            
            const webpages = data.video_options.filter(opt => {
                if (opt.type) return opt.type === "webpage";
                const ext = (opt.ext || "").toLowerCase();
                return htmlExts.includes(ext);
            });

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
                    const rowEls = [];
                    noGroup.forEach(option => {
                        const row = document.createElement("div");
                        row.className = "format-row video-row";
                        const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                        const drmBadge = option.is_drm ? `<span class="drm-badge" title="Định dạng này được mã hóa bảo vệ bản quyền DRM. Tải xuống có thể bị lỗi."><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>DRM</span>` : '';
                        row.innerHTML = `
                            <div class="format-left">
                                ${videoSvg}
                                <span class="format-name">${option.label}</span>
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

                        const drmBadge = option.is_drm ? `<span class="drm-badge" title="Định dạng này được mã hóa bảo vệ bản quyền DRM. Tải xuống có thể bị lỗi."><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:10px; height:10px; display:inline-block; vertical-align:middle; margin-right:2px;"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>DRM</span>` : '';
                        row.innerHTML = `
                            <div class="format-left">
                                ${videoSvg}
                                <span class="format-name">${displayLabel}</span>
                                ${sizeBadge}
                                ${drmBadge}
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
                    row.className = "format-row webpage-row";

                    const sizeBadge = option.size ? `<span class="format-size">${option.size}</span>` : '';
                    row.innerHTML = `
                        <div class="format-left">
                            <svg class="format-icon" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--warning); width: 18px; height: 18px; margin-right: 8px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
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
                    rowEls.push(row);
                });
                const titleHtml = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <span>Webpage Options</span>
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
                        <span class="format-name">${option.label}</span>
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
                triggerPreview(btn, formatId, ext, label, quality, customUrl, episode, server, type);
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

    // 3. Download Execution via Asynchronous Server Task & Polling
    // 3. Download Execution via Asynchronous Server Task & Polling
    async function triggerDownload(btn, formatId, ext, label, quality, customUrl, episode = "", server = "", forceRaw = false, capturedAudioSettings = null) {
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

        const activeRow = btn ? btn.closest(".format-row") : null;
        if (activeRow) {
            activeRow.classList.add("is-downloading");
        }
        try {
            const requestBody = {
                url: (formatId.startsWith("direct_") || formatId === "image_preview" || formatId === "image_download" || ext === "vtt") ? (customUrl || activeUrl) : activeUrl,
                format_id: formatId,
                ext: ext,
                quality: quality,
                title: videoTitle.textContent,
                thumbnail: videoThumbnail.getAttribute("data-original-url") || videoThumbnail.src,
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

                // Custom Audio Processing Settings
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

        let rawError = errorMessageText || "An error occurred while queuing the download.";
        let friendlyMessage = "Download failed. Please check your connection or view technical details below.";
        const lowerErr = rawError.toLowerCase();

        if (lowerErr.includes("fallback download also failed") || lowerErr.includes("returned non-zero code")) {
            friendlyMessage = "Cannot download from this source. The media might be encrypted or downloading is blocked. Please select another server (e.g. Server #1) or try again later.";
        } else if (lowerErr.includes("429") || lowerErr.includes("too many requests") || lowerErr.includes("rate limit") || lowerErr.includes("rate-limit")) {
            friendlyMessage = "Rate limit exceeded for this IP (Error 429 - Too Many Requests). Please wait a few minutes and try again, or update your Cookie/change network connection.";
        } else if (lowerErr.includes("403") || lowerErr.includes("forbidden") || lowerErr.includes("access denied")) {
            friendlyMessage = "Access denied (Error 403 - Forbidden). The source may require a valid login Cookie or is blocking the server IP.";
        } else if (lowerErr.includes("404") || lowerErr.includes("not found")) {
            friendlyMessage = "Resource not found (Error 404 - Not Found). Please check the URL and verify if the post/video still exists.";
        } else if (lowerErr.includes("sign in to confirm you're not a bot") || lowerErr.includes("confirm you're not a bot") || lowerErr.includes("confirm you are not a bot")) {
            friendlyMessage = "Download blocked due to bot verification requirement (Confirm you are not a bot). Please try again later or update your Cookie in 'Cookie Settings'.";
        } else if (lowerErr.includes("login") || lowerErr.includes("logged-in") || lowerErr.includes("cookie") || lowerErr.includes("private")) {
            friendlyMessage = "This content requires a login or account cookie. Please log in using your browser, export cookies, and update them in 'Cookie Settings'.";
        } else if (lowerErr.includes("unsupported url")) {
            friendlyMessage = "This URL is not supported for direct download. Please check the URL.";
        } else if (lowerErr.includes("connection refused") || lowerErr.includes("timeout") || lowerErr.includes("timed out")) {
            friendlyMessage = "Connection error to the source server. Please check your network connection or try again later.";
        } else if (lowerErr.includes("could not resolve host") || lowerErr.includes("name or service not known")) {
            friendlyMessage = "Cannot connect to the source server (DNS resolution error). Please check your system's network connection.";
        }

        let htmlContent = `<span>${friendlyMessage}</span>`;
        if (errorMessageText) {
            htmlContent += `<details class="error-details">
                <summary class="error-summary">Technical details</summary>
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
    async function triggerPreview(btn, formatId, ext, label, quality, customUrl, episode = "", server = "", type = "") {
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
                    videoOpts.forEach(opt => {
                        const optionEl = document.createElement("option");
                        optionEl.value = opt.format_id;
                        optionEl.textContent = `${opt.label} ${opt.size ? `(${opt.size})` : ""}`;
                        if (opt.format_id === formatId) {
                            optionEl.selected = true;
                        }
                        videoFormatSelect.appendChild(optionEl);
                    });
                } else {
                    videoFormatSelect.style.display = "none";
                }
            }
        }

        // Stop current playbacks
        stopAllPreviewPlaybacks();

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
        if (ext === "jpg" || ext === "png" || ext === "jpeg" || formatId === "image_preview") {
            const finalUrl = formatId === "image_preview"
                ? `/api/download/image?url=${encodeURIComponent(customUrl)}&client_id=${encodeURIComponent(clientId)}`
                : customUrl;

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
        const isHtmlPage = (lowerExt === "html" || lowerExt === "htm" || lowerType === "webpage");
        const isRawTextFile = (lowerExt === "txt" || lowerExt === "xml");
        
        const isSubtitleFile = (lowerExt === "vtt" || lowerExt === "srt" || lowerType === "subtitle");

        // Webpage / HTML / Text / Subtitle Preview Flow
        if (isHtmlPage || isRawTextFile || isSubtitleFile) {
            previewActiveUrl = streamUrl;
            
            if (isHtmlPage && previewWebpageContainer && previewWebpageIframe) {
                previewWebpageContainer.classList.remove("hidden");
                showPreviewLoader("Loading webpage view...");
                
                const proxyUrl = `/api/system/proxy-sub?url=${encodeURIComponent(streamUrl)}&mode=html&client_id=${encodeURIComponent(clientId)}`;
                previewWebpageIframe.src = proxyUrl;
                
                previewWebpageIframe.onload = () => {
                    hidePreviewLoader();
                };
                previewWebpageIframe.onerror = () => {
                    showPreviewLoader("Failed to render webpage preview.", true);
                };
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
        const isYoutube = streamUrl.toLowerCase().includes("youtube.com") || 
                          streamUrl.toLowerCase().includes("youtu.be") || 
                          streamUrl.toLowerCase().includes("googlevideo.com") ||
                          streamUrl.toLowerCase().includes("youtube-nocookie.com");

        const isAdaptiveYoutube = isYoutube && formatId.includes("+");

        // Direct stream preview (stream-on-demand)
        const isDirectStream = (ext !== "vtt") && (
            formatId.startsWith("direct_") ||
            (type === "audio") ||
            (customUrl && customUrl.startsWith("http") && !formatId.includes("+")) ||
            isAdaptiveYoutube
        );

        console.log("[triggerPreview] streamUrl:", streamUrl);
        console.log("[triggerPreview] isYoutube:", isYoutube);
        console.log("[triggerPreview] isDirectStream:", isDirectStream);

        if (isDirectStream) {
            const streamUrl = customUrl || activeUrl;
            previewActiveUrl = streamUrl;
            previewActiveDownloadId = null;
            const cleanTitle = getSafeTitle(videoTitle.textContent, "video");
            previewActiveFilename = `${cleanTitle}_Episode_${episode || 1}_${server || "Server"}.${ext}`;

            let proxyStreamUrl = "";
            if (isAdaptiveYoutube) {
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
                
                proxyStreamUrl = `/api/proxy/stream_adaptive?video_url=${encodeURIComponent(videoUrl)}&audio_url=${encodeURIComponent(audioUrl)}&container=${encodeURIComponent(ext || "mp4")}&start_time=0`;
            } else {
                previewIsAdaptive = false;
                proxyStreamUrl = `/api/proxy/stream?url=${encodeURIComponent(streamUrl)}&client_id=${encodeURIComponent(clientId)}`;
            }

            hidePreviewLoader();

            if (ext === "mp3" || ext === "m4a" || type === "audio") {
                if (previewAudioPlayer) {
                    previewAudioPlayer.onerror = () => {
                        console.warn("HTML5 Audio Error");
                        showPreviewLoader("Cannot play this audio stream directly. Please download the format instead using the button below.", true);
                        previewAudioContainer.classList.add("hidden");
                        stopAllPreviewPlaybacks();
                    };
                    previewAudioPlayer.src = proxyStreamUrl;
                    previewAudioPlayer.load();
                    previewAudioContainer.classList.remove("hidden");
                    setupAudioPreviewSubtitles();
                    previewAudioPlayer.play().catch(e => console.log("Playback blocked"));
                }
            } else {
                if (previewVideoPlayer) {
                    previewVideoContainer.classList.remove("hidden");
                    const isM3u8 = ext === "m3u8" || streamUrl.includes(".m3u8");

                    previewVideoPlayer.onerror = () => {
                        console.warn("HTML5 Video Error");
                        showPreviewLoader("Cannot play this source directly. Please select another Server (e.g. Server #1) or click the Download button below.", true);
                        previewVideoContainer.classList.add("hidden");
                        stopAllPreviewPlaybacks();
                    };

                    if (isM3u8 && typeof Hls !== "undefined" && Hls.isSupported()) {
                        const hls = new Hls({
                            maxBufferSize: 30 * 1024 * 1024, // 30MB buffer max
                            maxBufferLength: 30, // 30 seconds max buffer ahead
                            enableSubtitle: false
                        });
                        hls.loadSource(proxyStreamUrl);
                        hls.attachMedia(previewVideoPlayer);
                        hls.on(Hls.Events.MANIFEST_PARSED, () => {
                            previewVideoPlayer.play().catch(e => console.log("Playback blocked"));
                        });
                        hls.on(Hls.Events.ERROR, function (event, data) {
                            if (data.fatal) {
                                console.warn("HLS fatal error:", data.type);
                                showPreviewLoader("This server's source is encrypted by the provider and cannot be previewed directly. Please select another Server (e.g. Server #1) or click the Download button below.", true);
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
                url: (formatId.startsWith("direct_") || formatId === "image_preview" || formatId === "image_download" || (ext === "vtt" && !isYoutubeSub)) ? (customUrl || activeUrl) : activeUrl,
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
                        hidePreviewLoader();

                        const previewStreamUrl = `/api/download/file/${downloadId}?preview=true`;

                        if (ext === "mp3" || ext === "m4a" || type === "audio") {
                            if (previewAudioPlayer) {
                                previewAudioPlayer.onerror = () => {
                                    console.warn("HTML5 Audio Error");
                                    showPreviewLoader("Cannot play this audio file. Please try downloading the format instead using the button below.", true);
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

    async function loadDownloadHistory() {
        const downloadsList = document.getElementById("downloads-history-list");
        if (!downloadsList) return;
        downloadsList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading history...</div>`;
        try {
            const response = await fetch("/api/download/history");
            const data = await response.json();
            if (data.status === "success") {
                renderDownloadHistory(data.history);
            } else {
                downloadsList.innerHTML = `<div style="text-align: center; color: var(--red); padding: 20px;">Failed to load history</div>`;
            }
        } catch (e) {
            console.error("Error loading download history:", e);
            downloadsList.innerHTML = `<div style="text-align: center; color: var(--red); padding: 20px;">Error loading history</div>`;
        }
    }

    function renderDownloadHistory(history) {
        const downloadsList = document.getElementById("downloads-history-list");
        if (!downloadsList) return;
        downloadsList.innerHTML = "";
        if (history.length === 0) {
            downloadsList.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No downloaded files yet</div>`;
            return;
        }
        history.forEach(item => {
            const row = document.createElement("div");
            row.className = "history-item";
            row.style.cursor = "default";

            const thumbUrl = getProxiedImageUrl(item.thumbnail) || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=120";
            const platformTag = getPlatformTag(item.url);
            const timestampStr = item.timestamp ? formatHistoryDateTime(item.timestamp * 1000) : "Unknown date";
            
            let statusTag = "";
            if (item.status === "complete") {
                statusTag = `<span class="history-item-status-tag status-complete">Complete</span>`;
            } else if (item.status === "error") {
                statusTag = `<span class="history-item-status-tag status-error" title="${escapeHTML(item.error)}">Failed</span>`;
            } else if (item.status === "cancelled") {
                statusTag = `<span class="history-item-status-tag status-cancelled">Cancelled</span>`;
            } else {
                statusTag = `<span class="history-item-status-tag status-cancelled">${item.status}</span>`;
            }

            const title = item.title || "Unknown Title";
            const fileExists = !!item.file_exists;
            const extLabel = (item.ext || "mp4").toUpperCase();

            row.innerHTML = `
                <div class="history-item-left" style="flex: 1; min-width: 0;">
                    <img class="history-thumb" src="${thumbUrl}" alt="Thumb" style="cursor: pointer;">
                    <div class="history-details" style="min-width: 0;">
                        <span class="history-title" style="cursor: pointer;" title="${escapeHTML(title)}">${title}</span>
                        <div class="history-meta" style="flex-wrap: wrap; gap: 6px 10px;">
                            <span class="history-platform-tag ${platformTag.class}">${platformTag.label}</span>
                            <span style="color: var(--cyan); font-weight: 600;">${extLabel}</span>
                            <span>${timestampStr}</span>
                            ${statusTag}
                        </div>
                    </div>
                </div>
                <div class="history-item-actions">
                    <button class="history-action-btn btn-dl" ${fileExists ? '' : 'disabled'} title="${fileExists ? 'Download file directly from server' : 'File already purged from server'}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        <span>Download</span>
                    </button>
                    <button class="history-action-btn btn-re" title="Re-download / Fill configuration">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
                        <span>Re-download</span>
                    </button>
                    <button class="history-action-btn btn-del" title="Delete from history" style="border-color: rgba(239, 68, 68, 0.2); color: var(--red);">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                        <span>Delete</span>
                    </button>
                </div>
            `;

            const titleEl = row.querySelector(".history-title");
            const thumbEl = row.querySelector(".history-thumb");
            const dlBtn = row.querySelector(".btn-dl");
            const reBtn = row.querySelector(".btn-re");
            const delBtn = row.querySelector(".btn-del");

            const startAnalyze = () => {
                urlInput.value = item.url;
                performAnalysis();
            };
            titleEl.addEventListener("click", startAnalyze);
            thumbEl.addEventListener("click", startAnalyze);

            if (dlBtn && fileExists) {
                dlBtn.addEventListener("click", () => {
                    window.open(`/api/download/file/${item.download_id}`, "_blank");
                });
            }

            if (reBtn) {
                reBtn.addEventListener("click", () => {
                    urlInput.value = item.url;
                    autoFillSettingsAfterAnalysis = {
                        format_id: item.format_id,
                        ext: item.ext,
                        quality: item.quality,
                        trim_start: item.trim_start,
                        trim_end: item.trim_end,
                        voiceover_active: item.voiceover_active,
                        voiceover_voice: item.voiceover_voice,
                        voiceover_rate: item.voiceover_rate,
                        voiceover_pitch: item.voiceover_pitch,
                        cloud_destination: item.cloud_destination
                    };
                    performAnalysis();
                });
            }

            if (delBtn) {
                delBtn.addEventListener("click", () => {
                    showConfirm({
                        title: "Delete History Item",
                        message: `Are you sure you want to delete "${title}" from your history?`,
                        yesText: "Delete",
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

            downloadsList.appendChild(row);
        });
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
            return `<div class="sub-plain-text">${vttText}</div>`;
        }
        
        try {
            const cues = parseSubtitleText(vttText);
            if (!cues || cues.length === 0) {
                return `<div class="sub-plain-text"><div style="color: #ff4d4d; margin-bottom: 10px; font-weight: bold;">[DEBUG] Parsed 0 cues from VTT content. Fallback to raw text:</div>${vttText}</div>`;
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

    function getWordOverlap(text1, text2) {
        if (!text1 || !text2) return 0;
        const words1 = text1.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g,"").split(/\s+/).filter(Boolean);
        const words2 = text2.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g,"").split(/\s+/).filter(Boolean);
        
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
                const lastTextNorm = last.text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g,"").replace(/\s+/g, ' ').trim();
                const currTextNorm = current.text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g,"").replace(/\s+/g, ' ').trim();
                
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
            const transcriptList = document.getElementById("transcript-list");
            const sidebar = document.getElementById("preview-transcript-sidebar");
            if (transcriptList) {
                transcriptList.innerHTML = "";
                currentCues.forEach((cue, index) => {
                    const cueEl = document.createElement("div");
                    cueEl.className = "transcript-item";
                    cueEl.setAttribute("data-index", index);
                    
                    const timeEl = document.createElement("span");
                    timeEl.className = "transcript-item-time";
                    timeEl.textContent = formatTime(cue.start);
                    
                    const textEl = document.createElement("span");
                    textEl.className = "transcript-item-text";
                    textEl.textContent = cue.text;
                    
                    cueEl.appendChild(timeEl);
                    cueEl.appendChild(textEl);
                    
                    // Click to seek
                    cueEl.addEventListener("click", () => {
                        if (previewVideoPlayer) {
                            previewVideoPlayer.currentTime = cue.start;
                            previewVideoPlayer.play().catch(e => console.log(e));
                        }
                    });
                    
                    transcriptList.appendChild(cueEl);
                });
            }
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
                // Scroll into view if not manual scrolling
                const listEl = document.getElementById("transcript-list");
                if (listEl && !listEl.matches(':hover')) {
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
        previewSubSelect.addEventListener("change", function() {
            const val = this.value;
            const transSelect = document.getElementById("preview-sub-trans-select");
            if (transSelect) transSelect.value = "none";
            loadSubtitle(val);
        });
    }

    const previewSubTransSelect = document.getElementById("preview-sub-trans-select");
    if (previewSubTransSelect) {
        previewSubTransSelect.addEventListener("change", async function() {
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
        previewVoiceoverSelect.addEventListener("change", function() {
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
        speedSelectElement.addEventListener("change", function(e) {
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
        customSpeedInput.addEventListener("input", function() {
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

        customSpeedInput.addEventListener("change", function() {
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
        
        previewSubUploadFile.addEventListener("change", function() {
            const file = this.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(e) {
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
        });
    }

    if (loopPointAInput) {
        loopPointAInput.addEventListener("change", function() {
            const secs = parseTimeStringToSeconds(this.value);
            if (secs !== null) {
                loopStartSecs = secs;
                this.value = formatTimeDetailed(secs);
            } else {
                loopStartSecs = null;
                this.value = "";
            }
        });
    }

    if (loopPointBInput) {
        loopPointBInput.addEventListener("change", function() {
            const secs = parseTimeStringToSeconds(this.value);
            if (secs !== null) {
                loopEndSecs = secs;
                this.value = formatTimeDetailed(secs);
            } else {
                loopEndSecs = null;
                this.value = "";
            }
        });
    }

    // Video Ambient Light Glow System
    const ambientCanvas = document.getElementById("video-ambient-glow");
    const toggleAmbientGlow = document.getElementById("toggle-ambient-glow");
    let ambientAnimationFrame = null;

    if (ambientCanvas) {
        ambientCanvas.width = 64;
        ambientCanvas.height = 36;
    }

    function updateAmbientGlow() {
        if (!previewVideoPlayer || previewVideoPlayer.paused || previewVideoPlayer.ended) {
            return;
        }

        const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
        if (isGlowEnabled && ambientCanvas) {
            const ambientCtx = ambientCanvas.getContext("2d");
            if (ambientCtx) {
                try {
                    ambientCtx.drawImage(previewVideoPlayer, 0, 0, ambientCanvas.width, ambientCanvas.height);
                } catch (e) {}
            }
        }

        ambientAnimationFrame = requestAnimationFrame(updateAmbientGlow);
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
        previewVideoPlayer.addEventListener("ended", () => {
            if (ambientAnimationFrame) {
                cancelAnimationFrame(ambientAnimationFrame);
                ambientAnimationFrame = null;
            }
            const ambientCtx = ambientCanvas.getContext("2d");
            if (ambientCtx) {
                ambientCtx.clearRect(0, 0, ambientCanvas.width, ambientCanvas.height);
            }
        });
        previewVideoPlayer.addEventListener("seeked", () => {
            const isGlowEnabled = !toggleAmbientGlow || toggleAmbientGlow.checked;
            if (isGlowEnabled) {
                const ambientCtx = ambientCanvas.getContext("2d");
                if (ambientCtx) {
                    try {
                        ambientCtx.drawImage(previewVideoPlayer, 0, 0, ambientCanvas.width, ambientCanvas.height);
                    } catch (e) {}
                }
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
        } else {
            ambientCanvas.style.display = "none";
            if (videoWrapper) {
                videoWrapper.classList.remove("ambient-glow-active");
            }
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
                const ambientCtx = ambientCanvas.getContext("2d");
                if (ambientCtx && previewVideoPlayer) {
                    try {
                        ambientCtx.drawImage(previewVideoPlayer, 0, 0, ambientCanvas.width, ambientCanvas.height);
                    } catch (e) {}
                }
                if (previewVideoPlayer && !previewVideoPlayer.paused && !ambientAnimationFrame) {
                    updateAmbientGlow();
                }
            } else {
                ambientCanvas.style.display = "none";
                if (videoWrapper) {
                    videoWrapper.classList.remove("ambient-glow-active");
                }
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
        } else {
            abLoopWrapper.classList.remove("expanded");
            abLoopWrapper.classList.add("collapsed");
        }
        
        toggleAbLoop.addEventListener("change", () => {
            if (toggleAbLoop.checked) {
                abLoopWrapper.classList.remove("collapsed");
                abLoopWrapper.classList.add("expanded");
                localStorage.setItem("ab-loop-visible", "true");
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
    }

    // Set up listeners to sync preview settings back to main settings
    const previewExportType = document.getElementById("preview-export-type");
    if (previewExportType) {
        previewExportType.addEventListener("change", function() {
            const mainExport = document.getElementById("export-type-select");
            if (mainExport && mainExport.value !== this.value) {
                mainExport.value = this.value;
                mainExport.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewColorFilter = document.getElementById("preview-color-filter");
    if (previewColorFilter) {
        previewColorFilter.addEventListener("change", function() {
            const mainFilter = document.getElementById("color-filter-select");
            if (mainFilter && mainFilter.value !== this.value) {
                mainFilter.value = this.value;
                mainFilter.dispatchEvent(new Event("change"));
            }
        });
    }

    const previewCloudSync = document.getElementById("preview-cloud-sync");
    if (previewCloudSync) {
        previewCloudSync.addEventListener("change", function() {
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
        previewVoiceoverActive.addEventListener("change", function() {
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
        previewVoiceoverVoice.addEventListener("change", function() {
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
        previewVoiceoverRate.addEventListener("input", function() {
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
        previewVoiceoverPitch.addEventListener("input", function() {
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
                        get: function() {
                            return valueDescriptor.get.call(this);
                        },
                        set: function(val) {
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
                        get: function() {
                            return indexDescriptor.get.call(this);
                        },
                        set: function(idx) {
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
        subSizeSlider.addEventListener("input", function() {
            const valSpan = document.getElementById("preview-sub-size-val");
            if (valSpan) valSpan.textContent = this.value + "rem";
            applySubtitleStyles();
        });
    }

    const bgOpacitySlider = document.getElementById("preview-sub-bg-opacity");
    if (bgOpacitySlider) {
        bgOpacitySlider.addEventListener("input", function() {
            const valSpan = document.getElementById("preview-sub-bg-opacity-val");
            if (valSpan) valSpan.textContent = this.value + "%";
            applySubtitleStyles();
        });
    }

    const outlineSizeSlider = document.getElementById("preview-sub-outline");
    if (outlineSizeSlider) {
        outlineSizeSlider.addEventListener("input", function() {
            const valSpan = document.getElementById("preview-sub-outline-val");
            if (valSpan) valSpan.textContent = this.value + "px";
            applySubtitleStyles();
        });
    }

    const subPosSelect = document.getElementById("preview-sub-pos");
    if (subPosSelect) {
        subPosSelect.addEventListener("change", applySubtitleStyles);
    }

    // Swatches listeners
    document.querySelectorAll(".color-swatch").forEach(swatch => {
        swatch.addEventListener("click", function() {
            document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    document.querySelectorAll(".bg-swatch").forEach(swatch => {
        swatch.addEventListener("click", function() {
            document.querySelectorAll(".bg-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    document.querySelectorAll(".outline-swatch").forEach(swatch => {
        swatch.addEventListener("click", function() {
            document.querySelectorAll(".outline-swatch").forEach(s => s.classList.remove("active"));
            this.classList.add("active");
            applySubtitleStyles();
        });
    });

    // Custom color picker inputs
    const textColorPicker = document.getElementById("preview-sub-color");
    if (textColorPicker) {
        textColorPicker.addEventListener("input", function() {
            document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const bgColorPicker = document.getElementById("preview-sub-bg-color");
    if (bgColorPicker) {
        bgColorPicker.addEventListener("input", function() {
            document.querySelectorAll(".bg-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const outlineColorPicker = document.getElementById("preview-sub-outline-color");
    if (outlineColorPicker) {
        outlineColorPicker.addEventListener("input", function() {
            document.querySelectorAll(".outline-swatch").forEach(s => s.classList.remove("active"));
            applySubtitleStyles();
        });
    }

    const transcriptSearch = document.getElementById("transcript-search");
    if (transcriptSearch) {
        transcriptSearch.addEventListener("input", function() {
            const query = this.value.toLowerCase().trim();
            const cueEls = document.querySelectorAll(".transcript-item");
            cueEls.forEach(el => {
                const text = el.querySelector(".transcript-item-text").textContent.toLowerCase();
                if (text.includes(query)) {
                    el.style.display = "";
                } else {
                    el.style.display = "none";
                }
            });
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
        window.speechSynthesis.onvoiceschanged = () => {};
    }
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
});
