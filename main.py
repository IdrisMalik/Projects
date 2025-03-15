import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from file_handler import extract_text_from_file
from text_processor import preprocess_text
from summarization import lsa_summarize, bart_summarize
from translation import translate_text


class WorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, text, task, **kwargs):
        super().__init__()
        self.text = text
        self.task = task
        self.kwargs = kwargs

    def run(self):
        try:
            if self.task == "summarize":
                if self.kwargs["method"] == "lsa":
                    result = lsa_summarize(self.text, self.kwargs.get("num_sentences", 3))
                else:
                    result = bart_summarize(self.text)
            elif self.task == "translate":
                result = translate_text(self.text, self.kwargs["source_lang"], self.kwargs["target_lang"])
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))



class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text Summarization and Translation")
        self.resize(800, 600)

        self.input_text = QTextEdit()
        self.output_text = QTextEdit(readOnly=True)
        self.summarize_button = QPushButton("Summarize")
        self.translate_button = QPushButton("Translate")

        self.method_combo = QComboBox()
        self.method_combo.addItems(["lsa", "bart"])

        self.open_file_button = QPushButton("Open File")

        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["en", "fr", "de", "es", "it"])

        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["en", "fr", "de", "es", "it"])
        self.progress_bar = QProgressBar()

        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel("Input Text:"))
        input_layout.addWidget(self.input_text)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.open_file_button)

        summarization_layout = QHBoxLayout()
        summarization_layout.addWidget(QLabel("Method:"))
        summarization_layout.addWidget(self.method_combo)
        summarization_layout.addWidget(self.summarize_button)

        translation_layout = QHBoxLayout()
        translation_layout.addWidget(QLabel("Source:"))
        translation_layout.addWidget(self.source_lang_combo)
        translation_layout.addWidget(QLabel("Target:"))
        translation_layout.addWidget(self.target_lang_combo)
        translation_layout.addWidget(self.translate_button)


        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel("Output Text:"))
        output_layout.addWidget(self.output_text)

        main_layout = QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        main_layout.addLayout(summarization_layout)
        main_layout.addLayout(translation_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(output_layout)

        self.setLayout(main_layout)


        self.summarize_button.clicked.connect(self.summarize_text)
        self.translate_button.clicked.connect(self.translate_text)
        self.open_file_button.clicked.connect(self.open_file)



    def summarize_text(self):
        text = self.input_text.toPlainText()

        self.worker = WorkerThread(text, "summarize", method=self.method_combo.currentText())
        self.worker.finished.connect(self.display_output)
        self.worker.error.connect(self.display_error)
        self.worker.start()


    def translate_text(self):
        text = self.input_text.toPlainText()
        source_lang = self.source_lang_combo.currentText()
        target_lang = self.target_lang_combo.currentText()

        self.worker = WorkerThread(text, "translate", source_lang=source_lang, target_lang=target_lang)
        self.worker.finished.connect(self.display_output)
        self.worker.error.connect(self.display_error)

        self.worker.start()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Text Files (*.txt);;PDF Files (*.pdf);;DOCX Files (*.docx)"
        )
        if file_path:
            try:
                text = extract_text_from_file(file_path)
                self.input_text.setPlainText(text)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {e}")




    def display_output(self, result):
        self.output_text.setPlainText(result)


    def display_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())