// Runnable check for Media URL Normalization and History Deduplication
const assert = require("assert");

function normalizeMediaUrl(url) {
    if (!url || typeof url !== "string") return "";
    let clean = url.trim();

    try {
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
    }

    return clean.replace(/\/$/, "");
}

function isSameMediaItem(a, b) {
    if (!a || !b) return false;

    const normA = normalizeMediaUrl(a.url);
    const normB = normalizeMediaUrl(b.url);
    if (normA && normB && normA === normB) {
        return true;
    }

    if (a.id && b.id && String(a.id) === String(b.id)) {
        return true;
    }

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

// 1. YouTube with radio mix list and start_radio params vs clean watch URL
const radioUrl = "https://www.youtube.com/watch?v=DzOF3gUEqkY&list=RDDzOF3gUEqkY&start_radio=1";
const cleanUrl = "https://www.youtube.com/watch?v=DzOF3gUEqkY";
assert.strictEqual(normalizeMediaUrl(radioUrl), "https://www.youtube.com/watch?v=DzOF3gUEqkY");
assert.strictEqual(normalizeMediaUrl(cleanUrl), "https://www.youtube.com/watch?v=DzOF3gUEqkY");
assert.strictEqual(normalizeMediaUrl(radioUrl), normalizeMediaUrl(cleanUrl));

// 2. YouTube short link and timestamp params
const shortUrl = "https://youtu.be/DzOF3gUEqkY?t=45s";
assert.strictEqual(normalizeMediaUrl(shortUrl), "https://www.youtube.com/watch?v=DzOF3gUEqkY");

// 3. YouTube Shorts and Music links
const shortsUrl = "https://www.youtube.com/shorts/DzOF3gUEqkY";
const musicUrl = "https://music.youtube.com/watch?v=DzOF3gUEqkY";
assert.strictEqual(normalizeMediaUrl(shortsUrl), "https://www.youtube.com/watch?v=DzOF3gUEqkY");
assert.strictEqual(normalizeMediaUrl(musicUrl), "https://www.youtube.com/watch?v=DzOF3gUEqkY");

// 4. isSameMediaItem test across radio URL and clean URL
const itemRadio = { url: radioUrl, title: "NØIR/SIDE | Elegy - EP", platform_class: "youtube" };
const itemClean = { url: cleanUrl, title: "NØIR/SIDE | Elegy - EP", platform_class: "youtube" };
assert.strictEqual(isSameMediaItem(itemRadio, itemClean), true);

// 5. Deduplicate historical list (like user's screenshot with duplicate items)
const legacyHistory = [
    { url: cleanUrl, title: "NØIR/SIDE | Elegy - EP", platform_class: "youtube", timestamp: 1791044789000 },
    { url: "https://www.youtube.com/watch?v=TokyoShibuya123", title: "【4K HDR】Night Walk in Tokyo Shibuya (東京散歩)", platform_class: "youtube", timestamp: 1791041105000 },
    { url: radioUrl, title: "NØIR/SIDE | Elegy - EP", platform_class: "youtube", timestamp: 1791036821000 }
];

const cleaned = deduplicateHistory(legacyHistory);
assert.strictEqual(cleaned.length, 2, "Deduplication must eliminate the older duplicate of NØIR/SIDE | Elegy - EP");
assert.strictEqual(cleaned[0].title, "NØIR/SIDE | Elegy - EP");
assert.strictEqual(cleaned[0].timestamp, 1791044789000, "Newer timestamp is kept");
assert.strictEqual(cleaned[1].title, "【4K HDR】Night Walk in Tokyo Shibuya (東京散歩)");

console.log("All 5 URL normalization & history deduplication assertions passed successfully!");
