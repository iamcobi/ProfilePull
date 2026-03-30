import requests
import json
import http.cookiejar
import os
from bs4 import BeautifulSoup

def test():
    cookies_path = "cookies.txt"
    if not os.path.exists(cookies_path):
        print("No cookies.txt!")
        return

    session = requests.Session()
    cj = http.cookiejar.MozillaCookieJar(cookies_path)
    cj.load()
    session.cookies.update(cj)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = session.get("https://www.instagram.com/instagram/", headers=headers, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"URL loaded: {r.url}")  # if it says /accounts/login it failed

    # Parse
    soup = BeautifulSoup(r.text, 'html.parser')
    desc_meta = soup.find("meta", property="og:description")
    img_meta = soup.find("meta", property="og:image")

    print(f"Bio: {desc_meta.get('content') if desc_meta else 'NULL'}")
    print(f"Image: {img_meta.get('content') if img_meta else 'NULL'}")

if __name__ == "__main__":
    test()
