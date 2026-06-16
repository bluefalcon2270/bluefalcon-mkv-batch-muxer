# ==========================================
# BlueFalcon MKV Batch Muxer
# Version: v1.0
# Author: BlueFalcon
# ==========================================

import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog

# Set up modern dark theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MKVMuxerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("BlueFalcon MKV Batch Muxer v1.0")
        self.geometry("650x500")
        
        # Configuration Variables
        self.mkvmerge_path = ctk.StringVar(value=r"C:\Program Files\MKVToolNix\mkvmerge.exe")
        self.source_dir = ctk.StringVar(value="")
        
        # --- UI LAYOUT ---
        # 1. MKVToolNix Path Selection
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.pack(pady=10, padx=20, fill="x")
        
        self.lbl_path = ctk.CTkLabel(self.path_frame, text="mkvmerge.exe Path:")
        self.lbl_path.pack(side="left", padx=10, pady=10)
        
        self.entry_path = ctk.CTkEntry(self.path_frame, textvariable=self.mkvmerge_path, width=350)
        self.entry_path.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_browse_exe = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self.browse_mkvmerge)
        self.btn_browse_exe.pack(side="right", padx=10)

        # 2. Source Directory Selection
        self.dir_frame = ctk.CTkFrame(self)
        self.dir_frame.pack(pady=10, padx=20, fill="x")
        
        self.lbl_dir = ctk.CTkLabel(self.dir_frame, text="Working Directory:")
        self.lbl_dir.pack(side="left", padx=10, pady=10)
        
        self.entry_dir = ctk.CTkEntry(self.dir_frame, textvariable=self.source_dir, width=350, placeholder_text="Select folder containing MKV files...")
        self.entry_dir.pack(side="left", padx=5, expand=True, fill="x")
        
        self.btn_browse_dir = ctk.CTkButton(self.dir_frame, text="Browse", width=80, command=self.browse_directory)
        self.btn_browse_dir.pack(side="right", padx=10)

        # 3. Log Output Window
        self.log_text = ctk.CTkTextbox(self, height=220, activate_scrollbars=True)
        self.log_text.pack(pady=10, padx=20, fill="both", expand=True)
        self.log_text.insert("0.0", "System ready. Select a working directory containing your MKV, MKA, and subtitle files.\n\n")
        self.log_text.configure(state="disabled")

        # 4. Action Button
        self.btn_start = ctk.CTkButton(self, text="Start Batch Merge", command=self.start_processing_thread, height=40, font=("Arial", 14, "bold"))
        self.btn_start.pack(pady=15, padx=20, fill="x")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def browse_mkvmerge(self):
        file_path = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe")])
        if file_path:
            self.mkvmerge_path.set(file_path)

    def browse_directory(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.source_dir.set(folder_path)
            self.log(f"[INFO] Working directory changed to: {folder_path}")

    def start_processing_thread(self):
        # Run processing in a background thread so the GUI doesn't freeze
        threading.Thread(target=self.process_files, daemon=True).start()

    def process_files(self):
        mkvmerge = self.mkvmerge_path.get()
        working_dir = self.source_dir.get()

        if not os.path.exists(mkvmerge):
            self.log(f"[ERROR] mkvmerge.exe not found at '{mkvmerge}'")
            return
        
        if not working_dir or not os.path.exists(working_dir):
            self.log("[ERROR] Please select a valid working directory first.")
            return

        self.btn_start.configure(state="disabled")
        output_dir = os.path.join(working_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        files = os.listdir(working_dir)
        mkv_files = [f for f in files if f.lower().endswith('.mkv')]

        if not mkv_files:
            self.log("[INFO] No .mkv files found in the chosen directory.")
            self.btn_start.configure(state="normal")
            return

        for filename in mkv_files:
            basename = os.path.splitext(filename)[0]
            video_path = os.path.join(working_dir, filename)
            
            extra_args = []
            
            # Look for matching audio
            for f in files:
                if f.lower().startswith(basename.lower()) and f.lower().endswith('.mka') and f != filename:
                    extra_args.append(os.path.join(working_dir, f))
                    
            # Look for matching subtitles
            sub_extensions = ('.srt', '.ass', '.ssa', '.vtt', '.sup')
            for f in files:
                if f.lower().startswith(basename.lower()) and f.lower().endswith(sub_extensions):
                    extra_args.append(os.path.join(working_dir, f))

            if extra_args:
                self.log(f"[PROCESSING] {filename}")
                out_file = os.path.join(output_dir, filename)
                
                # Formulate the mkvmerge command array
                cmd = [mkvmerge, "-o", out_file, video_path] + extra_args
                
                try:
                    # Run hidden in background
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    if result.returncode == 0 or result.returncode == 1: # 1 is usually a warning, still success
                        self.log(f"[SUCCESS] Merged into output\\{filename}")
                    else:
                        self.log(f"[ERROR] Failed merging {filename}. Code: {result.returncode}")
                except Exception as e:
                    self.log(f"[CRITICAL] Error: {str(e)}")
            else:
                self.log(f"[SKIPPED] {filename} (No matching attachments found)")

        self.log("\n[DONE] All tasks completed!")
        self.btn_start.configure(state="normal")

if __name__ == "__main__":
    app = MKVMuxerGUI()
    app.mainloop()