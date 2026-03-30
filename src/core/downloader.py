import os
import sys
import yt_dlp
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def get_ffmpeg_location():
    # Priority 1: PyInstaller frozen bundle
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    
    # Priority 2: imageio-ffmpeg pip package (bundles a static ffmpeg binary)
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            return os.path.dirname(ffmpeg_path)
    except ImportError:
        pass
    
    return None

def extract_with_fallbacks(url: str, download: bool, base_opts: dict) -> dict:
    browsers = []
    
    # Priority 1: Direct Cookie injection (bypasses all Windows DPAPI and SQLite locking)
    cookie_path = os.path.join(os.getcwd(), "cookies.txt")
    if os.path.exists(cookie_path):
        browsers.append(f"cookiefile:{cookie_path}")
        
    # Priority 2: Fallback to Chromium variants natively
    browsers.extend(['edge', 'chrome', 'firefox', None])
    
    last_error = None
    
    for browser in browsers:
        opts = dict(base_opts)
        
        if browser and str(browser).startswith("cookiefile:"):
            opts['cookiefile'] = str(browser).split("cookiefile:")[1]
        elif browser:
            opts['cookiesfrombrowser'] = (browser,)
            
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=download)
        except Exception as e:
            last_error = e
            logger.warning(f"[yt-dlp] Fallback iteration {browser} failed: {str(e)}")
            
    # If all fail, throw the final exception to bubble up
    raise last_error

def get_video_info(url: str, extract_flat: bool = False) -> dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': extract_flat
    }
    return extract_with_fallbacks(url, download=False, base_opts=ydl_opts)

def download_video(url: str, output_path: str, quality_format: str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', progress_hook: Optional[Callable] = None) -> dict:
    ydl_opts = {
        'format': quality_format,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'outtmpl': os.path.join(output_path, '%(title)s_%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True
    }
    
    ffmpeg_loc = get_ffmpeg_location()
    if ffmpeg_loc:
        ydl_opts['ffmpeg_location'] = ffmpeg_loc

    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]

    return extract_with_fallbacks(url, download=True, base_opts=ydl_opts)
