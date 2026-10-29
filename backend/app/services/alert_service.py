import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from backend.app.models.entities import Alert

logger = logging.getLogger("visionguard.alerts")

class AlertService:
    @staticmethod
    def create_alert(db: Session, inspection_id: int, title: str, message: str, severity: str = "High") -> Alert:
        """Create in-app alert and trigger optional SMTP email if configured."""
        alert = Alert(
            inspection_id=inspection_id,
            title=title,
            message=message,
            severity=severity,
            is_read=False
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Trigger optional email if enabled in environment
        if os.getenv("SMTP_ENABLED", "False").lower() in ["true", "1", "yes"]:
            AlertService.send_email_alert(title, message)

        # Broadcast alert to real-time WebSocket clients
        try:
            from backend.app.services.event_bus import broadcast_sync
            broadcast_sync("alert.created", {
                "id": alert.id,
                "inspection_id": alert.inspection_id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity,
            }, source="alert_service")
        except Exception:
            pass

        return alert

    @staticmethod
    def send_email_alert(subject: str, body_text: str):
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        recipient = os.getenv("ALERT_RECIPIENT_EMAIL", "")

        if not recipient or not smtp_user:
            logger.info("SMTP email credentials not fully configured; skipping email dispatch.")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient
            msg['Subject'] = f"[VisionGuard AI Alert] {subject}"
            msg.attach(MIMEText(body_text, 'plain'))

            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())
            server.quit()
            logger.info(f"Email alert sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
