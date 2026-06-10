import inspect
import yt_dlp

print("YoutubeDL.urlopen source:")
print(inspect.getsource(yt_dlp.YoutubeDL.urlopen))
