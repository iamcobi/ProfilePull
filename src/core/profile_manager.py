import os
import logging
import shutil
import requests
import tempfile
import uuid
from pathlib import Path
from src.core.database import db
from src.core.utils import get_view_folder, compute_md5, get_unique_filename, sanitize_filename
from src.core.downloader import get_video_info, download_video

logger = logging.getLogger(__name__)

def get_profile_root(base_dir: str, username: str) -> Path:
    return Path(base_dir) / "ProfilePull" / username

def get_single_video_root(base_dir: str) -> Path:
    return Path(base_dir) / "ProfilePull" / "videos"

def re_sort_all_videos(username: str, base_path: str):
    """
    Moves all video files for a profile into the correct view-count subfolder
    based on current view counts from the database.
    Does NOT re-download any files — only moves them on the filesystem.
    """
    profile_root = get_profile_root(base_path, username)
    videos_root = profile_root / "videos"
    if not videos_root.exists():
        return

    # Find download entry
    downloads = db.get_all_downloads()
    download_entry = next((d for d in downloads if d["username"].lower() == username.lower()), None)
    if not download_entry:
        return

    videos = db.get_all_videos_for_download(download_entry["id"])
    for video in videos:
        view_count = video.get("view_count", 0)
        is_short = bool(video.get("is_short", 0))
        
        vid_root = videos_root / "shorts" if is_short else videos_root
        correct_folder_name = get_view_folder(view_count)
        correct_folder_path = vid_root / correct_folder_name
        correct_folder_path.mkdir(parents=True, exist_ok=True)
        
        # File's database path or filename
        filename = video.get("filename")
        if not filename:
            continue

        # We need to find where the file currently is by scanning all view folders
        current_file_path = None
        for root in [videos_root, videos_root / "shorts"]:
            for sub_folder in ["<1k", "1k-10k", "10k-100k", "100k-1m", ">1m", "0-100k", "Under 1k", "Over 1m"]:
                possible_path = root / sub_folder / filename
                if possible_path.exists():
                    current_file_path = possible_path
                    break
            if current_file_path:
                break

        if current_file_path:
            target_path = correct_folder_path / filename
            if current_file_path != target_path:
                logger.info(f"Moving {filename} from {current_file_path.parent.name} to {correct_folder_path.name}")
                shutil.move(str(current_file_path), str(target_path))
                # Update DB with new folder
                db.update_video_view_count(video["id"], view_count, correct_folder_name)

import subprocess
import json

def _download_instagram_gallery_dl(url: str, username: str, base_path: str, profile_root: Path, db_id: int, progress_callback=None):
    if progress_callback: progress_callback("Initializing gallery-dl Instagram Engine...", 5)
    
    cookies_path = os.path.join(os.getcwd(), "cookies.txt")
    if not os.path.exists(cookies_path):
        if progress_callback: progress_callback("Error: cookies.txt missing! Instagram locked.", 100)
        logger.error("cookies.txt not found.")
        return
        
    videos_root = profile_root / "videos"
    videos_root.mkdir(parents=True, exist_ok=True)
    
    tmp_uuid = str(uuid.uuid4())
    temp_videos_root = Path(tempfile.gettempdir()) / "ProfilePull" / tmp_uuid
    temp_videos_root.mkdir(parents=True, exist_ok=True)
    
    # Do not set "directory" inside config to avoid gallery-dl nested path translation 
    config = {
      "extractor": {
        "instagram": {
          "api": "rest",
          "cookies": str(cookies_path),
          "include": "posts,reels",
          "videos": True,
          "sleep-request": [3.0, 7.0],
          "write-metadata": True,
          "filename": "{shortcode}.{extension}",
          "archive": str(profile_root / "instagram_archive.sqlite3")
        }
      }
    }
    config_file = temp_videos_root / "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
        
    cmd = ["gallery-dl", "--config", str(config_file), "-d", str(temp_videos_root), url]
    
    if progress_callback: progress_callback("Scraping profile with gallery-dl... (This may take a while)", 20)
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
    count = 0
    for line in iter(proc.stdout.readline, ""):
        line = line.strip()
        if line:
            logger.info(line)
            if ".mp4" in line.lower() or "instagram.com" in line.lower():
                count += 1
                disp_line = line.split("\\")[-1].split("/")[-1] if ".mp4" in line.lower() else line
                if len(disp_line) > 50:
                    disp_line = disp_line[:47] + "..."
                if progress_callback: progress_callback(f"Downloading: {disp_line} (Found: {count})", 50)
                
    proc.wait()
    
    if progress_callback: progress_callback("Organizing downloaded Instagram videos...", 90)
    
    # gallery-dl safely dumped straight into temp_videos_root
    for file_path in temp_videos_root.rglob("*.*"):
        if file_path.suffix.lower() == ".mp4":
            filename = file_path.name
            vid_id = file_path.stem
            
            view_count = 0
            json_file = file_path.with_suffix('.json')
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                        # Metadata structures from gallery-dl json outputs
                        if isinstance(data, list) and len(data) > 0:
                            meta = data[-1] if isinstance(data[-1], dict) else data[0]
                        else:
                            meta = data
                        view_count = meta.get("video_view_count") or meta.get("view_count") or meta.get("play_count") or 0
                except Exception as e:
                    logger.error(f"Failed parsing meta json {json_file}: {e}")
                    
            target_folder = videos_root / get_view_folder(view_count)
            target_folder.mkdir(parents=True, exist_ok=True)
            final_path = target_folder / filename
            
            shutil.move(str(file_path), str(final_path))
            
            db.add_video(
                download_id=db_id,
                video_id=vid_id,
                title=filename,
                filename=filename,
                view_count=int(view_count),
                view_folder=get_view_folder(view_count)
            )
            
    if temp_videos_root.exists():
        shutil.rmtree(str(temp_videos_root), ignore_errors=True)
        
    if progress_callback: progress_callback("Re-sorting videos by view count...", 99)
    re_sort_all_videos(username, base_path)
    if progress_callback: progress_callback("Done.", 100)

