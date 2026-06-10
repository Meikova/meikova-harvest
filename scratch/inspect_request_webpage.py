import inspect
from yt_dlp.extractor.common import InfoExtractor

print("InfoExtractor._request_webpage source:")
print(inspect.getsource(InfoExtractor._request_webpage))
