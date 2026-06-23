# ==========================================
# Version: v2.1
# BlueFalcon MKV Batch Muxer
# ==========================================

import os
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QMessageBox, QGridLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, 
    QDialog, QStyle, QStyleOptionButton, QApplication, QFileDialog,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect, QThread
import sys
from PyQt6.QtGui import QIcon

# --- Helper for PyInstaller Paths ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller onefile """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Logging Setup ---
# Save log in the folder where the .exe actually is (not the temp folder)
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    
LOG_FILE = Path(application_path) / "bluefalcon-mkv-muxer.log"

class GUILogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

logger = logging.getLogger("BlueFalconMKV")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=2, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

gui_handler = GUILogHandler()
gui_handler.setFormatter(formatter)
logger.addHandler(gui_handler)

# --- Background Workers ---
class ScannerWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, target_dir: Path, output_dir_str: str):
        super().__init__()
        self.target_dir = target_dir
        self.output_dir_str = output_dir_str

    def run(self):
        try:
            data = {}
            if not self.target_dir.exists() or not self.target_dir.is_dir():
                self.finished.emit(data)
                return

            out_path = Path(self.output_dir_str) if self.output_dir_str else self.target_dir / "output"
            mkv_files = [f for f in self.target_dir.iterdir() if f.is_file() and f.suffix.lower() == '.mkv']
            
            for index, mkv in enumerate(mkv_files):
                basename = mkv.stem
                attachments = []
                
                for f in self.target_dir.iterdir():
                    if f.is_file() and f.name != mkv.name and f.name.lower().startswith(basename.lower()):
                        if f.suffix.lower() in ['.mka', '.srt', '.ass', '.ssa', '.vtt', '.sup']:
                            attachments.append(f)
                
                expected_out_file = out_path / mkv.name
                if expected_out_file.exists():
                    status = "Done"
                elif attachments:
                    status = "Ready"
                else:
                    status = "No Attachments"
                
                tracks = []
                tracks.append({
                    "name": mkv.name,
                    "path": str(mkv),
                    "type": "Source Video",
                    "icon": "🎬",
                    "active": True
                })
                
                for att in attachments:
                    ext = att.suffix.lower()
                    track_type = "Audio Track" if ext == '.mka' else "Subtitle Track"
                    icon = "🎵" if ext == '.mka' else "📝"
                    tracks.append({
                        "name": att.name,
                        "path": str(att),
                        "type": track_type,
                        "icon": icon,
                        "active": True
                    })

                data[index] = {
                    "basename": basename,
                    "status": status,
                    "active": True if status == "Ready" else False,
                    "has_attachments": bool(attachments),
                    "tracks": tracks
                }
                
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class ActionWorker(QThread):
    log_msg = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, mkvmerge_path: str, target_dir: Path, output_dir_str: str, tasks: list):
        super().__init__()
        self.mkvmerge_path = mkvmerge_path
        self.target_dir = target_dir
        self.output_dir_str = output_dir_str
        self.tasks = tasks

    def run(self):
        try:
            if not os.path.exists(self.mkvmerge_path):
                self.log_msg.emit(f"[ERROR] mkvmerge.exe not found at '{self.mkvmerge_path}'")
                self.finished.emit()
                return

            output_dir = Path(self.output_dir_str) if self.output_dir_str else self.target_dir / "output"
            output_dir.mkdir(exist_ok=True, parents=True)
            self.log_msg.emit(f"[INFO] Output directory ready at: {output_dir}")
            self.log_msg.emit("=" * 50)

            for task in self.tasks:
                video_track = next((t for t in task["tracks"] if t["type"] == "Source Video"), None)
                att_tracks = [t for t in task["tracks"] if t["type"] != "Source Video"]
                
                if not video_track:
                    self.log_msg.emit(f"[ERROR] {task['basename']} - Source Video missing.")
                    continue

                out_file = output_dir / video_track["name"]
                cmd = [self.mkvmerge_path, "-o", str(out_file), video_track["path"]]
                cmd.extend([t["path"] for t in att_tracks])

                self.log_msg.emit(f"[PROCESSING] {task['basename']}")
                
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if result.returncode == 0 or result.returncode == 1:
                    self.log_msg.emit(f"[SUCCESS] Merged Output: {video_track['name']}")
                else:
                    self.log_msg.emit(f"[ERROR] Failed merging {task['basename']}. Code: {result.returncode}")
                
                self.log_msg.emit("-" * 50)

            self.log_msg.emit("[DONE] All batch tasks completed.")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# --- UI Components ---
