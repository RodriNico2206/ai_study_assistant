from groq import Groq
from ai_study_assistant.config import Config

class NotesGenerator:
    """Class responsible for interacting with GroqCloud to generate and reduce study notes."""
    
    def __init__(self):
        Config.validate()
        # Initialize the native Groq client using the explicit API Key
        self.client = Groq(
            api_key=Config.GROQ_API_KEY
        )

    def generate_summary(self, chapter_text: str, custom_instructions: str = "") -> str:
        """Map Phase: Sends a text chunk to Groq requesting structured study notes."""
        system_instruction = (
            "You are an expert study assistant. Your task is to analyze book chapters and create structured study notes. "
            "You must include: 1) A general summary, 2) Key concepts with definitions, and 3) Main points in bullet points. "
            "Use a clear, educational tone and clean Markdown formatting."
        )
        
        user_prompt = f"Please generate study notes for the following chapter:\n\n{chapter_text}"
        if custom_instructions:
            user_prompt += f"\n\nAdditional user instructions: {custom_instructions}"

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content

    def reduce_summaries(self, consolidated_notes: str) -> str:
        """Reduce Phase: Synthesizes all partial notes into a cohesive global overview."""
        system_instruction = (
            "You are a master academic editor. You will receive a collection of partial study notes extracted from a book. "
            "Your task is to analyze them as a whole and create a single, unified, and fluid global summary. "
            "Connect related concepts, eliminate redundancies, explain the overarching narrative or learning path, "
            "and ensure everything transitions smoothly. Provide the final output in Spanish using clean Markdown formatting."
        )

        user_prompt = f"Here are the partial study notes collected from the document:\n\n{consolidated_notes}\n\nPlease generate the final global overview."

        response = self.client.chat.completions.create(
            model=Config.REDUCE_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        
        return response.choices[0].message.content