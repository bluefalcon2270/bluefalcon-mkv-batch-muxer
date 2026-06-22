# ==========================================
# Version: v1.5
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
    QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView, 
    QDialog, QStyle, QStyleOptionButton, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect, QThread
import sys
from PyQt6.QtGui import QIcon

# --- Logging Setup ---
LOG_FILE = Path(__file__).parent / "bluefalcon-mkv-muxer.log"

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
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, target_dir: Path):
        super().__init__()
        self.target_dir = target_dir

    def run(self):
        try:
            data = []
            if not self.target_dir.exists() or not self.target_dir.is_dir():
                self.finished.emit(data)
                return

            mkv_files = [f for f in self.target_dir.iterdir() if f.is_file() and f.suffix.lower() == '.mkv']
            
            for mkv in mkv_files:
                basename = mkv.stem
                attachments = []
                
                # Scan for matching external tracks
                for f in self.target_dir.iterdir():
                    if f.is_file() and f.name != mkv.name and f.name.lower().startswith(basename.lower()):
                        if f.suffix.lower() in ['.mka', '.srt', '.ass', '.ssa', '.vtt', '.sup']:
                            attachments.append(f)
                
                data.append({
                    "video_path": str(mkv),
                    "video_name": mkv.name,
                    "basename": basename,
                    "attachment_paths": [str(f) for f in attachments],
                    "has_attachments": bool(attachments)
                })
                
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
                if not task["has_attachments"]:
                    self.log_msg.emit(f"[SKIPPED] {task['video_name']} - No attachments selected.")
                    continue

                out_file = output_dir / task['video_name']
                cmd = [self.mkvmerge_path, "-o", str(out_file), task['video_path']]
                cmd.extend(task['attachment_paths'])

                self.log_msg.emit(f"[PROCESSING] {task['basename']}")
                
                # Run subprocess
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if result.returncode == 0 or result.returncode == 1:
                    self.log_msg.emit(f"[SUCCESS] Merged Output: {task['video_name']}")
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
            "<b>BlueFalcon MKV Batch Muxer</b><br>v1.5<br><br>"
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
        self.setWindowTitle("BlueFalcon MKV Batch Muxer v1.5")
        self.setMinimumSize(1200, 750)
        
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.target_directory = Path.cwd()
        self.scanner_worker = None
        self.action_worker = None
        self.current_file_data = {}

        self._apply_dark_theme()
        self._init_ui()
        
        logger.info(f"System initialized. Current working directory: {self.target_directory}")
        self._refresh_tree()

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1F22; }
            QWidget { color: #E3E3E3; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QLineEdit { background-color: #2B2D31; border: 1px solid #44474A; padding: 0px 10px; border-radius: 6px; color: #FFFFFF; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #A8C7FA; }
            QPushButton { background-color: #A8C7FA; border: none; border-radius: 6px; color: #062E6F; font-family: 'Segoe UI', Arial, sans-serif; font-weight: bold; font-size: 14px; padding: 4px; }
            QPushButton:hover { background-color: #D3E3FD; }
            QPushButton:disabled { background-color: #44474A; color: #8E918F; }
            QPushButton#overlay_btn { background-color: #2B2D31; border: 1px solid #44474A; border-radius: 6px; font-size: 16px; font-weight: bold; color: #A8C7FA; }
            QPushButton#overlay_btn:hover { background-color: #383A40; color: #D3E3FD; }
            QTextEdit { background-color: #1E1F22; border: 1px solid #44474A; color: #A0A0A0; padding: 10px; border-radius: 6px; font-family: Consolas, monospace; font-size: 13px; }
            QTreeWidget { background-color: #1E1F22; border: 1px solid #44474A; border-radius: 6px; color: #E3E3E3; outline: none; }
            QHeaderView::section { background-color: #1E1F22; color: #A8C7FA; padding: 4px; border: none; border-bottom: 1px solid #44474A; font-weight: bold; font-size: 13px; }
            QTreeWidget::item { padding: 4px 0px; border-bottom: 1px solid #2B2D31; }
            QTreeWidget::item:selected { background-color: #35383D; }
            QTreeWidget::branch:has-children:!has-siblings:closed, QTreeWidget::branch:closed:has-children:has-siblings { border-image: none; image: none; }
            QTreeWidget::branch:open:has-children:!has-siblings, QTreeWidget::branch:open:has-children:has-siblings { border-image: none; image: none; }
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

        # --- Hierarchical Data Tree ---
        tree_container = QWidget()
        tree_layout = QGridLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        
        # Reduced to 3 columns: Checkbox, Name, Type (Status removed)
        self.tree.setColumnCount(3)
        
        self.checkbox_header = CheckBoxHeader(Qt.Orientation.Horizontal)
        self.checkbox_header.stateChanged.connect(self._set_all_checkboxes)
        self.tree.setHeader(self.checkbox_header)
        
        self.tree.setHeaderLabels(["", "Media Group / File Name", "Type"])
        
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(20)
        self.tree.setWordWrap(False)
        
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        header = self.tree.header()
        header.setMinimumHeight(46) 
        header.setStretchLastSection(False) 
        
        # Center align headers
        for i in range(3):
            header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Explicit column sizing to maximize horizontal breathing room
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(0, 40)
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(2, 160)
        
        self.tree.itemChanged.connect(self._on_item_changed)
        
        tree_layout.addWidget(self.tree, 0, 0)

        refresh_wrapper = QWidget()
        refresh_box = QVBoxLayout(refresh_wrapper)
        refresh_box.setContentsMargins(0, 8, 8, 0) 
        
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("overlay_btn")
        self.btn_refresh.setFixedSize(30, 30)
        self.btn_refresh.setToolTip("Refresh Directory")
        self.btn_refresh.clicked.connect(self._refresh_tree)
        refresh_box.addWidget(self.btn_refresh)
        
        tree_layout.addWidget(refresh_wrapper, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(tree_container, stretch=2)

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

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column == 0:
            self.tree.blockSignals(True)
            state = item.checkState(0)
            
            if item.parent() is None:
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        child.setCheckState(0, state)
            else:
                parent = item.parent()
                checked_count = 0
                total_checkable = 0
                
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        total_checkable += 1
                        if child.checkState(0) == Qt.CheckState.Checked:
                            checked_count += 1
                            
                if checked_count == total_checkable and total_checkable > 0:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                elif checked_count == 0:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                    
            self.tree.blockSignals(False)

    def _set_all_checkboxes(self, state: Qt.CheckState):
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item and not item.isDisabled():
                item.setCheckState(0, state)
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                        child.setCheckState(0, state)
        self.tree.blockSignals(False)

    def _get_selected_tasks(self) -> list[dict]:
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            
            if parent and parent.checkState(0) != Qt.CheckState.Unchecked:
                task_index = parent.data(0, Qt.ItemDataRole.UserRole)
                
                if task_index is not None and task_index in self.current_file_data:
                    base_info = self.current_file_data[task_index]
                    
                    selected_attachments = []
                    video_selected = False
                    
                    for j in range(parent.childCount()):
                        child = parent.child(j)
                        if child.checkState(0) == Qt.CheckState.Checked:
                            path = child.data(0, Qt.ItemDataRole.UserRole)
                            if child.text(2) == "Source Video":
                                video_selected = True
                            else:
                                selected_attachments.append(path)
                                
                    if video_selected and selected_attachments:
                        task = base_info.copy()
                        task["attachment_paths"] = selected_attachments
                        selected.append(task)
        return selected

    def _refresh_tree(self):
        self.tree.clear()
        self.current_file_data.clear()
        
        self.scanner_worker = ScannerWorker(self.target_directory)
        self.scanner_worker.finished.connect(self._populate_tree)
        self.scanner_worker.error.connect(lambda e: logger.error(f"Scan Error: {e}"))
        self.scanner_worker.start()

    def _populate_tree(self, data: list[dict]):
        self.tree.blockSignals(True)
        self.tree.clear()
        
        for i, info in enumerate(data):
            self.current_file_data[i] = info
            
            # 1. Create Parent Group Item
            parent = QTreeWidgetItem(self.tree)
            parent.setData(0, Qt.ItemDataRole.UserRole, i)
            
            if info["has_attachments"]:
                parent.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                current_header_state = Qt.CheckState.Checked if self.checkbox_header._is_on else Qt.CheckState.Unchecked
                parent.setCheckState(0, current_header_state)
            else:
                parent.setFlags(Qt.ItemFlag.ItemIsSelectable)
                parent.setDisabled(True)

            parent.setText(1, f"📁 {info['basename']}")
            parent.setText(2, "Output Group" if info["has_attachments"] else "-")
            
            parent.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            
            font = parent.font(1)
            font.setBold(True)
            parent.setFont(1, font)

            # 2. Add Base Video Child
            child_vid = QTreeWidgetItem(parent)
            child_vid.setText(1, f"🎬 {info['video_name']}")
            child_vid.setText(2, "Source Video")
            child_vid.setData(0, Qt.ItemDataRole.UserRole, info["video_path"])
            
            child_vid.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
            
            if info["has_attachments"]:
                child_vid.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                child_vid.setCheckState(0, current_header_state)
            else:
                child_vid.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

            # 3. Add Attachment Children
            for att_path in info["attachment_paths"]:
                att_name = os.path.basename(att_path)
                ext = att_name.lower().split('.')[-1]
                icon = "🎵" if ext == 'mka' else "📝"
                
                child_att = QTreeWidgetItem(parent)
                child_att.setText(1, f"{icon} {att_name}")
                child_att.setText(2, "Audio Track" if ext == 'mka' else "Subtitle Track")
                child_att.setData(0, Qt.ItemDataRole.UserRole, att_path)
                
                child_att.setTextAlignment(2, Qt.AlignmentFlag.AlignCenter)
                
                child_att.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                child_att.setCheckState(0, current_header_state)

            parent.setExpanded(True)

        self.tree.blockSignals(False)
        self.btn_refresh.raise_()

    def _start_muxing(self):
        selected_tasks = self._get_selected_tasks()
        if not selected_tasks:
            QMessageBox.information(self, "No Selection", "Please verify that at least one valid video and its attachments are checked.")
            return

        exe_path = self.entry_exe_path.text().strip()
        out_str = self.entry_out_path.text().strip()
        
        self.tree.setEnabled(False)
        self.btn_run.setEnabled(False)
        
        self.action_worker = ActionWorker(exe_path, self.target_directory, out_str, selected_tasks)
        self.action_worker.log_msg.connect(logger.info)
        self.action_worker.error.connect(self._on_worker_error)
        self.action_worker.finished.connect(self._on_worker_finished)
        self.action_worker.start()

    def _on_worker_error(self, e: str):
        logger.error(f"Action Error: {e}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{e}")

    def _on_worker_finished(self):
        self.tree.setEnabled(True)
        self.btn_run.setEnabled(True)
        self.action_worker = None
        self._refresh_tree()

    def closeEvent(self, event):
        if self.action_worker and self.action_worker.isRunning():
            self.action_worker.wait()
        if self.scanner_worker and self.scanner_worker.isRunning():
            self.scanner_worker.wait()
            
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())