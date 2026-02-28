import streamlit as st
import gspread
import json
import os
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
# Ambiti (Scopes) richiesti per le API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Definizione delle intestazioni per ogni foglio del database
REQUIRED_SHEETS = {
    'Utenti': ["ID", "Email", "Nome", "Cognome", "Data_Nascita", "Luogo_Nascita", "Ruolo_Accademico", "Ruolo_Sistema"],
    'Progetti_Utenti': ["ID", "Email_Utente", "Nome_Progetto", "Codice_CUP", "Responsabile_Scientifico"],
    'Pratiche': ["ID_Pratica", "Tipo", "Email_Richiedente", "Progetto", "Oggetto", "Importo", "Stato_Attuale", "Data_Creazione", "Email_Operatore", "Note_Condivise", "JSON_Dati", "Notifica_Nota"],
    'Storico_Fasi': ["ID_Fase", "ID_Pratica", "Stato", "Data_Inizio", "Data_Fine", "Note"],
    'Allegati': ["ID", "ID_Pratica", "Nome_File", "Drive_Link", "Timestamp"],
    'Impostazioni_Sistema': ["Chiave", "Valore", "Descrizione"],
    'Template_Documenti': ["ID", "Nome", "Tipo", "Drive_Link"],
    'Configurazione_Pratiche': ["Tipo", "SLA_Giorni", "Semaforo_Arancio", "Semaforo_Rosso"]
}

