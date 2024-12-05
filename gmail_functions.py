from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email import message_from_bytes
import os
from typing import Optional


# Load credentials from `credentials.json`
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDS_FILE = "token.json"

def authenticate_gmail():
    creds = Credentials.from_authorized_user_file(CREDS_FILE, SCOPES)
    return build('gmail', 'v1', credentials=creds)

from email import message_from_bytes
import base64

def decode_email_body(payload):
    """Decode email body from Base64 format."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'body' in part:
                body = part['body'].get('data', '')
                return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
    elif 'body' in payload and 'data' in payload['body']:
        body = payload['body']['data']
        return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
    return "No content available"

def search_gmail(query: str, max_results: int = 5):
    """Search Gmail and fetch full email content."""
    service = authenticate_gmail()

    # Step 1: Fetch list of matching messages
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    email_data = []

    # Step 2: Fetch full content for each email
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()

        # Extract headers and body
        headers = {header['name']: header['value'] for header in msg['payload']['headers']}
        body = decode_email_body(msg['payload'])

        # Append full email data
        email_data.append({
            "id": message['id'],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "body": body
        })

    return email_data

from email.mime.text import MIMEText
import base64

def create_reply_email(to_email, subject, message_body, in_reply_to_id, cc=None, bcc=None):
    """Create a MIME email message for replying with CC and BCC."""
    from email.mime.text import MIMEText
    message = MIMEText(message_body)
    message['to'] = to_email
    message['subject'] = f"Re: {subject}"
    message['In-Reply-To'] = in_reply_to_id
    message['References'] = in_reply_to_id

    if cc:
        message['cc'] = cc
    if bcc:
        message['bcc'] = bcc

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}


def send_email_reply(service, reply_message):
    """Send the email reply using the Gmail API."""
    try:
        message = service.users().messages().send(userId='me', body=reply_message).execute()
        return message
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def modify_email_labels(service, email_id, add_labels=None, remove_labels=None):
    """Add or remove labels from an email."""
    body = {}
    if add_labels:
        body['addLabelIds'] = add_labels
    if remove_labels:
        body['removeLabelIds'] = remove_labels

    return service.users().messages().modify(userId='me', id=email_id, body=body).execute()

def star_email(service, email_id):
    """Star an email."""
    return modify_email_labels(service, email_id, add_labels=['STARRED'])

def snooze_email(service, email_id, snoozed_label_id):
    """Snooze an email by applying the Snoozed label."""
    return modify_email_labels(service, email_id, add_labels=[snoozed_label_id])

def mark_email(service, email_id, as_read=False, as_important=False):
    """Mark an email as read, important, or unread."""
    add_labels = []
    remove_labels = []

    if as_read:
        remove_labels.append('UNREAD')
    if not as_read:
        add_labels.append('UNREAD')
    if as_important:
        add_labels.append('IMPORTANT')

    return modify_email_labels(service, email_id, add_labels=add_labels, remove_labels=remove_labels)


from email.mime.text import MIMEText
import base64

def create_email(to_email: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None):
    """Create an email with optional CC and BCC."""
    # Create a plain-text email message
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject

    # Add optional CC and BCC fields
    if cc:
        message['cc'] = cc
    if bcc:
        message['bcc'] = bcc

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

scheduler = BackgroundScheduler()
scheduler.start()

def schedule_email(service, to_email: str, subject: str, body: str, send_time: datetime, cc: Optional[str] = None, bcc: Optional[str] = None):
    """Schedule an email to be sent at a specific time."""
    def send_email_job():
        email_message = create_email(to_email, subject, body, cc=cc, bcc=bcc)
        service.users().messages().send(userId='me', body=email_message).execute()
        print(f"Email sent to {to_email} at {datetime.now()}")

    # Schedule the email using APScheduler
    scheduler.add_job(
        send_email_job,
        'date',
        run_date=send_time
    )


def create_label(service, label_name):
    """Create a new label in Gmail."""
    label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    return service.users().labels().create(userId='me', body=label).execute()


def get_all_labels(service):
    """Retrieve all labels for the authenticated user."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    return labels

