import html
import re

import requests

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class BrevoEmailBackend(BaseEmailBackend):
    """
    Django email backend that sends messages through
    Brevo's HTTPS transactional email API.
    """

    api_url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not settings.BREVO_API_KEY:
            if self.fail_silently:
                return 0

            raise RuntimeError(
                "BREVO_API_KEY is not configured."
            )

        sent_count = 0

        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
        }

        for message in email_messages:

            if not message.recipients():
                continue

            sender_email = (
                settings.BREVO_SENDER_EMAIL
                or settings.DEFAULT_FROM_EMAIL
            )

            sender_name = settings.BREVO_SENDER_NAME

            text_content = message.body

            html_content = self._build_html_content(
                message.subject,
                message.body
            )

            data = {
                "sender": {
                    "name": sender_name,
                    "email": sender_email,
                },

                "to": [
                    {
                        "email": recipient,
                    }
                    for recipient in message.recipients()
                ],

                "subject": message.subject,

                "textContent": text_content,

                "htmlContent": html_content,
            }

            try:

                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=30,
                )

                response.raise_for_status()

                sent_count += 1

            except requests.RequestException:

                if self.fail_silently:
                    continue

                raise

        return sent_count

    @staticmethod
    def _build_html_content(subject, body):
        """
        Build a simple branded HTML email.

        Reset-password emails receive a clickable
        Reset Password button.
        """

        escaped_subject = html.escape(
            subject or "ScoreSkill"
        )

        escaped_body = html.escape(
            body or ""
        )

        # -----------------------------------------------------
        # LOOK FOR A RESET PASSWORD URL
        # -----------------------------------------------------

        reset_match = re.search(
            r"https?://[^\s<]+/password-reset/[^\s<]+",
            body or ""
        )

        reset_url = (
            reset_match.group(0)
            if reset_match
            else None
        )

        # -----------------------------------------------------
        # REMOVE THE RAW RESET URL FROM THE HTML BODY
        # -----------------------------------------------------

        if reset_url:

            escaped_url = html.escape(
                reset_url,
                quote=True
            )

            escaped_body = escaped_body.replace(
                escaped_url,
                ""
            )

        # -----------------------------------------------------
        # PRESERVE LINE BREAKS
        # -----------------------------------------------------

        escaped_body = escaped_body.replace(
            "\r\n",
            "\n"
        )

        escaped_body = escaped_body.replace(
            "\n",
            "<br>"
        )

        # -----------------------------------------------------
        # RESET BUTTON
        # -----------------------------------------------------

        reset_button = ""

        if reset_url:

            safe_url = html.escape(
                reset_url,
                quote=True
            )

            reset_button = f"""
                <div style="text-align:center;margin:30px 0;">
                    <a
                        href="{safe_url}"
                        style="
                            display:inline-block;
                            padding:12px 24px;
                            background:#4f46e5;
                            color:#ffffff;
                            text-decoration:none;
                            border-radius:8px;
                            font-weight:600;
                            font-size:15px;
                        "
                    >
                        Reset Password
                    </a>
                </div>
            """

        # -----------------------------------------------------
        # FINAL HTML EMAIL
        # -----------------------------------------------------

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{escaped_subject}</title>
</head>

<body
    style="
        margin:0;
        padding:0;
        background:#f8fafc;
        font-family:Arial,Helvetica,sans-serif;
        color:#1e293b;
    "
>

    <div
        style="
            max-width:600px;
            margin:30px auto;
            background:#ffffff;
            border-radius:12px;
            overflow:hidden;
            box-shadow:0 4px 18px rgba(0,0,0,0.08);
        "
    >

        <!-- HEADER -->

        <div
            style="
                background:#4f46e5;
                padding:24px;
                text-align:center;
            "
        >

            <div
                style="
                    color:#ffffff;
                    font-size:24px;
                    font-weight:700;
                "
            >
                ScoreSkill
            </div>

            <div
                style="
                    color:#e0e7ff;
                    font-size:13px;
                    margin-top:5px;
                "
            >
                AI Powered Learning
            </div>

        </div>


        <!-- CONTENT -->

        <div
            style="
                padding:30px;
                font-size:15px;
                line-height:1.7;
            "
        >

            <h2
                style="
                    margin-top:0;
                    color:#0f172a;
                "
            >
                {escaped_subject}
            </h2>

            <div>
                {escaped_body}
            </div>

            {reset_button}

        </div>


        <!-- FOOTER -->

        <div
            style="
                padding:18px 30px;
                background:#f8fafc;
                color:#64748b;
                font-size:12px;
                text-align:center;
            "
        >
            ScoreSkill · AI Powered Learning
        </div>

    </div>

</body>
</html>
"""
    