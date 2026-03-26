import os
import sys
import yt_dlp
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

def get_ffmpeg_location():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return None

def get_video_info(url: str, extract_flat: bool = False) -> dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': extract_flat  # True for fast playlist extraction
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def download_video(url: str, output_path: str, quality_format: str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', progress_hook: Optional[Callable] = None) -> dict:
    ydl_opts = {
        'format': quality_format,
        'merge_output_format': 'mp4',
        # Restrict filenames pattern to match sanitized naming
        'restrictfilenames': True,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    ffmpeg_loc = get_ffmpeg_location()
    if ffmpeg_loc:
        ydl_opts['ffmpeg_location'] = ffmpeg_loc

    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=True)
