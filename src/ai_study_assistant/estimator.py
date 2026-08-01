import re
from pypdf import PdfReader
from ai_study_assistant.config import Config


class TokenEstimator:
    """Utility class to estimate token usage before making API calls."""

    @staticmethod
    def _has_graphic_content(page_pdf, page_text: str) -> bool:
        """Detects if a page contains charts or diagrams based on native embedded images, captions, or empty native text."""
        if hasattr(page_pdf, "images") and len(page_pdf.images) > 0:
            return True

        pattern = r"\b(figura|gráfico|grafico|diagrama|tabla|ilustración)\s*\d+"
        if re.search(pattern, page_text.lower()):
            return True

        if len(page_text.strip()) < 10:
            return True

        return False

    @classmethod
    def estimate_pdf_cost(cls, input_file_path: str) -> dict:
        """Analyzes PDF pages and calculates an estimated token count."""
        reader = PdfReader(input_file_path)
        text_pages = 0
        vision_pages = 0

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if cls._has_graphic_content(page, page_text):
                vision_pages += 1
            else:
                text_pages += 1

        # Average estimations based on project architecture
        text_tokens = text_pages * 1100
        vision_tokens = vision_pages * 2000
        reduce_tokens = 2500  # Fixed estimate for the reduction phase
        total_tokens = text_tokens + vision_tokens + reduce_tokens

        groq_vision_pages = min(vision_pages, Config.MAX_VISION_PAGES)
        openrouter_vision_pages = max(0, vision_pages - Config.MAX_VISION_PAGES)

        return {
            "total_pages": len(reader.pages),
            "text_pages": text_pages,
            "vision_pages": vision_pages,
            "groq_vision_pages": groq_vision_pages,
            "openrouter_vision_pages": openrouter_vision_pages,
            "estimated_tokens": total_tokens,
        }

    @classmethod
    def print_report_and_confirm(
        cls, input_file_path: str, auto_confirm: bool = False
    ) -> bool:
        """Displays the estimation report and asks for user confirmation if auto_confirm is False."""
        report = cls.estimate_pdf_cost(input_file_path)

        print("\n" + "=" * 55)
        print("PREVIOUS ESTIMATED CONSUMPTION REPORT")
        print("=" * 55)
        print(f" Total pages to process      : {report['total_pages']}")
        print(f"  ├─ Plain Text Pages         : {report['text_pages']}")
        print(f"  └─ Multimodal/Vision Pages  : {report['vision_pages']}")
        print(f"      ├─ Routed to Groq Vision: {report['groq_vision_pages']}")
        print(f"      └─ Routed to OpenRouter : {report['openrouter_vision_pages']}")
        print("-" * 55)
        print(f" Approximate Total Tokens     : ~{report['estimated_tokens']:,} tokens")
        print("=" * 55 + "\n")

        if auto_confirm:
            print(" -> '-y / --yes' flag detected. Proceeding automatically...\n")
            return True

        response = (
            input("Do you wish to proceed with processing the PDF? (y/n): ")
            .strip()
            .lower()
        )
        return response in ["y", "yes"]