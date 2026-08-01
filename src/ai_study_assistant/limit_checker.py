import requests
from ai_study_assistant.config import Config


class APILimitChecker:
    """Utility class to inspect API keys, rate limits, and model contexts."""

    @staticmethod
    def check_openrouter_status() -> bool:
        """Inspects OpenRouter balance, daily quota, and configured model specifications."""
        if not Config.OPENROUTER_API_KEY:
            print(" -> [Limit Checker] OpenRouter API Key is not set.")
            return False

        url = "https://openrouter.ai/api/v1/auth/key"
        models_url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {Config.OPENROUTER_API_KEY}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json().get("data", {})
                label = data.get("label", "Key")
                usage = data.get("usage", 0)
                is_free = data.get("is_free_tier", False)
                rate_limit_info = data.get("rate_limit", {})
                daily_limit = rate_limit_info.get(
                    "requests_per_day", "Dynamic / Free Tier"
                )

                print(f" Valid OpenRouter Key ('{label}')")
                print(f"   ├─ Accumulated Usage : ${usage:.4f} USD")
                print(f"   ├─ Is Free Tier?     : {is_free}")
                print(f"   └─ Daily Requests    : {daily_limit}")

                # Model Context Checks
                models_to_check = [
                    Config.OPENROUTER_VISION_MODEL,
                    Config.OPENROUTER_TEXT_MODEL,
                ]
                models_res = requests.get(models_url, timeout=10)
                if models_res.status_code == 200:
                    available_models = {
                        m["id"]: m for m in models_res.json().get("data", [])
                    }
                    print("   +-- Configured OpenRouter Models Specs:")
                    for model_id in models_to_check:
                        if model_id in available_models:
                            ctx = available_models[model_id].get(
                                "context_length", "N/A"
                            )
                            print(
                                f"       ├─ {model_id}: Max Context = {ctx:,} tokens"
                            )
                        elif model_id == "openrouter/free":
                            print(
                                f"       ├─ {model_id}: Dynamic Router (Routes to free visual models)"
                            )
                        else:
                            print(f"       ├─ {model_id}: Dynamic or custom slug")
                return True
            elif response.status_code == 429:
                print(" -> [OpenRouter Warning] 429 Rate limit exceeded on key.")
                return False
            else:
                print(
                    f" -> Error checking OpenRouter Key ({response.status_code}): {response.text}"
                )
                return False
        except Exception as e:
            print(f" -> Failed to verify OpenRouter: {e}")
            return False

    @staticmethod
    def check_groq_status() -> bool:
        """Pings Groq API to retrieve TPM and TPD limits."""
        if not Config.GROQ_API_KEY:
            print(" -> [Limit Checker] Groq API Key is not set.")
            return False

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": Config.MODEL_NAME,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            h = response.headers

            if response.status_code == 200:
                tpm_remaining = h.get("x-ratelimit-remaining-tokens", "N/A")
                tpm_limit = h.get("x-ratelimit-limit-tokens", "N/A")
                tpd_remaining = h.get(
                    "x-ratelimit-remaining-tokens-day",
                    h.get("x-ratelimit-remaining-day", "Dynamic"),
                )

                print(" Groq API Active")
                print(
                    f"   ├─ Tokens Per Minute (TPM) : {tpm_remaining} / {tpm_limit}"
                )
                print(f"   └─ Daily Status (TPD)      : {tpd_remaining}")
                return True
            elif response.status_code == 429:
                print(" -> [Groq Warning] Rate limit reached (429).")
                return False
            else:
                print(
                    f" -> Error checking Groq Key ({response.status_code}): {response.text}"
                )
                return False
        except Exception as e:
            print(f" -> Failed to verify Groq: {e}")
            return False

    @classmethod
    def verify_all_services(cls) -> bool:
        """Runs validation against all configured API providers."""
        print("\n=== CHECKING PROVIDERS STATUS AND QUOTAS ===\n")
        groq_ok = cls.check_groq_status()
        print("-" * 52)
        or_ok = cls.check_openrouter_status()
        print("-" * 52)
        return groq_ok and or_ok