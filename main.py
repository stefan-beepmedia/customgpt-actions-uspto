from fastapi import FastAPI, HTTPException
from gmail_functions import *
from pydantic import BaseModel
from typing import Optional



app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to Gmail Search GPT Backend"}

@app.get("/search/")
def search_emails(query: str, max_results: int = 5):
    """Search for emails and return full content."""
    try:
        emails = search_gmail(query, max_results)
        if not emails:
            return {"message": "No emails found."}

        return {"emails": emails}
    except Exception as e:
        print(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail="Failed to search emails")

class ReplyEmailRequest(BaseModel):
    email_id: str
    message_body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None

@app.post("/reply/")
def reply_to_email(reply_request: ReplyEmailRequest):
    """Reply to a specific email."""
    try:
        service = authenticate_gmail()
        
        # Fetch the original email details
        email = service.users().messages().get(userId='me', id=reply_request.email_id, format='metadata').execute()
        headers = {header['name']: header['value'] for header in email['payload']['headers']}
        
        # Extract necessary fields
        to_email = headers.get('From')  # Reply to the sender
        subject = headers.get('Subject', "No Subject")
        thread_id = email.get('threadId')

        # Create reply message
        reply_message = create_reply_email(
            to_email=to_email,
            subject=subject,
            message_body=reply_request.message_body,
            thread_id=thread_id
        )
        
        # Send the email
        response = send_email_reply(service, reply_message)
        return {"message": "Reply sent successfully", "response": response}
    
    except Exception as e:
        print(f"Error replying to email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email reply")
    

@app.post("/star/")
def star_email_endpoint(email_id: str):
    """Star an email."""
    try:
        service = authenticate_gmail()
        response = star_email(service, email_id)
        return {"message": "Email starred successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starring email: {e}")



@app.post("/snooze/")
def snooze_email_endpoint(email_id: str):
    """Snooze an email by applying the Snoozed label."""
    try:
        service = authenticate_gmail()

        # Check for Snoozed label
        labels = get_all_labels(service)
        snoozed_label = next((label for label in labels if label['name'] == "Snoozed"), None)

        # Create label if it doesn't exist
        if not snoozed_label:
            snoozed_label = create_label(service, "Snoozed")
            print(f"Created Snoozed label: {snoozed_label['id']}")

        # Apply the Snoozed label
        response = snooze_email(service, email_id, snoozed_label['id'])
        return {"message": "Email snoozed successfully", "response": response}

    except Exception as e:
        print(f"Error snoozing email: {e}")
        raise HTTPException(status_code=500, detail=f"Error snoozing email: {e}")


@app.post("/mark/")
def mark_email_endpoint(email_id: str, as_read: bool = False, as_important: bool = False):
    """Mark an email as read, important, or unread."""
    try:
        service = authenticate_gmail()
        response = mark_email(service, email_id, as_read=as_read, as_important=as_important)
        return {"message": "Email updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking email: {e}")



@app.post("/schedule/")
def schedule_email_endpoint(to_email: str, subject: str, body: str, send_time: str, cc: Optional[str] = None, bcc: Optional[str] = None):
    """Schedule an email to be sent at a specific time."""
    try:
        service = authenticate_gmail()
        send_time = datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S")
        schedule_email(service, to_email, subject, body, send_time, cc=cc, bcc=bcc)
        return {"message": f"Email scheduled to {to_email} at {send_time}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling email: {e}")
