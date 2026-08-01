import base64
import json
import urllib.request
from io import BytesIO
from PIL import Image
from groq import Groq
from ai_study_assistant.config import Config


class NotesGenerator:
    """Class responsible for interacting with GroqCloud and OpenRouter to generate study notes."""

    def __init__(self):
        Config.validate()
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.last_remaining_tpd = None

    def _pil_image_to_base64(self, image: Image.Image) -> str:
        """Converts a PIL Image object to a compressed JPEG base64 string to optimize token usage."""
        buffered = BytesIO()
        rgb_image = image.convert("RGB")
        rgb_image.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _update_rate_limits(self, headers) -> None:
        """Extracts and stores remaining TPD tokens from response headers."""
        try:
            remaining_tpd = headers.get("x-ratelimit-remaining-tokens-day")
            if remaining_tpd is not None:
                # Conversión segura pasando por float()
                self.last_remaining_tpd = int(float(remaining_tpd))
                print(
                    f"       [Rate Limit Monitor] Available TPD tokens: {self.last_remaining_tpd:,}"
                )
        except Exception:
            pass

    def generate_summary(
        self, chapter_text: str, custom_instructions: str = ""
    ) -> str:
        """Map Phase: Sends a pure text chunk to Groq requesting structured study notes.
        If Groq quota is insufficient, routes to OpenRouter Text API.
        """
        estimated_tokens = 1000
        if (
            self.last_remaining_tpd is not None
            and self.last_remaining_tpd < estimated_tokens
        ):
            print(
                f"\n -> [Quota Fallback] Groq remaining tokens ({self.last_remaining_tpd:,}) lower than required ({estimated_tokens:,}). "
                f"Routing text batch to OpenRouter ({Config.OPENROUTER_TEXT_MODEL})..."
            )
            return self.generate_summary_from_openrouter_text(
                chapter_text, custom_instructions
            )

        system_instruction = (
            "You are an expert study assistant. Your task is to analyze book chapters and create structured study notes. "
            "You must include: 1) A general summary, 2) Key concepts with definitions, and 3) Main points in bullet points. "
            "Use a clear, educational tone and clean Markdown formatting."
        )

        user_prompt = f"Please generate study notes for the following chapter:\n\n{chapter_text}"
        if custom_instructions:
            user_prompt += (
                f"\n\nAdditional user instructions: {custom_instructions}"
            )

        raw_response = self.client.chat.completions.with_raw_response.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        self._update_rate_limits(raw_response.headers)
        completion = raw_response.parse()
        return completion.choices[0].message.content

    def generate_summary_from_openrouter_text(
        self, chapter_text: str, custom_instructions: str = ""
    ) -> str:
        """Fallback Text Map Phase: Sends text content to OpenRouter Text API."""
        system_instruction = (
            "You are an expert study assistant. Your task is to analyze book chapters and create structured study notes. "
            "You must include: 1) A general summary, 2) Key concepts with definitions, and 3) Main points in bullet points. "
            "Use a clear, educational tone and clean Markdown formatting."
        )

        user_prompt = f"Please generate study notes for the following chapter:\n\n{chapter_text}"
        if custom_instructions:
            user_prompt += (
                f"\n\nAdditional user instructions: {custom_instructions}"
            )

        payload = {
            "model": Config.OPENROUTER_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]

    def generate_summary_from_image(
        self,
        page_image: Image.Image,
        page_text: str = "",
        custom_instructions: str = "",
    ) -> str:
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
                "text": f"Here is the text extracted from the page:\n\n{page_text}\n\nPlease analyze both the image and text.",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
            },
        ]

        if custom_instructions:
            user_content[0]["text"] += (
                f"\n\nAdditional user instructions: {custom_instructions}"
            )

        raw_response = self.client.chat.completions.with_raw_response.create(
            model=Config.VISION_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )
        self._update_rate_limits(raw_response.headers)
        completion = raw_response.parse()
        return completion.choices[0].message.content

    def generate_summary_from_openrouter_vision(
        self,
        page_image: Image.Image,
        page_text: str = "",
        custom_instructions: str = "",
    ) -> str:
        """Fallback Multimodal Map Phase: Sends page image to OpenRouter Vision API."""
        base64_img = self._pil_image_to_base64(page_image)

        prompt = (
            "You are an expert study assistant with multimodal vision capabilities. "
            "Analyze the provided page image and any associated text. Pay special attention "
            "to any charts, diagrams, tables, or figures present. Create structured study notes including: "
            "1) General summary, 2) Key concepts, and 3) An explanation of the visual elements. "
            "Use clean Markdown formatting."
        )
        if page_text:
            prompt += f"\n\nExtracted text:\n{page_text}"
        if custom_instructions:
            prompt += f"\n\nAdditional instructions: {custom_instructions}"

        payload = {
            "model": Config.OPENROUTER_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]

    def reduce_summaries(self, consolidated_notes: str) -> str:
        """Reduce Phase: Synthesizes all partial notes into a cohesive global overview."""
        system_instruction = (
            "You are a master academic editor. You will receive a collection of partial study notes extracted from a book. "
            "Your task is to analyze them as a whole and create a single, unified, and fluid global summary. "
            "Connect related concepts, eliminate redundancies, explain the overarching narrative or learning path, "
            "and ensure everything transitions smoothly. Provide the final output in Spanish using clean Markdown formatting."
        )

        user_prompt = f"Here are the partial study notes collected from the document:\n\n{consolidated_notes}\n\nPlease generate the final global overview."

        raw_response = self.client.chat.completions.with_raw_response.create(
            model=Config.REDUCE_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        self._update_rate_limits(raw_response.headers)
        completion = raw_response.parse()
        return completion.choices[0].message.content