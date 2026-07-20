import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Default recommended Groq model for the Map phase (chunk processing)
    MODEL_NAME = "llama-3.1-8b-instant" 
    # Default recommended Groq model for the Reduce phase (global synthesis)
    REDUCE_MODEL_NAME = "llama-3.3-70b-versatile"
    # Default batch size fallback if not provided in the JSON file
    BATCH_SIZE = 2
    # Default empty API Key
    GROQ_API_KEY = None

    @classmethod
    def load_from_dict(cls, data: dict):
        """Loads configuration from a dictionary, falling back to environment variables."""
        cls.MODEL_NAME = data.get("MODEL_NAME") or os.getenv("MODEL_NAME", cls.MODEL_NAME)
        cls.REDUCE_MODEL_NAME = data.get("REDUCE_MODEL_NAME") or os.getenv("REDUCE_MODEL_NAME", cls.REDUCE_MODEL_NAME)
        cls.GROQ_API_KEY = data.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        cls.BATCH_SIZE = int(data.get("BATCH_SIZE", cls.BATCH_SIZE))

    @classmethod
    def validate(cls):
        """Validates that the necessary configuration and API keys are present."""
        if not cls.GROQ_API_KEY:
            raise ValueError("Error: GROQ_API_KEY is not set in the JSON file or environment variables.")
        if cls.BATCH_SIZE <= 0:
            raise ValueError("Error: BATCH_SIZE must be a positive integer greater than 0.")