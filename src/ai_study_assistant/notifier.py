import resend
from ai_study_assistant.config import Config


class EmailNotifier:
    """Utility class to send execution status emails using the Resend API."""

    @staticmethod
    def send_notification(subject: str, body: str) -> None:
        """Sends an email notification via Resend API if credentials are configured."""
        api_key = getattr(Config, "RESEND_API_KEY", None)
        to_email = getattr(Config, "NOTIFICATION_EMAIL", None)

        if not api_key or not to_email:
            print(
                " -> [Notifier Warning] Resend API key or notification email not configured. Skipping email alert."
            )
            return

        resend.api_key = api_key

        try:
            params = {
                "from": "AI Study Assistant <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body,
            }

            response = resend.Emails.send(params)
            print(
                f" -> [Notifier] Email alert sent successfully. ID: {response.get('id')}"
            )
        except Exception as e:
            print(f" -> [Notifier Error] Failed to send email alert via API: {e}")