def download_profile(url: str, username: str, platform: str, base_path: str, progress_callback=None):
    profile_root = get_profile_root(base_path, username)
    profile_root.mkdir(parents=True, exist_ok=True)
    
    # Check DB early
    db_id = db.get_or_create_download(username, platform, url, str(profile_root))

    # Grab channel info (YouTube / TikTok fallback)
    if progress_callback: progress_callback("Fetching profile information...", 0)
    info = {}
    entries = []
    
    if platform.lower() == "youtube":
        if not url.endswith("/videos") and not url.endswith("/shorts") and not url.endswith("/streams"):
            v_url = url.rstrip("/") + "/videos"
            s_url = url.rstrip("/") + "/shorts"
            
            if progress_callback: progress_callback("Evaluating Long-Form Videos tab...", 2)
            try:
                v_info = get_video_info(v_url, extract_flat=True)
                v_entries = v_info.get("entries", [])
                for e in v_entries: e["is_short"] = False
                entries.extend(v_entries)
            except Exception as e:
                logger.warning(f"No Long-Form tab found or failed: {e}")
                
            if progress_callback: progress_callback("Evaluating Shorts tab...", 4)
            try:
                s_info = get_video_info(s_url, extract_flat=True)
                s_entries = s_info.get("entries", [])
                for e in s_entries: e["is_short"] = True
                entries.extend(s_entries)
            except Exception as e:
                logger.warning(f"No Shorts tab found or failed: {e}")
                
            info = get_video_info(url, extract_flat=True)
            info["entries"] = entries
        else:
            info = get_video_info(url, extract_flat=True)
            page_entries = info.get("entries", [])
            is_sh = "/shorts" in url
            for e in page_entries: e["is_short"] = is_sh
            entries.extend(page_entries)
            info["entries"] = entries
    elif platform.lower() != "instagram":
        info = get_video_info(url, extract_flat=True)
    
    # Handle Bio and Profile Picture using BeautifulSoup & TikWM REST 
    if progress_callback: progress_callback("Extracting Profile Metadata directly...", 5)
    try:
        from bs4 import BeautifulSoup
        import http.cookiejar
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        session = requests.Session()
        
        cookies_path = os.path.join(os.getcwd(), "cookies.txt")
        if os.path.exists(cookies_path):
            cj = http.cookiejar.MozillaCookieJar(cookies_path)
            cj.load()
            session.cookies.update(cj)
            
        bio_text = ""
        best_thumb = ""
        
        # TikTok Specific REST API Bypass 
        if platform.lower() == "tiktok":
            if progress_callback: progress_callback("Engaging TikWM Captcha bypass protocol...", 10)
            tw_req = requests.get(f"https://tikwm.com/api/user/info?unique_id=@{username}", timeout=10)
            if tw_req.status_code == 200:
                tw_data = tw_req.json().get("data", {})
                if tw_data and "user" in tw_data:
                    bio_text = tw_data["user"].get("signature", "")
                    best_thumb = tw_data["user"].get("avatarThumb", "")
                    if progress_callback: progress_callback("TikWM extraction completely successful.", 15)
                    
        if not bio_text or not best_thumb:
            r = session.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Extract Bio
            desc_meta = soup.find("meta", property="og:description")
            if not bio_text:
                bio_text = desc_meta.get("content", "").strip() if desc_meta else ""
                if not bio_text and "description" in info:
                    bio_text = info.get("description", "")
                    
            # Extract Profile Picture
            img_meta = soup.find("meta", property="og:image")
            if not best_thumb:
                best_thumb = img_meta.get("content", "") if img_meta else ""
                if not best_thumb and info.get("thumbnails"):
                    best_thumb = info["thumbnails"][-1]["url"]
                    
        # Apply physical drops
        if bio_text:
            bio_path = profile_root / "bio.txt"
            target_bio = get_unique_filename(str(profile_root), "bio.txt")
            if not bio_path.exists():
                with open(profile_root / target_bio, "w", encoding="utf-8") as f:
                    f.write(bio_text)
                    
        if best_thumb:
            pic_path = profile_root / "profile.jpg"
            temp_pic = profile_root / "temp_profile.jpg"
            img_r = session.get(best_thumb, stream=True)
            if img_r.status_code == 200:
                with open(temp_pic, "wb") as f:
                    img_r.raw.decode_content = True
                    shutil.copyfileobj(img_r.raw, f)
                    
                if pic_path.exists():
                    old_hash = compute_md5(str(pic_path))
                    new_hash = compute_md5(str(temp_pic))
                    if old_hash == new_hash:
                        temp_pic.unlink()
                    else:
                        target_pic = get_unique_filename(str(profile_root), "profile.jpg")
                        temp_pic.rename(profile_root / target_pic)
                else:
                    temp_pic.rename(pic_path)
    except Exception as e:
        logger.error(f"Failed to scrape profile metadata: {e}")

    # Fork Instagram purely to gallery-dl to avoid yt-dlp blockers
    if platform.lower() == "instagram":
        _download_instagram_gallery_dl(url, username, base_path, profile_root, db_id, progress_callback)
        return

    # Handle Videos
    if "entries" not in info and entries:
        info["entries"] = entries
    entries = info.get("entries", [])
    if not entries:
        if progress_callback: progress_callback("No videos found or unable to fetch playlist.", 100)
        return
        
    videos_db = db.get_all_videos_for_download(db_id)
    known_ids = set()
    videos_root = profile_root / "videos"
    for v in videos_db:
        # Check if the physical file actually exists before skipping
        filename = v.get("filename")
        if filename:
            file_exists = False
            for root in [videos_root, videos_root / "shorts"]:
                for sub_folder in ["<1k", "1k-10k", "10k-100k", "100k-1m", ">1m", "0-100k", "Under 1k", "Over 1m"]:
                    if (root / sub_folder / filename).exists():
                        file_exists = True
                        break
                if file_exists:
                    break
            if file_exists:
                known_ids.add(v["video_id"])    
    to_download = [e for e in entries if e.get("id") not in known_ids or e.get("id") is None]
    total = len(to_download)
    if progress_callback: progress_callback("Extraction complete, preparing downloads...", 10, total=total)
    
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    completed = 0
    ui_lock = threading.Lock()

    def process_entry(entry):
        nonlocal completed
        vid_id = entry.get("id")
        vid_url = entry.get("url")
        if not vid_url and vid_id:
            if platform.lower() == "youtube":
                vid_url = f"https://www.youtube.com/watch?v={vid_id}"
            elif platform.lower() == "tiktok":
                vid_url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
            else:
                vid_url = url
            
        vid_title = sanitize_filename(entry.get("title", f"video_{vid_id}"))
            
        try:
            videos_root = profile_root / "videos"
            videos_root.mkdir(parents=True, exist_ok=True)
            
            # Use random temp dir instead of visible processing folder
            tmp_uuid = str(uuid.uuid4())
            temp_videos_root = Path(tempfile.gettempdir()) / "ProfilePull" / tmp_uuid
            temp_videos_root.mkdir(parents=True, exist_ok=True)
            
            vid_info = download_video(vid_url, str(temp_videos_root))
            
            raw_vc = vid_info.get("view_count", 0)
            if isinstance(raw_vc, str):
                cleaned_vc = "".join(filter(str.isdigit, raw_vc))
                view_count = int(cleaned_vc) if cleaned_vc else 0
            else:
                view_count = int(raw_vc) if raw_vc is not None else 0
            
            downloaded_file = next(temp_videos_root.iterdir(), None)
            if downloaded_file:
                is_short = entry.get("is_short", False)
                vid_root = videos_root / "shorts" if is_short else videos_root
                
                target_folder = vid_root / get_view_folder(view_count)
                target_folder.mkdir(parents=True, exist_ok=True)
                final_path = target_folder / downloaded_file.name
                shutil.move(str(downloaded_file), str(final_path))
                
                db.add_video(
                    download_id=db_id,
                    video_id=vid_info.get("id", vid_id),
                    title=vid_info.get("title", vid_title),
                    filename=downloaded_file.name,
                    view_count=view_count,
                    view_folder=get_view_folder(view_count),
                    is_short=is_short
                )
            
            # Cleanup temp dir
            if temp_videos_root.exists():
                shutil.rmtree(str(temp_videos_root), ignore_errors=True)
                
        except Exception as e:
            logger.error(f"Failed to download video {vid_url}: {e}")
            
        with ui_lock:
            completed += 1
            if progress_callback:
                pct = int((completed / total) * 100)
                progress_callback(f"Downloading parallel batches ({completed} of {total} completed)...", pct)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_entry, entry) for entry in to_download]
        for f in as_completed(futures):
            f.result()
            
    if progress_callback: progress_callback("Re-sorting videos by view count...", 99)
    re_sort_all_videos(username, base_path)
    
    if progress_callback: progress_callback(f"Done. Downloaded {total} new videos.", 100)

