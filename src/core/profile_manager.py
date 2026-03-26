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
        correct_folder_name = get_view_folder(view_count)
        correct_folder_path = videos_root / correct_folder_name
        correct_folder_path.mkdir(parents=True, exist_ok=True)
        
        # File's database path or filename
        filename = video.get("filename")
        if not filename:
            continue

        # We need to find where the file currently is by scanning all view folders
        current_file_path = None
        for sub_folder in ["<1k", "1k-10k", "10k-100k", "100k-1m", ">1m"]:
            possible_path = videos_root / sub_folder / filename
            if possible_path.exists():
                current_file_path = possible_path
                break

        if current_file_path:
            target_path = correct_folder_path / filename
            if current_file_path != target_path:
                logger.info(f"Moving {filename} from {current_file_path.parent.name} to {correct_folder_path.name}")
                shutil.move(str(current_file_path), str(target_path))
                # Update DB with new folder
                db.update_video_view_count(video["id"], view_count, correct_folder_name)

def download_profile(url: str, username: str, platform: str, base_path: str, progress_callback=None):
    profile_root = get_profile_root(base_path, username)
    profile_root.mkdir(parents=True, exist_ok=True)
    
    # Grab channel info
    if progress_callback: progress_callback("Fetching profile information...", 0)
    info = get_video_info(url, extract_flat=True)
    
    # Check DB
    db_id = db.get_or_create_download(username, platform, url, str(profile_root))
    
    # Handle Bio and Profile Picture using BeautifulSoup
    if progress_callback: progress_callback("Extracting Profile Metadata directly...", 5)
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Extract Bio
        desc_meta = soup.find("meta", property="og:description")
        bio_text = desc_meta.get("content", "").strip() if desc_meta else ""
        if not bio_text and "description" in info:
            bio_text = info.get("description", "")
            
        if bio_text:
            bio_path = profile_root / "bio.txt"
            target_bio = get_unique_filename(str(profile_root), "bio.txt")
            if not bio_path.exists():
                with open(profile_root / target_bio, "w", encoding="utf-8") as f:
                    f.write(bio_text)
                    
        # Extract Profile Picture
        img_meta = soup.find("meta", property="og:image")
        best_thumb = img_meta.get("content", "") if img_meta else ""
        if not best_thumb and info.get("thumbnails"):
            best_thumb = info["thumbnails"][-1]["url"]
            
        if best_thumb:
            pic_path = profile_root / "profile.jpg"
            temp_pic = profile_root / "temp_profile.jpg"
            img_r = requests.get(best_thumb, stream=True)
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

    # Handle Videos
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
            for sub_folder in ["<1k", "1k-10k", "10k-100k", "100k-1m", ">1m", "0-100k"]:
                if (videos_root / sub_folder / filename).exists():
                    file_exists = True
                    break
            if file_exists:
                known_ids.add(v["video_id"])    
    to_download = [e for e in entries if e.get("id") not in known_ids or e.get("id") is None]
    total = len(to_download)
    
    for i, entry in enumerate(to_download):
        vid_id = entry.get("id")
        vid_url = entry.get("url")
        if not vid_url and vid_id:
            vid_url = f"https://www.youtube.com/watch?v={vid_id}" if platform == "YouTube" else url
            
        vid_title = sanitize_filename(entry.get("title", f"video_{vid_id}"))
        
        if progress_callback:
            pct = int((i / total) * 100)
            progress_callback(f"Downloading video {i+1} of {total}: {vid_title}.mp4", pct)
            
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
                target_folder = videos_root / get_view_folder(view_count)
                target_folder.mkdir(parents=True, exist_ok=True)
                final_path = target_folder / downloaded_file.name
                shutil.move(str(downloaded_file), str(final_path))
                
                db.add_video(
                    download_id=db_id,
                    video_id=vid_info.get("id", vid_id),
                    title=vid_info.get("title", vid_title),
                    filename=downloaded_file.name,
                    view_count=view_count,
                    view_folder=get_view_folder(view_count)
                )
            
            # Cleanup temp dir
            if temp_videos_root.exists():
                shutil.rmtree(str(temp_videos_root), ignore_errors=True)
                
        except Exception as e:
            logger.error(f"Failed to download video {vid_url}: {e}")
            
    if progress_callback: progress_callback("Re-sorting videos by view count...", 99)
    re_sort_all_videos(username, base_path)
    
    if progress_callback: progress_callback(f"Done. Downloaded {total} new videos.", 100)

def download_single_video(url: str, base_path: str, progress_callback=None):
    videos_root = get_single_video_root(base_path)
    videos_root.mkdir(parents=True, exist_ok=True)
    
    tmp_uuid = str(uuid.uuid4())
    temp_videos_root = Path(tempfile.gettempdir()) / "ProfilePull" / tmp_uuid
    temp_videos_root.mkdir(parents=True, exist_ok=True)
    
    if progress_callback: progress_callback("Downloading single video...", 10)
    try:
        vid_info = download_video(url, str(temp_videos_root))
        
        raw_vc = vid_info.get("view_count", 0)
        if isinstance(raw_vc, str):
            cleaned_vc = "".join(filter(str.isdigit, raw_vc))
            view_count = int(cleaned_vc) if cleaned_vc else 0
        else:
            view_count = int(raw_vc) if raw_vc is not None else 0
        
        downloaded_file = next(temp_videos_root.iterdir(), None)
        if downloaded_file:
            target_folder = videos_root / get_view_folder(view_count)
            target_folder.mkdir(parents=True, exist_ok=True)
            final_path = target_folder / downloaded_file.name
            shutil.move(str(downloaded_file), str(final_path))
            if progress_callback: progress_callback(f"Done. Saved to {target_folder.name}/{downloaded_file.name}.", 100)
            
        if temp_videos_root.exists():
            shutil.rmtree(str(temp_videos_root), ignore_errors=True)
    except Exception as e:
        logger.error(f"Failed to download single video {url}: {e}")
        if progress_callback: progress_callback("Download failed.", 0)
