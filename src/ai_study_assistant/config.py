import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MODEL_NAME = "llama-3.1-8b-instant" 
    VISION_MODEL_NAME = "qwen/qwen3.6-27b"
    REDUCE_MODEL_NAME = "llama-3.3-70b-versatile"
    
    BATCH_SIZE = 2
    GROQ_API_KEY = None
    URLS = []

    @classmethod
    def load_from_dict(cls, data: dict):
        """Loads configuration from a dictionary, falling back to environment variables."""
        cls.MODEL_NAME = data.get("MODEL_NAME") or os.getenv("MODEL_NAME", cls.MODEL_NAME)
        cls.VISION_MODEL_NAME = data.get("VISION_MODEL_NAME") or os.getenv("VISION_MODEL_NAME", cls.VISION_MODEL_NAME)
        cls.REDUCE_MODEL_NAME = data.get("REDUCE_MODEL_NAME") or os.getenv("REDUCE_MODEL_NAME", cls.REDUCE_MODEL_NAME)
        cls.GROQ_API_KEY = data.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        cls.BATCH_SIZE = int(data.get("BATCH_SIZE", cls.BATCH_SIZE))
        cls.URLS = data.get("urls", [])

    @classmethod
    def validate(cls):
        """Validates that necessary configuration keys are present."""
        if not cls.GROQ_API_KEY:
            raise ValueError("Error: GROQ_API_KEY is not set in the JSON file or environment variables.")
        if cls.BATCH_SIZE <= 0:
            raise ValueError("Error: BATCH_SIZE must be a positive integer greater than 0.")