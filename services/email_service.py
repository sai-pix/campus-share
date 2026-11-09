import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))


def send_email(to_email, subject, body):
    try:
        if not MAIL_USERNAME or not MAIL_PASSWORD:
            print("Email configuration is missing.")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = MAIL_USERNAME
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=20) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully!")
        return True

    except Exception as e:
        print("Email sending failed:", e)
        return False
