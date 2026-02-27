import streamlit as st
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Ambiti (Scopes) richiesti per le API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleAPI:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleAPI, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inizializza le connessioni gspread e Drive API usando le credenziali"""
        self.creds = None
        self.client = None
        self.doc = None
        self.drive_service = None
        self.sheet_id = None
        self.drive_folder_id = None
        
        # Recupera credentials da st.secrets (Streamlit Cloud) o da variabili d'ambiente (Locale)
        try:
            # 1. Prova da secrets
            if "gcp_service_account" in st.secrets:
                creds_info = st.secrets["gcp_service_account"]
                self.creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            elif "GOOGLE_SERVICE_ACCOUNT_JSON" in os.environ:
                creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
                self.creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                 self.creds = Credentials.from_service_account_file(os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
            else:
                st.warning("Credenziali Google Service Account non trovate in st.secrets o .env")
                return
            
            # Setup ID
            self.sheet_id = st.secrets.get("GOOGLE_SHEET_ID") or os.environ.get("GOOGLE_SHEET_ID")
            self.drive_folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID") or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
            
            if not self.sheet_id:
                 st.warning("GOOGLE_SHEET_ID non impostato.")
                 return

            # Inizializza client
            self.client = gspread.authorize(self.creds)
            self.doc = self.client.open_by_key(self.sheet_id)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            
        except Exception as e:
            st.error(f"Errore durante l'inizializzazione delle API di Google: {e}")

    # --- METODI GOOGLE SHEETS ---

    @st.cache_data(ttl=300)
    def get_sheet_data(_self, sheet_name: str) -> list[dict]:
        """
        Scarica tutti i dati da un foglio e li restituisce come lista di dizionari.
        Usa la cache per minimizzare le letture.
        """
        try:
            if not _self.doc: return []
            sheet = _self.doc.worksheet(sheet_name)
            return sheet.get_all_records()
        except Exception as e:
            st.error(f"Errore lettura foglio {sheet_name}: {e}")
            return []

    def append_row(self, sheet_name: str, flat_list: list):
        """Aggiunge una riga in fondo al foglio specificato."""
        try:
            if not self.doc: return False
            sheet = self.doc.worksheet(sheet_name)
            sheet.append_row(flat_list)
            # Resetta le cache di lettura per questo foglio dopo un inserimento (da gestire a livello UI se necessario)
            return True
        except Exception as e:
            st.error(f"Errore aggiunta riga su {sheet_name}: {e}")
            return False
            
    def update_cell(self, sheet_name: str, row: int, col: int, value: any):
        """Aggiorna una singola cella."""
        try:
            if not self.doc: return False
            sheet = self.doc.worksheet(sheet_name)
            sheet.update_cell(row, col, value)
            return True
        except Exception as e:
            st.error(f"Errore aggiornamento cella su {sheet_name}: {e}")
            return False

    def update_row_by_id(self, sheet_name: str, id_chiave: str, value_chiave: str, new_values: dict):
         """
         Cerca una riga con un certo id e aggiorna i campi specificati in new_values (Key: col_name, Val: new_val)
         (Richiede logica custom per trovare l'indice, da implementare)
         """
         # TODO: implementare ricerca e aggiornamento puntuale in base all'ID primario.
         pass

    # --- METODI GOOGLE DRIVE ---
    
    def upload_file(self, file_bytes: bytes, file_name: str, mimetype: str, folder_id: str = None) -> str:
        """
        Carica un file su Google Drive e restituisce il WebViewLink.
        """
        try:
             if not self.drive_service: return None
             target_folder = folder_id if folder_id else self.drive_folder_id
             
             file_metadata = {
                 'name': file_name,
                 'parents': [target_folder] if target_folder else []
             }
             
             media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=True)
             
             file = self.drive_service.files().create(
                 body=file_metadata,
                 media_body=media,
                 fields='id, webViewLink'
             ).execute()
             
             # Rendi il file visibile o mantienilo ristretto (da definire)
             # Di default è accessibile solo da chi ha il link se modifichiamo i permessi
             self.drive_service.permissions().create(
                 fileId=file.get('id'),
                 body={'type': 'anyone', 'role': 'reader'}
             ).execute()
             
             return file.get('webViewLink')
             
        except Exception as e:
             st.error(f"Errore upload file {file_name} su Drive: {e}")
             return None

# Istanzia un oggetto globale (Singleton)
g_api = GoogleAPI()
