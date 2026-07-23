import os
import tempfile
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

class WebExtractor:
    """Class to extract URLs from web menus/cards and convert web pages to temporary PDFs."""

    @staticmethod
    def get_menu_urls(base_url: str) -> list[str]:
        """Extracts sub-links from sidebar navigation and main content cards using Playwright, filtering external domains."""
        try:
            base_domain = urlparse(base_url).netloc

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(base_url, wait_until="networkidle")
                
                # Extraer enlaces tanto del menú lateral (<nav>) como del contenido principal (tarjetas, botones)
                raw_links = page.eval_on_selector_all(
                    "nav a[href], main a[href], .docs-card a[href]", 
                    "elements => elements.map(e => e.href)"
                )
                browser.close()

            clean_links = []
            for link in raw_links:
                clean_link = link.split('#')[0]
                parsed_link = urlparse(clean_link)
                
                # FILTRADO DE SEGURIDAD: Solo URLs del mismo dominio exacto (ej: docs.databricks.com)
                if parsed_link.scheme in ['http', 'https'] and parsed_link.netloc == base_domain:
                    clean_links.append(clean_link)

            # Preservar orden y eliminar duplicados
            unique_links = list(dict.fromkeys(clean_links))
            return unique_links if unique_links else [base_url]

        except Exception as e:
            print(f" -> [WebExtractor Warning] Error extracting links: {e}. Processing base URL.")
            return [base_url]

    @staticmethod
    def url_to_pdf(url: str) -> str:
        """Renders a web URL in a headless browser and exports it as a temporary PDF file."""
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c if c.isalnum() else "_" for c in url])[-50:]
        pdf_path = os.path.join(temp_dir, f"web_page_{safe_name}.pdf")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, wait_until="networkidle")
            
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"}
            )
            browser.close()

        return pdf_path