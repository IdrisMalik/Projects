# Notepad Launcher

## Overview
Notepad Launcher is a Python application that allows users to create multiple text files with predefined content and open them using the system's default text editor. It supports both **CLI** and **GUI** modes.

## Features
- **GUI Mode**: User-friendly interface built with PySide6.
- **CLI Mode**: Command-line execution for quick operations.
- **File Creation**: Generates multiple text files with sequential numbering.
- **Custom Content**: Allows setting initial content for files.
- **Cross-Platform**: Works on Windows, macOS, and Linux.

## Installation
### Prerequisites
Ensure you have Python 3.8+ installed. Install dependencies with:

```sh
pip install PySide6
```

## Usage
### Running GUI Mode
To launch the graphical interface, simply run:

```sh
python notepad.py
```

### Running CLI Mode
Use the following command to create files via the command line:

```sh
python notepad.py --folder "path/to/folder" --base-name "note" --start 1 --count 5 --content "Sample text."
```

### CLI Arguments
- `--folder` → Target directory for file creation *(required)*
- `--base-name` → Base filename *(required)*
- `--start` → Starting number *(default: 1)*
- `--count` → Number of files *(default: 1)*
- `--content` → Initial content *(optional)*

## File Structure
- `notepad.py` - Entry point for CLI and GUI
- `backend.py` - Handles file operations and validation
- `cli.py` - CLI implementation
- `gui.py` - GUI implementation using PySide6
