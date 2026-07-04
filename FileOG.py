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
            url = "https://dl.google.com/drive-file-stream/GoogleDriveSetup.exe"
            installer_path = os.path.join(os.environ["TEMP"], "GoogleDriveSetup.exe")
            
            self.status_signal.emit("Downloading Google Drive...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response, open(installer_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            self.status_signal.emit("Installing Google Drive...")
            result = subprocess.run([installer_path, "/silent", "/install"], shell=True)
            
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
        # History log stores tuples of (original_full_path, organized_full_path)
        self.history_log = [] 
        self.last_organized_directory = ""
        
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
        self.setGeometry(300, 300, 450, 340) # Resized height slightly to fit the new layout

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

        # Operational Action Layout (Organize and Revert Side-by-Side)
        action_layout = QHBoxLayout()
        
        # Run Organizer Button
        self.btn_run = QPushButton("Run Organizer")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_organizer)
        action_layout.addWidget(self.btn_run)
        
        # --- NEW UI ELEMENT: Revert Changes Button ---
        self.btn_revert = QPushButton("Revert Changes")
        self.btn_revert.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        self.btn_revert.setEnabled(False) # Default to disabled until an action occurs
        self.btn_revert.clicked.connect(self.run_reverter)
        action_layout.addWidget(self.btn_revert)
        
        layout.addLayout(action_layout)
        
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
        self.progress_bar.setRange(0, 0)
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
        self.btn_revert.setEnabled(False)
        self.btn_run.setText("Organizing...")
        
        try:
            # Wipe previous history tracking session records cleanly on fresh initialization run
            self.history_log.clear()
            self.last_organized_directory = path
            
            moved_count = self.organize_files(path)
            
            if moved_count > 0:
                QMessageBox.information(self, "Success", f"Organizing complete! {moved_count} files moved.")
                self.btn_revert.setEnabled(True) # Unlock undo controls now that historical points exist
            else:
                QMessageBox.information(self, "Information", "No loose files matching specified criteria were found to organize.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
        finally:
            self.btn_run.setEnabled(True)
            self.btn_run.setText("Run Organizer")

    # --- NEW CONTROLLER METOD: Execute Undo Undo Restorations ---
    def run_reverter(self):
        """Processes the stored history file map coordinates inversely to restore original locations."""
        if not self.history_log:
            QMessageBox.warning(self, "Warning", "No tracking session found to undo.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Revert", 
            f"Are you sure you want to undo the changes and revert {len(self.history_log)} files back to their original positions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return

        self.btn_run.setEnabled(False)
        self.btn_revert.setEnabled(False)
        self.btn_revert.setText("Reverting...")

        revert_count = 0
        directories_to_check = set()

        try:
            # Step 1: Pop and reverse processing path loops backwards smoothly
            for original_path, organized_path in reversed(self.history_log):
                if os.path.exists(organized_path):
                    # Cache destination path components to scan for empty directories later
                    directories_to_check.add(os.path.dirname(organized_path))
                    
                    # Ship target file directly backwards safely
                    shutil.move(organized_path, original_path)
                    revert_count += 1

            # Step 2: Clean up organizational tracking folders if left fully empty
            for folder in directories_to_check:
                try:
                    if os.path.exists(folder) and not os.listdir(folder):
                        os.rmdir(folder) # Erases folder seamlessly only if completely bare
                except Exception:
                    pass # Safely bypass folders that may contain stray unmapped items

            QMessageBox.information(self, "Revert Success", f"Successfully restored {revert_count} files to original positions!")
            self.history_log.clear() # Clear memory out after complete execution
            
        except Exception as e:
            QMessageBox.critical(self, "Revert Failure", f"An error occurred during restoration mapping: {e}")
        finally:
            self.btn_run.setEnabled(True)
            self.btn_revert.setText("Revert Changes")
            self.btn_revert.setEnabled(False) # Re-lock structural revert mechanics

    def start_gdrive_installation(self):
        self.btn_add_gdrive.setEnabled(False)
        self.btn_run.setEnabled(False) 
        self.btn_revert.setEnabled(False)
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
        if self.history_log:
            self.btn_revert.setEnabled(True)
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
                # Trace coordinates mapping step precisely inside memory before shifting disk sectors
                self.history_log.append((src, dst))
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
