import inspect
from yt_dlp.extractor.common import InfoExtractor

print("InfoExtractor._create_request source:")
print(inspect.getsource(InfoExtractor._create_request))