def get_secret(key, default=None):
    """Accede in modo sicuro a st.secrets o env"""
    # 1. Priorità alle variabili d'ambiente
    val = os.environ.get(key)
    if val is not None:
        return val
        
    # 2. Prova st.secrets solo se il file esiste
    try:
        if os.path.exists(".streamlit/secrets.toml"):
             return st.secrets.get(key, default)
    except Exception:
        pass
        
    return default

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
        
        # 1. Recupera credenziali Service Account
        creds_info = get_secret("gcp_service_account")
        
        try:
            if creds_info:
                if isinstance(creds_info, str):
                    try:
                        creds_info = json.loads(creds_info)
                        self.creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
                    except:
                        # Se è una stringa ma non JSON, potrebbe essere il path del file
                        if os.path.exists(creds_info):
                             self.creds = Credentials.from_service_account_file(creds_info, scopes=SCOPES)
                else:
                    self.creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            
            # Fallback a GOOGLE_APPLICATION_CREDENTIALS se non trovato sopra
            if not self.creds:
                 sa_path = get_secret("GOOGLE_APPLICATION_CREDENTIALS")
                 if sa_path and os.path.exists(sa_path):
                      self.creds = Credentials.from_service_account_file(sa_path, scopes=SCOPES)

            if not self.creds:
                st.warning("Credenziali Google Service Account non trovate. Verifica .env o secrets.")
                return
            
            # Setup ID
            self.sheet_id = get_secret("GOOGLE_SHEET_ID")
            self.drive_folder_id = get_secret("GOOGLE_DRIVE_FOLDER_ID")
            
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
            if not _self.doc:
                 _self._initialize() # Tenta una ri-inizializzazione se doc è nullo
            if not _self.doc: return []
            
            try:
                sheet = _self.doc.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                # Se il foglio è uno di quelli necessari, lo creiamo con le intestazioni
                if sheet_name in REQUIRED_SHEETS:
                     new_ws = _self.doc.add_worksheet(title=sheet_name, rows="1000", cols="20")
                     new_ws.append_row(REQUIRED_SHEETS[sheet_name])
                     sheet = new_ws
                else:
                    # Se non lo trova ed è sconosciuto, prova a ricaricare il documento
                    _self.doc = _self.client.open_by_key(_self.sheet_id)
                    sheet = _self.doc.worksheet(sheet_name)
                
            return sheet.get_all_records()
        except Exception as e:
            st.error(f"Errore lettura foglio {sheet_name}: {e}")
            return []

    def append_row(self, sheet_name: str, flat_list: list):
        """Aggiunge una riga in fondo al foglio specificato."""
        try:
            if not self.doc: self._initialize()
            if not self.doc: return False
            
            try:
                sheet = self.doc.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                if sheet_name in REQUIRED_SHEETS:
                     new_ws = self.doc.add_worksheet(title=sheet_name, rows="1000", cols="20")
                     new_ws.append_row(REQUIRED_SHEETS[sheet_name])
                     sheet = new_ws
                else:
                    self.doc = self.client.open_by_key(self.sheet_id)
                    sheet = self.doc.worksheet(sheet_name)
                
            sheet.append_row(flat_list)
            # Pulizia cache per forzare il ricaricamento dei dati aggiornati
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Errore aggiunta riga su {sheet_name}: {e}")
            return False
            
    def update_cell(self, sheet_name: str, row: int, col: int, value: any):
        """Aggiorna una singola cella."""
        try:
            if not self.doc: self._initialize()
            sheet = self.doc.worksheet(sheet_name)
            sheet.update_cell(row, col, value)
            st.cache_data.clear() # Forza il refresh del frontend
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

    def delete_row_by_id(self, sheet_name: str, id_col_name: str, id_value: any) -> bool:
        """
        Elimina la riga che ha un certo ID nella colonna specificata.
        """
        try:
            if not self.doc: self._initialize()
            sheet = self.doc.worksheet(sheet_name)
            data = sheet.get_all_records()
            
            # Trova l'indice della riga (gspread usa indici 1-based, +1 per headers, +1 per list index)
            row_idx = None
            for i, row in enumerate(data):
                if str(row.get(id_col_name)) == str(id_value):
                    row_idx = i + 2 # +1 per l'intestazione, +1 perché enumerate parte da 0
                    break
            
            if row_idx:
                sheet.delete_rows(row_idx)
                st.cache_data.clear()
                return True
            return False
        except Exception as e:
            st.error(f"Errore eliminazione riga su {sheet_name}: {e}")
            return False

    # --- METODI GOOGLE DRIVE ---
    
    def _get_drive_service(self, user_creds_json: str = None):
        """Restituisce il servizio drive (User o Service Account)"""
        if user_creds_json:
            try:
                from google.oauth2.credentials import Credentials as UserCredentials
                u_creds_info = json.loads(user_creds_json)
                u_creds = UserCredentials.from_authorized_user_info(u_creds_info)
                return build('drive', 'v3', credentials=u_creds)
            except Exception as e:
                st.error(f"Errore inizializzazione credenziali utente: {e}")
        return self.drive_service

    def get_or_create_folder(self, folder_name: str, parent_id: str = None, user_creds_json: str = None) -> str:
        """Restituisce l'ID di una cartella cercandola o creandola se non esiste."""
        try:
            service = self._get_drive_service(user_creds_json)
            if not service: return None
            
            p_id = parent_id if parent_id else self.drive_folder_id
            
            # Cerca se esiste già
            query = f"name = '{folder_name}' and '{p_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            # Altrimenti crea
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [p_id] if p_id else []
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            
            # Opzionale: Permessi (anyone reader) se serve che gli altri la vedano subito
            service.permissions().create(fileId=folder.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
            
            return folder.get('id')
        except Exception as e:
            st.error(f"Errore gestione cartella {folder_name}: {e}")
            return None

    def move_item(self, item_id: str, new_parent_id: str, user_creds_json: str = None) -> bool:
        """Sposta un file o cartella in un nuovo parent."""
        try:
            service = self._get_drive_service(user_creds_json)
            if not service: return False
            
            # Recupera i parent attuali per rimuoverli
            file = service.files().get(fileId=item_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            
            # Sposta
            service.files().update(
                fileId=item_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            return True
        except Exception as e:
            st.error(f"Errore spostamento item {item_id}: {e}")
            return False

    def archive_pratica_folder(self, id_pratica: str, tipo: str, user_creds_json: str = None) -> bool:
        """Sposta la cartella della pratica nel sotto-archivio."""
        try:
            # 1. Trova/Crea folder del Tipo
            tipo_f_id = self.get_or_create_folder(tipo, user_creds_json=user_creds_json)
            # 2. Trova/Crea 'Pratiche archiviate' dentro il Tipo
            arch_f_id = self.get_or_create_folder("Pratiche archiviate", parent_id=tipo_f_id, user_creds_json=user_creds_json)
            # 3. Cerca la cartella della pratica (dovrebbe essere sotto tipo_f_id)
            pratica_f_id = self.get_or_create_folder(id_pratica, parent_id=tipo_f_id, user_creds_json=user_creds_json)
            
            if pratica_f_id:
                return self.move_item(pratica_f_id, arch_f_id, user_creds_json=user_creds_json)
            return False
        except Exception:
            return False

    def reopen_pratica_folder(self, id_pratica: str, tipo: str, user_creds_json: str = None) -> bool:
        """Sposta la cartella della pratica fuori dal sotto-archivio e la riporta nella cartella tipo."""
        try:
            # 1. Trova/Crea folder del Tipo
            tipo_f_id = self.get_or_create_folder(tipo, user_creds_json=user_creds_json)
            # 2. Trova 'Pratiche archiviate' dentro il Tipo
            arch_f_id = self.get_or_create_folder("Pratiche archiviate", parent_id=tipo_f_id, user_creds_json=user_creds_json)
            # 3. Cerca la cartella della pratica dentro l'archivio
            pratica_f_id = self.get_or_create_folder(id_pratica, parent_id=arch_f_id, user_creds_json=user_creds_json)
            
            if pratica_f_id:
                return self.move_item(pratica_f_id, tipo_f_id, user_creds_json=user_creds_json)
            return False
        except Exception:
            return False

    def upload_file(self, file_bytes: bytes, file_name: str, mimetype: str, folder_id: str = None, user_creds_json: str = None) -> str:
        """
        Carica un file su Google Drive e restituisce il WebViewLink.
        Può usare le credenziali dell'utente loggato (per evitare limiti di quota del service account).
        """
        try:
             service = self._get_drive_service(user_creds_json)
             if not service: return None
             target_folder = folder_id if folder_id else self.drive_folder_id
             
             file_metadata = {
                 'name': file_name,
                 'parents': [target_folder] if target_folder else []
             }
             
             media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=True)
             
             file = service.files().create(
                 body=file_metadata,
                 media_body=media,
                 fields='id, webViewLink'
             ).execute()
             
             # Rendi il file visibile o mantienilo ristretto (da definire)
             # Di default è accessibile solo da chi ha il link se modifichiamo i permessi
             service.permissions().create(
                 fileId=file.get('id'),
                 body={'type': 'anyone', 'role': 'reader'}
             ).execute()
             
             return file.get('webViewLink')
             
        except Exception as e:
             st.error(f"Errore upload file {file_name} su Drive: {e}")
             return None

# Istanzia un oggetto globale (Singleton)
g_api = GoogleAPI()
