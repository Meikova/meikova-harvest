import os
import logging
import yt_dlp
from config import TEMP_DOWNLOAD_DIR

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
except ImportError:
    ImpersonateTarget = None

logger = logging.getLogger(__name__)

# Monkey-patch CurlCFFIRH to dynamically match the TLS fingerprint with the request's User-Agent
try:
    from yt_dlp.networking._curlcffi import CurlCFFIRH
    if ImpersonateTarget and CurlCFFIRH:
        original_get_request_target = CurlCFFIRH._get_request_target

        def custom_get_request_target(self, request):
            ua = request.headers.get('User-Agent', '')
            if ua:
                ua_lower = ua.lower()
                if 'firefox' in ua_lower:
                    target_str = 'firefox'
                elif 'safari' in ua_lower and 'chrome' not in ua_lower and 'chromium' not in ua_lower:
                    target_str = 'safari'
                elif 'edge' in ua_lower or 'edg/' in ua_lower:
                    target_str = 'edge'
                elif 'android' in ua_lower:
                    target_str = 'chrome-131:android-14'
                else:
                    target_str = 'chrome'
                try:
                    resolved = self._resolve_target(ImpersonateTarget.from_str(target_str))
                    if resolved:
                        return resolved
                except Exception:
                    pass
            return original_get_request_target(self, request)

        CurlCFFIRH._get_request_target = custom_get_request_target
        logger.info("Successfully monkey-patched CurlCFFIRH._get_request_target to align TLS fingerprint with User-Agent.")
except Exception as patch_err:
    logger.warning(f"Could not monkey-patch CurlCFFIRH: {patch_err}")


