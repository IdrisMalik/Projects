import os
import sys
import subprocess

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