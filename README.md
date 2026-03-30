# ProfilePull Web 🚀
**The Ultimate Social Media Downloading Software.**  
*Built by Chukwuebuka Obi (@iamcobi)*  
👉 [Got Feedback? Report an Issue or Suggest a Feature here!](https://github.com/iamcobi/ProfilePull/issues)

---

As an AI expert passionate about streamlining data acquisition, I engineered **ProfilePull** to circumvent the erratic limitations. I vibe coded it to elegantly harvest profiles, bios, avatars, and asynchronous video metadata seamlessly across TikTok, YouTube, and Instagram — directly into a single, unified, premium local web dashboard.

## 🌟 What's New in Version 2.0
- **Asynchronous Multi-Threading:** ProfilePull now spawns 5 parallel connection pipes dynamically boosting extraction speeds by 500%.
- **Infinite Concurrent Profiling:** The UI no longer locks you out! You can seamlessly paste and queue an unlimited amount of profiles simultaneously; they will all download smoothly in the background while dynamically generating individual progress tracking bars.
- **YouTube Shorts Segregation:** Intelligently splits YouTube streams, shifting Shorts into a bespoke `/shorts/` directory independently of Long-Form videos, while identically retaining exact View-Count sorting.
- **Universal Re-Pull Deduplication:** Hardened SQLite databases now mathematically skip existing Instagram/TikTok identifiers natively blocking network API duplicates completely.
- **Single Video Isolation:** Drops explicit single `.mp4` payloads straight into the root `videos/` folder cleanly ignoring bulk profile logic.

## 🎯 Features
- **Cross-Platform Intelligence:** Automatically detects overlapping identities and merges Instagram/TikTok databases intelligently.
- **Deep Metadata Extraction:** Bypasses extraction limits, utilizing custom native HTTP parsing to forcefully extract text bios and high-res avatars.
- **State-of-the-Art Web GUI:** A completely responsive, hyper-minimalist Dark Mode web interface powered by a custom Flask server.
- **Intelligent File Verification:** Native disk-probing dynamically checks if you've manually deleted archived videos, silently re-queuing them on the next pull.

## ⚙️ Requirements
- **OS:** Windows (10/11), macOS, or Linux.
- **Python:** Version 3.10 or higher installed with PATH enabled.
- **FFmpeg:** Highly recommended for resolving `yt-dlp` media formats.

## 📥 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamcobi/ProfilePull.git
   cd ProfilePull
   ```

2. **Auto-Install Dependencies:**
   - **On Windows:** Double-click the `install.bat` file to automatically build your virtual environment.
   - **On Linux/macOS:** Run `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` inside the folder directory. 

3. **Instagram Authentication Setup (CRITICAL STEP):**
   To successfully scrape massive Instagram profiles without Meta instantly IP blocking you, you **must** export your logged-in Instagram session into a `cookies.txt` file and place it in the root `ProfilePull` folder.
   
   **How to get your `cookies.txt` file in 30 seconds:**
   1. Open Google Chrome, Firefox, or Edge.
   2. Install the free [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) browser extension.
   3. Go to [Instagram.com](https://www.instagram.com/) and ensure you are logged in to any account (a burner account is highly recommended).
   4. Click the extension icon in your browser toolbar and select **Export**.
   5. Move the downloaded `cookies.txt` file exactly into the root folder of this repository (right next to `app.py`).

4. **Run the Server:**
   - **On Windows:** Double-click `run.bat`!
   - **On Linux/macOS:** Run `python3 app.py`.
   - Finally, open `http://127.0.0.1:5000` locally in any modern web browser to access your dashboard!

---
*Connect with me on [LinkedIn](https://www.linkedin.com/in/chukwuebuka-obi-662504310/) or [GitHub](https://github.com/iamcobi).*
