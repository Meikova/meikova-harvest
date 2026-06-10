import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.networking import Request
from yt_dlp.networking.exceptions import UnsupportedRequest

# Create request with impersonate
request = Request("https://www.youtube.com/watch?v=eBm23CzA-w4")

ydl_opts = {
    "quiet": True,
    "no_warnings": False,
    "nocheckcertificate": True,
    "noplaylist": True,
    "impersonate": ImpersonateTarget.from_str("chrome"),
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    director = ydl._request_director
    print("Checking validation for each handler:")
    for handler in director._get_handlers(request):
        try:
            handler.validate(request)
            print(f"  {handler.RH_NAME} supports this request.")
        except UnsupportedRequest as e:
            print(f"  {handler.RH_NAME} DOES NOT support this request: {e}")
