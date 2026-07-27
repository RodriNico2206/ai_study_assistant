import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MODEL_NAME = "llama-3.1-8b-instant"
    VISION_MODEL_NAME = "qwen/qwen3.6-27b"
    REDUCE_MODEL_NAME = "llama-3.3-70b-versatile"

    BATCH_SIZE = 2
    PDF_DPI = 130
    MAX_VISION_PAGES = 3  # Límite por defecto de llamadas a API de visión
    GROQ_API_KEY = None

    # Email notification settings (Resend API)
    RESEND_API_KEY = None
    NOTIFICATION_EMAIL = None

    @classmethod
    def load_from_dict(cls, data: dict):
        """Loads configuration from a dictionary, falling back to environment variables."""
        cls.MODEL_NAME = data.get("MODEL_NAME") or os.getenv(
            "MODEL_NAME", cls.MODEL_NAME
        )
        cls.VISION_MODEL_NAME = data.get("VISION_MODEL_NAME") or os.getenv(
            "VISION_MODEL_NAME", cls.VISION_MODEL_NAME
        )
        cls.REDUCE_MODEL_NAME = data.get("REDUCE_MODEL_NAME") or os.getenv(
            "REDUCE_MODEL_NAME", cls.REDUCE_MODEL_NAME
        )
        cls.GROQ_API_KEY = data.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        cls.BATCH_SIZE = int(data.get("BATCH_SIZE", cls.BATCH_SIZE))
        cls.PDF_DPI = int(data.get("PDF_DPI", cls.PDF_DPI))
        cls.MAX_VISION_PAGES = int(data.get("MAX_VISION_PAGES", cls.MAX_VISION_PAGES))

        # Load Resend notification variables
        cls.RESEND_API_KEY = data.get("RESEND_API_KEY") or os.getenv(
            "RESEND_API_KEY"
        )
        cls.NOTIFICATION_EMAIL = data.get("NOTIFICATION_EMAIL") or os.getenv(
            "NOTIFICATION_EMAIL"
        )

    @classmethod
    def validate(cls):
        """Validates that necessary configuration and API keys are present."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "Error: GROQ_API_KEY is not set in the JSON file or environment variables."
            )
        if cls.BATCH_SIZE <= 0:
            raise ValueError(
                "Error: BATCH_SIZE must be a positive integer greater than 0."
            )
        if cls.MAX_VISION_PAGES < 0:
            raise ValueError(
                "Error: MAX_VISION_PAGES must be an integer greater than or equal to 0."
            )