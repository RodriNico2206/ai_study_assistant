import os
from pypdf import PdfReader

class TextExtractor:
    """Class to extract text from local files."""
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """Detects file extension and extracts its text content."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file does not exist at path: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".pdf":
            return TextExtractor._read_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    @staticmethod
    def _read_pdf(file_path: str) -> str:
        """Extracts text from a PDF file."""
        reader = PdfReader(file_path)
        text_runs = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_runs.append(page_text)
        return "\n".join(text_runs)