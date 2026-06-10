import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.networking import RequestDirector, RequestHandler

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

# Let's override RequestDirector.send to see which handler is chosen
original_send = RequestDirector.send

def custom_send(self, request):
    print(f"\n[Trace] Request URL: {request.url}")
    # Find which handler is selected for this request
    for handler in self.handlers.values():
        if isinstance(handler, RequestHandler):
            # Check if handler can handle the request
            # Let's see if this handler gets called
            pass
    # We can inspect the handler that gets returned by _get_handler or similar, or just let original run
    res = original_send(self, request)
    # Let's inspect the response to see which handler processed it
    # Responses usually have a handler attribute or request handler info
    print(f"[Trace] Response processed. Headers: {res.headers}")
    return res

RequestDirector.send = custom_send

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info(url, download=False)
