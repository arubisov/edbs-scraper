"""
PATH: ./wix-scraper/utils/
"""

import argparse
import base64
import mimetypes
import os
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.configs.config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def gmail_send_message(folder_path: Path):
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)
        mime_message = EmailMessage()

        # headers
        mime_message["To"] = settings.email_to
        mime_message["From"] = settings.email_from
        mime_message["Subject"] = settings.email_subject

        # text
        mime_message.set_content(settings.email_body)

        # attachments from the provided folder
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == ".txt":
                # guess MIME type
                type_subtype, _ = mimetypes.guess_type(str(file_path))
                if not type_subtype:
                    maintype, subtype = "application", "octet-stream"
                else:
                    maintype, subtype = type_subtype.split("/", 1)
                with open(file_path, "rb") as fp:
                    attachment_data = fp.read()
                mime_message.add_attachment(
                    attachment_data,
                    maintype,
                    subtype,
                    filename=file_path.name,
                )

        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"Message Id: {send_message['id']}")
    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
    return send_message


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a Gmail draft with every file in a folder as attachments"
    )
    parser.add_argument(
        "folder",
        type=str,
        help="Path to the folder containing attachments",
    )
    args = parser.parse_args()

    folder_path = Path(args.folder)
    if not folder_path.is_dir():
        parser.error(f"{folder_path!r} is not a valid directory")

    gmail_send_message(folder_path)
