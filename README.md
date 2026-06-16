<div align="center">

# 🎬 BlueFalcon MKV Batch Muxer

**A modern, fast, and elegant way to batch multiplex MKV files.**

![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
[![Language](https://img.shields.io/badge/Written%20in-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@BlueFalcon2270)

<br />
</div>

A lightweight, interactive Python desktop GUI application built to effortlessly automate the merging of MKV video files with their corresponding external audio (MKA) and subtitle (SRT, ASS, VTT) tracks. This utility provides a beautiful dark-mode interface to safely manage your video processing queue without touching the command line.
<br><br>

## ⚡ Quick Run
To run this application on your local machine, clone the repository and execute the script. Make sure you have [MKVToolNix](https://mkvtoolnix.download/) installed first.

```bash
git clone [https://github.com/bluefalcon2270/bluefalcon-mkv-batch-muxer.git](https://github.com/bluefalcon2270/bluefalcon-mkv-batch-muxer.git)
cd bluefalcon-mkv-batch-muxer
pip install customtkinter
python main.py
```

<br>

## 🌟 Features
This application replaces the need to remember complex `mkvmerge` command line arguments by providing a clean, graphical dashboard:

### 1️⃣ Automated Smart Matching
* **Filename Detection:** Automatically scans your chosen directory and groups base video files with any audio or subtitle files sharing the exact same prefix.
* **Safe Output:** Generates all final multiplexed files into an isolated `output` folder, guaranteeing your original source media is never overwritten or corrupted.

### 2️⃣ Seamless Processing
* **Background Threading:** Keeps the user interface responsive and fluid while heavy file processing occurs in the background.
* **Live Activity Log:** Displays real-time CLI outputs natively in the dashboard, notifying you instantly of `[PROCESSING]`, `[SUCCESS]`, or `[SKIPPED]` file statuses.

### 3️⃣ Modern UI/UX
* **CustomTkinter Engine:** Built entirely on `customtkinter` for a polished, modern, and dark-themed interface that natively matches Windows 11 aesthetics.
* **Dynamic Pathing:** Includes intuitive folder and executable browsing dialogs, saving you from manually typing out complex file paths.

<br><br>

## ✅ Supported Systems
| Operating System | Compatibility |
| :--- | :---: |
| **Windows 10** | ✅ |
| **Windows 11** | ✅ |

*(Note: Linux and macOS are not natively supported as the application relies on Windows-specific `subprocess` process creation flags and MKVToolNix installation paths).*

<br><br>

---
**Watch the Tutorials:** Subscribe to the [YouTube Channel](https://www.youtube.com/@BlueFalcon2270) to learn how to build applications like this from scratch and master server infrastructure!