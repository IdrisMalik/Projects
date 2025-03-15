# Text Processor

## Overview
Text Processor is a Python-based application that provides functionalities for text extraction, preprocessing, summarization, and translation. It features a GUI built with PyQt6 for an intuitive user experience.

## Features
- **Text Extraction**: Supports `.txt`, `.pdf`, and `.docx` files.
- **Text Preprocessing**: Tokenizes text into sentences and words.
- **Summarization**: Implements LSA-based and BART-based summarization methods.
- **Translation**: Uses the Helsinki-NLP model for multilingual translation.

## Installation
### Prerequisites
Ensure you have Python 3.8+ installed. Install dependencies using:

```sh
pip install -r requirements.txt
```

### Additional Requirements
Some libraries may require additional setup:
- `nltk`: Download the required tokenizer:

```sh
import nltk
nltk.download('punkt')
```

## Usage
Run the application with:

```sh
python main.py
```

### GUI Features
- **Load Files**: Select and extract text from documents.
- **Summarization**: Choose between LSA and BART summarization models.
- **Translation**: Translate text between supported languages.

## File Structure
- `main.py` - Main GUI application
- `file_handler.py` - Handles file extraction
- `text_processor.py` - Preprocesses text (tokenization)
- `summarization.py` - Implements LSA and BART summarization
- `translation.py` - Handles text translation
