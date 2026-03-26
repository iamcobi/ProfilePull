import os
import re
import hashlib
from pathlib import Path

def get_view_folder(view_count: int) -> str:
    """Returns the folder name for a given view count."""
    if view_count < 1000:
        return "Under 1k"
    elif view_count < 10000:
        return "1k-10k"
    elif view_count < 100000:
        return "10k-100k"
    elif view_count < 1000000:
        return "100k-1m"
    else:
        return "Over 1m"

def sanitize_filename(name: str) -> str:
    if not name:
        return "video"
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def get_unique_filename(base_path: str, filename: str) -> str:
    """Given a full path, if file exists, appends _2, _3 etc to the stem."""
    p = Path(base_path) / filename
    if not p.exists():
        return filename
    
    stem = p.stem
    ext = p.suffix
    counter = 2
    while (Path(base_path) / f"{stem}_{counter}{ext}").exists():
        counter += 1
    return f"{stem}_{counter}{ext}"

def compute_md5(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
