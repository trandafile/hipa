import os
import sys
import json
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Carica .env
load_dotenv()

def test_connection():
    print("=== TEST GOOGLE API CONNECTION ===")
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"SHEET_ID: {sheet_id}")
    print(f"SA_PATH: {sa_path}")
    
    if not sheet_id:
        print("FAIL: GOOGLE_SHEET_ID non trovato nel .env")
        return
    
    if not sa_path:
        print("FAIL: GOOGLE_APPLICATION_CREDENTIALS non trovato nel .env")
        return
        
    if not os.path.exists(sa_path):
        print(f"FAIL: Il file {sa_path} non esiste nella directory corrente.")
        return

    try:
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        print("OK: Credenziali SA caricate correttamente.")
        
        gc = gspread.authorize(creds)
        print("OK: Client gspread autorizzato.")
        
        doc = gc.open_by_key(sheet_id)
        print(f"OK: Documento aperto: '{doc.title}'")
        
        print("\nVerifica fogli presenti:")
        worksheets = doc.worksheets()
        names = [w.title for w in worksheets]
        print(f"Fogli trovati: {names}")
        
        if "Utenti" not in names:
            print("WARNING: Foglio 'Utenti' non trovato. Provo a crearlo...")
            ws = doc.add_worksheet(title="Utenti", rows="100", cols="20")
            headers = ["ID", "Email", "Nome", "Cognome", "Data_Nascita", "Luogo_Nascita", "Ruolo_Accademico", "Ruolo_Sistema"]
            ws.append_row(headers)
            print("OK: Foglio 'Utenti' creato con intestazioni.")
        else:
            print("OK: Foglio 'Utenti' presente.")
            ws = doc.worksheet("Utenti")
            data = ws.get_all_records()
            print(f"OK: Trovate {len(data)} righe esistenti.")
            
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        print("\nSuggerimenti:")
        print("1. Verifica di aver condiviso lo Sheet con l'email del Service Account che trovi nel JSON.")
        print("2. Verifica che le API 'Google Sheets' e 'Google Drive' siano abilitate nel progetto GCP.")

if __name__ == "__main__":
    test_connection()
