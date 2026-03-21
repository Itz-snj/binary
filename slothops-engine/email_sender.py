import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("slothops.qa.email")

def send_qa_report_email(
    qa_report: dict,
    recipient_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str
) -> bool:
    """Send a formatted HTML email with the QA report summary."""
    if not recipient_email or not smtp_host:
        logger.warning("Email configuration missing. Skipping QA report email.")
        return False
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"SlothOps QA Report: PR #{qa_report.get('pr_number', 'Unknown')}"
        msg["From"] = smtp_user
        msg["To"] = recipient_email
        
        status_color = "green"
        if qa_report.get("overall_status") == "failed":
            status_color = "red"
        elif qa_report.get("overall_status") == "warning":
            status_color = "orange"
            
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: {status_color};">SlothOps QA Report</h2>
                <p><strong>PR:</strong> <a href="{qa_report.get('pr_url', '#')}">#{qa_report.get('pr_number', 'N/A')}</a></p>
                <p><strong>Repository:</strong> {qa_report.get('repo_name', 'N/A')}</p>
                <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{qa_report.get('overall_status', 'N/A').upper()}</span></p>
                
                <div style="margin-top: 20px; padding: 15px; background: #f9f9f9; border-radius: 5px;">
                    <h3>Execution Summary</h3>
                    <p style="white-space: pre-wrap;">{qa_report.get('summary', 'No summary available.')}</p>
                </div>
                
                <p style="margin-top: 30px; font-size: 0.9em; color: #777;">
                    View full details in the SlothOps Dashboard.
                </p>
            </div>
        </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        msg.attach(part)
        
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient_email, msg.as_string())
        server.quit()
        
        logger.info("Successfully sent QA report email to %s", recipient_email)
        return True
    except Exception as e:
        logger.error("Failed to send QA report email: %s", e)
        return False
