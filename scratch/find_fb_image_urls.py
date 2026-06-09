import urllib.request
import re

url = "https://www.facebook.com/FuzeTeaVN/videos/1305800194990596/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='ignore')
    
    print("Page length:", len(html))
    
    # Look for image URLs, especially og:image or twitter:image
    og_image = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if og_image:
        print("og:image found:")
        for img in og_image:
            print("  ", img)
            
    twitter_image = re.findall(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if twitter_image:
        print("twitter:image found:")
        for img in twitter_image:
            print("  ", img)

    # Let's search for JSON fields containing "image" or "thumbnail"
    # Find all strings like "preferred_thumbnail":{"image":{"uri":"..."}}
    pref_thumbs = re.findall(r'"preferred_thumbnail"\s*:\s*{\s*"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
    if pref_thumbs:
        print("preferred_thumbnail found:")
        for img in pref_thumbs:
            print("  ", img.replace(r'\/', '/'))
            
    # Also generic image/uri patterns
    uri_images = re.findall(r'"image"\s*:\s*{\s*"uri"\s*:\s*"([^"]+)"', html)
    if uri_images:
        print("image uri found (first 10):")
        for img in uri_images[:10]:
            print("  ", img.replace(r'\/', '/'))

except Exception as e:
    print("Failed to inspect HTML:", e)
