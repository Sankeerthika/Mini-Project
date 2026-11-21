import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_from = os.getenv("EMAIL_FROM")

    def send_task_assignment_email(self, to_email: str, task_title: str, deadline: str, assigned_by: str):
        subject = f"New Task Assigned: {task_title}"

        body = f"""
        <html>
        <body>
            <h2>You have been assigned a new task!</h2>
            <p><strong>Task:</strong> {task_title}</p>
            <p><strong>Deadline:</strong> {deadline}</p>
            <p><strong>Assigned by:</strong> {assigned_by}</p>
            <br>
            <p>Please log in to the AI Meeting Intelligence platform to view more details.</p>
            <p>Best regards,<br>AI Meeting Intelligence Team</p>
        </body>
        </html>
        """

        return self._send_email(to_email, subject, body)

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
                print(f"Email not configured. Skipping email to {to_email}: {subject}")
                return False

            msg = MIMEMultipart("alternative")
            msg["From"] = self.email_from
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.email_from, to_email, msg.as_string())

            print(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            return False