class CheckBoxHeader(QHeaderView):
    stateChanged = pyqtSignal(Qt.CheckState)

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._is_on = True

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(rect.x() + 4, rect.y() + rect.height() // 2 - 9, 18, 18)
            option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active
            if self._is_on:
                option.state |= QStyle.StateFlag.State_On
            else:
                option.state |= QStyle.StateFlag.State_Off
            self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        logicalIndex = self.logicalIndexAt(event.pos())
        if logicalIndex == 0:
            self._is_on = not self._is_on
            state = Qt.CheckState.Checked if self._is_on else Qt.CheckState.Unchecked
            self.stateChanged.emit(state)
            self.viewport().update()
        super().mousePressEvent(event)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(350, 200)
        self.setStyleSheet("""
            QDialog { background-color: #2B2D31; color: white; border-radius: 8px; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #A8C7FA; border: none; padding: 6px 12px; border-radius: 4px; color: #062E6F; font-family: 'Segoe UI', Arial, sans-serif; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #D3E3FD; }
            a { color: #A8C7FA; text-decoration: none; }
            a:hover { text-decoration: underline; }
        """)
        
        layout = QVBoxLayout(self)
        title = QLabel(
            "<b>BlueFalcon MKV Batch Muxer</b><br>v2.1<br><br>"
            "Created by BlueFalcon<br><br>"
            "<a href='https://github.com/bluefalcon2270/bluefalcon-mkv-batch-muxer'>GitHub Repository</a>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setOpenExternalLinks(True)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        
        layout.addWidget(title)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BlueFalcon MKV Batch Muxer v2.1")
        self.setMinimumSize(1200, 750)
        
        # Correctly load the bundled icon at runtime
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.target_directory = Path(application_path)
        self.scanner_worker = None
        self.action_worker = None
        
        self.data_state = {}
        self.current_selected_task_id = None

        self._apply_dark_theme()
        self._init_ui()
        
        logger.info(f"System initialized. Current working directory: {self.target_directory}")
        self._refresh_data()

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1F22; }
            QWidget { color: #E3E3E3; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QLineEdit { background-color: #2B2D31; border: 1px solid #44474A; padding: 0px 10px; border-radius: 6px; color: #FFFFFF; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #A8C7FA; }
            QPushButton { background-color: #A8C7FA; border: none; border-radius: 6px; color: #062E6F; font-family: 'Segoe UI', Arial, sans-serif; font-weight: bold; font-size: 14px; padding: 4px; }
            QPushButton:hover { background-color: #D3E3FD; }
            QPushButton:disabled { background-color: #44474A; color: #8E918F; }
            QPushButton#overlay_btn { background-color: #2B2D31; border: 1px solid #44474A; border-radius: 6px; font-size: 16px; font-weight: bold; color: #A8C7FA; padding: 0px; }
            QPushButton#overlay_btn:hover { background-color: #383A40; color: #D3E3FD; }
            QTextEdit { background-color: #1E1F22; border: 1px solid #44474A; color: #A0A0A0; padding: 10px; border-radius: 6px; font-family: Consolas, monospace; font-size: 13px; }
            QTableWidget { background-color: #1E1F22; border: 1px solid #44474A; border-radius: 6px; color: #E3E3E3; gridline-color: transparent; outline: none; }
            QHeaderView::section { background-color: #1E1F22; color: #A8C7FA; padding: 8px; border: none; border-bottom: 1px solid #44474A; font-weight: bold; font-size: 13px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #2B2D31; }
            QTableWidget::item:selected { background-color: #35383D; color: #FFFFFF; }
            QSplitter::handle { background-color: #44474A; width: 2px; }
            QLabel#panel_title { font-weight: bold; font-size: 14px; color: #E3E3E3; margin-bottom: 5px; }
        """)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Top Action Bar ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        lbl_exe_path = QLabel("mkvmerge.exe:")
        lbl_exe_path.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_bar.addWidget(lbl_exe_path)

        self.entry_exe_path = QLineEdit()
        self.entry_exe_path.setText(r"C:\Program Files\MKVToolNix\mkvmerge.exe")
        self.entry_exe_path.setFixedSize(250, 36)
        top_bar.addWidget(self.entry_exe_path)

        btn_browse_exe = QPushButton("Browse")
        btn_browse_exe.setFixedSize(80, 36)
        btn_browse_exe.clicked.connect(self._browse_exe)
        top_bar.addWidget(btn_browse_exe)
        
        top_bar.addSpacing(20)

        lbl_out_path = QLabel("Output:")
        lbl_out_path.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_bar.addWidget(lbl_out_path)

        self.entry_out_path = QLineEdit()
        self.entry_out_path.setPlaceholderText("Default: ./output")
        self.entry_out_path.setFixedSize(250, 36)
        top_bar.addWidget(self.entry_out_path)

        btn_browse_out = QPushButton("Browse")
        btn_browse_out.setFixedSize(80, 36)
        btn_browse_out.clicked.connect(self._browse_output)
        top_bar.addWidget(btn_browse_out)

        top_bar.addStretch()

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("overlay_btn")
        self.btn_refresh.setFixedSize(36, 36)
        self.btn_refresh.setToolTip("Refresh Directory")
        self.btn_refresh.clicked.connect(self._refresh_data)
        top_bar.addWidget(self.btn_refresh)

        self.btn_run = QPushButton("Run Batch Muxer")
        self.btn_run.setFixedSize(160, 36)
        self.btn_run.clicked.connect(self._start_muxing)
        top_bar.addWidget(self.btn_run)

        btn_about = QPushButton("ⓘ")
        btn_about.setObjectName("overlay_btn")
        btn_about.setFixedSize(36, 36)
        btn_about.clicked.connect(self._show_about)
        top_bar.addWidget(btn_about)

        main_layout.addLayout(top_bar)

        # --- Master-Detail Splitter ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Left Panel (Master)
        left_panel = QWidget()
        left_panel.setMinimumWidth(300) 
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_master = QLabel("Media Groups")
        lbl_master.setObjectName("panel_title")
        left_layout.addWidget(lbl_master)

        self.table_master = QTableWidget()
        self.table_master.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_master.setColumnCount(3)
        
        self.header_master = CheckBoxHeader(Qt.Orientation.Horizontal)
        self.header_master.stateChanged.connect(self._master_header_toggled)
        self.table_master.setHorizontalHeader(self.header_master)
        self.table_master.setHorizontalHeaderLabels(["", "Media Group", "Status"])
        
        self.table_master.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.table_master.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_master.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_master.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_master.verticalHeader().setVisible(False)
        
        h_master = self.table_master.horizontalHeader()
        h_master.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_master.setColumnWidth(0, 30)
        h_master.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h_master.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_master.setColumnWidth(2, 80)
        
        self.table_master.itemSelectionChanged.connect(self._on_master_selection)
        self.table_master.itemChanged.connect(self._on_master_item_changed)
        
        left_layout.addWidget(self.table_master)
        
        # 2. Right Panel (Detail)
        right_panel = QWidget()
        right_panel.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_detail = QLabel("Tracks (Files to Mux)")
        lbl_detail.setObjectName("panel_title")
        right_layout.addWidget(lbl_detail)

        self.table_detail = QTableWidget()
        self.table_detail.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table_detail.setColumnCount(3)
        
        self.header_detail = CheckBoxHeader(Qt.Orientation.Horizontal)
        self.header_detail.stateChanged.connect(self._detail_header_toggled)
        self.table_detail.setHorizontalHeader(self.header_detail)
        self.table_detail.setHorizontalHeaderLabels(["", "Track File Name", "Type"])
        
        self.table_detail.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.table_detail.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_detail.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_detail.verticalHeader().setVisible(False)
        
        h_detail = self.table_detail.horizontalHeader()
        h_detail.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_detail.setColumnWidth(0, 30)
        h_detail.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h_detail.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_detail.setColumnWidth(2, 120)
        
        self.table_detail.itemChanged.connect(self._on_detail_item_changed)

        right_layout.addWidget(self.table_detail)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([450, 700]) 
        
        main_layout.addWidget(self.splitter, stretch=2)

        # --- Log Viewer ---
        log_container = QWidget()
        log_layout = QGridLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        log_layout.addWidget(self.log_viewer, 0, 0)

        clear_wrapper = QWidget()
        clear_box = QVBoxLayout(clear_wrapper)
        clear_box.setContentsMargins(0, 8, 8, 0)
        
        self.btn_clear_log = QPushButton("✕")
        self.btn_clear_log.setObjectName("overlay_btn")
        self.btn_clear_log.setFixedSize(30, 30)
        self.btn_clear_log.setToolTip("Clear Terminal Log")
        self.btn_clear_log.clicked.connect(self.log_viewer.clear)
        clear_box.addWidget(self.btn_clear_log)

        log_layout.addWidget(clear_wrapper, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(log_container, stretch=1)
        
        gui_handler.log_signal.connect(self.log_viewer.append)

    def _browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select mkvmerge.exe", "", "Executable Files (*.exe)")
        if file_path:
            self.entry_exe_path.setText(file_path)
            
    def _browse_output(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder_path:
            self.entry_out_path.setText(folder_path)

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    # --- Data State Management ---
    def _refresh_data(self):
        self.table_master.blockSignals(True)
        self.table_detail.blockSignals(True)
        self.table_master.setRowCount(0)
        self.table_detail.setRowCount(0)
        self.data_state.clear()
        self.current_selected_task_id = None
        self.table_master.blockSignals(False)
        self.table_detail.blockSignals(False)
        
        out_str = self.entry_out_path.text().strip()
        self.scanner_worker = ScannerWorker(self.target_directory, out_str)
        self.scanner_worker.finished.connect(self._on_scan_finished)
        self.scanner_worker.error.connect(lambda e: logger.error(f"Scan Error: {e}"))
        self.scanner_worker.start()

    def _on_scan_finished(self, data: dict):
        self.data_state = data
        self.table_master.blockSignals(True)
        self.table_master.setRowCount(len(self.data_state))
        
        for row, (task_id, info) in enumerate(self.data_state.items()):
            # Checkbox
            chk = QTableWidgetItem()
            if info["has_attachments"]:
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                chk.setCheckState(Qt.CheckState.Checked if info["active"] else Qt.CheckState.Unchecked)
            else:
                chk.setFlags(Qt.ItemFlag.ItemIsSelectable)
            chk.setData(Qt.ItemDataRole.UserRole, task_id)
            self.table_master.setItem(row, 0, chk)
            
            # Name
            name_item = QTableWidgetItem(f"📁 {info['basename']}")
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            font = name_item.font()
            font.setBold(True)
            name_item.setFont(font)
            self.table_master.setItem(row, 1, name_item)
            
            # Status
            status_item = QTableWidgetItem(info["status"])
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_master.setItem(row, 2, status_item)

        self.table_master.blockSignals(False)
        
        if self.table_master.rowCount() > 0:
            self.table_master.selectRow(0)

    # --- Master Logic ---
    def _master_header_toggled(self, state: Qt.CheckState):
        self.table_master.blockSignals(True)
        for row in range(self.table_master.rowCount()):
            item = self.table_master.item(row, 0)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(state)
                task_id = item.data(Qt.ItemDataRole.UserRole)
                self.data_state[task_id]["active"] = (state == Qt.CheckState.Checked)
        self.table_master.blockSignals(False)

    def _on_master_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            task_id = item.data(Qt.ItemDataRole.UserRole)
            is_checked = (item.checkState() == Qt.CheckState.Checked)
            self.data_state[task_id]["active"] = is_checked

    def _on_master_selection(self):
        selected_items = self.table_master.selectedItems()
        if not selected_items:
            self.current_selected_task_id = None
            self.table_detail.setRowCount(0)
            return

        row = selected_items[0].row()
        task_id = self.table_master.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.current_selected_task_id = task_id
        self._populate_details(task_id)

    # --- Detail Logic ---
    def _populate_details(self, task_id: int):
        self.table_detail.blockSignals(True)
        info = self.data_state[task_id]
        tracks = info["tracks"]
        
        self.table_detail.setRowCount(len(tracks))
        
        all_checked = True
        none_checked = True
        
        for row, track in enumerate(tracks):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk.setCheckState(Qt.CheckState.Checked if track["active"] else Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, row)
            self.table_detail.setItem(row, 0, chk)
            
            if track["active"]: none_checked = False
            else: all_checked = False
            
            name_item = QTableWidgetItem(f"{track['icon']} {track['name']}")
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_detail.setItem(row, 1, name_item)
            
            type_item = QTableWidgetItem(track["type"])
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_detail.setItem(row, 2, type_item)
            
        self.header_detail.blockSignals(True)
        if all_checked and len(tracks) > 0: self.header_detail._is_on = True
        elif none_checked: self.header_detail._is_on = False
        self.header_detail.viewport().update()
        self.header_detail.blockSignals(False)
        
        self.table_detail.blockSignals(False)

    def _detail_header_toggled(self, state: Qt.CheckState):
        if self.current_selected_task_id is None: return
        self.table_detail.blockSignals(True)
        
        is_checked = (state == Qt.CheckState.Checked)
        
        for row in range(self.table_detail.rowCount()):
            item = self.table_detail.item(row, 0)
            item.setCheckState(state)
            
            track_idx = item.data(Qt.ItemDataRole.UserRole)
            self.data_state[self.current_selected_task_id]["tracks"][track_idx]["active"] = is_checked
            
        self.table_detail.blockSignals(False)

    def _on_detail_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0 and self.current_selected_task_id is not None:
            track_idx = item.data(Qt.ItemDataRole.UserRole)
            is_checked = (item.checkState() == Qt.CheckState.Checked)
            self.data_state[self.current_selected_task_id]["tracks"][track_idx]["active"] = is_checked

    # --- Processing ---
    def _start_muxing(self):
        tasks_to_run = []
        
        for task_id, info in self.data_state.items():
            if info["active"]:
                active_tracks = [t for t in info["tracks"] if t["active"]]
                video_track = next((t for t in active_tracks if t["type"] == "Source Video"), None)
                
                if video_track and len(active_tracks) > 1:
                    tasks_to_run.append({
                        "basename": info["basename"],
                        "has_attachments": True,
                        "tracks": active_tracks
                    })

        if not tasks_to_run:
            QMessageBox.information(self, "No Selection", "No valid groups selected. Ensure at least one group is checked, and its Source Video plus at least one attachment is active.")
            return

        exe_path = self.entry_exe_path.text().strip()
        out_str = self.entry_out_path.text().strip()
        
        self.table_master.setEnabled(False)
        self.table_detail.setEnabled(False)
        self.btn_run.setEnabled(False)
        
        self.action_worker = ActionWorker(exe_path, self.target_directory, out_str, tasks_to_run)
        self.action_worker.log_msg.connect(logger.info)
        self.action_worker.error.connect(self._on_worker_error)
        self.action_worker.finished.connect(self._on_worker_finished)
        self.action_worker.start()

    def _on_worker_error(self, e: str):
        logger.error(f"Action Error: {e}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{e}")

    def _on_worker_finished(self):
        self.table_master.setEnabled(True)
        self.table_detail.setEnabled(True)
        self.btn_run.setEnabled(True)
        self.action_worker = None
        self._refresh_data()

    def closeEvent(self, event):
        if self.action_worker and self.action_worker.isRunning():
            self.action_worker.wait()
        if self.scanner_worker and self.scanner_worker.isRunning():
            self.scanner_worker.wait()
            
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
            
        event.accept()

# Windows specifically needs this AppUserModelID to group taskbar icons correctly
if __name__ == "__main__":
    if os.name == 'nt':
        import ctypes
        myappid = 'bluefalcon.mkvbatchmuxer.2.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())