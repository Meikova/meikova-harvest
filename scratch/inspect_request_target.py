import inspect
import yt_dlp.networking._curlcffi as cc

# Let's inspect _get_request_target
try:
    print(inspect.getsource(cc.CurlCFFIRH._get_request_target))
except AttributeError:
    # Check parent class ImpersonateRequestHandler
    from yt_dlp.networking.impersonate import ImpersonateRequestHandler
    print(inspect.getsource(ImpersonateRequestHandler._get_request_target))
