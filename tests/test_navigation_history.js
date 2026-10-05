// Runnable check for Navigation History Stack logic
const assert = require("assert");

// Simulates the exact state machine from static/js/main.js
function createNavigationManager() {
    const navigationHistory = [""];
    let navigationIndex = 0;
    let isNavigating = false;
    let navBackDisabled = true;
    let navForwardDisabled = true;
    let navBackTitle = "";
    let navForwardTitle = "";
    let welcomeResetCalled = false;
    let analyzedUrl = null;

    function updateNavigationButtons() {
        const canGoBack = navigationIndex > 0;
        const canGoForward = navigationIndex < navigationHistory.length - 1;

        navBackDisabled = !canGoBack;
        if (canGoBack) {
            const prevUrl = navigationHistory[navigationIndex - 1];
            navBackTitle = prevUrl ? `Go back: ${prevUrl}` : "Go back to Welcome Screen (Backspace / Alt + Left)";
        } else {
            navBackTitle = "Go back (No earlier history)";
        }

        navForwardDisabled = !canGoForward;
        if (canGoForward) {
            const nextUrl = navigationHistory[navigationIndex + 1];
            navForwardTitle = nextUrl ? `Go forward: ${nextUrl}` : "Go forward to Welcome Screen (Alt + Right)";
        } else {
            navForwardTitle = "Go forward (No forward history)";
        }
    }

    function pushToNavigationHistory(url) {
        if (isNavigating) return;
        const cleanUrl = (url || "").trim();

        if (navigationIndex >= 0 && navigationHistory[navigationIndex] === cleanUrl) {
            return;
        }

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
                updateNavigationButtons();
                if (targetUrl) {
                    analyzedUrl = targetUrl;
                } else {
                    welcomeResetCalled = true;
                    analyzedUrl = null;
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
                updateNavigationButtons();
                if (targetUrl) {
                    analyzedUrl = targetUrl;
                } else {
                    welcomeResetCalled = true;
                    analyzedUrl = null;
                }
            } finally {
                isNavigating = false;
                updateNavigationButtons();
            }
        }
    }

    updateNavigationButtons();

    return {
        getHistory: () => [...navigationHistory],
        getIndex: () => navigationIndex,
        isBackDisabled: () => navBackDisabled,
        isForwardDisabled: () => navForwardDisabled,
        getBackTitle: () => navBackTitle,
        getForwardTitle: () => navForwardTitle,
        push: pushToNavigationHistory,
        back: navigateHistoryBack,
        forward: navigateHistoryForward,
        wasWelcomeReset: () => welcomeResetCalled,
        getAnalyzedUrl: () => analyzedUrl
    };
}

// 1. Initial State
const nav = createNavigationManager();
assert.strictEqual(nav.getIndex(), 0, "Initial index should be 0");
assert.deepStrictEqual(nav.getHistory(), [""], "Initial history should contain empty Home URL");
assert.strictEqual(nav.isBackDisabled(), true, "Back button should initially be disabled");
assert.strictEqual(nav.isForwardDisabled(), true, "Forward button should initially be disabled");

// 2. User analyzes first URL (YouTube)
nav.push("https://youtu.be/test1");
assert.strictEqual(nav.getIndex(), 1, "Index should be 1 after first URL push");
assert.deepStrictEqual(nav.getHistory(), ["", "https://youtu.be/test1"]);
assert.strictEqual(nav.isBackDisabled(), false, "Back button MUST be enabled after analyzing first link");
assert.strictEqual(nav.isForwardDisabled(), true, "Forward button should be disabled when at tip");
assert.ok(nav.getBackTitle().includes("Welcome Screen"), "Back button tooltip points to Welcome Screen");

// 3. User clicks Back -> returns to Welcome Screen
nav.back();
assert.strictEqual(nav.getIndex(), 0, "Index should return to 0 after back");
assert.strictEqual(nav.isBackDisabled(), true, "Back button should be disabled at root");
assert.strictEqual(nav.isForwardDisabled(), false, "Forward button MUST be enabled after navigating back");
assert.strictEqual(nav.wasWelcomeReset(), true, "Welcome screen reset should be triggered");
assert.ok(nav.getForwardTitle().includes("https://youtu.be/test1"), "Forward button tooltip points to URL 1");

// 4. User clicks Forward -> returns to first URL
nav.forward();
assert.strictEqual(nav.getIndex(), 1, "Index should return to 1 after forward");
assert.strictEqual(nav.isBackDisabled(), false, "Back button should be enabled again");
assert.strictEqual(nav.isForwardDisabled(), true, "Forward button should be disabled at tip");
assert.strictEqual(nav.getAnalyzedUrl(), "https://youtu.be/test1");

// 5. User analyzes second URL
nav.push("https://youtu.be/test2");
assert.strictEqual(nav.getIndex(), 2, "Index should advance to 2");
assert.deepStrictEqual(nav.getHistory(), ["", "https://youtu.be/test1", "https://youtu.be/test2"]);
assert.strictEqual(nav.isBackDisabled(), false);
assert.strictEqual(nav.isForwardDisabled(), true);

// 6. User clicks Back -> returns to URL 1
nav.back();
assert.strictEqual(nav.getIndex(), 1);
assert.strictEqual(nav.getAnalyzedUrl(), "https://youtu.be/test1");
assert.strictEqual(nav.isBackDisabled(), false, "Back still enabled (can reach Welcome)");
assert.strictEqual(nav.isForwardDisabled(), false, "Forward still enabled (can reach URL 2)");

// 7. Duplicate consecutive push is ignored
nav.push("https://youtu.be/test1");
assert.strictEqual(nav.getIndex(), 1, "Sequential duplicate push should not append or corrupt index");

console.log("All 7 navigation history test assertions passed successfully!");
