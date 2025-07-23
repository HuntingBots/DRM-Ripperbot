import os
import mimetypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = config.GOOGLE_CREDENTIALS
FOLDER_ID = config.GOOGLE_FOLDER_ID

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

def upload_file(file_path: str, filename: str = None) -> str:
    if not filename:
        filename = os.path.basename(file_path)

    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }

    mime_type, _ = mimetypes.guess_type(file_path)

    from googleapiclient.http import MediaFileUpload
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    return uploaded_file.get("webViewLink")
