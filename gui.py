import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QSpinBox, QPlainTextEdit, QFileDialog
)
from PySide6.QtCore import Qt
from backend import NotepadModel

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