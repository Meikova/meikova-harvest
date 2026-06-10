import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.networking import RequestDirector, RequestHandler

url = "https://www.youtube.com/watch?v=eBm23CzA-w4"

# Intercept RequestHandler.send to see which handler runs
original_handler_send = RequestHandler.send

def custom_handler_send(self, request):
    print(f"[Handler Run] {self.RH_NAME} is processing {request.url}")
    return original_handler_send(self, request)

RequestHandler.send = custom_handler_send

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.extract_info(url, download=False)