def download_single_video(url: str, username: str, platform: str, base_path: str, progress_callback=None):
    videos_root = get_single_video_root(base_path)
    videos_root.mkdir(parents=True, exist_ok=True)
    
    uname = username if username and username != "unknown" else "Single Videos"
    db_url = url if uname != "Single Videos" else "Single Videos"
    db_id = db.get_or_create_download(uname, platform, db_url, str(videos_root))
    
    tmp_uuid = str(uuid.uuid4())
    temp_videos_root = Path(tempfile.gettempdir()) / "ProfilePull" / tmp_uuid
    temp_videos_root.mkdir(parents=True, exist_ok=True)
    
    if progress_callback: progress_callback("Downloading single video natively...", 10)
    try:
        vid_info = {"id": "single", "title": "video", "view_count": 0}
        
        if platform.lower() == "instagram":
            if progress_callback: progress_callback("Engaging gallery-dl Instagram bypass...", 20)
            import subprocess
            cookie_path = os.path.join(os.getcwd(), "cookies.txt")
            
            if not os.path.exists(cookie_path):
                raise Exception("cookies.txt not found! Instagram requires authentication. See README for setup instructions.")
            
            config = {
                "extractor": {
                    "instagram": {
                        "api": "rest",
                        "cookies": str(cookie_path),
                        "videos": True,
                        "filename": "{shortcode}.{extension}"
                    }
                }
            }
            config_file = temp_videos_root / "config.json"
            with open(config_file, "w") as f:
                json.dump(config, f)
            
            cmd = ["gallery-dl", "--config", str(config_file), "-d", str(temp_videos_root), url]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                err_text = result.stderr.strip()
                if "login" in err_text.lower() or "401" in err_text:
                    raise Exception("Your Instagram cookies.txt has expired! Please re-export a fresh cookies.txt from your browser. See README for instructions.")
                raise Exception(f"gallery-dl failed: {err_text}")
                
        else:
            if progress_callback: progress_callback("Using native yt-dlp core...", 20)
            
            def ydl_hook(d):
                if d['status'] == 'downloading':
                    try:
                        pct_str = d.get('_percent_str', '').strip()
                        if pct_str:
                            pct_val = float(pct_str.replace('%', ''))
                            scaled_pct = 20 + int((pct_val / 100.0) * 70)
                            if progress_callback: progress_callback(f"Downloading: {pct_str}", scaled_pct)
                    except:
                        pass
            
            vid_info = download_video(url, str(temp_videos_root), progress_hook=ydl_hook)
        
        raw_vc = vid_info.get("view_count", 0)
        if isinstance(raw_vc, str):
            cleaned_vc = "".join(filter(str.isdigit, raw_vc))
            view_count = int(cleaned_vc) if cleaned_vc else 0
        else:
            view_count = int(raw_vc) if raw_vc is not None else 0
        
        downloaded_file = None
        for root_dir, dirs, files in os.walk(str(temp_videos_root)):
            for f in files:
                if f.endswith(".mp4") or f.endswith(".webm"):
                    downloaded_file = Path(root_dir) / f
                    break
        
        if downloaded_file:
            target_folder = videos_root
            target_folder.mkdir(parents=True, exist_ok=True)
            final_path = target_folder / downloaded_file.name
            shutil.move(str(downloaded_file), str(final_path))
            
            db.add_video(
                download_id=db_id,
                video_id=vid_info.get("id", "single_video"),
                title=vid_info.get("title", downloaded_file.name),
                filename=downloaded_file.name,
                view_count=view_count,
                view_folder=""
            )
            
            if progress_callback: progress_callback(f"Done. Saved to {target_folder.name}/{downloaded_file.name}.", 100)
        else:
            raise Exception("No output file generated. The platform likely blocked the download request natively.")
            
        if temp_videos_root.exists():
            shutil.rmtree(str(temp_videos_root), ignore_errors=True)
    except Exception as e:
        logger.error(f"Failed to download single video {url}: {e}")
        if progress_callback: progress_callback(f"Download failed: {str(e)}", 0)
        raise e
