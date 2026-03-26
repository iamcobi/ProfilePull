import re
from urllib.parse import urlparse, unquote

def detect_url_type(url: str) -> dict:
    """
    1. Strips all query parameters and tracking suffixes before parsing
    2. Returns a dict with keys: platform, content_type, username, video_id
    3. Raises ValueError if the URL is unrecognized
    """
    # Strip query parameters handling
    parsed = urlparse(url)
    # clean path
    clean_path = unquote(parsed.path)
    clean_url = f"{parsed.netloc}{clean_path}".lower()
    
    # Check TikTok
    if "tiktok.com" in clean_url:
        platform = "TikTok"
        # Video: tiktok.com/@{username}/video/{id}
        video_match = re.search(r"@([a-zA-Z0-9_.-]+)/video/(\d+)", clean_path)
        if video_match:
            return {
                "platform": platform,
                "content_type": "video",
                "username": video_match.group(1),
                "video_id": video_match.group(2)
            }
        # Profile: tiktok.com/@{username}
        profile_match = re.search(r"@([a-zA-Z0-9_.-]+)", clean_path)
        if profile_match:
            return {
                "platform": platform,
                "content_type": "profile",
                "username": profile_match.group(1),
                "video_id": None
            }
            
    # Check Instagram
    elif "instagram.com" in clean_url:
        platform = "Instagram"
        # Video: instagram.com/p/{shortcode} or instagram.com/reel/{shortcode}
        video_match = re.search(r"/(?:p|reel)/([a-zA-Z0-9_-]+)", clean_path)
        if video_match:
            return {
                "platform": platform,
                "content_type": "video",
                # Note: username is not immediately parsed from a shortcode url, we might leave it unknown here
                "username": "unknown",
                "video_id": video_match.group(1)
            }
        # Profile: instagram.com/{username}
        # Avoid matching /p/, /reel/, /explore/, etc
        profile_match = re.search(r"^/([a-zA-Z0-9_.-]+)/?$", clean_path)
        if profile_match and profile_match.group(1) not in ['p', 'reel', 'explore', 'stories', 'tv']:
            return {
                "platform": platform,
                "content_type": "profile",
                "username": profile_match.group(1),
                "video_id": None
            }

    # Check YouTube
    elif "youtube.com" in clean_url or "youtu.be" in clean_url:
        platform = "YouTube"
        # Video: youtube.com/watch?v={id} or youtu.be/{id}
        if "youtu.be" in clean_url:
            video_id = clean_path.strip("/")
            if video_id:
                return {
                    "platform": platform,
                    "content_type": "video",
                    "username": "unknown",
                    "video_id": video_id
                }
        else:
            # Need to check query params for youtube.com/watch?v={id} since we stripped it in clean_url
            query = dict(q.split("=") for q in parsed.query.split("&") if "=" in q)
            if "watch" in clean_path and "v" in query:
                return {
                    "platform": platform,
                    "content_type": "video",
                    "username": "unknown",
                    "video_id": query["v"]
                }
            
            # Additional Youtube video formats 
            shorts_match = re.search(r"/shorts/([a-zA-Z0-9_-]+)", clean_path)
            if shorts_match:
                return {
                    "platform": platform,
                    "content_type": "video",
                    "username": "unknown",
                    "video_id": shorts_match.group(1)
                }

        # Profile: youtube.com/@{handle}, youtube.com/c/{name}, youtube.com/user/{name}, youtube.com/channel/{id}
        profile_match = re.search(r"/(?:@|c/|user/|channel/)([a-zA-Z0-9_.-]+)", clean_path)
        if profile_match:
            return {
                "platform": platform,
                "content_type": "profile",
                "username": profile_match.group(1),
                "video_id": None
            }

    raise ValueError("Unrecognized URL. Please paste a TikTok, Instagram, or YouTube profile or video link.")
