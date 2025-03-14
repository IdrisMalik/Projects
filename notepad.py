import os
import sys
import argparse
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSpinBox, QPlainTextEdit, QFileDialog
)
from PySide6.QtCore import Qt

class FileHandler:
    @staticmethod
    def open_files(file_paths):
        """Open files using default applications."""
        for file_path in file_paths:
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                    subprocess.call((opener, file_path))
            except Exception as e:
                print(f"Error opening {file_path}: {e}")

    @staticmethod
    def create_files(folder_path, base_filename, start_num, file_count, initial_content):
        """Create multiple text files with sequential numbering."""
        created_files = []
        for i in range(start_num, start_num + file_count):
            file_name = f"{base_filename}{i}.txt"
            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(initial_content)
                created_files.append(file_path)
            except Exception as e:
                print(f"Error creating {file_path}: {e}")
        return created_files

def validate_inputs(folder_path, base_filename, file_count):
    """Validate folder path, base filename, and file count."""
    if not os.path.isdir(folder_path):
        return False, "Invalid folder path"
    invalid_chars = r'/\\:*?"<>|'
    if not base_filename:
        return False, "Base filename cannot be empty"
    if any(char in invalid_chars for char in base_filename):
        return False, f"Base filename contains invalid characters: {invalid_chars}"
    if not (1 <= file_count <= 1000):
        return False, "File count must be between 1 and 1000"
    return True, ""

def cli_main():
    """Handle command-line interface execution."""
    parser = argparse.ArgumentParser(
        description="CLI Notepad Launcher - Create multiple text files and open them",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--folder', required=True, help="Target directory for files")
    parser.add_argument('--base-name', required=True, help="Base filename (without extension)")
    parser.add_argument('--start', type=int, default=1, help="Starting number for files")
    parser.add_argument('--count', type=int, default=1, help="Number of files to create")
    parser.add_argument('--content', default='', help="Initial content for files")
    
    args = parser.parse_args()
    
    valid, message = validate_inputs(args.folder, args.base_name, args.count)
    if not valid:
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(1)
    
    try:
        created_files = FileHandler.create_files(
            args.folder,
            args.base_name,
            args.start,
            args.count,
            args.content
        )
        print(f"Successfully created {len(created_files)} files in {args.folder}")
        FileHandler.open_files(created_files)
        print(f"Opened {len(created_files)} files in default applications")
    except Exception as e:
        print(f"Critical error: {str(e)}", file=sys.stderr)
        sys.exit(1)

class NotepadModel:
    """Model for handling file creation logic and validation."""
    def __init__(self):
        self.folder_path = ""
        self.base_filename = ""
        self.start_num = 1
        self.file_count = 1
        self.initial_content = ""

    def validate(self):
        return validate_inputs(self.folder_path, self.base_filename, self.file_count)

    def create_and_open_files(self):
        """Create files and open them using FileHandler."""
        valid, message = self.validate()
        if not valid:
            return False, message
        try:
            created_files = FileHandler.create_files(
                self.folder_path, self.base_filename,
                self.start_num, self.file_count, self.initial_content
            )
            FileHandler.open_files(created_files)
            return True, f"Successfully created and opened {len(created_files)} files."
        except Exception as e:
            return False, f"Error: {str(e)}"

class NotepadWindow(QMainWindow):
    """Main application window for GUI mode."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notepad Launcher")
        self.model = NotepadModel()
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Folder selection
        folder_layout = QHBoxLayout()
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.clicked.connect(self._select_folder)
        select_folder_btn.setToolTip("Choose a folder to create files in")
        folder_layout.addWidget(select_folder_btn)
        self.folder_display = QLineEdit(readOnly=True, placeholderText="No folder selected")
        folder_layout.addWidget(self.folder_display)
        main_layout.addLayout(folder_layout)

        # Filename field
        self.filename_field = QLineEdit(placeholderText="Base Filename (e.g., note)")
        main_layout.addWidget(self.filename_field)

        # Number controls
        number_layout = QHBoxLayout()
        self.start_num_spin = QSpinBox(minimum=1, maximum=10000, value=1, prefix="Start: ")
        number_layout.addWidget(self.start_num_spin)
        self.count_spin = QSpinBox(minimum=1, maximum=1000, value=1, prefix="Count: ")
        number_layout.addWidget(self.count_spin)
        main_layout.addLayout(number_layout)

        # Content field
        self.content_field = QPlainTextEdit(placeholderText="Initial Content (Optional)")
        main_layout.addWidget(self.content_field)

        # Create button
        self.create_button = QPushButton("Create & Open")
        self.create_button.clicked.connect(self._create_files)
        main_layout.addWidget(self.create_button)

        # Status message
        self.status_message = QLabel("", alignment=Qt.AlignCenter)
        main_layout.addWidget(self.status_message)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", os.getcwd())
        if folder:
            self.model.folder_path = folder
            self.folder_display.setText(folder)
        else:
            self.model.folder_path = ""
            self.folder_display.setText("No folder selected")

    def _create_files(self):
        self.model.base_filename = self.filename_field.text().strip()
        self.model.start_num = self.start_num_spin.value()
        self.model.file_count = self.count_spin.value()
        self.model.initial_content = self.content_field.toPlainText()

        success, message = self.model.create_and_open_files()
        self.status_message.setStyleSheet("color: green;" if success else "color: red;")
        self.status_message.setText(message)

def gui_main():
    """Handle GUI mode execution."""
    app = QApplication(sys.argv)
    window = NotepadWindow()
    window.resize(500, 400)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_main()
    else:
        gui_main()