import inspect
from yt_dlp.extractor.common import InfoExtractor

# Let's inspect the signature and source code of _download_webpage_handle
print("InfoExtractor._download_webpage_handle source:")
print(inspect.getsource(InfoExtractor._download_webpage_handle))
