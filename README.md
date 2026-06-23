<div align="center">

# 🎬 BlueFalcon MKV Batch Muxer

**A robust, easy-to-use desktop application to batch multiplex MKV files.**

![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@BlueFalcon2270)

<br />
</div>

A high-performance Windows tool designed to automate the merging of MKV video files with their corresponding external audio (MKA) and subtitle (SRT, ASS, VTT) tracks. Built with a modern dual-panel dashboard, it allows you to process entire folders of episodes or movies at once, while giving you granular control over exactly which audio and subtitle tracks are kept.

<br>

## 📥 Getting Started (Installation)

This application is ready to use right out of the box—no coding or complex setup required!

### Step 1: Install MKVToolNix (Required)
This application acts as a smart dashboard, but it relies on the industry-standard MKVToolNix engine to do the actual video processing.
1. Download and install **[MKVToolNix for Windows](https://mkvtoolnix.download/downloads.html#windows)**.
2. Install it using the default settings.

### Step 2: Download BlueFalcon MKV Muxer
1. Go to the **[Releases page](../../releases)** on this repository.
2. Download the latest `BlueFalcon MKV Muxer v2.0.exe` file.
3. Place this `.exe` file directly into the folder containing the `.mkv` videos and audio/subtitle tracks you want to merge.

<br>

## 🚀 How to Use

1. **Run the App:** Double-click the `.exe` file inside your media folder. It will instantly scan the folder and load all matching video, audio, and subtitle files into the dashboard.
2. **Verify Engine Path:** Ensure the `mkvmerge.exe` path at the top left is correct (it defaults to the standard `C:\Program Files\MKVToolNix\mkvmerge.exe`).
3. **Select Your Groups:** On the **left panel**, check the boxes next to the media groups (episodes/movies) you want to process.
4. **Fine-Tune Tracks:** Click on any group on the left. On the **right panel**, you can uncheck specific audio or subtitle files if you want to leave them out of the final video.
5. **Set Output:** Choose where you want the finished files to go (defaults to a safe `output` folder inside your current directory so your original files are never overwritten).
6. **Mux!** Click **Run Batch Muxer** and watch the live terminal at the bottom as it processes your entire queue automatically.

<br>

## 🌟 Key Features

* **Master-Detail Dashboard:** A clean, modern split-screen interface. Navigate your media queue on the left, and view the exact track list for the selected video on the right.
* **Granular Track Selection:** You aren't forced to merge everything. Easily uncheck extra foreign audio tracks or unwanted subtitles on a per-episode basis.
* **Smart Memory:** The app remembers your individual track selections as you click back and forth between different media groups.
* **Auto-Scanning:** Instantly detects matching media files based on their base filenames (e.g., `Video01.mkv` will automatically pair with `Video01.mka`).
* **Live Embedded Terminal:** Watch the multiplexing progress and success/error logs directly inside the app. No annoying popup command prompt windows!

<br>

---
**Created by BlueFalcon.** Subscribe to the [YouTube Channel](https://www.youtube.com/@BlueFalcon2270) to learn how to build advanced GUI applications and master your development workflow!