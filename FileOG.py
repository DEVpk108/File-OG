import sys
import os
import shutil
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class FileOrganizerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(self.resource_path("icon.ico")))
        self.initUI()
        
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)    

    def initUI(self):
        self.setWindowTitle("File Organizer")
        self.setGeometry(300, 300, 450, 200)

        # Layouts
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

        # Run Button
        self.btn_run = QPushButton("Run Organizer")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_organizer)
        layout.addWidget(self.btn_run)

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

    def organize_files(self, directory):
        folder_mapping = {
            '.txt': 'documents', '.pdf': 'documents', '.docx': 'documents', '.pptx': 'documents',
            '.xlsx': 'documents', '.csv': 'documents', # Added spreadsheets
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
            
            # Determine target folder; fall back to an 'others' folder instead of ignoring it
            target_folder = folder_mapping.get(ext, 'others')
            dest_dir = os.path.join(directory, target_folder)
            os.makedirs(dest_dir, exist_ok=True)
            
            src = os.path.join(directory, file)
            dst = os.path.join(dest_dir, file)
            
            # Resolve collisions (e.g., if 'photo.jpg' exists, make it 'photo (1).jpg')
            counter = 1
            base_name = name
            while os.path.exists(dst):
                if src == dst: # Skip processing if it's somehow identical paths
                    break
                dst = os.path.join(dest_dir, f"{base_name} ({counter}){ext}")
                counter += 1
            
            if src != dst and os.path.exists(src):
                shutil.move(src, dst)
                count += 1
                
        return count

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileOrganizerApp()
    ex.show()
    sys.exit(app.exec())