def create_ydl_instance(ydl_opts, url=None, client_id=None):
    """
    Attempts to instantiate YoutubeDL. 
    If cookiesfrombrowser is 'auto', it will attempt different browsers one by one.
    If all fail, it will fall back to using no cookies.
    """
    logger.info(f"create_ydl_instance: client_id='{client_id}', url='{url}'")
    if ImpersonateTarget:
        try:
            ydl_opts["impersonate"] = ImpersonateTarget.from_str("chrome")
            logger.info("Automatically added 'chrome' impersonate option to ydl_opts in create_ydl_instance.")
        except Exception as e:
            logger.warning(f"Failed to apply client impersonate settings in create_ydl_instance: {e}")
            
    # Check if a client-specific cookies file exists
    if client_id:
        client_cookies = os.path.join(TEMP_DOWNLOAD_DIR, "cookies", f"cookies_{client_id}.txt")
        logger.info(f"Checking client-specific cookies at: {client_cookies} (exists={os.path.exists(client_cookies)})")
        if os.path.exists(client_cookies):
            logger.info(f"Using client-specific cookies for client: {client_id}")
            opts = ydl_opts.copy()
            opts["cookiefile"] = client_cookies
            opts.pop("cookiesfrombrowser", None)
            try:
                with open(client_cookies, "r", encoding="utf-8") as f:
                    cookie_content = f.read()
                youtube_cookie_lines = []
                for line in cookie_content.splitlines():
                    if not line.strip().startswith("#") and "youtube.com" in line:
                        parts = line.split("\t")
                        if len(parts) >= 7:
                            masked_val = parts[6][:4] + "..." + parts[6][-4:] if len(parts[6]) > 8 else "..."
                            youtube_cookie_lines.append(f"Domain={parts[0]}, Name={parts[5]}, Expires={parts[4]}, Value={masked_val}")
                logger.info(f"Loaded client cookies for youtube.com (count={len(youtube_cookie_lines)}):")
                for c_log in youtube_cookie_lines:
                    logger.info(f"  [Cookie] {c_log}")
            except Exception as read_err:
                logger.warning(f"Could not print cookies diagnostics: {read_err}")

            try:
                ydl = yt_dlp.YoutubeDL(opts)
                logger.info(f"Successfully loaded yt_dlp with client-specific cookies for: {client_id}")
                return ydl
            except Exception as e:
                logger.warning(f"Failed to load client cookies: {e}")

    # Check if a local cookies.txt file exists in the root folder
    local_cookies = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    if os.path.exists(local_cookies):
        logger.info("Using local default cookies.txt file")
        opts = ydl_opts.copy()
        opts["cookiefile"] = local_cookies
        opts.pop("cookiesfrombrowser", None)
        try:
            return yt_dlp.YoutubeDL(opts)
        except Exception as e:
            logger.warning(f"Failed to load local cookies.txt: {e}")

    if ydl_opts.get("cookiesfrombrowser") != "auto":
        return yt_dlp.YoutubeDL(ydl_opts)
        
    is_headless = os.path.exists('/.dockerenv') or os.environ.get('RENDER') == 'true'
    if is_headless:
        logger.info("Running in headless/Docker/Render environment. Skipping browser cookies search.")
        opts = ydl_opts.copy()
        opts.pop("cookiesfrombrowser", None)
        logger.info("Falling back to YoutubeDL instance without cookies")
        return yt_dlp.YoutubeDL(opts)

    browsers = ["chrome", "edge", "firefox", "opera", "vivaldi", "brave"]
    
    # Filter browsers based on whether their user data directory exists to avoid FileNotFoundError logs
    available_browsers = []
    appdata_local = os.environ.get("LOCALAPPDATA")
    appdata_roaming = os.environ.get("APPDATA")
    
    for browser in browsers:
        exists = False
        if browser == "chrome" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Google/Chrome/User Data"))
        elif browser == "edge" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Microsoft/Edge/User Data"))
        elif browser == "brave" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "BraveSoftware/Brave-Browser/User Data"))
        elif browser == "vivaldi" and appdata_local:
            exists = os.path.exists(os.path.join(appdata_local, "Vivaldi/User Data"))
        elif browser == "opera":
            exists = (
                (appdata_roaming and os.path.exists(os.path.join(appdata_roaming, "Opera Software"))) or 
                (appdata_local and os.path.exists(os.path.join(appdata_local, "Opera Software")))
            )
        elif browser == "firefox" and appdata_roaming:
            exists = os.path.exists(os.path.join(appdata_roaming, "Mozilla/Firefox/Profiles"))
        else:
            # Fallback for non-Windows or unknown environments
            exists = True
            
        if exists:
            available_browsers.append(browser)
            
    browsers = available_browsers
    logger.info(f"Available browser cookie sources: {browsers}")

    # Extract target domain for cookie filtering
    target_domain = None
    if url:
        url_lower = url.lower()
        if "facebook" in url_lower or "fb.watch" in url_lower or "fb.gg" in url_lower or "fb.com" in url_lower:
            target_domain = "facebook"
        elif "youtube" in url_lower or "youtu.be" in url_lower:
            target_domain = "youtube"
        elif "instagram" in url_lower:
            target_domain = "instagram"
        elif "tiktok" in url_lower:
            target_domain = "tiktok"

    # Step 1: Prioritize browsers that have cookies for the target domain
    if target_domain:
        for browser in browsers:
            opts = ydl_opts.copy()
            opts["cookiesfrombrowser"] = (browser,)
            try:
                ydl = yt_dlp.YoutubeDL(opts)
                # Force loading of cookiejar and check for domain cookies
                cookiejar = ydl.cookiejar
                if any(target_domain in cookie.domain for cookie in cookiejar):
                    logger.info(f"Successfully loaded cookies from browser: {browser} (matched target domain '{target_domain}')")
                    return ydl
            except Exception:
                pass

    # Step 2: Fallback to the first browser that loads successfully (regardless of domain cookies)
    for browser in browsers:
        opts = ydl_opts.copy()
        opts["cookiesfrombrowser"] = (browser,)
        try:
            ydl = yt_dlp.YoutubeDL(opts)
            _ = ydl.cookiejar
            logger.info(f"Fallback to cookies from browser: {browser}")
            return ydl
        except Exception as e:
            logger.warning(f"Failed to load cookies from browser '{browser}': {e}")
            
    # Step 3: Fallback to no cookies if all failed
    opts = ydl_opts.copy()
    opts.pop("cookiesfrombrowser", None)
    logger.info("Falling back to YoutubeDL instance without cookies")
    return yt_dlp.YoutubeDL(opts)
