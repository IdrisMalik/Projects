import PyPDF2
import docx2txt
from urllib.request import urlopen

def extract_text_from_file(file_path):
    try:
        if file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        elif file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        elif file_path.lower().endswith('.docx'):
            return docx2txt.process(file_path)
        elif file_path.startswith('http://') or file_path.startswith('https://'):
            with urlopen(file_path) as response:
                return response.read().decode('utf-8')
        else:
            return "Unsupported file format."
    except Exception as e:
        return f"Error processing file: {e}"