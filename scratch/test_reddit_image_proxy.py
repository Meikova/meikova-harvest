import requests

# Let's use a real reddit preview image URL
url = "https://preview.redd.it/why-is-fable-5-included-only-till-june-22-does-anthropic-v0-bX7TYEv45P.png?width=1080&crop=smart&auto=webp&s=554c25f5be4cb0e764a85fa0fdfa344933939393" # Just a guess or similar

# Actually, let's look at the resolved page for this post to get the exact image URL!
post_url = "https://old.reddit.com/r/ArtificialInteligence/comments/1u1dkg0/why_is_fable_5_included_only_till_june_22_does/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
res = requests.get(post_url, headers=headers)
print("old.reddit status code:", res.status_code)
# Find preview.redd.it or i.redd.it URLs
import re
urls = re.findall(r'https?://(?:preview|i)\.redd\.it/[^\s"\'&?]+', res.text)
print("Found image URLs:", urls)

if urls:
    target_url = urls[0]
    # Test proxy request with Referer
    proxy_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.reddit.com/"
    }
    proxy_res = requests.get(target_url, headers=proxy_headers)
    print("Proxy request status with referer:", proxy_res.status_code)
    
    # Test proxy request without Referer
    proxy_headers_no_ref = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    proxy_res_no_ref = requests.get(target_url, headers=proxy_headers_no_ref)
    print("Proxy request status without referer:", proxy_res_no_ref.status_code)
