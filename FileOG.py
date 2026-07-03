import sys
import os
import shutil
import urllib.request
import subprocess
import ctypes
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QProgressBar)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QThread, pyqtSignal

class GoogleDriveInstallerThread(QThread):
    """Background thread to handle downloading and installing Google Drive 
       without freezing the main PyQt6 user interface."""
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            # Direct download link for Google Drive Setup
            url = "https://dl.google.com/drive-file-stream/GoogleDriveSetup.exe"
            installer_path = os.path.join(os.environ["TEMP"], "GoogleDriveSetup.exe")
            
            # Step 1: Send 'Downloading...' log status to UI
            self.status_signal.emit("Downloading Google Drive...")
            
            # Bypass Google's bot-blocking policy by adding a standard web browser User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Request file streaming safely with a 30-second timeout guard
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response, open(installer_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            # Step 2: Send 'Installing...' log status to UI
            self.status_signal.emit("Installing Google Drive...")
            
            # Run the installer silently in the background
            result = subprocess.run([installer_path, "/silent", "/install"], shell=True)
            
            # Step 3: Clean up the setup file from TEMP
            if os.path.exists(installer_path):
                os.remove(installer_path)
                
            if result.returncode == 0:
                self.status_signal.emit("Installation complete!")
                self.finished_signal.emit(True, "Google Drive successfully installed!")
            else:
                self.finished_signal.emit(False, f"Installation process returned code: {result.returncode}")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class FileOrganizerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(self.resource_path("icon.ico")))
        self.initUI()
        
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)    

    def initUI(self):
        self.setWindowTitle("File Organizer")
        self.setGeometry(300, 300, 450, 300)

        # Main Layout
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Select Directory to Organize:"))

        # File Selection Row
        h_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        h_layout.addWidget(self.path_input)
        
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_directory)
        h_layout.addWidget(btn_browse)
        
        layout.addLayout(h_layout)

        # Run Organizer Button
        self.btn_run = QPushButton("Run Organizer")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_organizer)
        layout.addWidget(self.btn_run)
        
        # Add Google Drive Button
        self.btn_add_gdrive = QPushButton("Add Google Drive")
        self.btn_add_gdrive.setStyleSheet("background-color: #4285F4; color: white; font-weight: bold; padding: 10px; margin-top: 5px;")
        self.btn_add_gdrive.clicked.connect(self.start_gdrive_installation)
        layout.addWidget(self.btn_add_gdrive)

        # Status Log Label
        self.status_log_label = QLabel("")
        self.status_log_label.setStyleSheet("color: #aaaaaa; font-style: italic; margin-top: 5px;")
        self.status_log_label.setVisible(False)
        layout.addWidget(self.status_log_label)

        # Progress Bar Widget
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Infinite sliding animation
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 15px;
            }
            QProgressBar::chunk {
                background-color: #4285F4;
                width: 25px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.path_input.setText(directory)

    def run_organizer(self):
        path = self.path_input.text()
        if not os.path.isdir(path):
            QMessageBox.critical(self, "Error", "Please select a valid directory.")
            return

        self.btn_run.setEnabled(False)
        self.btn_run.setText("Organizing...")
        
        try:
            moved_count = self.organize_files(path)
            QMessageBox.information(self, "Success", f"Organizing complete! {moved_count} files moved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        finally:
            self.btn_run.setEnabled(True)
            self.btn_run.setText("Run Organizer")

    def start_gdrive_installation(self):
        self.btn_add_gdrive.setEnabled(False)
        self.btn_run.setEnabled(False) 
        self.btn_add_gdrive.setText("Processing...")
        
        self.status_log_label.setText("Starting process...")
        self.status_log_label.setVisible(True)
        self.progress_bar.setVisible(True)
        
        self.installer_thread = GoogleDriveInstallerThread()
        self.installer_thread.status_signal.connect(self.update_status_log)
        self.installer_thread.finished_signal.connect(self.on_installation_complete)
        self.installer_thread.start()

    def update_status_log(self, text):
        self.status_log_label.setText(text)

    def on_installation_complete(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_log_label.setVisible(False)
        self.btn_add_gdrive.setEnabled(True)
        self.btn_run.setEnabled(True)
        self.btn_add_gdrive.setText("Add Google Drive")
        
        if success:
            QMessageBox.information(
                self, "Success", 
                "Google Drive has been installed successfully!\n\n"
                "Please verify your browser window or taskbar notification to complete "
                "the secure sign-in process and mount your workspace."
            )
        else:
            QMessageBox.warning(
                self, "Installation Failed", 
                f"The background installation process encountered an issue:\n\n{message}"
            )

    def organize_files(self, directory):
        folder_mapping = {
            '.txt': 'documents', '.pdf': 'documents', '.docx': 'documents', '.pptx': 'documents',
            '.xlsx': 'documents', '.csv': 'documents',
            '.lua': 'codes', '.py': 'codes', '.html': 'codes', '.json': 'codes',
            '.mp3': 'audio', '.wav': 'audio',
            '.mp4': 'video', '.mkv': 'video', '.mov': 'video',
            '.jpg': 'images', '.png': 'images', '.svg': 'images', '.jpeg': 'images', '.heic': 'images',
            '.exe': 'setups', '.apk': 'setups',
            '.7z': 'archives', '.zip': 'archives', '.iso': 'archives', '.rar': 'archives'
        }
        
        count = 0
        try:
            items = os.listdir(directory)
            files = [f for f in items if os.path.isfile(os.path.join(directory, f))]
        except Exception as e:
            raise Exception(f"Could not access directory: {e}")
            
        for file in files:
            name, ext = os.path.splitext(file)
            ext = ext.lower()
            
            target_folder = folder_mapping.get(ext, 'others')
            dest_dir = os.path.join(directory, target_folder)
            os.makedirs(dest_dir, exist_ok=True)
            
            src = os.path.join(directory, file)
            dst = os.path.join(dest_dir, file)
            
            counter = 1
            base_name = name
            while os.path.exists(dst):
                if src == dst:
                    break
                dst = os.path.join(dest_dir, f"{base_name} ({counter}){ext}")
                counter += 1
            
            if src != dst and os.path.exists(src):
                shutil.move(src, dst)
                count += 1
                
        return count


if __name__ == '__main__':
    if ctypes.windll.shell32.IsUserAnAdmin():
        app = QApplication(sys.argv)
        ex = FileOrganizerApp()
        ex.show()
        sys.exit(app.exec())
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
