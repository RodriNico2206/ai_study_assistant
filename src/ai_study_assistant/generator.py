import base64
import re
import time
from io import BytesIO
from PIL import Image
from groq import Groq, RateLimitError
from ai_study_assistant.config import Config


class NotesGenerator:
    """Class responsible for interacting with GroqCloud to generate and reduce study notes."""

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
                self.last_remaining_tpd = int(remaining_tpd)
                print(
                    f"       [Rate Limit Monitor] Available TPD tokens: {self.last_remaining_tpd:,}"
                )
        except Exception:
            pass

    def _execute_with_rate_limit_protection(
            self, api_call_func, estimated_tokens: int = 4000
        ) -> str:
            """Executes API calls with pre-check safeguard and automatic 429 error retry handling."""
            # 1. PRE-CHECK: If we know remaining quota is lower than estimated request cost
            if (
                self.last_remaining_tpd is not None
                and self.last_remaining_tpd < estimated_tokens
            ):
                needed = estimated_tokens - self.last_remaining_tpd
                # Estimate wait time based on continuous regeneration (~140 tokens/min) + safety buffer
                estimated_wait = int((needed / 140) * 60) + 15
                print(
                    f"\n -> [Pre-check Safeguard] Remaining tokens ({self.last_remaining_tpd:,}) lower than required estimate ({estimated_tokens:,})."
                )
                print(
                    f" -> Pausing execution for ~{estimated_wait} seconds to regenerate quota..."
                )
                time.sleep(estimated_wait)

            # 2. RETRY LOOP: Catch 429 errors if the API rejects the request
            while True:
                try:
                    raw_response = api_call_func()
                    self._update_rate_limits(raw_response.headers)
                    completion = raw_response.parse()
                    return completion.choices[0].message.content

                except RateLimitError as e:
                    error_str = str(e)
                    wait_seconds = 60  # Fallback sleep time

                    # Extract exact wait time requested by Groq from error message (e.g., '17m36.672s' or '30.912s.')
                    match = re.search(r"Please try again in\s+([0-9m.s]+)", error_str)
                    if match:
                        time_str = match.group(1).rstrip(".")
                        if "m" in time_str:
                            parts = time_str.replace("s", "").split("m")
                            m_val = int(parts[0])
                            s_str = parts[1].strip(".") if len(parts) > 1 and parts[1] else "0"
                            s_val = int(float(s_str)) if s_str else 0
                            wait_seconds = m_val * 60 + s_val
                        elif "s" in time_str:
                            s_str = time_str.replace("s", "").strip(".")
                            wait_seconds = int(float(s_str)) if s_str else 60

                    wait_seconds += 10  # Safety buffer
                    print(
                        f"\n -> [Rate Limit Hit] Quota exceeded. Auto-pausing execution for {wait_seconds} seconds..."
                    )
                    time.sleep(wait_seconds)
                    print(" -> [Rate Limit Safeguard] Resuming execution...")

    def generate_summary(
        self, chapter_text: str, custom_instructions: str = ""
    ) -> str:
        """Map Phase: Sends a pure text chunk to Groq requesting structured study notes."""
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

        def api_call():
            return self.client.chat.completions.with_raw_response.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

        return self._execute_with_rate_limit_protection(
            api_call, estimated_tokens=1000
        )

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

        def api_call():
            return self.client.chat.completions.with_raw_response.create(
                model=Config.VISION_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )

        return self._execute_with_rate_limit_protection(
            api_call, estimated_tokens=4000
        )

    def reduce_summaries(self, consolidated_notes: str) -> str:
        """Reduce Phase: Synthesizes all partial notes into a cohesive global overview."""
        system_instruction = (
            "You are a master academic editor. You will receive a collection of partial study notes extracted from a book. "
            "Your task is to analyze them as a whole and create a single, unified, and fluid global summary. "
            "Connect related concepts, eliminate redundancies, explain the overarching narrative or learning path, "
            "and ensure everything transitions smoothly. Provide the final output in Spanish using clean Markdown formatting."
        )

        user_prompt = f"Here are the partial study notes collected from the document:\n\n{consolidated_notes}\n\nPlease generate the final global overview."

        def api_call():
            return self.client.chat.completions.with_raw_response.create(
                model=Config.REDUCE_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
            )

        return self._execute_with_rate_limit_protection(
            api_call, estimated_tokens=2000
        )