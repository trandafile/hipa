import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

# OAuth 2.0 Scopes per leggere le info dell'utente (Email, Nome, ecc.)
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

def init_oauth_flow():
    """Inizializza il flusso OAuth 2.0 usando st.secrets o le variabili d'ambiente"""
    # 1. Recupero Client Config
    client_config = None
    if "gcp_oauth_client" in st.secrets:
        client_config = st.secrets["gcp_oauth_client"]
    elif "GOOGLE_OAUTH_CLIENT_JSON" in os.environ:
         client_config = json.loads(os.environ["GOOGLE_OAUTH_CLIENT_JSON"])
    else:
        # Fallback manuale per sviluppo locale leggendo le singole variabili
        client_id = st.secrets.get("GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET")
        if client_id and client_secret:
             client_config = {
                "web": {
                    "client_id": client_id,
                    "project_id": "hipa-ticketing",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                }
             }

    if not client_config:
        st.error("Configurazione OAuth (Client ID o file JSON) mancante.")
        return None

    redirect_uri = st.secrets.get("GOOGLE_REDIRECT_URI") or os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow

def login_button():
    """Genera il bottone di Login per avviare il flusso OAuth."""
    flow = init_oauth_flow()
    if not flow: return

    auth_url, _ = flow.authorization_url(prompt='consent')
    st.markdown(f'''
        <a href="{auth_url}" target="_self">
            <button style="
                background-color: #4285F4;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                font-family: sans-serif;
            ">
                Accedi con Google
            </button>
        </a>
    ''', unsafe_allow_html=True)

def handle_oauth_callback():
    """Gesisce il ritorno da Google con il codice di autorizzazione nell'URL."""
    if 'code' in st.query_params:
        code = st.query_params['code']
        # Rimuoviamo il codice dall'URL per non rifare il login se l'utente ricarica
        # Streamlit 1.30+ usa query_params.clear() o delete()
        del st.query_params['code']
        
        flow = init_oauth_flow()
        if not flow: return
        
        try:
             # Recuperiamo il token
             flow.fetch_token(code=code)
             creds = flow.credentials
             
             # Chiamiamo l'API 'userinfo' per ottenere nome ed email
             user_info_service = build('oauth2', 'v2', credentials=creds)
             user_info = user_info_service.userinfo().get().execute()
             
             st.session_state['user_email'] = user_info.get('email')
             st.session_state['user_given_name'] = user_info.get('given_name')
             st.session_state['user_family_name'] = user_info.get('family_name')
             st.session_state['logged_in'] = True
             
             st.rerun() # Forza il ridisegno della UI ora che l'utente è loggato
             
        except Exception as e:
             st.error(f"Errore durante l'autenticazione OAuth: {e}")

def check_login():
    """Controlla se l'utente è loggato. Se no, mostra il bottone."""
    if st.session_state.get('logged_in', False):
        return True
    
    st.title("Sistema di Ticketing Amministrativo Universitario (HipA)")
    st.write("Esegui l'accesso con il tuo account istituzionale Google per continuare.")
    
    handle_oauth_callback() # Controlla se siamo appena tornati da Google
    login_button() # Se non lo siamo o il token è scaduto, mostra il bottone
    
    return False

def logout():
    """Effettua il logout pulendo lo stato."""
    for key in ['logged_in', 'user_email', 'user_given_name', 'user_family_name', 'user_role']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
