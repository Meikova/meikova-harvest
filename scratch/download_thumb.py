import urllib.request

url = "https://scontent.fhan3-4.fna.fbcdn.net/v/t15.5256-10/698127967_27223746060592760_8753129920712595591_n.jpg?stp=dst-jpg_tt6&cstp=mx720x1280&ctp=s960x960&_nc_cat=104&ccb=1-7&_nc_sid=50ce42&_nc_ohc=Iehp0bz1rEoQ7kNvwGV1Ogc&_nc_oc=AdrTgqKz6ZDuzv42moE0JnRKgmXBgBNMxeue61Kp7ILxFSC0U_3o1NDNqXdgdOUKXv8&_nc_zt=23&_nc_ht=scontent.fhan3-4.fna&_nc_gid=6dKHitp5O5KF91cW_1GPig&_nc_ss=7c289&oh=00_Af_Qyb70ir9X7aF-WF068TbBi2ONUdYRI9z64aFUTFD_tg&oe=6A2D8B68"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        content = response.read()
        print(f"Downloaded successfully! Size: {len(content)} bytes")
        with open("scratch/facebook_thumbnail.jpg", "wb") as f:
            f.write(content)
        print("Saved to scratch/facebook_thumbnail.jpg")
except Exception as e:
    print("Download failed:", e)
