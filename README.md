# ProfilePull Web 🚀
**The Ultimate Cross-Platform Profile Archiver**  
*Built by Chukwuebuka Obi (@iamcobi)*

---

As an AI expert passionate about streamlining data acquisition, I engineered **ProfilePull** to circumvent the erratic limitations and data-silos of modern social media platforms. I vibe coded it to elegantly harvest profiles, bios, avatars, and asynchronous video metadata seamlessly across TikTok, YouTube, and Instagram — directly into a single, unified, premium local web dashboard.

## 🎯 Features
- **Cross-Platform Intelligence:** Automatically detects overlapping identities (e.g., if you archive an Instagram profile that you've previously downloaded via TikTok) and merges the databases intelligently.
- **Deep Metadata Extraction:** Bypasses `yt-dlp` scraping limits, utilizing custom native Python HTTP parsing to forcefully extract Open-Graph textual bios and high-resolution avatars that other scrapers miss.
- **State-of-the-Art Web GUI:** A completely responsive, hyper-minimalist Dark Mode web interface powered by a custom Flask REST server and native HTML Server-Sent Events (SSE).
- **Intelligent File Verification:** Native disk-probing dynamically checks if you've manually deleted archived videos across view-count directories, silently re-queuing them on the next pull.
- **Instant Windows Integration:** One-click directory unzipping natively hooks into your local `explorer.exe`.

## ⚙️ Requirements
> [!IMPORTANT]
> **This application is exclusively built for Windows Operating Systems.** It fundamentally relies on native Windows explorer sub-processing scripts.

- **OS:** Windows 10 or Windows 11
- **Python:** Version 3.10 or higher installed with PATH enabled.
- **FFmpeg:** Highly recommended for resolving `yt-dlp` media formats.

## 📥 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/iamcobi/ProfilePull.git
   cd ProfilePull
   ```
2. **Auto-Install:**
   Double-click the `install.bat` file. This automated script will generate your Python virtual environment and cleanly install all backend dependencies.

3. **Run the Server:**
   Double-click the `run.bat` file to boot up the Flask server, then easily open `http://127.0.0.1:5000` in any web browser!

---
*Connect with me on [LinkedIn](https://www.linkedin.com/in/chukwuebuka-obi-662504310/) or [GitHub](https://github.com/iamcobi).*
