import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import inspect

# Let's print the signature of functions and class definitions
print("ImpersonateTarget definition:")
print(inspect.getsource(ImpersonateTarget))

# Let's see what is inside yt_dlp.networking.impersonate
import yt_dlp.networking.impersonate as imp
print("\nFunctions / classes in yt_dlp.networking.impersonate:")
for name, obj in inspect.getmembers(imp):
    if inspect.isfunction(obj) or inspect.isclass(obj):
        print(f"  {name}")

# Let's see how yt-dlp parses CLI --impersonate option. E.g. where does it parse the string target?
try:
    from yt_dlp.networking.impersonate import parse_target
    print("\nparse_target found! Source:")
    print(inspect.getsource(parse_target))
except ImportError:
    print("\nparse_target not found.")
