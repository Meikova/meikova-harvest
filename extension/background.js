/**
 * Meikova Harvest Companion — Background Service Worker
 * 
 * Automatically syncs browser cookies to the local Meikova Harvest server
 * whenever the user completes a page navigation. This ensures the backend always
 * has fresh session cookies for protected sites (Cloudflare, login-gated, etc.).
 */

const DEFAULT_SERVER = "http://127.0.0.1:18650";

/**
 * Sync cookies for a given URL to the local ETD server.
 */
async function syncCookiesForUrl(url) {
  if (!url || (!url.startsWith("http://") && !url.startsWith("https://"))) return;

  // Skip local/internal URLs
  try {
    const hostname = new URL(url).hostname;
    if (hostname === "127.0.0.1" || hostname === "localhost" || hostname === "0.0.0.0") return;
  } catch { return; }

  try {
    const cookies = await chrome.cookies.getAll({ url });
    if (!cookies || cookies.length === 0) return;

    // Read server URL from storage
    const storage = await chrome.storage.local.get("etd_server_url");
    const serverUrl = (storage.etd_server_url || DEFAULT_SERVER).replace(/\/$/, "");

    const resp = await fetch(`${serverUrl}/api/cookies/paste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: "chrome-extension",
        content: JSON.stringify(cookies)
      })
    });

    if (resp.ok) {
      console.log(`[ETD Background] Synced ${cookies.length} cookies for ${new URL(url).hostname}`);
    }
  } catch {
    // Server not running or unreachable — silently ignore
  }
}

// Auto-sync cookies when the user finishes loading a page (main frame only)
chrome.webNavigation.onCompleted.addListener((details) => {
  if (details.frameId !== 0) return;
  syncCookiesForUrl(details.url);
});

// Also sync when a cookie changes for a domain the user recently visited
chrome.cookies.onChanged.addListener((changeInfo) => {
  if (changeInfo.removed) return; // Only care about new/updated cookies
  const cookie = changeInfo.cookie;
  const scheme = cookie.secure ? "https" : "http";
  const domain = cookie.domain.startsWith(".") ? cookie.domain.slice(1) : cookie.domain;
  syncCookiesForUrl(`${scheme}://${domain}/`);
});
