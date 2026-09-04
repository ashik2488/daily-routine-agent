import subprocess
import requests
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from database import get_settings, log_notification

def send_windows_toast(title: str, message: str, sound: bool = True):
    """
    Sends a native Windows Toast notification using PowerShell WinRT API.
    """
    clean_title = title.replace('"', '`"').replace("'", "''")
    clean_message = message.replace('"', '`"').replace("'", "''")
    
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @"
    <toast duration="long">
        <visual>
            <binding template="ToastGeneric">
                <text hint-maxLines="1">{clean_title}</text>
                <text>{clean_message}</text>
                <text placement="attribution">Daily Routine Agent</text>
            </binding>
        </visual>
        <audio src="ms-winsoundevent:Notification.Default" />
    </toast>
"@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Daily Routine Agent")
    $notifier.Show($toast)
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=8
        )
        return True
    except Exception as e:
        print(f"Error triggering Windows toast: {e}")
        return False

def send_email_notification(recipient_str: str, subject: str, body_text: str):
    """
    Sends a styled HTML and Plaintext email notification via SMTP.
    Supports single email or comma-separated multiple emails.
    """
    settings = get_settings()
    sender = settings.get('email_sender') or 'ashikchowdhury2488@gmail.com'
    password = settings.get('email_smtp_password', '') or os.environ.get('ROUTINE_SMTP_PASSWORD', '')
    host = settings.get('email_smtp_host', 'smtp.gmail.com')
    port = int(settings.get('email_smtp_port', '587'))

    if not recipient_str:
        return False, "Recipient email address is missing."
    if not password:
        return False, "SMTP Password / App Password is missing in settings."

    # Parse recipients (support multiple comma-separated)
    recipients = [r.strip() for r in recipient_str.split(",") if r.strip()]
    if not recipients:
        return False, "No valid recipient email provided."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 {subject}"
        msg["From"] = f"Daily Routine Agent <{sender}>"
        msg["To"] = ", ".join(recipients)

        text_part = MIMEText(body_text, "plain")
        formatted_body = body_text.replace("\n", "<br>")
        current_time_str = datetime.now().strftime("%I:%M %p")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
            .card {{ max-width: 550px; margin: 0 auto; background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }}
            .header {{ background: linear-gradient(135deg, #6366f1, #a855f7); padding: 20px; text-align: center; color: white; font-weight: bold; font-size: 20px; }}
            .body {{ padding: 24px; color: #e2e8f0; line-height: 1.6; font-size: 15px; }}
            .alert-box {{ background: #0f172a; border-left: 4px solid #6366f1; padding: 12px 16px; border-radius: 6px; margin: 15px 0; font-size: 14px; white-space: pre-line; }}
            .footer {{ background: #0f172a; padding: 12px; text-align: center; color: #64748b; font-size: 12px; border-top: 1px solid #334155; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              🤖 Daily Routine Agent Alert
            </div>
            <div class="body">
              <h3 style="margin-top: 0; color: #38bdf8;">{subject}</h3>
              <div class="alert-box">
                {formatted_body}
              </div>
              <p style="color: #94a3b8; font-size: 13px; margin-top: 20px;">
                Generated automatically by your Daily Routine System at {current_time_str}.
              </p>
            </div>
            <div class="footer">
              Daily Routine Agent • Sent to {", ".join(recipients)}
            </div>
          </div>
        </body>
        </html>
        """
        html_part = MIMEText(html_content, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()

        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
        return True, f"Email successfully delivered to {', '.join(recipients)}."
    except Exception as e:
        print(f"Error sending email: {e}")
        return False, str(e)

def send_discord_notification(webhook_url: str, title: str, message: str):
    if not webhook_url:
        return False
    try:
        payload = {
            "embeds": [
                {
                    "title": f"🔔 {title}",
                    "description": message,
                    "color": 0x4F46E5,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "Daily Routine Agent"}
                }
            ]
        }
        res = requests.post(webhook_url, json=payload, timeout=5)
        return res.status_code in [200, 204]
    except Exception as e:
        print(f"Error sending Discord notification: {e}")
        return False

def send_telegram_notification(bot_token: str, chat_id: str, title: str, message: str):
    if not bot_token or not chat_id:
        return False
    try:
        text = f"<b>🔔 {title}</b>\n\n{message}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        res = requests.post(url, json=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return False

def notify(title: str, message: str, category: str = "general"):
    settings = get_settings()
    
    # 1. Windows Toast
    if settings.get('enable_windows_toast', 'true').lower() == 'true':
        send_windows_toast(title, message, sound=(settings.get('enable_audio_chime', 'true').lower() == 'true'))
        log_notification(title, message, "Windows Toast")

    # 2. Email Notification
    if settings.get('enable_email_notifications', 'true').lower() == 'true':
        recipient = settings.get('email_recipient')
        password = settings.get('email_smtp_password', '') or os.environ.get('ROUTINE_SMTP_PASSWORD', '')
        if recipient and password:
            success, err_msg = send_email_notification(recipient, title, message)
            log_notification(title, message, "Email", status="sent" if success else f"failed: {err_msg}")

    # 3. Discord Webhook
    discord_url = settings.get('discord_webhook_url')
    if discord_url:
        send_discord_notification(discord_url, title, message)
        log_notification(title, message, "Discord")

    # 4. Telegram Bot
    tg_token = settings.get('telegram_bot_token')
    tg_chat = settings.get('telegram_chat_id')
    if tg_token and tg_chat:
        send_telegram_notification(tg_token, tg_chat, title, message)
        log_notification(title, message, "Telegram")
