import base64
import time
from io import BytesIO
from PIL import Image
from groq import Groq
from ai_study_assistant.config import Config

class NotesGenerator:
    """Class responsible for interacting with GroqCloud to generate and reduce study notes."""
    
    def __init__(self):
        Config.validate()
        self.client = Groq(
            api_key=Config.GROQ_API_KEY
        )

    def _pil_image_to_base64(self, image: Image.Image) -> str:
        """Converts a PIL Image object to a base64 encoded string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _retry_api_call(self, api_func, max_retries=3, delay=5):
        """Helper to retry API calls on connection or rate-limit errors."""
        for attempt in range(1, max_retries + 1):
            try:
                return api_func()
            except Exception as e:
                print(f"\n    ⚠️ [Groq API Warning] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    raise e
                print(f"    Waiting {delay} seconds before retrying...")
                time.sleep(delay)

    def generate_summary(self, chapter_text: str, custom_instructions: str = "") -> str:
        """Map Phase: Sends a pure text chunk to Groq requesting structured study notes."""
        system_instruction = (
            "You are an expert study assistant. Your task is to analyze book chapters and create structured study notes. "
            "You must include: 1) A general summary, 2) Key concepts with definitions, and 3) Main points in bullet points. "
            "Use a clear, educational tone and clean Markdown formatting."
        )
        
        user_prompt = f"Please generate study notes for the following chapter:\n\n{chapter_text}"
        if custom_instructions:
            user_prompt += f"\n\nAdditional user instructions: {custom_instructions}"

        def _call():
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content

        return self._retry_api_call(_call)

    def generate_summary_from_image(self, page_image: Image.Image, page_text: str = "", custom_instructions: str = "") -> str:
        """Multimodal Map Phase: Sends page image + extracted text to Groq Vision model."""
        base64_img = self._pil_image_to_base64(page_image)
        
        system_instruction = (
            "You are an expert study assistant with multimodal vision capabilities. "
            "Analyze the provided book page image and its extracted text. Pay special attention "
            "to any charts, diagrams, tables, or figures present. Create structured study notes including: "
            "1) General summary, 2) Key concepts, and 3) An explanation of the charts or visual elements. "
            "Use clean Markdown formatting."
        )

        user_content = [
            {
                "type": "text", 
                "text": f"Here is the text extracted from the page:\n\n{page_text}\n\nPlease analyze both the image and text."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_img}"
                }
            }
        ]

        if custom_instructions:
            user_content[0]["text"] += f"\n\nAdditional user instructions: {custom_instructions}"

        def _call():
            response = self.client.chat.completions.create(
                model=Config.VISION_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content

        return self._retry_api_call(_call)

    def reduce_summaries(self, consolidated_notes: str) -> str:
        """Reduce Phase: Synthesizes all partial notes into a cohesive global overview."""
        system_instruction = (
            "You are a master academic editor. You will receive a collection of partial study notes extracted from a book. "
            "Your task is to analyze them as a whole and create a single, unified, and fluid global summary. "
            "Connect related concepts, eliminate redundancies, explain the overarching narrative or learning path, "
            "and ensure everything transitions smoothly. Provide the final output in Spanish using clean Markdown formatting."
        )

        user_prompt = f"Here are the partial study notes collected from the document:\n\n{consolidated_notes}\n\nPlease generate the final global overview."

        def _call():
            response = self.client.chat.completions.create(
                model=Config.REDUCE_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content

        return self._retry_api_call(_call)