import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Use explicit path for .env since this script is for temporary debug
# But actually let's just parse the .env manually if needed or set it here
sa_name = "credenziali-bot.json"
folder_id = "19PjYZA3sfm1Z_FwH7snGumUpE536wUwi"

if not os.path.exists(sa_name):
    print(f"ERRORE: File '{sa_name}' non trovato nella directory corrente.")
else:
    with open(sa_name, 'r') as f:
        creds_dict = json.load(f)
        
    print(f"Service Account Email: {creds_dict.get('client_email')}")
    print(f"Target Folder ID: {folder_id}")
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
    drive_service = build('drive', 'v3', credentials=creds)
    
    try:
        folder = drive_service.files().get(fileId=folder_id, fields='id, name').execute()
        print(f"SUCCESS: Folder Found! Name: {folder.get('name')}")
    except Exception as e:
        print(f"FAILURE: Access error: {e}")
