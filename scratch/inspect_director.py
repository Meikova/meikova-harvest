import yt_dlp.networking
import inspect

print("yt_dlp.networking file:", inspect.getfile(yt_dlp.networking))

from yt_dlp.networking import RequestDirector
print("RequestDirector file:", inspect.getfile(RequestDirector))
print("\nRequestDirector.send source:")
print(inspect.getsource(RequestDirector.send))
