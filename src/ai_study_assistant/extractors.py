import os
from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_path

class TextExtractor:
    """Class to extract text from local files, with native support for OCR on scanned PDFs."""
    
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
        """Extracts text from a PDF file using a hybrid Native/OCR method."""
        reader = PdfReader(file_path)
        text_runs = []
        pdf_images = None  # Lazy loading de imágenes para optimizar rendimiento
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            
            # Si el texto está vacío o es insignificante, asumimos que es un PDF escaneado/imagen
            if len(page_text.strip()) < 10:
                print(f" -> [Extractor] Page {i+1} appears to be an image. Applying OCR...")
                if pdf_images is None:
                    # Convertimos el PDF completo a imágenes solo si es estrictamente necesario
                    pdf_images = convert_from_path(file_path, dpi=200)
                
                # Ejecutamos OCR en español sobre la imagen de la página correspondiente
                page_text = pytesseract.image_to_string(pdf_images[i], lang='spa')
                
            if page_text.strip():
                text_runs.append(f"--- [Page {i+1}] ---\n{page_text}")
                
        return "\n".join(text_runs)